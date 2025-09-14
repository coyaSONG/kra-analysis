"""
Lightweight integration tests for top-level main_v2 endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_root_endpoint(client: AsyncClient):
    r = await client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["service"]
    assert "endpoints" in data

