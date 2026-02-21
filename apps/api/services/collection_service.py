"""
데이터 수집 서비스
경주 데이터 수집, 전처리, 강화 로직
"""

from datetime import UTC, datetime
from typing import Any

import pandas as pd
import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.kra_response_adapter import KRAResponseAdapter
from infrastructure.redis_client import CacheService
from models.database_models import DataStatus, Race
from services.collection_enrichment import (
    analyze_weather_impact as analyze_weather_impact_helper,
)
from services.collection_enrichment import (
    calculate_performance_stats as calculate_performance_stats_helper,
)
from services.collection_enrichment import (
    calculate_recent_form as calculate_recent_form_helper,
)
from services.collection_enrichment import (
    enrich_data as enrich_data_helper,
)
from services.collection_enrichment import (
    get_default_stats as get_default_stats_helper,
)
from services.collection_enrichment import (
    get_horse_past_performances as get_horse_past_performances_helper,
)
from services.collection_enrichment import (
    get_jockey_stats as get_jockey_stats_helper,
)
from services.collection_enrichment import (
    get_trainer_stats as get_trainer_stats_helper,
)
from services.collection_preprocessing import preprocess_data as preprocess_data_helper
from services.kra_api_service import KRAAPIService
from utils.field_mapping import convert_api_to_internal

logger = structlog.get_logger()


class CollectionService:
    """데이터 수집 및 처리 서비스"""

    def __init__(self, kra_api_service: KRAAPIService):
        self.kra_api = kra_api_service
        self.cache_service = CacheService()

    @staticmethod
    async def get_collection_status(
        db: AsyncSession, race_date: str, meet: int
    ) -> dict[str, Any]:
        """특정 날짜/경마장의 수집 상태를 집계한다."""
        filters = and_(Race.date == race_date, Race.meet == meet)

        async def count_where(condition) -> int:
            result = await db.execute(
                select(func.count()).select_from(Race).where(condition)
            )
            return int(result.scalar_one() or 0)

        total_races = await count_where(filters)
        collected_races = await count_where(
            and_(
                filters,
                Race.collection_status.in_([DataStatus.COLLECTED, DataStatus.ENRICHED]),
            )
        )
        enriched_races = await count_where(
            and_(filters, Race.enrichment_status == DataStatus.ENRICHED)
        )

        failed_collection = await count_where(
            and_(filters, Race.collection_status == DataStatus.FAILED)
        )
        failed_enrichment = await count_where(
            and_(filters, Race.enrichment_status == DataStatus.FAILED)
        )
        result_collected = await count_where(
            and_(filters, Race.result_status == DataStatus.COLLECTED)
        )
        result_failed = await count_where(
            and_(filters, Race.result_status == DataStatus.FAILED)
        )

        latest_updated_result = await db.execute(
            select(func.max(Race.updated_at)).where(filters)
        )
        last_updated = latest_updated_result.scalar_one_or_none()

        if total_races == 0:
            overall_status = "pending"
        elif enriched_races == total_races:
            overall_status = "completed"
        elif collected_races > 0 or enriched_races > 0:
            overall_status = "running"
        else:
            overall_status = "pending"

        if total_races == 0:
            collection_status = DataStatus.PENDING
        elif failed_collection == total_races and collected_races == 0:
            collection_status = DataStatus.FAILED
        elif collected_races > 0:
            collection_status = DataStatus.COLLECTED
        else:
            collection_status = DataStatus.PENDING

        if total_races == 0:
            enrichment_status = DataStatus.PENDING
        elif failed_enrichment == total_races and enriched_races == 0:
            enrichment_status = DataStatus.FAILED
        elif enriched_races > 0:
            enrichment_status = DataStatus.ENRICHED
        else:
            enrichment_status = DataStatus.PENDING

        if total_races == 0:
            result_status = DataStatus.PENDING
        elif result_failed == total_races and result_collected == 0:
            result_status = DataStatus.FAILED
        elif result_collected > 0:
            result_status = DataStatus.COLLECTED
        else:
            result_status = DataStatus.PENDING

        return {
            "date": race_date,
            "meet": meet,
            "total_races": total_races,
            "collected_races": collected_races,
            "enriched_races": enriched_races,
            "status": overall_status,
            "collection_status": collection_status.value,
            "enrichment_status": enrichment_status.value,
            "result_status": result_status.value,
            "last_updated": last_updated,
        }

    async def collect_race_data(
        self, race_date: str, meet: int, race_no: int, db: AsyncSession
    ) -> dict[str, Any]:
        """
        단일 경주 데이터 수집

        Args:
            race_date: 경주 날짜 (YYYYMMDD)
            meet: 경마장 코드
            race_no: 경주 번호
            db: 데이터베이스 세션

        Returns:
            수집된 경주 데이터
        """
        try:
            logger.info(
                "Starting race data collection",
                race_date=race_date,
                meet=meet,
                race_no=race_no,
            )

            # 기본 경주 정보 수집 (캐시 활성화)
            race_info = await self.kra_api.get_race_info(race_date, str(meet), race_no)

            # 날씨 정보 수집 (현재 API에서 제공하지 않음)
            weather_info: dict[str, Any] = {}

            # 마필별 상세 정보 수집
            horses_data = []
            if race_info and KRAResponseAdapter.is_successful_response(race_info):
                normalized_race = KRAResponseAdapter.normalize_race_info(race_info)
                horses = normalized_race["horses"]

                for horse in horses:
                    # Convert API camelCase to internal snake_case
                    horse_converted = convert_api_to_internal(horse)
                    horse_detail = await self._collect_horse_details(horse_converted)
                    horses_data.append(horse_detail)

            # 데이터 통합
            collected_data = {
                # compatibility fields expected by tests
                "race_date": race_date,
                "race_no": race_no,
                # internal canonical fields
                "date": race_date,
                "meet": meet,
                "race_number": race_no,
                "race_info": race_info,
                "weather": weather_info,
                "horses": horses_data,
                "collected_at": datetime.now(UTC).isoformat(),
            }

            # 데이터베이스 저장
            await self._save_race_data(collected_data, db)

            logger.info(
                "Race data collection completed",
                race_date=race_date,
                meet=meet,
                race_no=race_no,
                horses_count=len(horses_data),
            )

            return collected_data

        except Exception as e:
            logger.error(
                "Race data collection failed",
                race_date=race_date,
                meet=meet,
                race_no=race_no,
                error=str(e),
            )
            raise

    async def _collect_horse_details(
        self, horse_basic: dict[str, Any]
    ) -> dict[str, Any]:
        """마필 상세 정보 수집"""
        try:
            # 마필 정보 (캐시 비활성화)
            horse_no = horse_basic.get("hr_no")
            horse_info = (
                await self.kra_api.get_horse_info(horse_no, use_cache=False)
                if horse_no
                else None
            )

            # 기수 정보 (캐시 비활성화)
            jockey_no = horse_basic.get("jk_no")
            jockey_info = (
                await self.kra_api.get_jockey_info(jockey_no, use_cache=False)
                if jockey_no
                else None
            )

            # 조교사 정보 (캐시 비활성화)
            trainer_no = horse_basic.get("tr_no")
            trainer_info = (
                await self.kra_api.get_trainer_info(trainer_no, use_cache=False)
                if trainer_no
                else None
            )

            # 통합 - Follow JavaScript enrichment pattern with hrDetail, jkDetail, trDetail
            result = {**horse_basic}

            # 어댑터를 사용한 응답 정규화
            if horse_info:
                normalized_horse = KRAResponseAdapter.normalize_horse_info(horse_info)
                if normalized_horse:
                    result["hrDetail"] = convert_api_to_internal(
                        normalized_horse["raw_data"]
                    )

            if jockey_info:
                normalized_jockey = KRAResponseAdapter.normalize_jockey_info(
                    jockey_info
                )
                if normalized_jockey:
                    result["jkDetail"] = convert_api_to_internal(
                        normalized_jockey["raw_data"]
                    )

            if trainer_info:
                normalized_trainer = KRAResponseAdapter.normalize_trainer_info(
                    trainer_info
                )
                if normalized_trainer:
                    result["trDetail"] = convert_api_to_internal(
                        normalized_trainer["raw_data"]
                    )

            return result

        except Exception as e:
            logger.warning(
                "Failed to collect horse details",
                horse_no=horse_basic.get("hr_no"),
                error=str(e),
            )
            return horse_basic

    async def _save_race_data(self, data: dict[str, Any], db: AsyncSession) -> None:
        """경주 데이터 데이터베이스 저장"""
        try:
            # Generate race_id
            race_id = f"{data['date']}_{data['meet']}_{data['race_number']}"

            # 기존 데이터 확인
            existing = await db.execute(
                select(Race).where(
                    and_(
                        Race.date == data["date"],
                        Race.meet == data["meet"],
                        Race.race_number == data["race_number"],
                    )
                )
            )
            race = existing.scalar_one_or_none()

            if race:
                # 업데이트
                race.basic_data = data  # type: ignore[assignment]
                race.updated_at = datetime.now(UTC)  # type: ignore[assignment]
                race.collection_status = DataStatus.COLLECTED  # type: ignore[assignment]
                race.collected_at = datetime.now(UTC)  # type: ignore[assignment]
                race.status = DataStatus.COLLECTED
                # keep compatibility columns in sync
                race.race_date = data["date"]
                race.race_no = data["race_number"]
            else:
                # 신규 생성
                race = Race(
                    race_id=race_id,
                    date=data["date"],
                    race_date=data["date"],
                    meet=data["meet"],
                    race_number=data["race_number"],
                    race_no=data["race_number"],
                    basic_data=data,
                    status=DataStatus.COLLECTED,
                    collection_status=DataStatus.COLLECTED,
                    collected_at=datetime.now(UTC),
                )
                db.add(race)

            await db.commit()

        except Exception as e:
            logger.error("Failed to save race data", error=str(e))
            await db.rollback()
            raise

    async def preprocess_race_data(
        self, race_id: str, db: AsyncSession
    ) -> dict[str, Any]:
        """
        경주 데이터 전처리

        Args:
            race_id: 경주 ID
            db: 데이터베이스 세션

        Returns:
            전처리된 데이터
        """
        try:
            # 경주 데이터 로드
            result = await db.execute(select(Race).where(Race.race_id == race_id))
            race = result.scalar_one_or_none()

            if not race:
                raise ValueError(f"Race not found: {race_id}")

            basic_data = race.basic_data

            # 전처리 수행
            preprocessed = await self._preprocess_data(basic_data)  # type: ignore[arg-type]

            # 저장 - basic_data는 유지하고 preprocessed는 enriched_data에 저장
            race.enriched_data = preprocessed  # type: ignore[assignment]
            race.enrichment_status = DataStatus.ENRICHED  # type: ignore[assignment]
            race.enriched_at = datetime.now(UTC)  # type: ignore[assignment]
            race.updated_at = datetime.now(UTC)  # type: ignore[assignment]

            await db.commit()

            return preprocessed

        except Exception as e:
            logger.error("Preprocessing failed", race_id=race_id, error=str(e))
            await db.rollback()
            raise

    async def _preprocess_data(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """데이터 전처리 로직"""
        return preprocess_data_helper(raw_data)

    async def enrich_race_data(self, race_id: str, db: AsyncSession) -> dict[str, Any]:
        """
        경주 데이터 강화

        Args:
            race_id: 경주 ID
            db: 데이터베이스 세션

        Returns:
            강화된 데이터
        """
        try:
            # 경주 데이터 로드
            result = await db.execute(select(Race).where(Race.race_id == race_id))
            race = result.scalar_one_or_none()

            if not race:
                raise ValueError(f"Race not found: {race_id}")

            # Use enriched_data if exists, otherwise basic_data, then raw_data (for tests)
            base_data = race.enriched_data or race.basic_data or race.raw_data

            # 강화 수행
            enriched = await self._enrich_data(base_data, db)  # type: ignore[arg-type]

            # 저장
            race.enriched_data = enriched  # type: ignore[assignment]
            race.enrichment_status = DataStatus.ENRICHED  # type: ignore[assignment]
            race.enriched_at = datetime.now(UTC)  # type: ignore[assignment]
            race.updated_at = datetime.now(UTC)  # type: ignore[assignment]

            await db.commit()

            return enriched

        except Exception as e:
            logger.error("Enrichment failed", race_id=race_id, error=str(e))
            await db.rollback()
            raise

    async def _enrich_data(
        self, data: dict[str, Any], db: AsyncSession
    ) -> dict[str, Any]:
        """데이터 강화 로직"""
        return await enrich_data_helper(
            data,
            db,
            get_horse_past_performances=self._get_horse_past_performances,
            calculate_performance_stats_fn=self._calculate_performance_stats,
            get_default_stats_fn=self._get_default_stats,
            get_jockey_stats=self._get_jockey_stats,
            get_trainer_stats=self._get_trainer_stats,
            analyze_weather_impact_fn=self._analyze_weather_impact,
        )

    async def _get_horse_past_performances(
        self, horse_no: str, race_date: str, db: AsyncSession
    ) -> list[dict[str, Any]]:
        """마필 과거 성적 조회"""
        return await get_horse_past_performances_helper(horse_no, race_date, db)

    def _calculate_performance_stats(
        self, performances: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """성적 통계 계산"""
        return calculate_performance_stats_helper(performances)

    def _get_default_stats(self) -> dict[str, Any]:
        """기본 통계값"""
        return get_default_stats_helper()

    def _calculate_recent_form(self, df: pd.DataFrame) -> float:
        """최근 폼 계산"""
        return calculate_recent_form_helper(df)

    async def _get_jockey_stats(
        self, jockey_no: str, race_date: str, db: AsyncSession
    ) -> dict[str, Any]:
        """기수 통계 조회"""
        return await get_jockey_stats_helper(self.kra_api, jockey_no, race_date, db)

    async def _get_trainer_stats(
        self, trainer_no: str, race_date: str, db: AsyncSession
    ) -> dict[str, Any]:
        """조교사 통계 조회"""
        return await get_trainer_stats_helper(self.kra_api, trainer_no, race_date, db)

    def _analyze_weather_impact(self, weather: dict[str, Any]) -> dict[str, Any]:
        """날씨 영향 분석"""
        return analyze_weather_impact_helper(weather)

    async def collect_batch_races(
        self, race_date: str, meet: int, race_numbers: list[int], db: AsyncSession
    ) -> dict[int, dict[str, Any]]:
        """
        여러 경주 일괄 수집

        Args:
            race_date: 경주 날짜
            meet: 경마장 코드
            race_numbers: 경주 번호 리스트
            db: 데이터베이스 세션

        Returns:
            경주 번호별 수집 결과
        """
        results = {}

        for race_no in race_numbers:
            try:
                result = await self.collect_race_data(race_date, meet, race_no, db)
                results[race_no] = {"status": "success", "data": result}
            except Exception as e:
                logger.error(
                    "Batch collection failed for race", race_no=race_no, error=str(e)
                )
                results[race_no] = {"status": "error", "error": str(e)}

        return results
