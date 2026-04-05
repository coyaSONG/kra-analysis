"""신규 KRA API 엔드포인트 단위 테스트"""

from unittest.mock import AsyncMock, patch

import pytest

from services.kra_api_service import KRAAPIService


def _make_api_response(items):
    """KRA API 표준 응답 생성 헬퍼"""
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
def kra_service():
    with patch.object(KRAAPIService, "__init__", lambda self: None):
        svc = KRAAPIService.__new__(KRAAPIService)
        svc._make_request = AsyncMock()
        svc._get_cached = AsyncMock(return_value=None)
        svc._set_cached = AsyncMock()
        return svc


# ── get_track_info ──────────────────────────────────────────────


class TestGetTrackInfo:
    @pytest.mark.asyncio
    async def test_calls_correct_endpoint(self, kra_service):
        response = _make_api_response({"trackCd": "S01"})
        kra_service._make_request.return_value = response

        result = await kra_service.get_track_info("20250315", "1")

        kra_service._make_request.assert_called_once_with(
            endpoint="API189_1/Track_1",
            params={
                "meet": "1",
                "rc_date_fr": "20250315",
                "rc_date_to": "20250315",
                "numOfRows": 50,
                "pageNo": 1,
                "_type": "json",
            },
        )
        assert result == response

    @pytest.mark.asyncio
    async def test_returns_cached_data(self, kra_service):
        cached = _make_api_response({"trackCd": "cached"})
        kra_service._get_cached.return_value = cached

        result = await kra_service.get_track_info("20250315", "1")

        kra_service._make_request.assert_not_called()
        assert result == cached

    @pytest.mark.asyncio
    async def test_cache_ttl_is_3600(self, kra_service):
        response = _make_api_response({"trackCd": "S01"})
        kra_service._make_request.return_value = response

        await kra_service.get_track_info("20250315", "1")

        kra_service._set_cached.assert_called_once_with(
            "track_info:20250315:1", response, ttl=3600
        )


# ── get_race_plan ───────────────────────────────────────────────


class TestGetRacePlan:
    @pytest.mark.asyncio
    async def test_calls_correct_endpoint(self, kra_service):
        response = _make_api_response({"rcNo": 1})
        kra_service._make_request.return_value = response

        result = await kra_service.get_race_plan("20250315", "1")

        kra_service._make_request.assert_called_once_with(
            endpoint="API72_2/racePlan_2",
            params={
                "meet": "1",
                "rc_date": "20250315",
                "numOfRows": 50,
                "pageNo": 1,
                "_type": "json",
            },
        )
        assert result == response

    @pytest.mark.asyncio
    async def test_returns_cached_data(self, kra_service):
        cached = _make_api_response({"rcNo": "cached"})
        kra_service._get_cached.return_value = cached

        result = await kra_service.get_race_plan("20250315", "1")

        kra_service._make_request.assert_not_called()
        assert result == cached

    @pytest.mark.asyncio
    async def test_cache_ttl_is_86400(self, kra_service):
        response = _make_api_response({"rcNo": 1})
        kra_service._make_request.return_value = response

        await kra_service.get_race_plan("20250315", "1")

        kra_service._set_cached.assert_called_once_with(
            "race_plan:20250315:1", response, ttl=86400
        )


# ── get_cancelled_horses ────────────────────────────────────────


class TestGetCancelledHorses:
    @pytest.mark.asyncio
    async def test_calls_correct_endpoint(self, kra_service):
        response = _make_api_response({"hrNo": "12345"})
        kra_service._make_request.return_value = response

        result = await kra_service.get_cancelled_horses("20250315", "1")

        kra_service._make_request.assert_called_once_with(
            endpoint="API9_1/raceHorseCancelInfo_1",
            params={
                "meet": "1",
                "rc_date": "20250315",
                "numOfRows": 100,
                "pageNo": 1,
                "_type": "json",
            },
        )
        assert result == response

    @pytest.mark.asyncio
    async def test_returns_cached_data(self, kra_service):
        cached = _make_api_response({"hrNo": "cached"})
        kra_service._get_cached.return_value = cached

        result = await kra_service.get_cancelled_horses("20250315", "1")

        kra_service._make_request.assert_not_called()
        assert result == cached

    @pytest.mark.asyncio
    async def test_cache_ttl_is_1800(self, kra_service):
        response = _make_api_response({"hrNo": "12345"})
        kra_service._make_request.return_value = response

        await kra_service.get_cancelled_horses("20250315", "1")

        kra_service._set_cached.assert_called_once_with(
            "cancelled_horses:20250315:1", response, ttl=1800
        )


# ── get_jockey_stats ────────────────────────────────────────────


class TestGetJockeyStats:
    @pytest.mark.asyncio
    async def test_calls_correct_endpoint(self, kra_service):
        response = _make_api_response({"jkNo": "101"})
        kra_service._make_request.return_value = response

        result = await kra_service.get_jockey_stats("101")

        kra_service._make_request.assert_called_once_with(
            endpoint="API11_1/jockeyResult_1",
            params={
                "jk_no": "101",
                "meet": "1",
                "numOfRows": 10,
                "pageNo": 1,
                "_type": "json",
            },
        )
        assert result == response

    @pytest.mark.asyncio
    async def test_custom_meet_parameter(self, kra_service):
        response = _make_api_response({"jkNo": "101"})
        kra_service._make_request.return_value = response

        await kra_service.get_jockey_stats("101", meet="3")

        kra_service._make_request.assert_called_once_with(
            endpoint="API11_1/jockeyResult_1",
            params={
                "jk_no": "101",
                "meet": "3",
                "numOfRows": 10,
                "pageNo": 1,
                "_type": "json",
            },
        )

    @pytest.mark.asyncio
    async def test_returns_cached_data(self, kra_service):
        cached = _make_api_response({"jkNo": "cached"})
        kra_service._get_cached.return_value = cached

        result = await kra_service.get_jockey_stats("101")

        kra_service._make_request.assert_not_called()
        assert result == cached

    @pytest.mark.asyncio
    async def test_cache_ttl_is_86400(self, kra_service):
        response = _make_api_response({"jkNo": "101"})
        kra_service._make_request.return_value = response

        await kra_service.get_jockey_stats("101")

        kra_service._set_cached.assert_called_once_with(
            "jockey_stats:101:1", response, ttl=86400
        )


# ── get_owner_info ──────────────────────────────────────────────


class TestGetOwnerInfo:
    @pytest.mark.asyncio
    async def test_calls_correct_endpoint(self, kra_service):
        response = _make_api_response({"owNo": "200"})
        kra_service._make_request.return_value = response

        result = await kra_service.get_owner_info("200")

        kra_service._make_request.assert_called_once_with(
            endpoint="API14_1/horseOwnerInfo_1",
            params={
                "ow_no": "200",
                "meet": "1",
                "numOfRows": 10,
                "pageNo": 1,
                "_type": "json",
            },
        )
        assert result == response

    @pytest.mark.asyncio
    async def test_returns_cached_data(self, kra_service):
        cached = _make_api_response({"owNo": "cached"})
        kra_service._get_cached.return_value = cached

        result = await kra_service.get_owner_info("200")

        kra_service._make_request.assert_not_called()
        assert result == cached

    @pytest.mark.asyncio
    async def test_cache_ttl_is_86400(self, kra_service):
        response = _make_api_response({"owNo": "200"})
        kra_service._make_request.return_value = response

        await kra_service.get_owner_info("200")

        kra_service._set_cached.assert_called_once_with(
            "owner_info:200:1", response, ttl=86400
        )


# ── get_training_status ─────────────────────────────────────────


class TestGetTrainingStatus:
    @pytest.mark.asyncio
    async def test_calls_correct_endpoint(self, kra_service):
        response = _make_api_response({"trngDt": "20250314"})
        kra_service._make_request.return_value = response

        result = await kra_service.get_training_status("20250314")

        kra_service._make_request.assert_called_once_with(
            endpoint="API329/textDataSeGtscol",
            params={
                "trng_dt": "20250314",
                "numOfRows": 500,
                "pageNo": 1,
                "_type": "json",
            },
        )
        assert result == response

    @pytest.mark.asyncio
    async def test_returns_cached_data(self, kra_service):
        cached = _make_api_response({"trngDt": "cached"})
        kra_service._get_cached.return_value = cached

        result = await kra_service.get_training_status("20250314")

        kra_service._make_request.assert_not_called()
        assert result == cached

    @pytest.mark.asyncio
    async def test_cache_ttl_is_21600(self, kra_service):
        response = _make_api_response({"trngDt": "20250314"})
        kra_service._make_request.return_value = response

        await kra_service.get_training_status("20250314")

        kra_service._set_cached.assert_called_once_with(
            "training_status:20250314", response, ttl=21600
        )


# ── get_final_odds (no cache) ───────────────────────────────────


class TestGetFinalOdds:
    @pytest.mark.asyncio
    async def test_calls_correct_endpoint(self, kra_service):
        response = _make_api_response({"odds": 3.5})
        kra_service._make_request.return_value = response

        result = await kra_service.get_final_odds("20250315", "1")

        kra_service._make_request.assert_called_once_with(
            endpoint="API160_1/integratedInfo_1",
            params={
                "meet": "1",
                "rc_date": "20250315",
                "numOfRows": 1000,
                "pageNo": 1,
                "_type": "json",
            },
        )
        assert result == response

    @pytest.mark.asyncio
    async def test_optional_pool_and_race_no(self, kra_service):
        response = _make_api_response({"odds": 3.5})
        kra_service._make_request.return_value = response

        await kra_service.get_final_odds("20250315", "1", pool="WIN", race_no=3)

        kra_service._make_request.assert_called_once_with(
            endpoint="API160_1/integratedInfo_1",
            params={
                "meet": "1",
                "rc_date": "20250315",
                "numOfRows": 1000,
                "pageNo": 1,
                "_type": "json",
                "pool": "WIN",
                "rc_no": 3,
            },
        )

    @pytest.mark.asyncio
    async def test_no_cache_operations(self, kra_service):
        response = _make_api_response({"odds": 3.5})
        kra_service._make_request.return_value = response

        await kra_service.get_final_odds("20250315", "1")

        kra_service._get_cached.assert_not_called()
        kra_service._set_cached.assert_not_called()


# ── get_final_odds_total (no cache) ─────────────────────────────


class TestGetFinalOddsTotal:
    @pytest.mark.asyncio
    async def test_calls_correct_endpoint(self, kra_service):
        response = _make_api_response({"totalOdds": 100.0})
        kra_service._make_request.return_value = response

        result = await kra_service.get_final_odds_total("20250315", "1")

        kra_service._make_request.assert_called_once_with(
            endpoint="API301/Dividend_rate_total",
            params={
                "meet": "1",
                "rc_date": "20250315",
                "numOfRows": 1000,
                "pageNo": 1,
                "_type": "json",
            },
        )
        assert result == response

    @pytest.mark.asyncio
    async def test_optional_pool_and_race_no(self, kra_service):
        response = _make_api_response({"totalOdds": 100.0})
        kra_service._make_request.return_value = response

        await kra_service.get_final_odds_total(
            "20250315", "1", pool="EXACTA", race_no=5
        )

        kra_service._make_request.assert_called_once_with(
            endpoint="API301/Dividend_rate_total",
            params={
                "meet": "1",
                "rc_date": "20250315",
                "numOfRows": 1000,
                "pageNo": 1,
                "_type": "json",
                "pool": "EXACTA",
                "rc_no": 5,
            },
        )

    @pytest.mark.asyncio
    async def test_no_cache_operations(self, kra_service):
        response = _make_api_response({"totalOdds": 100.0})
        kra_service._make_request.return_value = response

        await kra_service.get_final_odds_total("20250315", "1")

        kra_service._get_cached.assert_not_called()
        kra_service._set_cached.assert_not_called()
