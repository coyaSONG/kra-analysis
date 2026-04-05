"""신규 API 통합 수집 테스트"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from services.collection_service import CollectionService


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


@pytest.fixture
def mock_kra_api():
    api = MagicMock()
    api.get_race_info = AsyncMock(
        return_value=_make_api_response(
            [
                {
                    "hrNo": "001",
                    "hrName": "테스트마",
                    "chulNo": 1,
                    "winOdds": 5.0,
                    "jkNo": "J01",
                    "jkName": "기수1",
                    "trNo": "T01",
                    "trName": "조교사1",
                    "ord": 1,
                }
            ]
        )
    )
    api.get_horse_info = AsyncMock(
        return_value=_make_api_response({"hrNo": "001", "rcCntT": 10})
    )
    api.get_jockey_info = AsyncMock(
        return_value=_make_api_response({"jkNo": "J01", "winRateT": "10.0"})
    )
    api.get_trainer_info = AsyncMock(
        return_value=_make_api_response({"trNo": "T01", "winRateT": 15.0})
    )
    api.get_race_plan = AsyncMock(
        return_value=_make_api_response(
            [{"rcNo": 1, "rank": "국6등급", "rcDist": 1200, "schStTime": 1035}]
        )
    )
    api.get_track_info = AsyncMock(
        return_value=_make_api_response(
            [{"rcNo": 1, "weather": "맑음", "track": "건조", "waterPercent": 3}]
        )
    )
    api.get_cancelled_horses = AsyncMock(return_value=_make_api_response([]))
    api.get_jockey_stats = AsyncMock(
        return_value=_make_api_response(
            {"jkNo": "J01", "winRateT": 9.3, "qnlRateT": 18.8}
        )
    )
    api.get_owner_info = AsyncMock(
        return_value=_make_api_response(
            {"owNo": 110034, "owName": "(주)나스카", "ord1CntT": 205}
        )
    )
    api.get_training_status = AsyncMock(
        return_value=_make_api_response(
            [{"hrnm": "테스트마", "remkTxt": "양호", "trngDt": 20260313}]
        )
    )
    return api


class TestCollectRaceDataNewAPIs:
    """collect_race_data에 신규 API 데이터가 포함되는지 테스트"""

    @pytest.mark.asyncio
    async def test_includes_race_plan(self, mock_kra_api):
        service = CollectionService(mock_kra_api)
        saved_data = {}

        async def capture_save(data, session):
            saved_data.update(data)

        service._save_race_data = capture_save
        await service.collect_race_data("20260315", 1, 1, AsyncMock())
        assert "race_plan" in saved_data
        assert saved_data["race_plan"]["rank"] == "국6등급"

    @pytest.mark.asyncio
    async def test_includes_track(self, mock_kra_api):
        service = CollectionService(mock_kra_api)
        saved_data = {}

        async def capture_save(data, session):
            saved_data.update(data)

        service._save_race_data = capture_save
        await service.collect_race_data("20260315", 1, 1, AsyncMock())
        assert "track" in saved_data
        assert saved_data["track"]["weather"] == "맑음"

    @pytest.mark.asyncio
    async def test_includes_cancelled_horses(self, mock_kra_api):
        mock_kra_api.get_cancelled_horses.return_value = _make_api_response(
            [{"chulNo": 2, "hrName": "취소마", "reason": "마체이상", "rcNo": 1}]
        )
        service = CollectionService(mock_kra_api)
        saved_data = {}

        async def capture_save(data, session):
            saved_data.update(data)

        service._save_race_data = capture_save
        await service.collect_race_data("20260315", 1, 1, AsyncMock())
        assert "cancelled_horses" in saved_data
        assert len(saved_data["cancelled_horses"]) == 1

    @pytest.mark.asyncio
    async def test_horse_has_jk_stats(self, mock_kra_api):
        service = CollectionService(mock_kra_api)
        saved_data = {}

        async def capture_save(data, session):
            saved_data.update(data)

        service._save_race_data = capture_save
        await service.collect_race_data("20260315", 1, 1, AsyncMock())
        horse = saved_data["horses"][0]
        assert "jkStats" in horse

    @pytest.mark.asyncio
    async def test_horse_has_training(self, mock_kra_api):
        service = CollectionService(mock_kra_api)
        saved_data = {}

        async def capture_save(data, session):
            saved_data.update(data)

        service._save_race_data = capture_save
        await service.collect_race_data("20260315", 1, 1, AsyncMock())
        horse = saved_data["horses"][0]
        assert "training" in horse
        assert horse["training"]["remk_txt"] == "양호"

    @pytest.mark.asyncio
    async def test_new_api_failure_does_not_block_collection(self, mock_kra_api):
        """신규 API 실패해도 수집은 계속됨"""
        mock_kra_api.get_race_plan.side_effect = Exception("API down")
        mock_kra_api.get_track_info.side_effect = Exception("API down")
        mock_kra_api.get_cancelled_horses.side_effect = Exception("API down")
        mock_kra_api.get_jockey_stats.side_effect = Exception("API down")
        mock_kra_api.get_owner_info.side_effect = Exception("API down")
        mock_kra_api.get_training_status.side_effect = Exception("API down")

        service = CollectionService(mock_kra_api)
        saved_data = {}

        async def capture_save(data, session):
            saved_data.update(data)

        service._save_race_data = capture_save

        # 기존 API만으로 수집 성공해야 함
        await service.collect_race_data("20260315", 1, 1, AsyncMock())
        assert "horses" in saved_data
        assert len(saved_data["horses"]) == 1
        # 실패한 신규 필드는 빈 값
        assert saved_data.get("race_plan") == {}
        assert saved_data.get("track") == {}


class TestCollectRaceOdds:
    @pytest.mark.asyncio
    async def test_collect_race_odds_parses_items(self, mock_kra_api):
        mock_kra_api.get_final_odds = AsyncMock(
            return_value=_make_api_response(
                [
                    {
                        "chulNo": 1,
                        "chulNo2": 0,
                        "chulNo3": 0,
                        "odds": 5.0,
                        "pool": "단승식",
                        "rcDate": 20260315,
                        "rcNo": 1,
                    },
                    {
                        "chulNo": 2,
                        "chulNo2": 0,
                        "chulNo3": 0,
                        "odds": 3.2,
                        "pool": "단승식",
                        "rcDate": 20260315,
                        "rcNo": 1,
                    },
                ]
            )
        )
        service = CollectionService(mock_kra_api)
        db = AsyncMock()
        result = await service.collect_race_odds(
            "20260315", 1, 1, db, source="API160_1"
        )
        assert result["inserted_count"] == 2
        assert result["source"] == "API160_1"

    @pytest.mark.asyncio
    async def test_collect_race_odds_failed_response(self, mock_kra_api):
        mock_kra_api.get_final_odds = AsyncMock(
            return_value={"response": {"header": {"resultCode": "99"}}}
        )
        service = CollectionService(mock_kra_api)
        db = AsyncMock()
        result = await service.collect_race_odds("20260315", 1, 1, db)
        assert result["inserted_count"] == 0
        assert "error" in result
