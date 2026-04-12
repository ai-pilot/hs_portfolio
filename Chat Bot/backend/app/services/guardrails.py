"""
Guardrails service — lightweight custom guardrails.
NeMo Guardrails config is in app/guardrails/ for reference and can be
integrated when deploying with the full nemoguardrails server.

For the portfolio demo, we use a fast custom guardrails layer that handles:
- Prompt injection detection
- PII detection and redaction
- Topic boundary enforcement
- Input sanitization
- Rate limiting per session
"""

import re
import time
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# --- PII Patterns ---
PII_PATTERNS = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    "email_address": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "phone_intl": re.compile(r"\b\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b"),
    "ip_address": re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
}

# --- Jailbreak Patterns ---
JAILBREAK_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)", re.I),
    re.compile(r"you\s+are\s+now\s+(DAN|a\s+new|an?\s+unrestricted)", re.I),
    re.compile(r"pretend\s+(you'?re|to\s+be|you\s+are)\s+(a|an)\s+(?!helpful)", re.I),
    re.compile(r"(system\s*prompt|reveal|show)\s*(your|the)\s*(instructions|prompt|system)", re.I),
    re.compile(r"jailbreak|bypass\s+(filter|safety|guardrail)", re.I),
    re.compile(r"do\s+anything\s+now", re.I),
    re.compile(r"act\s+as\s+if\s+you\s+have\s+no\s+(restrictions|rules|limits)", re.I),
    re.compile(r"disregard\s+(your|all|any)\s+(programming|training|rules)", re.I),
]

# --- Blocked Topics ---
BLOCKED_TOPIC_PATTERNS = [
    re.compile(r"\b(kill|murder|attack|bomb|weapon|gun|shoot|explod)\w*\b", re.I),
    re.compile(r"\b(drug|narcotic|cocaine|heroin|meth)\w*\b", re.I),
    re.compile(r"\b(porn|xxx|nsfw|nude|naked|sex\s+scene)\w*\b", re.I),
    re.compile(r"\b(hack\s+into|steal\s+data|ddos|exploit\s+vulnerab)\w*\b", re.I),
]

# --- Rate Limiting ---
_rate_limits: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 30  # requests per window


class GuardrailResult:
    def __init__(self, passed: bool, message: str = "", category: str = ""):
        self.passed = passed
        self.message = message
        self.category = category


def check_input(text: str, session_id: str = "default") -> GuardrailResult:
    """Run all input guardrails. Returns GuardrailResult."""

    # 1. Input length check
    if len(text) > 4000:
        return GuardrailResult(
            False,
            "Your message is a bit too long for me to process. Could you shorten it a bit? I work best with concise questions.",
            "length",
        )

    if len(text.strip()) == 0:
        return GuardrailResult(False, "Looks like an empty message! What would you like to know?", "empty")

    # 2. Rate limiting
    now = time.time()
    _rate_limits[session_id] = [
        t for t in _rate_limits[session_id] if now - t < RATE_LIMIT_WINDOW
    ]
    if len(_rate_limits[session_id]) >= RATE_LIMIT_MAX:
        return GuardrailResult(
            False,
            "You're sending messages faster than I can keep up! Let's slow down a bit — try again in a minute.",
            "rate_limit",
        )
    _rate_limits[session_id].append(now)

    # 3. Jailbreak detection
    for pattern in JAILBREAK_PATTERNS:
        if pattern.search(text):
            logger.warning(f"Jailbreak attempt detected from session {session_id}")
            return GuardrailResult(
                False,
                "Nice try, but this train stays on its tracks! 🛤️ I'm here to help you learn about Himanshu's work and analyze your documents. What can I help you with?",
                "jailbreak",
            )

    # 4. Blocked topics
    for pattern in BLOCKED_TOPIC_PATTERNS:
        if pattern.search(text):
            return GuardrailResult(
                False,
                "That topic is a bit off my route! I'm best at discussing Himanshu's experience, AI/ML, and analyzing documents. Want to explore any of those?",
                "blocked_topic",
            )

    # 5. PII detection (warn, don't block)
    pii_found = []
    for pii_type, pattern in PII_PATTERNS.items():
        if pattern.search(text):
            pii_found.append(pii_type)

    if pii_found:
        logger.info(f"PII detected in input: {pii_found}")
        # Don't block, but the response will note it
        return GuardrailResult(
            True,
            f"⚠️ I noticed what looks like personal information ({', '.join(pii_found)}) in your message. For your privacy, consider not sharing sensitive data in chat.",
            "pii_warning",
        )

    return GuardrailResult(True)


def redact_pii_in_output(text: str) -> str:
    """Redact any PII that might appear in bot output."""
    for pii_type, pattern in PII_PATTERNS.items():
        if pii_type == "email_address":
            # Don't redact Himanshu's public email
            text = re.sub(
                r"\b(?!surihimanshu9@gmail\.com)[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                "[EMAIL REDACTED]",
                text,
            )
        elif pii_type == "phone_intl":
            # Don't redact Himanshu's public phone
            text = text  # Keep as-is since CV phone is public
        else:
            text = pattern.sub(f"[{pii_type.upper()} REDACTED]", text)
    return text


def check_output(text: str) -> GuardrailResult:
    """Run output guardrails on bot response."""
    # Check for system prompt leakage
    system_leak_patterns = [
        re.compile(r"(my\s+)?system\s+prompt\s+(is|says|reads)", re.I),
        re.compile(r"I\s+was\s+instructed\s+to", re.I),
        re.compile(r"my\s+instructions\s+(are|say|tell)", re.I),
    ]

    for pattern in system_leak_patterns:
        if pattern.search(text):
            return GuardrailResult(
                False,
                "I want to make sure I give you a helpful response. Could you rephrase your question?",
                "system_leak",
            )

    return GuardrailResult(True)
