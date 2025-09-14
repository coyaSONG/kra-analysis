import pytest


@pytest.mark.asyncio
async def test_collect_race_error_returns_500(monkeypatch, authenticated_client):
    # Patch service to raise inside route handler
    import services.collection_service as cs

    class Boom(Exception): ...

    async def boom(*args, **kwargs):
        raise Boom("fail")

    monkeypatch.setattr(cs.CollectionService, "collect_race_data", boom)

    r = await authenticated_client.post(
        "/api/v2/collection/", json={"date": "20240719", "meet": 1, "race_numbers": [1]}
    )
    # Route logs error per race but continues; success with zero collected
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "Collected" in data["message"]
