from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from config import settings
from dependencies import auth as auth_dep
from dependencies.auth import (
    APIKeyBackendError,
    AuthenticatedPrincipal,
    check_resource_access,
    create_access_token,
    get_current_user,
    require_action,
    require_api_key,
    require_api_key_record,
    require_permissions,
    require_principal,
    verify_api_key,
    verify_token,
)
from models.database_models import APIKey as DBAPIKey
from models.database_models import Job
from policy.principal import PolicyLimits


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_api_key_env_valid(db_session):
    # test_settings fixture seeds valid_api_keys with test keys
    key = (
        settings.valid_api_keys[0]
        if settings.valid_api_keys
        else "test-api-key-123456789"
    )
    api_key_obj = await verify_api_key(key, db_session)
    assert api_key_obj is not None
    assert api_key_obj.is_active is True


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_api_key_invalid_format(db_session):
    key = "bad"  # too short, invalid format
    api_key_obj = await verify_api_key(key, db_session)
    assert api_key_obj is None


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_require_api_key_missing_raises(db_session):
    with pytest.raises(HTTPException) as ex:
        await require_api_key(x_api_key=None, api_key=None, db=db_session)
    assert ex.value.status_code == 401


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_require_principal_returns_normalized_principal(db_session):
    key_value = "principal-key-12345"
    keyrow = DBAPIKey(
        key=key_value,
        name="principal-user",
        is_active=True,
        permissions=["read", "write"],
    )
    db_session.add(keyrow)
    await db_session.commit()

    principal = await require_principal(
        x_api_key=key_value,
        api_key=None,
        api_key_obj=keyrow,
    )

    assert isinstance(principal, AuthenticatedPrincipal)
    assert principal.owner_ref == key_value
    assert principal.credential_id == key_value
    assert principal.permissions == frozenset({"read", "write"})


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_require_permissions_allow_and_forbid(db_session):
    principal = AuthenticatedPrincipal(
        principal_id="api_key:k1",
        subject_id="tester",
        owner_ref="k1",
        credential_id="k1",
        display_name="tester",
        auth_method="api_key",
        permissions=frozenset({"read", "write"}),
        limits=PolicyLimits(),
    )

    ok = await require_permissions(["write"], principal=principal)
    assert ok is principal

    with pytest.raises(HTTPException) as ex:
        await require_permissions(["admin"], principal=principal)
    assert ex.value.status_code == 403


@pytest.mark.asyncio
@pytest.mark.unit
async def test_require_action_sets_request_state(monkeypatch):
    principal = AuthenticatedPrincipal(
        principal_id="api_key:test-key",
        subject_id="test-key",
        owner_ref="test-key",
        credential_id="test-key",
        display_name="tester",
        auth_method="api_key",
        permissions=frozenset({"jobs.list"}),
        limits=PolicyLimits(),
    )
    reservation = SimpleNamespace(action="jobs.list", units=1)
    request = SimpleNamespace(state=SimpleNamespace())

    async def fake_authorize(_principal, _action):
        return None

    async def fake_reserve(_principal, _action):
        return reservation

    monkeypatch.setattr(auth_dep._policy_authorizer, "authorize", fake_authorize)
    monkeypatch.setattr(auth_dep._usage_accountant, "reserve", fake_reserve)

    dependency = require_action("jobs.list")
    result = await dependency(request=request, principal=principal)

    assert result is principal
    assert request.state.principal is principal
    assert request.state.policy_action == "jobs.list"
    assert request.state.usage_reservation is reservation


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_jwt_token_and_current_user(db_session):
    token = create_access_token({"sub": "user-1"}, expires_delta=timedelta(seconds=60))
    payload = verify_token(token)
    assert payload is not None and payload.get("sub") == "user-1"

    user = await get_current_user(authorization=f"Bearer {token}", db=db_session)
    assert user is not None and user.get("sub") == "user-1"


@pytest.mark.unit
def test_verify_token_invalid_returns_none():
    assert verify_token("not-a-jwt") is None


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_require_api_key_daily_limit_exceeded(db_session):
    # Create a DB key that is not in env valid_api_keys
    blocked_key = "BLOCKEDKEY12345"
    from models.database_models import APIKey as DBAPIKey

    keyrow = DBAPIKey(
        key=blocked_key,
        name="blocked",
        is_active=True,
        daily_limit=1,
        today_requests=2,
        last_used_at=datetime.now(UTC),
        permissions=["read"],
    )
    db_session.add(keyrow)
    await db_session.commit()

    with pytest.raises(HTTPException) as ex:
        await require_api_key(x_api_key=blocked_key, api_key=None, db=db_session)
    assert ex.value.status_code == 429


@pytest.mark.asyncio
@pytest.mark.unit
async def test_require_api_key_backend_error_returns_503(monkeypatch, db_session):
    async def boom(_api_key, _db):
        raise APIKeyBackendError("db down")

    monkeypatch.setattr("dependencies.auth.verify_api_key", boom)

    with pytest.raises(HTTPException) as ex:
        await require_api_key_record(
            x_api_key="test-api-key-12345", api_key=None, db=db_session
        )

    assert ex.value.status_code == 503


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_resource_access_paths(db_session):
    admin_principal = AuthenticatedPrincipal(
        principal_id="api_key:adm",
        subject_id="admin",
        owner_ref="adm",
        credential_id="adm",
        display_name="admin",
        auth_method="api_key",
        permissions=frozenset({"admin"}),
        limits=PolicyLimits(),
    )
    assert (
        await check_resource_access("race", "rid", admin_principal, db_session) is True
    )

    reader_principal = AuthenticatedPrincipal(
        principal_id="api_key:r1",
        subject_id="reader",
        owner_ref="r1",
        credential_id="r1",
        display_name="reader",
        auth_method="api_key",
        permissions=frozenset({"read"}),
        limits=PolicyLimits(),
    )
    assert (
        await check_resource_access("race", "rid", reader_principal, db_session) is True
    )

    owner_name = "creator"
    job = Job(type="collection", status="pending", parameters={}, created_by=owner_name)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    owner_principal = AuthenticatedPrincipal(
        principal_id="api_key:own",
        subject_id="own",
        owner_ref="own",
        credential_id="own",
        display_name=owner_name,
        auth_method="api_key",
        permissions=frozenset({"read"}),
        limits=PolicyLimits(),
    )
    assert (
        await check_resource_access("job", job.job_id, owner_principal, db_session)
        is True
    )
