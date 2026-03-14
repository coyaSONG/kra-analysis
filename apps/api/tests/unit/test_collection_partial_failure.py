from unittest.mock import AsyncMock, Mock

import pytest

from models.database_models import DataStatus
from services.collection_service import CollectionService
from services.kra_api_service import KRAAPIService


@pytest.fixture
def mock_kra_api_service():
    mock = Mock(spec=KRAAPIService)
    mock.get_race_info = AsyncMock(
        return_value={
            "response": {
                "header": {"resultCode": "00", "resultMsg": "OK"},
                "body": {
                    "items": {
                        "item": [
                            {
                                "hrNo": "001",
                                "hrName": "Horse 1",
                                "jkNo": "J001",
                                "trNo": "T001",
                            },
                            {
                                "hrNo": "002",
                                "hrName": "Horse 2",
                                "jkNo": "J002",
                                "trNo": "T002",
                            },
                            {
                                "hrNo": "003",
                                "hrName": "Horse 3",
                                "jkNo": "J003",
                                "trNo": "T003",
                            },
                        ]
                    }
                },
            }
        }
    )
    return mock


@pytest.fixture
def collection_service(mock_kra_api_service):
    return CollectionService(mock_kra_api_service)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_race_data_keeps_successful_horses_on_partial_failure(
    collection_service, db_session, monkeypatch
):
    async def fake_collect_horse_details(horse_basic):
        if horse_basic["hr_no"] == "002":
            raise RuntimeError("horse detail failed")
        return {**horse_basic, "hrDetail": {"name": horse_basic["hr_name"]}}

    monkeypatch.setattr(
        collection_service,
        "_collect_horse_details",
        fake_collect_horse_details,
    )

    result = await collection_service.collect_race_data(
        race_date="20240719", meet=1, race_no=1, db=db_session
    )

    assert result["status"] == "partial_failure"
    assert [horse["hr_no"] for horse in result["horses"]] == ["001", "003"]
    assert result["failed_horses"] == [
        {
            "horse_no": "002",
            "horse_name": "Horse 2",
            "error": "horse detail failed",
        }
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_race_data_fails_when_horse_failures_reach_threshold(
    collection_service, db_session, monkeypatch
):
    async def fake_collect_horse_details(horse_basic):
        if horse_basic["hr_no"] == "003":
            return {**horse_basic, "hrDetail": {"name": horse_basic["hr_name"]}}
        raise RuntimeError(f"{horse_basic['hr_no']} failed")

    monkeypatch.setattr(
        collection_service,
        "_collect_horse_details",
        fake_collect_horse_details,
    )

    with pytest.raises(ValueError, match="Too many horse detail collection failures"):
        await collection_service.collect_race_data(
            race_date="20240719", meet=1, race_no=2, db=db_session
        )

    saved_race = await db_session.execute(
        "SELECT collection_status FROM races WHERE date = '20240719' AND meet = 1 AND race_number = 2"
    )
    row = saved_race.first()
    assert row is not None
    assert row[0] == DataStatus.FAILED.value
