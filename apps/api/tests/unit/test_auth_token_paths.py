from datetime import timedelta

import pytest

from dependencies.auth import create_access_token, get_current_user, verify_token


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_current_user_no_header(db_session):
    user = await get_current_user(authorization=None, db=db_session)
    assert user is None


@pytest.mark.unit
def test_verify_token_expired():
    token = create_access_token({"sub": "u"}, expires_delta=timedelta(seconds=-1))
    assert verify_token(token) is None
