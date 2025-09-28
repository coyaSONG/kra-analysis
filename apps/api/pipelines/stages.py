"""
Pipeline Stages Implementation
구체적인 데이터 처리 단계들의 구현
"""

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from services.collection_service import CollectionService
from services.kra_api_service import KRAAPIService

from .base import PipelineContext, PipelineStage, StageResult, StageStatus


class CollectionStage(PipelineStage):
    """데이터 수집 단계"""

    def __init__(self, kra_api_service: KRAAPIService, db_session: AsyncSession):
        super().__init__("collection")
        self.kra_api_service = kra_api_service
        self.db_session = db_session
        self.collection_service = CollectionService(kra_api_service)

    async def validate_prerequisites(self, context: PipelineContext) -> bool:
        """전제조건 검증: API 서비스와 DB 세션 확인"""
        if not self.kra_api_service:
            self.logger.error("KRA API service not available")
            return False

        if not self.db_session:
            self.logger.error("Database session not available")
            return False

        # 기본 파라미터 검증
        if not context.race_date or not context.meet or not context.race_number:
            self.logger.error(
                "Invalid race parameters",
                race_date=context.race_date,
                meet=context.meet,
                race_number=context.race_number,
            )
            return False

        return True

    async def execute(self, context: PipelineContext) -> StageResult:
        """데이터 수집 실행"""
        try:
            self.logger.info(
                "Starting data collection",
                race_date=context.race_date,
                meet=context.meet,
                race_number=context.race_number,
            )

            # 기존 CollectionService 활용
            collected_data = await self.collection_service.collect_race_data(
                race_date=context.race_date,
                meet=context.meet,
                race_no=context.race_number,
                db=self.db_session,
            )

            # 컨텍스트에 데이터 저장
            context.raw_data = collected_data

            # 메타데이터 생성
            metadata = {
                "horses_count": len(collected_data.get("horses", [])),
                "collection_method": "kra_api",
                "data_quality_score": self._calculate_data_quality(collected_data),
            }

            self.logger.info(
                "Data collection completed",
                horses_count=metadata["horses_count"],
                data_quality_score=metadata["data_quality_score"],
            )

            return StageResult(
                status=StageStatus.COMPLETED,
                data={"raw_data": collected_data},
                metadata=metadata,
            )

        except Exception as e:
            self.logger.error("Data collection failed", error=str(e))
            return StageResult(
                status=StageStatus.FAILED, error=f"Collection failed: {str(e)}"
            )

    def _calculate_data_quality(self, data: dict[str, Any]) -> float:
        """데이터 품질 점수 계산"""
        if not data:
            return 0.0

        horses = data.get("horses", [])
        if not horses:
            return 0.5

        # 필수 필드 체크
        required_fields = ["hr_no", "hr_name", "win_odds"]
        quality_score = 0.0

        for horse in horses:
            field_score = sum(1 for field in required_fields if horse.get(field))
            quality_score += field_score / len(required_fields)

        return quality_score / len(horses) if horses else 0.0

    def should_skip(self, context: PipelineContext) -> bool:
        """이미 수집된 데이터가 있는 경우 생략"""
        return context.raw_data is not None

    async def rollback(self, context: PipelineContext) -> None:
        """수집 데이터 롤백"""
        if context.raw_data:
            self.logger.info("Clearing collected data")
            context.raw_data = None


class PreprocessingStage(PipelineStage):
    """데이터 전처리 단계"""

    def __init__(self):
        super().__init__("preprocessing")

    async def validate_prerequisites(self, context: PipelineContext) -> bool:
        """전제조건 검증: 수집 데이터 존재 여부"""
        if not context.raw_data:
            self.logger.error("No raw data available for preprocessing")
            return False

        if not context.raw_data.get("horses"):
            self.logger.error("No horses data available")
            return False

        return True

    async def execute(self, context: PipelineContext) -> StageResult:
        """데이터 전처리 실행"""
        try:
            self.logger.info("Starting data preprocessing")

            raw_data = context.raw_data
            preprocessed_data = self._preprocess_data(raw_data)

            # 컨텍스트에 전처리된 데이터 저장
            context.preprocessed_data = preprocessed_data

            # 메타데이터 생성
            metadata = {
                "horses_filtered": len(preprocessed_data.get("horses", [])),
                "horses_original": len(raw_data.get("horses", [])),
                "filter_criteria": ["win_odds > 0", "valid_horse_info"],
            }

            self.logger.info(
                "Data preprocessing completed",
                horses_filtered=metadata["horses_filtered"],
                horses_original=metadata["horses_original"],
            )

            return StageResult(
                status=StageStatus.COMPLETED,
                data={"preprocessed_data": preprocessed_data},
                metadata=metadata,
            )

        except Exception as e:
            self.logger.error("Data preprocessing failed", error=str(e))
            return StageResult(
                status=StageStatus.FAILED, error=f"Preprocessing failed: {str(e)}"
            )

    def _preprocess_data(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """데이터 전처리 로직"""
        preprocessed = raw_data.copy()
        horses = raw_data.get("horses", [])

        # 기권/제외마 필터링 (win_odds = 0)
        valid_horses = []
        for horse in horses:
            win_odds = horse.get("win_odds", 0)
            try:
                win_odds = float(win_odds)
                if win_odds > 0:  # 기권/제외마 제외
                    valid_horses.append(horse)
            except (ValueError, TypeError):
                # 유효하지 않은 배당률 데이터도 제외
                continue

        preprocessed["horses"] = valid_horses

        # 데이터 품질 플래그 추가
        preprocessed["data_flags"] = {
            "has_valid_horses": len(valid_horses) > 0,
            "horses_count": len(valid_horses),
            "filtering_applied": True,
        }

        return preprocessed

    def should_skip(self, context: PipelineContext) -> bool:
        """이미 전처리된 데이터가 있는 경우 생략"""
        return context.preprocessed_data is not None

    async def rollback(self, context: PipelineContext) -> None:
        """전처리 데이터 롤백"""
        if context.preprocessed_data:
            self.logger.info("Clearing preprocessed data")
            context.preprocessed_data = None


class EnrichmentStage(PipelineStage):
    """데이터 보강 단계"""

    def __init__(self, collection_service: CollectionService, db_session: AsyncSession):
        super().__init__("enrichment")
        self.collection_service = collection_service
        self.db_session = db_session

    async def validate_prerequisites(self, context: PipelineContext) -> bool:
        """전제조건 검증: 전처리 데이터 존재 여부"""
        if not context.preprocessed_data:
            self.logger.error("No preprocessed data available for enrichment")
            return False

        if not self.collection_service:
            self.logger.error("Collection service not available")
            return False

        return True

    async def execute(self, context: PipelineContext) -> StageResult:
        """데이터 보강 실행"""
        try:
            self.logger.info("Starting data enrichment")

            race_id = context.get_race_id()

            # 기존 EnrichmentService 활용
            enriched_data = await self.collection_service.enrich_race_data(
                race_id=race_id, db=self.db_session
            )

            # 컨텍스트에 보강된 데이터 저장
            context.enriched_data = enriched_data

            # 메타데이터 생성
            metadata = {
                "enrichment_fields": [
                    "past_performances",
                    "jockey_stats",
                    "trainer_stats",
                    "weather_impact",
                ],
                "horses_enriched": len(enriched_data.get("horses", [])),
                "enrichment_quality": self._calculate_enrichment_quality(enriched_data),
            }

            self.logger.info(
                "Data enrichment completed",
                horses_enriched=metadata["horses_enriched"],
                enrichment_quality=metadata["enrichment_quality"],
            )

            return StageResult(
                status=StageStatus.COMPLETED,
                data={"enriched_data": enriched_data},
                metadata=metadata,
            )

        except Exception as e:
            self.logger.error("Data enrichment failed", error=str(e))
            return StageResult(
                status=StageStatus.FAILED, error=f"Enrichment failed: {str(e)}"
            )

    def _calculate_enrichment_quality(self, data: dict[str, Any]) -> float:
        """보강 품질 점수 계산"""
        if not data:
            return 0.0

        horses = data.get("horses", [])
        if not horses:
            return 0.0

        # 보강 필드 체크
        enrichment_fields = ["past_stats", "jockey_stats", "trainer_stats"]
        quality_scores = []

        for horse in horses:
            field_score = sum(1 for field in enrichment_fields if horse.get(field))
            quality_scores.append(field_score / len(enrichment_fields))

        return sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

    def should_skip(self, context: PipelineContext) -> bool:
        """이미 보강된 데이터가 있는 경우 생략"""
        return context.enriched_data is not None

    async def rollback(self, context: PipelineContext) -> None:
        """보강 데이터 롤백"""
        if context.enriched_data:
            self.logger.info("Clearing enriched data")
            context.enriched_data = None


class ValidationStage(PipelineStage):
    """데이터 검증 단계"""

    def __init__(self, min_horses: int = 5, min_quality_score: float = 0.7):
        super().__init__("validation")
        self.min_horses = min_horses
        self.min_quality_score = min_quality_score

    async def validate_prerequisites(self, context: PipelineContext) -> bool:
        """전제조건 검증: 보강 데이터 존재 여부"""
        if not context.enriched_data:
            self.logger.error("No enriched data available for validation")
            return False

        return True

    async def execute(self, context: PipelineContext) -> StageResult:
        """데이터 검증 실행"""
        try:
            self.logger.info("Starting data validation")

            enriched_data = context.enriched_data
            validation_result = self._validate_data(enriched_data)

            # 컨텍스트에 검증 결과 저장
            context.validation_result = validation_result

            # 검증 성공/실패 결정
            is_valid = validation_result["is_valid"]
            status = StageStatus.COMPLETED if is_valid else StageStatus.FAILED

            self.logger.info(
                "Data validation completed",
                is_valid=is_valid,
                validation_score=validation_result["validation_score"],
                errors=validation_result["errors"],
            )

            return StageResult(
                status=status,
                data={"validation_result": validation_result},
                metadata={
                    "validation_criteria": {
                        "min_horses": self.min_horses,
                        "min_quality_score": self.min_quality_score,
                    }
                },
                error=(
                    None
                    if is_valid
                    else f"Validation failed: {validation_result['errors']}"
                ),
            )

        except Exception as e:
            self.logger.error("Data validation failed", error=str(e))
            return StageResult(
                status=StageStatus.FAILED, error=f"Validation error: {str(e)}"
            )

    def _validate_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """데이터 검증 로직"""
        errors = []
        warnings = []

        # 기본 구조 검증
        if not data:
            errors.append("Empty data")

        horses = data.get("horses", [])
        horses_count = len(horses)

        # 최소 마필 수 검증
        if horses_count < self.min_horses:
            errors.append(f"Insufficient horses: {horses_count} < {self.min_horses}")

        # 데이터 품질 검증
        quality_score = self._calculate_overall_quality(data)
        if quality_score < self.min_quality_score:
            errors.append(
                f"Low quality score: {quality_score:.2f} < {self.min_quality_score}"
            )

        # 필수 필드 검증
        required_fields = ["race_date", "meet", "race_number"]
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # 마필별 데이터 검증
        for i, horse in enumerate(horses):
            horse_errors = self._validate_horse_data(horse, i + 1)
            errors.extend(horse_errors)

        validation_result = {
            "is_valid": len(errors) == 0,
            "validation_score": quality_score,
            "horses_count": horses_count,
            "errors": errors,
            "warnings": warnings,
            "validated_at": datetime.utcnow().isoformat(),
        }

        return validation_result

    def _validate_horse_data(self, horse: dict[str, Any], horse_num: int) -> list[str]:
        """개별 마필 데이터 검증"""
        errors = []

        # 필수 필드 검증
        required_fields = ["hr_no", "hr_name", "win_odds"]
        for field in required_fields:
            if not horse.get(field):
                errors.append(f"Horse {horse_num}: Missing {field}")

        # 배당률 검증
        win_odds = horse.get("win_odds")
        if win_odds is not None:
            try:
                odds_value = float(win_odds)
                if odds_value <= 0:
                    errors.append(f"Horse {horse_num}: Invalid win_odds: {odds_value}")
            except (ValueError, TypeError):
                errors.append(f"Horse {horse_num}: Invalid win_odds format: {win_odds}")

        return errors

    def _calculate_overall_quality(self, data: dict[str, Any]) -> float:
        """전체 데이터 품질 점수 계산"""
        if not data:
            return 0.0

        horses = data.get("horses", [])
        if not horses:
            return 0.0

        scores = []
        for horse in horses:
            # 기본 필드 점수
            basic_score = self._calculate_basic_horse_score(horse)
            # 보강 필드 점수
            enrichment_score = self._calculate_enrichment_horse_score(horse)

            # 가중 평균 (기본 60%, 보강 40%)
            overall_score = basic_score * 0.6 + enrichment_score * 0.4
            scores.append(overall_score)

        return sum(scores) / len(scores) if scores else 0.0

    def _calculate_basic_horse_score(self, horse: dict[str, Any]) -> float:
        """기본 마필 정보 점수"""
        required_fields = ["hr_no", "hr_name", "win_odds", "jk_no", "tr_no"]
        score = sum(1 for field in required_fields if horse.get(field))
        return score / len(required_fields)

    def _calculate_enrichment_horse_score(self, horse: dict[str, Any]) -> float:
        """보강 정보 점수"""
        enrichment_fields = ["past_stats", "jockey_stats", "trainer_stats"]
        score = sum(1 for field in enrichment_fields if horse.get(field))
        return score / len(enrichment_fields)

    def should_skip(self, context: PipelineContext) -> bool:
        """검증 결과가 이미 있는 경우 생략"""
        return context.validation_result is not None

    async def rollback(self, context: PipelineContext) -> None:
        """검증 결과 롤백"""
        if context.validation_result:
            self.logger.info("Clearing validation result")
            context.validation_result = None
