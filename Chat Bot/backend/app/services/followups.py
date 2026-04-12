"""
Generate contextual follow-up suggestions based on conversation topic.
Lightweight — no LLM call, just keyword matching for speed.
"""

import re

# Topic -> follow-up suggestions
TOPIC_FOLLOWUPS = {
    "experience": [
        "What AI tools does he use?",
        "Tell me about his DAMAC projects",
        "What industries has he worked in?",
    ],
    "skills": [
        "How does he use LangChain?",
        "What about RAG systems?",
        "Does he do MLOps?",
    ],
    "education": [
        "What was his GPA?",
        "What did he study?",
        "Any certifications?",
    ],
    "rag": [
        "How does he handle guardrails?",
        "What vector databases does he use?",
        "Explain the chunking strategy",
    ],
    "damac": [
        "What team does he lead?",
        "What AI solutions did he build there?",
        "What's the tech stack at DAMAC?",
    ],
    "agent": [
        "How does multi-agent work?",
        "What frameworks does he use?",
        "Any real-world agent examples?",
    ],
    "data": [
        "Show summary statistics",
        "What are the correlations?",
        "Describe the columns",
    ],
    "upload": [
        "Summarize this document",
        "What are the key points?",
        "Any action items in this?",
    ],
}

# Keyword -> topic mapping
KEYWORD_MAP = {
    r"experience|career|work|job|role": "experience",
    r"skill|tech|stack|tool|framework": "skills",
    r"education|degree|university|school|gpa": "education",
    r"rag|retrieval|vector|embedding|chunk": "rag",
    r"damac|dubai|current": "damac",
    r"agent|multi.agent|langgraph|orchestrat": "agent",
    r"data|csv|excel|statistic|column|correlat": "data",
}

DEFAULT_FOLLOWUPS = [
    "What are his core skills?",
    "Tell me about his projects",
    "Upload a document to analyze",
]


def generate_followups(user_message: str, bot_response: str, has_upload: bool = False) -> list[str]:
    """Return 2-3 contextual follow-up suggestions."""
    if has_upload:
        return TOPIC_FOLLOWUPS["upload"]

    combined = f"{user_message} {bot_response}".lower()

    for pattern, topic in KEYWORD_MAP.items():
        if re.search(pattern, combined):
            return TOPIC_FOLLOWUPS[topic]

    return DEFAULT_FOLLOWUPS
