import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_jobs_empty(authenticated_client: AsyncClient):
    resp = await authenticated_client.get("/api/v2/jobs/?limit=10&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert "jobs" in data and isinstance(data["jobs"], list)
    assert "total" in data and isinstance(data["total"], int)
