import asyncio
from pathlib import Path
from typing import Any

import httpx
import structlog

from config import settings
from infrastructure.kra_api.core import (
    KRAApiAuthenticationError as _KRAApiAuthenticationError,
)
from infrastructure.kra_api.core import (
    KRAApiRateLimitError as _KRAApiRateLimitError,
)
from infrastructure.kra_api.core import (
    KRAApiRequestError,
    KRARequestPolicy,
    build_httpx_client_kwargs,
    request_json_with_retry,
)

logger = structlog.get_logger()

KRAApiClientError = KRAApiRequestError
KRAApiAuthenticationError = _KRAApiAuthenticationError
KRAApiRateLimitError = _KRAApiRateLimitError


class KRAApiClient:
    def __init__(self):
        self._policy = KRARequestPolicy(
            base_url=settings.kra_api_base_url,
            api_key=settings.kra_api_key,
            timeout=settings.kra_api_timeout,
            max_retries=settings.kra_api_max_retries,
            verify_ssl=settings.kra_api_verify_ssl,
        )
        self.verify_ssl = self._policy.verify_ssl

        # API 엔드포인트별 경로
        self.endpoints = {
            "race_detail": "/API214_1/RaceDetailResult_1",
            "race_result": "/API299/Race_Result_total",
            "horse_detail": "/API8_2/raceHorseInfo_2",
            "jockey_detail": "/API12_1/jockeyInfo_1",
            "trainer_detail": "/API19_1/trainerInfo_1",
        }

        # 경마장 매핑
        self.meet_names = {"1": "서울", "2": "제주", "3": "부산경남"}
        self.meet_folders = {"1": "seoul", "2": "jeju", "3": "busan"}

        # 데이터 저장 경로
        self.data_base_path = Path("data")
        self.cache_base_path = self.data_base_path / "cache"

    async def _make_request(
        self, endpoint: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """KRA API에 요청을 보내고 응답을 반환합니다."""
        async with httpx.AsyncClient(**build_httpx_client_kwargs(self._policy)) as client:
            return await request_json_with_retry(
                client, self._policy, endpoint, params=params
            )

    async def get_race_detail(
        self, date: str, meet: int, race_no: int
    ) -> dict[str, Any] | None:
        """특정 경주의 상세 데이터를 가져옵니다."""
        params = {
            "numOfRows": "50",
            "pageNo": "1",
            "meet": str(meet),
            "rc_date": date,
            "rc_no": str(race_no),
        }

        try:
            response = await self._make_request(self.endpoints["race_detail"], params)

            # 응답 검증
            if response.get("response", {}).get("header", {}).get("resultCode") == "00":
                body = response.get("response", {}).get("body", {})
                if body.get("items"):
                    return self._process_race_detail(body["items"], date, meet, race_no)

            return None

        except Exception as e:
            logger.error(
                "Failed to get race detail",
                date=date,
                meet=meet,
                race_no=race_no,
                error=str(e),
            )
            return None

    def _process_race_detail(
        self, items: dict[str, Any], date: str, meet: int, race_no: int
    ) -> dict[str, Any]:
        """경주 상세 데이터를 처리합니다."""
        horses = items.get("item", [])
        if not isinstance(horses, list):
            horses = [horses]

        # 첫 번째 말 데이터에서 경주 정보 추출
        first_horse = horses[0] if horses else {}

        race_info = {
            "date": date,
            "meet": meet,
            "race_no": race_no,
            "race_name": first_horse.get("rcName", ""),
            "distance": first_horse.get("rcDist", 0),
            "track_condition": first_horse.get("track", ""),
            "weather": first_horse.get("weather", ""),
            "race_time": first_horse.get("rcTime", 0),
            "horses": [],
        }

        # 말 정보 처리
        for horse in horses:
            horse_info = {
                "chul_no": horse.get("chulNo", 0),
                "horse_no": horse.get("hrNo", ""),
                "horse_name": horse.get("hrName", ""),
                "age": horse.get("age", 0),
                "sex": horse.get("sex", ""),
                "weight": horse.get("wgHr", ""),
                "jockey_no": horse.get("jkNo", ""),
                "jockey_name": horse.get("jkName", ""),
                "trainer_no": horse.get("trNo", ""),
                "trainer_name": horse.get("trName", ""),
                "owner_no": horse.get("owNo", ""),
                "owner_name": horse.get("owName", ""),
                "win_odds": float(horse.get("winOdds", 0)),
                "plc_odds": float(horse.get("plcOdds", 0)),
                "ord": horse.get("ord", 0),
                "wg_budam": horse.get("wgBudam", 0),
                "rating": horse.get("rating", 0),
            }
            race_info["horses"].append(horse_info)

        return race_info

    async def get_all_races(self, date: str, meet: int) -> list[dict[str, Any]]:
        """특정 날짜의 모든 경주 데이터를 가져옵니다."""
        races = []

        # 일반적으로 1일 최대 15경주
        for race_no in range(1, 16):
            try:
                race_data = await self.get_race_detail(date, meet, race_no)
                if race_data:
                    races.append(race_data)
                else:
                    # 데이터가 없으면 중단
                    break

                # API 호출 제한 방지
                await asyncio.sleep(1)

            except Exception as e:
                logger.warning(f"Failed to get race {race_no}", error=str(e))
                break

        return races

    async def get_horse_detail(self, horse_no: str) -> dict[str, Any] | None:
        """말의 상세 정보를 가져옵니다."""
        params = {"pageNo": "1", "numOfRows": "10", "hr_no": horse_no}

        try:
            response = await self._make_request(self.endpoints["horse_detail"], params)

            if response.get("response", {}).get("header", {}).get("resultCode") == "00":
                body = response.get("response", {}).get("body", {})
                if body.get("items"):
                    item = body["items"].get("item", {})
                    if not isinstance(item, list):
                        item = [item]
                    return item[0] if item else None

            return None

        except Exception as e:
            logger.error("Failed to get horse detail", horse_no=horse_no, error=str(e))
            return None

    async def get_jockey_detail(self, jockey_no: str) -> dict[str, Any] | None:
        """기수의 상세 정보를 가져옵니다."""
        params = {"pageNo": "1", "numOfRows": "10", "jk_no": jockey_no}

        try:
            response = await self._make_request(self.endpoints["jockey_detail"], params)

            if response.get("response", {}).get("header", {}).get("resultCode") == "00":
                body = response.get("response", {}).get("body", {})
                if body.get("items"):
                    item = body["items"].get("item", {})
                    if not isinstance(item, list):
                        item = [item]
                    return item[0] if item else None

            return None

        except Exception as e:
            logger.error(
                "Failed to get jockey detail", jockey_no=jockey_no, error=str(e)
            )
            return None

    async def get_trainer_detail(self, trainer_no: str) -> dict[str, Any] | None:
        """조교사의 상세 정보를 가져옵니다."""
        params = {"pageNo": "1", "numOfRows": "10", "tr_no": trainer_no}

        try:
            response = await self._make_request(
                self.endpoints["trainer_detail"], params
            )

            if response.get("response", {}).get("header", {}).get("resultCode") == "00":
                body = response.get("response", {}).get("body", {})
                if body.get("items"):
                    item = body["items"].get("item", {})
                    if not isinstance(item, list):
                        item = [item]
                    return item[0] if item else None

            return None

        except Exception as e:
            logger.error(
                "Failed to get trainer detail", trainer_no=trainer_no, error=str(e)
            )
            return None
