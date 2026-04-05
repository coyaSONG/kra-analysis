"""
Policy accounting middleware.
"""

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware

from policy.accounting import UsageAccountant

logger = structlog.get_logger()


class PolicyAccountingMiddleware(BaseHTTPMiddleware):
    """Persist append-only usage events after a policy-guarded request completes."""

    def __init__(self, app):
        super().__init__(app)
        self._accountant = UsageAccountant()

    async def dispatch(self, request, call_next):
        if not getattr(request.state, "request_id", None):
            request.state.request_id = str(uuid.uuid4())

        response = None
        error_detail = None
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:
            error_detail = str(exc)
            raise
        finally:
            if response is not None and not response.headers.get("X-Request-ID"):
                response.headers["X-Request-ID"] = request.state.request_id

            try:
                await self._accountant.commit_request(
                    request,
                    status_code=status_code,
                    error_detail=error_detail,
                )
            except Exception as exc:
                logger.warning("Usage accounting commit failed", error=str(exc))
