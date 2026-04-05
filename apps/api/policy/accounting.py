"""
Usage accounting seam for the policy module.
"""

from dataclasses import dataclass
from typing import Any

import structlog

from models.database_models import UsageEvent
from policy.principal import AuthenticatedPrincipal

logger = structlog.get_logger()


@dataclass(frozen=True, slots=True)
class UsageReservation:
    """Reserved usage record captured at authorization time."""

    principal_id: str
    owner_ref: str
    credential_id: str
    action: str
    units: int


class UsageAccountant:
    """Reserve and persist append-only usage events."""

    async def reserve(
        self, principal: AuthenticatedPrincipal, action: str, units: int = 1
    ) -> UsageReservation:
        return UsageReservation(
            principal_id=principal.principal_id,
            owner_ref=principal.owner_ref,
            credential_id=principal.credential_id,
            action=action,
            units=units,
        )

    async def commit(
        self,
        reservation: UsageReservation,
        *,
        request_id: str | None,
        method: str | None,
        path: str | None,
        status_code: int,
        error_detail: str | None = None,
        metadata: dict[str, Any] | None = None,
        session_factory: Any,
    ) -> None:
        outcome = "success" if status_code < 400 else "error"
        async with session_factory() as session:
            event = UsageEvent(
                principal_id=reservation.principal_id,
                owner_ref=reservation.owner_ref,
                credential_id=reservation.credential_id,
                action=reservation.action,
                units=reservation.units,
                outcome=outcome,
                status_code=status_code,
                request_id=request_id,
                method=method,
                path=path,
                error_detail=error_detail,
                event_metadata=metadata or {},
            )
            session.add(event)
            await session.commit()

    async def commit_request(
        self,
        request: Any,
        *,
        status_code: int,
        error_detail: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        reservation = getattr(request.state, "usage_reservation", None)
        if reservation is None:
            return

        session_factory = getattr(request.app.state, "db_session_factory", None)
        if session_factory is None:
            logger.warning("Usage accounting skipped; db session factory missing")
            return

        request_id = getattr(request.state, "request_id", None) or request.headers.get(
            "X-Request-ID"
        )
        await self.commit(
            reservation,
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            error_detail=error_detail,
            metadata=metadata,
            session_factory=session_factory,
        )
