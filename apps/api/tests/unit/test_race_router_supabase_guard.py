import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from routers import race as race_router


@pytest.mark.asyncio
@pytest.mark.unit
async def test_race_collect_returns_503_when_supabase_not_configured():
    app = FastAPI()
    app.include_router(race_router.router, prefix="/races")
    app.dependency_overrides[race_router.get_supabase_client] = lambda: None

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/races/collect", json={"date": "20240719", "meet": 1})
        assert response.status_code == 503


@pytest.mark.asyncio
@pytest.mark.unit
async def test_race_list_returns_503_when_supabase_not_configured():
    app = FastAPI()
    app.include_router(race_router.router, prefix="/races")
    app.dependency_overrides[race_router.get_supabase_client] = lambda: None

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/races/20240719")
        assert response.status_code == 503
