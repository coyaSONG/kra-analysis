"""결과 수집 시 배당률 자동 수집 테스트"""

import pytest

from models.database_models import DataStatus, Race
from services.result_collection_service import ResultCollectionService


def _make_api_response(items):
    item_list = items if isinstance(items, list) else [items]
    return {
        "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
            "body": {
                "items": {"item": item_list},
                "numOfRows": len(item_list),
                "pageNo": 1,
                "totalCount": len(item_list),
            },
        }
    }


def _make_race_result_response():
    """경주 결과 API 응답 (1-3위)"""
    return _make_api_response(
        [
            {"chulNo": 3, "ord": 1, "hrName": "말A"},
            {"chulNo": 1, "ord": 2, "hrName": "말B"},
            {"chulNo": 5, "ord": 3, "hrName": "말C"},
        ]
    )


class MockKRAApi:
    """테스트용 KRA API mock"""

    def __init__(self, odds_response=None, odds_error=None):
        self._odds_response = odds_response
        self._odds_error = odds_error

    async def get_race_result(self, *args, **kwargs):
        return _make_race_result_response()

    async def get_final_odds(self, *args, **kwargs):
        if self._odds_error:
            raise self._odds_error
        return self._odds_response or _make_api_response([])


@pytest.mark.asyncio
@pytest.mark.unit
async def test_odds_collected_on_successful_result(db_session):
    """결과 수집 성공 시 배당률도 수집되고 result_status는 COLLECTED 유지"""
    race = Race(
        race_id="20260315_1_1",
        date="20260315",
        meet=1,
        race_number=1,
        collection_status=DataStatus.COLLECTED,
        result_status=DataStatus.PENDING,
    )
    db_session.add(race)
    await db_session.commit()

    kra_api = MockKRAApi(
        odds_response=_make_api_response(
            [
                {"chulNo": 1, "chulNo2": 0, "chulNo3": 0, "odds": 5.0, "pool": "WIN"},
                {"chulNo": 2, "chulNo2": 0, "chulNo3": 0, "odds": 3.2, "pool": "WIN"},
            ]
        )
    )

    service = ResultCollectionService()
    result = await service.collect_result(
        race_date="20260315",
        meet=1,
        race_number=1,
        db=db_session,
        kra_api=kra_api,
    )

    # 결과 수집 성공
    assert result["top3"] == [3, 1, 5]
    # 배당률 수집 성공
    assert result["odds"]["collected"] is True
    # result_status는 COLLECTED 유지
    await db_session.refresh(race)
    assert race.result_status == DataStatus.COLLECTED


@pytest.mark.asyncio
@pytest.mark.unit
async def test_odds_api_failure_does_not_block_result(db_session):
    """배당률 API 실패해도 결과 수집은 성공"""
    race = Race(
        race_id="20260315_1_2",
        date="20260315",
        meet=1,
        race_number=2,
        collection_status=DataStatus.COLLECTED,
        result_status=DataStatus.PENDING,
    )
    db_session.add(race)
    await db_session.commit()

    kra_api = MockKRAApi(odds_error=Exception("API timeout"))

    service = ResultCollectionService()
    result = await service.collect_result(
        race_date="20260315",
        meet=1,
        race_number=2,
        db=db_session,
        kra_api=kra_api,
    )

    # 결과 수집은 성공
    assert result["top3"] == [3, 1, 5]
    # 배당률 수집은 실패 (non-blocking)
    assert result["odds"]["collected"] is False
    # result_status는 여전히 COLLECTED
    await db_session.refresh(race)
    assert race.result_status == DataStatus.COLLECTED


@pytest.mark.asyncio
@pytest.mark.unit
async def test_odds_unsuccessful_response_does_not_block_result(db_session):
    """배당률 API가 에러 응답 반환해도 결과 데이터 유지"""
    race = Race(
        race_id="20260315_1_3",
        date="20260315",
        meet=1,
        race_number=3,
        collection_status=DataStatus.COLLECTED,
        result_status=DataStatus.PENDING,
    )
    db_session.add(race)
    await db_session.commit()

    kra_api = MockKRAApi(
        odds_response={
            "response": {"header": {"resultCode": "99", "resultMsg": "ERROR"}}
        }
    )

    service = ResultCollectionService()
    result = await service.collect_result(
        race_date="20260315",
        meet=1,
        race_number=3,
        db=db_session,
        kra_api=kra_api,
    )

    assert result["top3"] == [3, 1, 5]
    assert result["odds"]["collected"] is False
    await db_session.refresh(race)
    assert race.result_status == DataStatus.COLLECTED
    assert race.result_data == [3, 1, 5]
