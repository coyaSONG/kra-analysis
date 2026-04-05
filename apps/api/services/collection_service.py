"""
데이터 수집 서비스
경주 데이터 수집, 전처리, 강화 로직
"""

from datetime import UTC, datetime
from typing import Any, Literal

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
from services.race_processing_workflow import (
    CollectOddsCommand,
    CollectRaceCommand,
    MaterializeRaceCommand,
    RaceKey,
    RaceProcessingWorkflow,
    build_race_processing_workflow,
)
from utils.field_mapping import convert_api_to_internal

logger = structlog.get_logger()
_HORSE_FAILURE_THRESHOLD = 0.5


def _utcnow() -> datetime:
    """Return current UTC time as naive datetime (for TIMESTAMP WITHOUT TIME ZONE columns)."""
    return datetime.now(UTC).replace(tzinfo=None)


class CollectionService:
    """데이터 수집 및 처리 서비스"""

    def __init__(self, kra_api_service: KRAAPIService):
        self.kra_api = kra_api_service
        self.cache_service = CacheService()

    def _build_workflow(self, db: AsyncSession) -> RaceProcessingWorkflow:
        async def save_collection(payload: dict[str, Any]) -> None:
            await self._save_race_data(payload, db)

        async def save_collection_failure(
            key: RaceKey, race_info: dict[str, Any] | None, reason: str
        ) -> None:
            await self._save_collection_failure(
                key.race_date,
                key.meet,
                key.race_number,
                race_info,
                db,
                reason,
            )

        async def preprocess_payload(payload: dict[str, Any]) -> dict[str, Any]:
            return await self._preprocess_data(payload)

        async def enrich_payload(payload: dict[str, Any]) -> dict[str, Any]:
            return await self._enrich_data(payload, db)

        return build_race_processing_workflow(
            self.kra_api,
            db,
            preprocess_payload_fn=preprocess_payload,
            enrich_payload_fn=enrich_payload,
            collect_horse_details_fn=self._collect_horse_details,
            save_collection_fn=save_collection,
            save_collection_failure_fn=save_collection_failure,
        )

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
        elif failed_collection == total_races and collected_races == 0:
            overall_status = "failed"
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
        workflow = self._build_workflow(db)
        try:
            logger.info(
                "Starting race data collection",
                race_date=race_date,
                meet=meet,
                race_no=race_no,
            )
            collected = await workflow.collect(
                CollectRaceCommand(
                    key=RaceKey(race_date=race_date, meet=meet, race_number=race_no),
                    horse_failure_threshold=_HORSE_FAILURE_THRESHOLD,
                )
            )
            logger.info(
                "Race data collection completed",
                race_date=race_date,
                meet=meet,
                race_no=race_no,
                horses_count=len(collected.payload.get("horses", [])),
            )
            return collected.payload
        except Exception as e:
            logger.error(
                "Race data collection failed",
                race_date=race_date,
                meet=meet,
                race_no=race_no,
                error=str(e),
            )
            raise

    async def _save_collection_failure(
        self,
        race_date: str,
        meet: int,
        race_no: int,
        race_info: dict[str, Any] | None,
        db: AsyncSession,
        reason: str,
    ) -> None:
        """Persist a failed collection attempt unless valid collected data already exists."""
        try:
            race_id = f"{race_date}_{meet}_{race_no}"
            existing = await db.execute(select(Race).where(Race.race_id == race_id))
            race = existing.scalar_one_or_none()

            if race and race.collection_status in (
                DataStatus.COLLECTED,
                DataStatus.ENRICHED,
            ):
                race.updated_at = _utcnow()
                await db.commit()
                return

            failure_payload = {
                "race_info": race_info,
                "failure_reason": reason,
                "failed_at": datetime.now(UTC).isoformat(),
            }

            if race:
                race.raw_data = failure_payload
                race.collection_status = DataStatus.FAILED
                race.updated_at = _utcnow()
            else:
                race = Race(
                    race_id=race_id,
                    date=race_date,
                    race_date=race_date,
                    meet=meet,
                    race_number=race_no,
                    race_no=race_no,
                    raw_data=failure_payload,
                    status=DataStatus.FAILED,
                    collection_status=DataStatus.FAILED,
                    updated_at=_utcnow(),
                )
                db.add(race)

            await db.commit()
        except Exception as exc:
            logger.error(
                "Failed to persist collection failure",
                race_date=race_date,
                meet=meet,
                race_no=race_no,
                error=str(exc),
            )
            await db.rollback()
            raise

    async def _collect_horse_details(
        self, horse_basic: dict[str, Any], meet: int = 1
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

            # 기수 성적 (API11_1) → jkStats (별도 네임스페이스)
            jockey_no = horse_basic.get("jk_no")
            if jockey_no:
                try:
                    jk_stats_response = await self.kra_api.get_jockey_stats(
                        str(jockey_no), meet=str(meet)
                    )
                    if jk_stats_response and KRAResponseAdapter.is_successful_response(
                        jk_stats_response
                    ):
                        jk_stats_item = KRAResponseAdapter.extract_single_item(
                            jk_stats_response
                        )
                        if jk_stats_item:
                            result["jkStats"] = convert_api_to_internal(jk_stats_item)
                except Exception as e:
                    logger.warning(
                        "Failed to get jockey stats", jockey_no=jockey_no, error=str(e)
                    )

            # 마주 정보 (API14_1) → owDetail
            owner_no = horse_basic.get("ow_no")
            if not owner_no and "hrDetail" in result:
                owner_no = result["hrDetail"].get("ow_no")
            if owner_no:
                try:
                    owner_response = await self.kra_api.get_owner_info(
                        str(owner_no), meet=str(meet)
                    )
                    if owner_response and KRAResponseAdapter.is_successful_response(
                        owner_response
                    ):
                        owner_item = KRAResponseAdapter.extract_single_item(
                            owner_response
                        )
                        if owner_item:
                            result["owDetail"] = convert_api_to_internal(owner_item)
                except Exception as e:
                    logger.warning(
                        "Failed to get owner info", owner_no=owner_no, error=str(e)
                    )

            return result

        except Exception as e:
            logger.warning(
                "Failed to collect horse details",
                horse_no=horse_basic.get("hr_no"),
                error=str(e),
            )
            raise

    async def collect_race_odds(
        self,
        race_date: str,
        meet: int,
        race_no: int,
        db: AsyncSession,
        source: Literal["API160_1", "API301"] = "API160_1",
    ) -> dict[str, Any]:
        """배당률 데이터 수집 및 race_odds 테이블 UPSERT"""
        workflow = self._build_workflow(db)
        result = await workflow.collect_odds(
            CollectOddsCommand(
                key=RaceKey(race_date=race_date, meet=meet, race_number=race_no),
                source=source,
            )
        )
        payload = {
            "race_id": result.race_id,
            "inserted_count": result.inserted_count,
        }
        if result.error:
            payload["error"] = result.error
        else:
            payload["source"] = result.source
        return payload

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
                race.basic_data = data
                race.updated_at = _utcnow()
                race.collection_status = DataStatus.COLLECTED
                race.collected_at = _utcnow()
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
                    collected_at=_utcnow(),
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
        workflow = self._build_workflow(db)
        try:
            materialized = await workflow.materialize(
                MaterializeRaceCommand(race_id=race_id, target="preprocessed")
            )
            return materialized.payload
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
        workflow = self._build_workflow(db)
        try:
            materialized = await workflow.materialize(
                MaterializeRaceCommand(race_id=race_id, target="enriched")
            )
            return materialized.payload
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
        """Backward-compatible batch collector preserving instance-level seams."""
        results: dict[int, dict[str, Any]] = {}
        for race_no in race_numbers:
            try:
                result = await self.collect_race_data(race_date, meet, race_no, db)
                results[race_no] = {"status": "success", "data": result}
            except Exception as exc:
                results[race_no] = {"status": "error", "error": str(exc)}

        return results
