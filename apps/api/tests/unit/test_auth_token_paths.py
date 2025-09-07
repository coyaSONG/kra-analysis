import pytest
from datetime import timedelta

from dependencies.auth import get_current_user, create_access_token, verify_token


@pytest.mark.asyncio
async def test_get_current_user_no_header(db_session):
    user = await get_current_user(authorization=None, db=db_session)
    assert user is None


def test_verify_token_expired():
    token = create_access_token({'sub': 'u'}, expires_delta=timedelta(seconds=-1))
    assert verify_token(token) is None

