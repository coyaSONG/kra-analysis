from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException

from config import settings
from dependencies.auth import (
    check_resource_access,
    create_access_token,
    get_current_user,
    require_api_key,
    require_permissions,
    verify_api_key,
    verify_token,
)
from models.database_models import APIKey as DBAPIKey
from models.database_models import Job


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
async def test_verify_api_key_invalid_format(db_session):
    key = "bad"  # too short, invalid format
    api_key_obj = await verify_api_key(key, db_session)
    assert api_key_obj is None


@pytest.mark.asyncio
async def test_require_api_key_missing_raises(db_session):
    with pytest.raises(HTTPException) as ex:
        await require_api_key(x_api_key=None, api_key=None, db=db_session)
    assert ex.value.status_code == 401


@pytest.mark.asyncio
async def test_require_permissions_allow_and_forbid(db_session):
    # Prepare API key object with write permission
    api_key_obj = DBAPIKey(
        key="k1",
        name="tester",
        is_active=True,
        permissions=["read", "write"],
    )
    db_session.add(api_key_obj)
    await db_session.commit()

    # Allowed
    ok = await require_permissions(["write"], api_key_obj=api_key_obj, db=db_session)
    assert ok is not None

    # Forbidden
    with pytest.raises(HTTPException) as ex:
        await require_permissions(["admin"], api_key_obj=api_key_obj, db=db_session)
    assert ex.value.status_code == 403


@pytest.mark.asyncio
async def test_jwt_token_and_current_user(db_session):
    token = create_access_token({"sub": "user-1"}, expires_delta=timedelta(seconds=60))
    payload = verify_token(token)
    assert payload is not None and payload.get("sub") == "user-1"

    user = await get_current_user(authorization=f"Bearer {token}", db=db_session)
    assert user is not None and user.get("sub") == "user-1"


def test_verify_token_invalid_returns_none():
    assert verify_token("not-a-jwt") is None


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
        last_used_at=datetime.utcnow(),
        permissions=["read"],
    )
    db_session.add(keyrow)
    await db_session.commit()

    with pytest.raises(HTTPException) as ex:
        await require_api_key(x_api_key=blocked_key, api_key=None, db=db_session)
    assert ex.value.status_code == 429


@pytest.mark.asyncio
async def test_check_resource_access_paths(db_session):
    # Admin path
    admin_key = DBAPIKey(key="adm", name="admin", is_active=True, permissions=["admin"])
    assert await check_resource_access("race", "rid", admin_key, db_session) is True

    # Race read path
    reader_key = DBAPIKey(key="r1", name="reader", is_active=True, permissions=["read"])
    assert await check_resource_access("race", "rid", reader_key, db_session) is True

    # Job owner path
    owner_name = "creator"
    job = Job(type="collection", status="pending", parameters={}, created_by=owner_name)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    owner_key = DBAPIKey(
        key="own", name=owner_name, is_active=True, permissions=["read"]
    )
    assert await check_resource_access("job", job.job_id, owner_key, db_session) is True
