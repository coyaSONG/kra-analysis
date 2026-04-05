"""
KRA API 클라이언트 서비스
KRA 공공 API와의 모든 통신 처리
"""

import asyncio
from typing import Any

import httpx
import structlog

from adapters.kra_response_adapter import KRAResponseAdapter
from config import settings
from infrastructure.kra_api.core import (
    KRAApiRequestError,
    KRARequestPolicy,
    build_httpx_client_kwargs,
    cache_ttl_for,
    request_json_with_retry,
)
from infrastructure.redis_client import CacheService

logger = structlog.get_logger()
_cache_failure_streak = 0


class KRAAPIError(KRAApiRequestError):
    """KRA API 관련 오류"""

    pass


class KRAAPIService:
    """KRA API 통신 서비스"""

    def __init__(self):
        self._policy = KRARequestPolicy(
            base_url=settings.kra_api_base_url,
            api_key=settings.kra_api_key,
            timeout=settings.kra_api_timeout,
            max_retries=settings.kra_api_max_retries,
            verify_ssl=settings.kra_api_verify_ssl,
            user_agent=f"{settings.app_name}/{settings.version}",
        )
        # Don't initialize cache service in constructor
        self._cache_service = None

        # HTTP 클라이언트 설정
        self.client = httpx.AsyncClient(**build_httpx_client_kwargs(self._policy))

    @property
    def cache_service(self):
        """Lazy load cache service"""
        if self._cache_service is None:
            self._cache_service = CacheService()
        return self._cache_service

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """클라이언트 종료"""
        await self.client.aclose()

    def _reset_cache_failure_streak(self) -> None:
        global _cache_failure_streak
        _cache_failure_streak = 0

    def _log_cache_failure(
        self, operation: str, cache_key: str, error: Exception | str
    ) -> None:
        global _cache_failure_streak
        _cache_failure_streak += 1
        log_method = logger.error if _cache_failure_streak >= 5 else logger.warning
        log_method(
            "KRA API cache operation failed",
            operation=operation,
            cache_key=cache_key,
            error=str(error),
            failure_count=_cache_failure_streak,
        )

    async def _get_cached(self, cache_key: str) -> dict[str, Any] | None:
        try:
            cached_data = await self.cache_service.get(cache_key)
            self._reset_cache_failure_streak()
            return cached_data
        except Exception as e:
            self._log_cache_failure("read", cache_key, e)
            return None

    async def _set_cached(
        self, cache_key: str, value: dict[str, Any], ttl: int
    ) -> None:
        try:
            cached = await self.cache_service.set(cache_key, value, ttl=ttl)
            if cached is False:
                raise RuntimeError("Cache write returned False")
            self._reset_cache_failure_streak()
        except Exception as e:
            self._log_cache_failure("write", cache_key, e)

    async def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        KRA API 요청 실행

        Args:
            endpoint: API 엔드포인트
            method: HTTP 메서드
            params: 쿼리 파라미터
            data: 요청 바디 데이터

        Returns:
            API 응답 데이터
        """
        try:
            return await request_json_with_retry(
                self.client,
                self._policy,
                endpoint,
                method=method,
                params=params,
                data=data,
            )
        except KRAApiRequestError as e:
            logger.error("KRA API request failed", endpoint=endpoint, error=str(e))
            raise KRAAPIError(str(e)) from e
        except Exception as e:
            logger.error("Unexpected error in KRA API request", error=str(e))
            raise KRAAPIError(f"Unexpected error: {str(e)}") from e

    async def get_race_info(
        self, race_date: str, meet: str, race_no: int, use_cache: bool = True
    ) -> dict[str, Any]:
        """
        경주 정보 조회 (API214_1 - 경주 상세 결과)

        Args:
            race_date: 경주 날짜 (YYYYMMDD)
            meet: 경마장 코드 (1: 서울, 2: 제주, 3: 부산)
            race_no: 경주 번호
            use_cache: 캐시 사용 여부

        Returns:
            경주 정보
        """
        cache_key = f"race_info:{race_date}:{meet}:{race_no}"

        # 캐시 확인
        if use_cache:
            cached_data = await self._get_cached(cache_key)
            if cached_data:
                logger.info("Using cached race info", key=cache_key)
                return cached_data

        # API 호출
        params = {
            "meet": meet,
            "rc_date": race_date,
            "rc_no": race_no,
            "numOfRows": 50,
            "pageNo": 1,
        }

        # Use correct endpoint from KRA API documentation
        result = await self._make_request(
            endpoint="API214_1/RaceDetailResult_1", params=params
        )

        # 캐시 저장 (1시간)
        if use_cache:
            await self._set_cached(cache_key, result, ttl=cache_ttl_for("race_info"))

        return result

    async def get_race_result(
        self, race_date: str, meet: str, race_no: int, use_cache: bool = True
    ) -> dict[str, Any]:
        """
        경주 결과 조회 (get_race_info와 동일 - API214_1 사용)

        Args:
            race_date: 경주 날짜 (YYYYMMDD)
            meet: 경마장 코드
            race_no: 경주 번호
            use_cache: 캐시 사용 여부

        Returns:
            경주 결과
        """
        # get_race_info와 동일한 API 사용
        return await self.get_race_info(race_date, meet, race_no, use_cache)

    async def get_horse_info(
        self, horse_no: str, use_cache: bool = True
    ) -> dict[str, Any]:
        """
        마필 정보 조회 (API8_2 - 경주마 상세정보)

        Args:
            horse_no: 마번
            use_cache: 캐시 사용 여부

        Returns:
            마필 정보
        """
        cache_key = f"horse_info:{horse_no}"

        # 캐시 확인
        if use_cache:
            cached_data = await self._get_cached(cache_key)
            if cached_data:
                logger.info("Using cached horse info", key=cache_key)
                return cached_data

        # API 호출
        params = {"hr_no": horse_no, "pageNo": 1, "numOfRows": 10}

        result = await self._make_request(
            endpoint="API8_2/raceHorseInfo_2", params=params
        )

        # 캐시 저장 (24시간)
        if use_cache:
            await self._set_cached(cache_key, result, ttl=cache_ttl_for("horse_info"))

        return result

    async def get_jockey_info(
        self, jockey_no: str, use_cache: bool = True
    ) -> dict[str, Any]:
        """
        기수 정보 조회 (API12_1 - 기수 정보)

        Args:
            jockey_no: 기수 번호
            use_cache: 캐시 사용 여부

        Returns:
            기수 정보
        """
        cache_key = f"jockey_info:{jockey_no}"

        # 캐시 확인
        if use_cache:
            cached_data = await self._get_cached(cache_key)
            if cached_data:
                logger.info("Using cached jockey info", key=cache_key)
                return cached_data

        # API 호출
        params = {"jk_no": jockey_no, "numOfRows": 100, "pageNo": 1}

        result = await self._make_request(
            endpoint="API12_1/jockeyInfo_1", params=params
        )

        # 캐시 저장 (24시간)
        if use_cache:
            await self._set_cached(cache_key, result, ttl=cache_ttl_for("jockey_info"))

        return result

    async def get_trainer_info(
        self, trainer_no: str, use_cache: bool = True
    ) -> dict[str, Any]:
        """
        조교사 정보 조회 (API19_1 - 조교사 정보)

        Args:
            trainer_no: 조교사 번호
            use_cache: 캐시 사용 여부

        Returns:
            조교사 정보
        """
        cache_key = f"trainer_info:{trainer_no}"

        # 캐시 확인
        if use_cache:
            cached_data = await self._get_cached(cache_key)
            if cached_data:
                logger.info("Using cached trainer info", key=cache_key)
                return cached_data

        # API 호출
        params = {"tr_no": trainer_no, "pageNo": 1, "numOfRows": 10}

        result = await self._make_request(
            endpoint="API19_1/trainerInfo_1", params=params
        )

        # 캐시 저장 (24시간)
        if use_cache:
            await self._set_cached(cache_key, result, ttl=cache_ttl_for("trainer_info"))

        return result

    async def get_track_info(
        self, race_date: str, meet: str, use_cache: bool = True
    ) -> dict[str, Any]:
        """주로 정보 조회 (API189_1)"""
        cache_key = f"track_info:{race_date}:{meet}"

        if use_cache:
            cached_data = await self._get_cached(cache_key)
            if cached_data:
                return cached_data

        params = {
            "meet": meet,
            "rc_date_fr": race_date,
            "rc_date_to": race_date,
            "numOfRows": 50,
            "pageNo": 1,
        }

        result = await self._make_request(endpoint="API189_1/Track_1", params=params)

        if use_cache:
            await self._set_cached(cache_key, result, ttl=cache_ttl_for("track_info"))

        return result

    async def get_race_plan(
        self, race_date: str, meet: str, use_cache: bool = True
    ) -> dict[str, Any]:
        """경주 계획 조회 (API72_2)"""
        cache_key = f"race_plan:{race_date}:{meet}"

        if use_cache:
            cached_data = await self._get_cached(cache_key)
            if cached_data:
                return cached_data

        params = {
            "meet": meet,
            "rc_date": race_date,
            "numOfRows": 50,
            "pageNo": 1,
        }

        result = await self._make_request(endpoint="API72_2/racePlan_2", params=params)

        if use_cache:
            await self._set_cached(cache_key, result, ttl=cache_ttl_for("race_plan"))

        return result

    async def get_cancelled_horses(
        self, race_date: str, meet: str, use_cache: bool = True
    ) -> dict[str, Any]:
        """기권/제외마 정보 조회 (API9_1)"""
        cache_key = f"cancelled_horses:{race_date}:{meet}"

        if use_cache:
            cached_data = await self._get_cached(cache_key)
            if cached_data:
                return cached_data

        params = {
            "meet": meet,
            "rc_date": race_date,
            "numOfRows": 100,
            "pageNo": 1,
        }

        result = await self._make_request(
            endpoint="API9_1/raceHorseCancelInfo_1", params=params
        )

        if use_cache:
            await self._set_cached(
                cache_key, result, ttl=cache_ttl_for("cancelled_horses")
            )

        return result

    async def get_jockey_stats(
        self, jockey_no: str, meet: str = "1", use_cache: bool = True
    ) -> dict[str, Any]:
        """기수 성적 조회 (API11_1)"""
        cache_key = f"jockey_stats:{jockey_no}:{meet}"

        if use_cache:
            cached_data = await self._get_cached(cache_key)
            if cached_data:
                return cached_data

        params = {
            "jk_no": jockey_no,
            "meet": meet,
            "numOfRows": 10,
            "pageNo": 1,
        }

        result = await self._make_request(
            endpoint="API11_1/jockeyResult_1", params=params
        )

        if use_cache:
            await self._set_cached(cache_key, result, ttl=cache_ttl_for("jockey_stats"))

        return result

    async def get_owner_info(
        self, owner_no: str, meet: str = "1", use_cache: bool = True
    ) -> dict[str, Any]:
        """마주 정보 조회 (API14_1)"""
        cache_key = f"owner_info:{owner_no}:{meet}"

        if use_cache:
            cached_data = await self._get_cached(cache_key)
            if cached_data:
                return cached_data

        params = {
            "ow_no": owner_no,
            "meet": meet,
            "numOfRows": 10,
            "pageNo": 1,
        }

        result = await self._make_request(
            endpoint="API14_1/horseOwnerInfo_1", params=params
        )

        if use_cache:
            await self._set_cached(cache_key, result, ttl=cache_ttl_for("owner_info"))

        return result

    async def get_training_status(
        self, training_date: str, use_cache: bool = True
    ) -> dict[str, Any]:
        """조교 상태 조회 (API329)"""
        cache_key = f"training_status:{training_date}"

        if use_cache:
            cached_data = await self._get_cached(cache_key)
            if cached_data:
                return cached_data

        params = {
            "trng_dt": training_date,
            "numOfRows": 500,
            "pageNo": 1,
        }

        result = await self._make_request(
            endpoint="API329/textDataSeGtscol", params=params
        )

        if use_cache:
            await self._set_cached(
                cache_key, result, ttl=cache_ttl_for("training_status")
            )

        return result

    async def get_final_odds(
        self,
        race_date: str,
        meet: str,
        pool: str | None = None,
        race_no: int | None = None,
    ) -> dict[str, Any]:
        """최종 배당률 조회 (API160_1) - 캐시 없음"""
        params: dict[str, Any] = {
            "meet": meet,
            "rc_date": race_date,
            "numOfRows": 1000,
            "pageNo": 1,
        }
        if pool is not None:
            params["pool"] = pool
        if race_no is not None:
            params["rc_no"] = race_no

        return await self._make_request(
            endpoint="API160_1/integratedInfo_1", params=params
        )

    async def get_final_odds_total(
        self,
        race_date: str,
        meet: str,
        pool: str | None = None,
        race_no: int | None = None,
    ) -> dict[str, Any]:
        """최종 배당률 합계 조회 (API301) - 캐시 없음"""
        params: dict[str, Any] = {
            "meet": meet,
            "rc_date": race_date,
            "numOfRows": 1000,
            "pageNo": 1,
        }
        if pool is not None:
            params["pool"] = pool
        if race_no is not None:
            params["rc_no"] = race_no

        return await self._make_request(
            endpoint="API301/Dividend_rate_total", params=params
        )

    async def get_odds_from_race_info(
        self, race_date: str, meet: str, race_no: int, use_cache: bool = True
    ) -> dict[str, Any]:
        """
        경주 정보에서 배당률 추출

        Args:
            race_date: 경주 날짜
            meet: 경마장 코드
            race_no: 경주 번호
            use_cache: 캐시 사용 여부

        Returns:
            배당률 정보
        """
        # 경주 정보 조회
        race_info = await self.get_race_info(race_date, meet, race_no, use_cache)

        # 배당률 정보 추출
        odds_data: dict[str, Any] = {
            "race_date": race_date,
            "meet": meet,
            "race_no": race_no,
            "horses": [],
        }

        # 어댑터를 사용한 응답 정규화
        if race_info and KRAResponseAdapter.is_successful_response(race_info):
            normalized_race = KRAResponseAdapter.normalize_race_info(race_info)
            horses = normalized_race["horses"]

            for horse in horses:
                odds_data["horses"].append(
                    {
                        "hr_no": horse.get("hrNo"),
                        "hr_name": horse.get("hrName"),
                        "chul_no": horse.get("chulNo"),
                        "win_odds": horse.get("winOdds", 0),
                        "plc_odds": horse.get("plcOdds", 0),
                        "ord": horse.get("ord", 0),
                    }
                )

        return odds_data

    async def get_weather_info(
        self, race_date: str, meet: str, use_cache: bool = True
    ) -> dict[str, Any]:
        """
        날씨 정보 조회 (현재 KRA API에서 제공하지 않음)

        Args:
            race_date: 경주 날짜
            meet: 경마장 코드
            use_cache: 캐시 사용 여부

        Returns:
            날씨 정보 (빈 딕셔너리)
        """
        # KRA API에서 날씨 정보를 제공하지 않으므로 빈 딕셔너리 반환
        return {
            "race_date": race_date,
            "meet": meet,
            "weather_data": None,
            "note": "Weather information is not available from KRA API",
        }

    async def batch_get_race_results(
        self, race_date: str, meet: str, race_numbers: list[int]
    ) -> dict[int, dict[str, Any] | None]:
        """
        여러 경주 결과 일괄 조회

        Args:
            race_date: 경주 날짜
            meet: 경마장 코드
            race_numbers: 경주 번호 리스트

        Returns:
            경주 번호별 결과 딕셔너리
        """
        tasks = []
        for race_no in race_numbers:
            task = self.get_race_result(race_date, meet, race_no)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        race_results: dict[int, dict[str, Any] | None] = {}
        for race_no, result in zip(race_numbers, results, strict=False):
            if isinstance(result, BaseException):
                logger.error(
                    "Failed to get race result", race_no=race_no, error=str(result)
                )
                race_results[race_no] = None
            else:
                race_results[race_no] = result

        return race_results


# 싱글톤 인스턴스
_kra_api_service: KRAAPIService | None = None


async def get_kra_api_service() -> KRAAPIService:
    """KRA API 서비스 인스턴스 반환"""
    global _kra_api_service
    if _kra_api_service is None:
        _kra_api_service = KRAAPIService()
    return _kra_api_service
