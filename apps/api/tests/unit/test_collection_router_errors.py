import pytest


@pytest.mark.asyncio
@pytest.mark.unit
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
    assert r.status_code == 502
    data = r.json()
    assert data["detail"]["message"] == "All requested races failed to collect"
    assert data["detail"]["errors"][0]["race_no"] == 1
