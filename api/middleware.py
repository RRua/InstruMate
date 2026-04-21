"""API key authentication middleware.

If INSTRUMATE_API_KEY is set, requires X-API-Key header on all /api/ requests
(except /api/health). If not set, passes through (backward compatible).
"""

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Optional API key authentication for /api/ endpoints."""

    EXEMPT_PATHS = {"/api/health"}

    async def dispatch(self, request: Request, call_next):
        api_key = os.environ.get("INSTRUMATE_API_KEY", "")
        if not api_key:
            return await call_next(request)

        path = request.url.path
        if not path.startswith("/api/") and path != "/api":
            return await call_next(request)
        if path in self.EXEMPT_PATHS:
            return await call_next(request)

        provided = request.headers.get("X-API-Key", "")
        if provided != api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"},
            )

        return await call_next(request)
