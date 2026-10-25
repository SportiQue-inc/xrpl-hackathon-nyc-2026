"""HTTP hardening: CORS allow-list, rate limit, security headers, and an access record of every
state-changing call (who, which route, result) in the hash-chained event log."""
from __future__ import annotations

import hashlib
import os
import threading
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")


def cors_origins() -> list[str]:
    """Exact origins only (comma separated). Empty = same-origin only; '*' is never accepted."""
    raw = os.environ.get("AGENTRAIL_CORS_ORIGINS", "")
    return [o.strip() for o in raw.split(",") if o.strip() and o.strip() != "*"]


class SecurityHeaders(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        resp = await call_next(request)
        h = resp.headers
        if request.url.path.startswith("/apps/demo/"):
            # The before/after stage frames its own two static pages (no data); same origin only.
            h.setdefault("X-Frame-Options", "SAMEORIGIN")
            h.setdefault("Content-Security-Policy", CSP.replace("frame-ancestors 'none'", "frame-ancestors 'self'"))
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Referrer-Policy", "no-referrer")
        h.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        h.setdefault("Content-Security-Policy", CSP)
        h.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        if request.url.path.startswith("/api/"):
            h["Cache-Control"] = "no-store"
        if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
            h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return resp


_HITS: dict[str, deque] = defaultdict(deque)
_HITS_LOCK = threading.Lock()


def reset_rate_limits():
    with _HITS_LOCK:
        _HITS.clear()


class RateLimit(BaseHTTPMiddleware):
    """Sliding window per client: login routes per IP, everything else per token (or IP)."""

    def __init__(self, app, per_min: int | None = None, login_per_min: int | None = None):
        super().__init__(app)
        self.per_min = per_min or int(os.environ.get("AGENTRAIL_RATE_PER_MIN", "600"))
        self.login_per_min = login_per_min or int(os.environ.get("AGENTRAIL_LOGIN_RATE_PER_MIN", "30"))
        self.hits, self.lock = _HITS, _HITS_LOCK

    def _key(self, request) -> tuple[str, int]:
        ip = request.client.host if request.client else "?"
        path = request.url.path
        if path.startswith(("/api/auth/", "/api/dev/login")):
            return f"login|{ip}", self.login_per_min
        auth = request.headers.get("authorization", "")
        who = hashlib.sha256(auth.encode()).hexdigest()[:16] if auth else ip
        return f"api|{who}", self.per_min

    async def dispatch(self, request, call_next):
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        key, limit = self._key(request)
        now = time.monotonic()
        with self.lock:
            q = self.hits[key]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= limit:
                retry = int(60 - (now - q[0])) + 1
                return JSONResponse({"detail": "rate limit exceeded"}, status_code=429,
                                    headers={"Retry-After": str(retry)})
            q.append(now)
        return await call_next(request)


class AccessAudit(BaseHTTPMiddleware):
    """Every non-GET API call becomes an `access` event: actor (token subject), route, status."""

    def __init__(self, app, get_store):
        super().__init__(app)
        self.get_store = get_store

    async def dispatch(self, request, call_next):
        resp = await call_next(request)
        if request.method != "GET" and request.url.path.startswith("/api/"):
            claims = getattr(request.state, "claims", None) or {}
            route = request.scope.get("route")
            try:
                store = self.get_store()
                if store is not None:
                    store.log(claims.get("sub", "anonymous"), "access",
                              f"{request.method} {getattr(route, 'path', request.url.path)} -> {resp.status_code}",
                              {"role": claims.get("role"), "path": request.url.path, "status": resp.status_code})
            except Exception:
                pass
        return resp
