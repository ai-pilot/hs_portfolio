"""
Security middleware — origin verification and IP-based daily rate limiting.
"""

import time
import logging
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = logging.getLogger(__name__)

# IP -> list of timestamps for the current day
_ip_requests: dict[str, list[float]] = defaultdict(list)
_current_day: str = ""


def _get_client_ip(request: Request) -> str:
    """Extract real client IP, respecting proxy headers."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _reset_if_new_day():
    """Clear all counters at midnight UTC."""
    global _current_day, _ip_requests
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if today != _current_day:
        _ip_requests.clear()
        _current_day = today


class RateLimitMiddleware(BaseHTTPMiddleware):
    """IP-based daily rate limit — only applies to /api/chat and /api/upload."""

    async def dispatch(self, request: Request, call_next):
        # Only rate-limit API endpoints that cost money (LLM / embedding calls)
        if request.url.path not in ("/api/chat", "/api/upload"):
            return await call_next(request)

        # Allow preflight CORS requests through
        if request.method == "OPTIONS":
            return await call_next(request)

        _reset_if_new_day()

        ip = _get_client_ip(request)
        count = len(_ip_requests[ip])

        if count >= settings.daily_ip_limit:
            logger.warning(f"Daily limit reached for IP {ip} ({count}/{settings.daily_ip_limit})")
            return Response(
                content='{"detail":"Daily request limit reached. Please try again tomorrow."}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": "86400"},
            )

        _ip_requests[ip].append(time.time())
        return await call_next(request)


class OriginCheckMiddleware(BaseHTTPMiddleware):
    """Reject non-browser / unknown-origin requests to API endpoints."""

    # Endpoints that don't need origin check
    OPEN_PATHS = {"/api/health", "/api/suggestions"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/") and request.url.path not in self.OPEN_PATHS:
            # Allow preflight
            if request.method == "OPTIONS":
                return await call_next(request)

            origin = request.headers.get("origin", "")
            referer = request.headers.get("referer", "")

            # Allow requests proxied from our own Node server (no origin header)
            if not origin and request.client and request.client.host == "127.0.0.1":
                return await call_next(request)

            # In production, require valid origin
            allowed = settings.cors_origins
            if "http://localhost" not in origin and origin not in allowed:
                # Also check referer as fallback
                if not any(referer.startswith(a) for a in allowed):
                    logger.warning(f"Blocked request from origin={origin} referer={referer}")
                    return Response(
                        content='{"detail":"Unauthorized origin."}',
                        status_code=403,
                        media_type="application/json",
                    )

        return await call_next(request)
