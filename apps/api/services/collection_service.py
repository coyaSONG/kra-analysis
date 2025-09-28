"""
데이터 수집 서비스
경주 데이터 수집, 전처리, 강화 로직
"""

from datetime import datetime
from typing import Any

import pandas as pd
import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.kra_response_adapter import KRAResponseAdapter
from infrastructure.redis_client import CacheService
from models.database_models import DataStatus, Race
from services.kra_api_service import KRAAPIService
from utils.field_mapping import convert_api_to_internal

logger = structlog.get_logger()


class CollectionService:
    """데이터 수집 및 처리 서비스"""

    def __init__(self, kra_api_service: KRAAPIService):
        self.kra_api = kra_api_service
        self.cache_service = CacheService()

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
            weather_info = {}

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
                "collected_at": datetime.utcnow().isoformat(),
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
                    result["hrDetail"] = convert_api_to_internal(normalized_horse["raw_data"])

            if jockey_info:
                normalized_jockey = KRAResponseAdapter.normalize_jockey_info(jockey_info)
                if normalized_jockey:
                    result["jkDetail"] = convert_api_to_internal(normalized_jockey["raw_data"])

            if trainer_info:
                normalized_trainer = KRAResponseAdapter.normalize_trainer_info(trainer_info)
                if normalized_trainer:
                    result["trDetail"] = convert_api_to_internal(normalized_trainer["raw_data"])

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
                race.basic_data = data
                race.updated_at = datetime.utcnow()
                race.collection_status = DataStatus.COLLECTED
                race.collected_at = datetime.utcnow()
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
                    collected_at=datetime.utcnow(),
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
            preprocessed = await self._preprocess_data(basic_data)

            # 저장 - basic_data는 유지하고 preprocessed는 enriched_data에 저장
            race.enriched_data = preprocessed
            race.enrichment_status = DataStatus.ENRICHED
            race.enriched_at = datetime.utcnow()
            race.updated_at = datetime.utcnow()

            await db.commit()

            return preprocessed

        except Exception as e:
            logger.error("Preprocessing failed", race_id=race_id, error=str(e))
            await db.rollback()
            raise

    async def _preprocess_data(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """데이터 전처리 로직"""
        try:
            horses = raw_data.get("horses", [])

            # 기권마 필터링
            active_horses = []
            for h in horses:
                try:
                    win_odds = float(h.get("win_odds", 0))
                    if win_odds > 0:
                        active_horses.append(h)
                except (ValueError, TypeError):
                    # Skip horses with invalid win_odds
                    pass

            # 기본 통계 계산
            if active_horses:
                df = pd.DataFrame(active_horses)
                # Ensure numeric types
                for col in ["weight", "rating", "win_odds"]:
                    if col in df:
                        df[col] = pd.to_numeric(df[col], errors="coerce")

                # 평균 계산
                avg_weight = df["weight"].mean() if "weight" in df else 0
                avg_rating = df["rating"].mean() if "rating" in df else 0
                avg_win_odds = df["win_odds"].mean() if "win_odds" in df else 0

                # 각 마필에 대한 상대적 지표 계산
                for horse in active_horses:
                    if avg_weight > 0:
                        try:
                            horse["weight_ratio"] = (
                                float(horse.get("weight", 0)) / avg_weight
                            )
                        except (ValueError, TypeError):
                            horse["weight_ratio"] = 0
                    if avg_rating > 0:
                        try:
                            horse["rating_ratio"] = (
                                float(horse.get("rating", 0)) / avg_rating
                            )
                        except (ValueError, TypeError):
                            horse["rating_ratio"] = 0
                    if avg_win_odds > 0:
                        try:
                            horse["odds_ratio"] = (
                                float(horse.get("win_odds", 0)) / avg_win_odds
                            )
                        except (ValueError, TypeError):
                            horse["odds_ratio"] = 0

            preprocessed = {
                **raw_data,
                "horses": active_horses,
                "excluded_horses": len(horses) - len(active_horses),
                "preprocessing_timestamp": datetime.utcnow().isoformat(),
                "statistics": {
                    "avg_weight": avg_weight if "avg_weight" in locals() else 0,
                    "avg_rating": avg_rating if "avg_rating" in locals() else 0,
                    "avg_win_odds": avg_win_odds if "avg_win_odds" in locals() else 0,
                },
            }

            return preprocessed

        except Exception as e:
            logger.error("Preprocessing logic failed", error=str(e))
            raise

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
            enriched = await self._enrich_data(base_data, db)

            # 저장
            race.enriched_data = enriched
            race.enrichment_status = DataStatus.ENRICHED
            race.enriched_at = datetime.utcnow()
            race.updated_at = datetime.utcnow()

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
        try:
            horses = data.get("horses", [])
            race_date = data.get("race_date")
            _meet = data.get("meet")

            # 각 마필에 대한 과거 성적 조회
            for horse in horses:
                horse_no = horse.get("hr_no") or horse.get("horse_no")

                # 과거 3개월 성적 조회
                past_performances = await self._get_horse_past_performances(
                    horse_no, race_date, db
                )

                # 성적 통계 계산
                if past_performances:
                    horse["past_stats"] = self._calculate_performance_stats(
                        past_performances
                    )
                else:
                    horse["past_stats"] = self._get_default_stats()

                # 기수/조교사 통계
                jockey_no = horse.get("jk_no") or horse.get("jockey_no")
                trainer_no = horse.get("tr_no") or horse.get("trainer_no")

                if jockey_no:
                    horse["jockey_stats"] = await self._get_jockey_stats(
                        jockey_no, race_date, db
                    )

                if trainer_no:
                    horse["trainer_stats"] = await self._get_trainer_stats(
                        trainer_no, race_date, db
                    )

            # 날씨 영향 분석
            weather = data.get("weather", {})
            weather_impact = self._analyze_weather_impact(weather)

            enriched = {
                **data,
                "horses": horses,
                "weather_impact": weather_impact,
                "enrichment_timestamp": datetime.utcnow().isoformat(),
            }

            return enriched

        except Exception as e:
            logger.error("Enrichment logic failed", error=str(e))
            raise

    async def _get_horse_past_performances(
        self, horse_no: str, race_date: str, db: AsyncSession
    ) -> list[dict[str, Any]]:
        """마필 과거 성적 조회"""
        try:
            # Calculate date 3 months ago
            from dateutil.relativedelta import relativedelta

            current_date = datetime.strptime(race_date, "%Y%m%d")
            three_months_ago = current_date - relativedelta(months=3)
            three_months_ago_str = three_months_ago.strftime("%Y%m%d")

            # Query past races
            result = await db.execute(
                select(Race)
                .where(
                    and_(
                        Race.date >= three_months_ago_str,
                        Race.date < race_date,
                        Race.result_status == DataStatus.COLLECTED,
                    )
                )
                .order_by(Race.date.desc())
            )
            races = result.scalars().all()

            performances = []
            for race in races:
                # Check if this horse participated in the race
                if race.result_data:
                    horses = race.result_data.get("horses", [])
                    for horse in horses:
                        if horse.get("hr_no") == horse_no:
                            performances.append(
                                {
                                    "date": race.date,
                                    "meet": race.meet,
                                    "race_no": race.race_number,
                                    "position": horse.get("ord", 0),
                                    "win_odds": horse.get("win_odds", 0),
                                    "rating": horse.get("rating", 0),
                                    "weight": horse.get("weight", 0),
                                    "jockey": horse.get("jk_name", ""),
                                    "trainer": horse.get("tr_name", ""),
                                }
                            )
                            break

            return performances

        except Exception as e:
            logger.warning(f"Failed to get past performances: {e}")
            return []

    def _calculate_performance_stats(
        self, performances: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """성적 통계 계산"""
        df = pd.DataFrame(performances)

        return {
            "total_races": len(performances),
            "wins": len(df[df["position"] == 1]),
            "win_rate": len(df[df["position"] == 1]) / len(df) if len(df) > 0 else 0,
            "avg_position": df["position"].mean() if "position" in df else 0,
            "recent_form": self._calculate_recent_form(df),
        }

    def _get_default_stats(self) -> dict[str, Any]:
        """기본 통계값"""
        return {
            "total_races": 0,
            "wins": 0,
            "win_rate": 0,
            "avg_position": 0,
            "recent_form": 0,
        }

    def _calculate_recent_form(self, df: pd.DataFrame) -> float:
        """최근 폼 계산"""
        if len(df) == 0:
            return 0

        # 최근 5경기 가중치 적용
        recent = df.head(5)
        weights = [5, 4, 3, 2, 1][: len(recent)]

        form_score = 0
        for i, (_, race) in enumerate(recent.iterrows()):
            position = race.get("position", 10)
            score = max(0, 11 - position) * weights[i]
            form_score += score

        max_score = sum(weights) * 10
        return form_score / max_score if max_score > 0 else 0

    async def _get_jockey_stats(
        self, jockey_no: str, race_date: str, db: AsyncSession
    ) -> dict[str, Any]:
        """기수 통계 조회"""
        try:
            # Get jockey info from API (no cache)
            jockey_info = await self.kra_api.get_jockey_info(jockey_no, use_cache=False)

            # 어댑터를 사용한 기수 정보 정규화
            normalized_jockey = KRAResponseAdapter.normalize_jockey_info(jockey_info)
            if normalized_jockey:
                # Convert API response to internal format
                from utils.field_mapping import convert_api_to_internal

                jk_data = convert_api_to_internal(normalized_jockey["raw_data"])

                return {
                    "recent_win_rate": float(jk_data.get("win_rate_y", 0)) / 100,
                    "career_win_rate": float(jk_data.get("win_rate_t", 0)) / 100,
                    "total_wins": jk_data.get("ord1_cnt_t", 0),
                    "total_races": jk_data.get("rc_cnt_t", 0),
                    "recent_races": jk_data.get("rc_cnt_y", 0),
                }

            # Default values if API call fails
            return {
                "recent_win_rate": 0.15,
                "career_win_rate": 0.12,
                "total_wins": 0,
                "total_races": 0,
                "recent_races": 0,
            }

        except Exception as e:
            logger.warning(f"Failed to get jockey stats: {e}")
            return {
                "recent_win_rate": 0.15,
                "career_win_rate": 0.12,
                "total_wins": 0,
                "total_races": 0,
                "recent_races": 0,
            }

    async def _get_trainer_stats(
        self, trainer_no: str, race_date: str, db: AsyncSession
    ) -> dict[str, Any]:
        """조교사 통계 조회"""
        try:
            # Get trainer info from API (no cache)
            trainer_info = await self.kra_api.get_trainer_info(
                trainer_no, use_cache=False
            )

            # 어댑터를 사용한 조교사 정보 정규화
            normalized_trainer = KRAResponseAdapter.normalize_trainer_info(trainer_info)
            if normalized_trainer:
                # Convert API response to internal format
                from utils.field_mapping import convert_api_to_internal

                tr_data = convert_api_to_internal(normalized_trainer["raw_data"])

                return {
                    "recent_win_rate": float(tr_data.get("win_rate_y", 0)) / 100,
                    "career_win_rate": float(tr_data.get("win_rate_t", 0)) / 100,
                    "total_wins": tr_data.get("ord1_cnt_t", 0),
                    "total_races": tr_data.get("rc_cnt_t", 0),
                        "recent_races": tr_data.get("rc_cnt_y", 0),
                        "plc_rate": float(tr_data.get("plc_rate_t", 0)) / 100,
                        "meet": tr_data.get("meet", ""),
                    }

            # Default values if API call fails
            return {
                "recent_win_rate": 0.18,
                "career_win_rate": 0.16,
                "total_wins": 0,
                "total_races": 0,
                "recent_races": 0,
                "plc_rate": 0.35,
                "meet": "",
            }

        except Exception as e:
            logger.warning(f"Failed to get trainer stats: {e}")
            return {
                "recent_win_rate": 0.18,
                "career_win_rate": 0.16,
                "total_wins": 0,
                "total_races": 0,
                "recent_races": 0,
                "plc_rate": 0.35,
                "meet": "",
            }

    def _analyze_weather_impact(self, weather: dict[str, Any]) -> dict[str, Any]:
        """날씨 영향 분석"""
        track_condition = weather.get("track_condition", "good")

        impact = {
            "track_speed_factor": 1.0,
            "stamina_importance": 1.0,
            "weight_impact": 1.0,
        }

        if track_condition in ["heavy", "soft"]:
            impact["track_speed_factor"] = 0.95
            impact["stamina_importance"] = 1.2
            impact["weight_impact"] = 1.1
        elif track_condition == "firm":
            impact["track_speed_factor"] = 1.05
            impact["stamina_importance"] = 0.9

        return impact

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
