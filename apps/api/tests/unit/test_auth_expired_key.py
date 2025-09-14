from datetime import UTC, datetime, timedelta

import pytest

from dependencies.auth import verify_api_key
from models.database_models import APIKey as DBAPIKey


@pytest.mark.asyncio
async def test_verify_api_key_expired_returns_none(db_session):
    key = "EXPIREDKEY12345"
    expired = DBAPIKey(
        key=key,
        name="expired",
        is_active=True,
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    db_session.add(expired)
    await db_session.commit()

    res = await verify_api_key(key, db_session)
    assert res is None
