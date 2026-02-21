from unittest.mock import AsyncMock

import pytest

from services.result_collection_service import ResultNotFoundError


@pytest.mark.asyncio
@pytest.mark.unit
async def test_collect_result_success(monkeypatch, authenticated_client):
    async def fake_collect_result(*args, **kwargs):
        return {
            "race_id": "20240719_1_1",
            "race_date": "20240719",
            "meet": 1,
            "race_no": 1,
            "result": [1, 2, 3],
        }

    monkeypatch.setattr(
        "routers.collection_v2.result_collection_service.collect_result",
        AsyncMock(side_effect=fake_collect_result),
    )

    response = await authenticated_client.post(
        "/api/v2/collection/result",
        json={"date": "20240719", "meet": 1, "race_number": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"][0]["race_id"] == "20240719_1_1"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_collect_result_not_found_maps_to_404(monkeypatch, authenticated_client):
    monkeypatch.setattr(
        "routers.collection_v2.result_collection_service.collect_result",
        AsyncMock(side_effect=ResultNotFoundError("result missing")),
    )

    response = await authenticated_client.post(
        "/api/v2/collection/result",
        json={"date": "20240719", "meet": 1, "race_number": 1},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "result missing"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_collect_result_unexpected_error_maps_to_500(
    monkeypatch, authenticated_client
):
    monkeypatch.setattr(
        "routers.collection_v2.result_collection_service.collect_result",
        AsyncMock(side_effect=RuntimeError("boom")),
    )

    response = await authenticated_client.post(
        "/api/v2/collection/result",
        json={"date": "20240719", "meet": 1, "race_number": 1},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "boom"
