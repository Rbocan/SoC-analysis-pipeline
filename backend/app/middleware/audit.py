"""Audit logging middleware — records every mutating API call."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog

logger = structlog.get_logger()

_SKIP_PATHS = {"/api/health", "/api/docs", "/api/redoc", "/api/openapi.json"}
_AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        if request.method in _AUDIT_METHODS and not any(request.url.path.startswith(p) for p in _SKIP_PATHS):
            logger.info(
                "api_call",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                client=request.client.host if request.client else "unknown",
            )

        return response
