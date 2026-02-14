import pytest
from httpx import ASGITransport, AsyncClient

import main_v2


@pytest.mark.asyncio
@pytest.mark.unit
async def test_lifespan_without_background_tasks():
    """Verify the app starts fine with background task runner."""
    transport = ASGITransport(app=main_v2.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/health")
        assert r.status_code == 200
