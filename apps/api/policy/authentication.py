"""
Principal creation logic for API key backed callers.
"""

from models.database_models import APIKey
from policy.principal import AuthenticatedPrincipal, PolicyLimits


class PrincipalAuthenticator:
    """Build principals from validated credentials."""

    def authenticate_api_key(
        self, presented_key: str, api_key_obj: APIKey, *, is_environment_key: bool
    ) -> AuthenticatedPrincipal:
        owner_ref = presented_key
        principal_id = (
            f"env:{presented_key}" if is_environment_key else f"api_key:{presented_key}"
        )
        permissions = frozenset(api_key_obj.permissions or [])
        return AuthenticatedPrincipal(
            principal_id=principal_id,
            subject_id=owner_ref,
            owner_ref=owner_ref,
            credential_id=presented_key,
            display_name=api_key_obj.name,
            auth_method="api_key",
            permissions=permissions,
            limits=PolicyLimits(
                rate_limit_per_minute=api_key_obj.rate_limit,
                daily_request_limit=api_key_obj.daily_limit,
            ),
            is_environment_key=is_environment_key,
        )

