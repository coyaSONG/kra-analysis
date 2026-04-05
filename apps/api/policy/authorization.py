"""
Action-level authorization rules.
"""

from typing import Literal

from fastapi import HTTPException, status

from policy.principal import AuthenticatedPrincipal

PolicyAction = Literal[
    "collection.collect",
    "collection.collect_async",
    "collection.status.read",
    "collection.result.collect",
    "jobs.list",
    "jobs.read",
    "jobs.cancel",
]


class PolicyAuthorizer:
    """Authorize a principal for a named action."""

    _required_permissions: dict[PolicyAction, frozenset[str]] = {
        "collection.collect": frozenset({"write"}),
        "collection.collect_async": frozenset({"write"}),
        "collection.status.read": frozenset({"read"}),
        "collection.result.collect": frozenset({"write"}),
        "jobs.list": frozenset({"read"}),
        "jobs.read": frozenset({"read"}),
        "jobs.cancel": frozenset({"write"}),
    }

    async def authorize(
        self,
        principal: AuthenticatedPrincipal,
        action: PolicyAction,
    ) -> None:
        required = self._required_permissions.get(action, frozenset())
        if required and not required.issubset(principal.permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
