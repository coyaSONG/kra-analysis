"""The public collection request boundary supports physical Yeongcheon code 4."""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from models.collection_dto import CollectionRequest, ResultCollectionRequest
from models.race_dto import CollectRaceRequest


@pytest.mark.parametrize(
    "model,extra",
    [
        (CollectRaceRequest, {"race_no": 1}),
        (CollectionRequest, {"race_numbers": [1]}),
        (ResultCollectionRequest, {"race_number": 1}),
    ],
)
@pytest.mark.parametrize("meet", [1, 2, 3, 4])
def test_collection_requests_accept_all_documented_venues(model, extra, meet):
    request = model.model_validate({"date": "20260101", "meet": meet, **extra})
    assert request.meet == meet
    assert model.model_json_schema()["properties"]["meet"]["maximum"] == 4


@pytest.mark.parametrize(
    "model,extra",
    [
        (CollectRaceRequest, {"race_no": 1}),
        (CollectionRequest, {"race_numbers": [1]}),
        (ResultCollectionRequest, {"race_number": 1}),
    ],
)
@pytest.mark.parametrize("meet", [0, 5])
def test_collection_requests_reject_unsupported_venues(model, extra, meet):
    with pytest.raises(ValidationError) as error:
        model.model_validate({"date": "20260101", "meet": meet, **extra})
    assert any(item["loc"] == ("meet",) for item in error.value.errors())


@pytest.mark.asyncio
async def test_collection_route_passes_yeongcheon_identity_unchanged(
    monkeypatch, authenticated_client
):
    import routers.collection_v2 as router

    observed = []

    async def collect_batch(payload, *, db):
        observed.append(payload)
        return SimpleNamespace(status="success", message="collected", data=[])

    monkeypatch.setattr(
        router.collection_module.commands, "collect_batch", collect_batch
    )
    response = await authenticated_client.post(
        "/api/v2/collection/",
        json={"date": "20260101", "meet": 4, "race_numbers": [1]},
    )
    assert response.status_code == 200
    assert len(observed) == 1
    assert observed[0].meet == 4
    assert observed[0].race_date == "20260101"
    assert observed[0].race_numbers == [1]
