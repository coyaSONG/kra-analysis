"""
Extended unit tests for authentication and authorization to improve coverage.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi import HTTPException, status

from dependencies import auth as auth_dep
from models.database_models import APIKey, Job, Prediction


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.asyncio
async def test_verify_api_key_from_env(monkeypatch, db_session):
    """Verify that keys coming from settings.valid_api_keys are accepted."""
    key = "env-key-abcdef1234"

    # Patch settings.valid_api_keys
    monkeypatch.setattr(auth_dep, "settings", type("S", (), {
        "valid_api_keys": [key],
        "access_token_expire_minutes": 30,
        "secret_key": "test-secret",
        "algorithm": "HS256"
    })())

    result = await auth_dep.verify_api_key(key, db_session)
    assert result is not None
    assert result.key == key
    assert result.is_active is True
    assert set(result.permissions or []) >= {"read", "write"}


@pytest.mark.unit
@pytest.mark.auth
@pytest.mark.asyncio
async def test_require_api_key_daily_limit_exceeded(db_session):
    """Exceed the daily limit and expect 429 from require_api_key."""
    api_key_value = "daily-limit-key-123456"

    api_key = APIKey(
        key=api_key_value,
        name="DailyLimitUser",
        is_active=True,
        daily_limit=5,
        today_requests=5,  # verify_api_key will increment to 6
        created_at=datetime.utcnow(),
    )
    db_session.add(api_key)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await auth_dep.require_api_key(api_key=api_key_value, db=db_session)

    assert exc.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "Daily request limit" in exc.value.detail


@pytest.mark.unit
def test_verify_token_valid_and_invalid(monkeypatch):
    """Validate verify_token for valid, expired, and malformed tokens."""
    # Minimal settings for token operations
    monkeypatch.setattr(auth_dep, "settings", type("S", (), {
        "secret_key": "test-secret",
        "algorithm": "HS256",
        "access_token_expire_minutes": 30,
    })())

    # Valid token
    token_valid = auth_dep.create_access_token({"sub": "user-1"})
    payload = auth_dep.verify_token(token_valid)
    assert payload is not None and payload.get("sub") == "user-1"

    # Expired token
    expired = auth_dep.jwt.encode(
        {"sub": "user-1", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        auth_dep.settings.secret_key,
        algorithm=auth_dep.settings.algorithm,
    )
    assert auth_dep.verify_token(expired) is None

    # Malformed token
    assert auth_dep.verify_token("not-a-jwt") is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_current_user(monkeypatch, db_session):
    """get_current_user returns payload for Bearer token, None otherwise."""
    monkeypatch.setattr(auth_dep, "settings", type("S", (), {
        "secret_key": "test-secret",
        "algorithm": "HS256",
        "access_token_expire_minutes": 30,
    })())

    token = auth_dep.create_access_token({"sub": "tester"})
    user = await auth_dep.get_current_user(authorization=f"Bearer {token}", db=db_session)
    assert user is not None and user.get("sub") == "tester"

    assert await auth_dep.get_current_user(authorization=None, db=db_session) is None
    assert await auth_dep.get_current_user(authorization="Bearer invalid", db=db_session) is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_require_permissions_allow_and_deny(db_session):
    """require_permissions allows when permission present and denies when missing."""
    api_key = APIKey(
        key="perm-key-123456",
        name="PermUser",
        is_active=True,
        permissions=["read"],
        created_at=datetime.utcnow(),
    )

    # When permission is present
    allowed = await auth_dep.require_permissions(["read"], api_key, db_session)
    assert allowed is api_key

    # When permission is missing
    with pytest.raises(HTTPException) as exc:
        await auth_dep.require_permissions(["admin"], api_key, db_session)
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_resource_access_paths(db_session):
    # race: requires read permission
    api_key = APIKey(key="k1-1234567890", name="u1", is_active=True, permissions=["read"]) 
    assert await auth_dep.check_resource_access("race", "r1", api_key, db_session) is True

    # job: only creator can access
    job = Job(type="collection", status="completed", parameters={}, created_by="u1")
    db_session.add(job)
    await db_session.commit()
    assert await auth_dep.check_resource_access("job", job.job_id, api_key, db_session) is True

    # prediction: existence implies accessible (until created_by field exists)
    pred = Prediction(prediction_id="p1", race_id="r1", prompt_id="t", predicted_positions=[1,2,3])
    db_session.add(pred)
    await db_session.commit()
    assert await auth_dep.check_resource_access("prediction", "p1", api_key, db_session) is True
