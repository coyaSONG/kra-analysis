"""
Canonical principal types for the policy module.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PolicyLimits:
    """Normalized limits carried with an authenticated principal."""

    rate_limit_per_minute: int | None = None
    daily_request_limit: int | None = None


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    """Normalized caller identity for routers and services."""

    principal_id: str
    subject_id: str
    owner_ref: str
    credential_id: str
    display_name: str | None
    auth_method: str
    permissions: frozenset[str]
    limits: PolicyLimits
    is_environment_key: bool = False

