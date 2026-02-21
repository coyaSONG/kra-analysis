"""
Pipeline Base Classes
데이터 처리 파이프라인의 기본 인터페이스와 추상 클래스들
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class StageStatus(str, Enum):
    """파이프라인 단계 상태"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStatus(str, Enum):
    """파이프라인 전체 상태"""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class StageResult:
    """파이프라인 단계 실행 결과"""

    status: StageStatus
    data: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    execution_time_ms: int | None = None
    stage_name: str | None = None

    def is_success(self) -> bool:
        """성공 여부 확인"""
        return self.status == StageStatus.COMPLETED

    def is_failure(self) -> bool:
        """실패 여부 확인"""
        return self.status == StageStatus.FAILED


@dataclass
class PipelineContext:
    """파이프라인 실행 컨텍스트"""

    # 입력 파라미터
    race_date: str
    meet: int
    race_number: int

    # 처리 데이터 (단계별로 누적)
    raw_data: dict[str, Any] | None = None
    preprocessed_data: dict[str, Any] | None = None
    enriched_data: dict[str, Any] | None = None
    validation_result: dict[str, Any] | None = None

    # 메타데이터
    pipeline_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # 진행 상황 추적
    current_stage: str | None = None
    stage_results: dict[str, StageResult] = field(default_factory=dict)

    def add_stage_result(self, stage_name: str, result: StageResult) -> None:
        """단계 결과 추가"""
        result.stage_name = stage_name
        self.stage_results[stage_name] = result

    def get_stage_result(self, stage_name: str) -> StageResult | None:
        """특정 단계 결과 조회"""
        return self.stage_results.get(stage_name)

    def is_stage_completed(self, stage_name: str) -> bool:
        """특정 단계 완료 여부 확인"""
        result = self.get_stage_result(stage_name)
        return result is not None and result.is_success()

    def get_race_id(self) -> str:
        """경주 ID 생성"""
        return f"{self.race_date}_{self.meet}_{self.race_number}"

    def get_execution_time_ms(self) -> int | None:
        """전체 실행 시간 계산 (밀리초)"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() * 1000)
        return None


class PipelineStage(ABC):
    """파이프라인 단계 추상 클래스"""

    def __init__(self, name: str):
        self.name = name
        self.logger = structlog.get_logger().bind(stage=name)

    @abstractmethod
    async def execute(self, context: PipelineContext) -> StageResult:
        """
        단계 실행

        Args:
            context: 파이프라인 컨텍스트

        Returns:
            단계 실행 결과
        """
        pass

    @abstractmethod
    async def validate_prerequisites(self, context: PipelineContext) -> bool:
        """
        전제조건 검증

        Args:
            context: 파이프라인 컨텍스트

        Returns:
            전제조건 만족 여부
        """
        pass

    async def rollback(self, context: PipelineContext) -> None:
        """
        롤백 처리 (선택적 구현)

        Args:
            context: 파이프라인 컨텍스트
        """
        self.logger.info("No rollback needed for stage", stage=self.name)

    def should_skip(self, context: PipelineContext) -> bool:
        """
        단계 생략 여부 결정

        Args:
            context: 파이프라인 컨텍스트

        Returns:
            생략 여부
        """
        return False


class Pipeline:
    """데이터 처리 파이프라인"""

    def __init__(self, name: str):
        self.name = name
        self.stages: list[PipelineStage] = []
        self.status = PipelineStatus.IDLE
        self.logger = structlog.get_logger().bind(pipeline=name)

    def add_stage(self, stage: PipelineStage) -> "Pipeline":
        """파이프라인에 단계 추가"""
        self.stages.append(stage)
        return self

    def add_stages(self, stages: list[PipelineStage]) -> "Pipeline":
        """파이프라인에 여러 단계 추가"""
        self.stages.extend(stages)
        return self

    async def execute(self, context: PipelineContext) -> PipelineContext:
        """
        파이프라인 실행

        Args:
            context: 파이프라인 컨텍스트

        Returns:
            업데이트된 컨텍스트

        Raises:
            PipelineExecutionError: 파이프라인 실행 실패
        """
        self.status = PipelineStatus.RUNNING
        context.started_at = datetime.now(UTC)
        context.pipeline_id = (
            f"{self.name}_{context.get_race_id()}_{int(context.started_at.timestamp())}"
        )

        self.logger.info(
            "Starting pipeline execution",
            pipeline_id=context.pipeline_id,
            race_id=context.get_race_id(),
            stages_count=len(self.stages),
        )

        executed_stages = []

        try:
            for stage in self.stages:
                context.current_stage = stage.name

                # 생략 여부 확인
                if stage.should_skip(context):
                    self.logger.info("Skipping stage", stage=stage.name)
                    result = StageResult(
                        status=StageStatus.SKIPPED,
                        metadata={"reason": "stage_skip_condition_met"},
                    )
                    context.add_stage_result(stage.name, result)
                    continue

                # 전제조건 검증
                if not await stage.validate_prerequisites(context):
                    error_msg = f"Prerequisites not met for stage: {stage.name}"
                    self.logger.error(error_msg, stage=stage.name)
                    result = StageResult(status=StageStatus.FAILED, error=error_msg)
                    context.add_stage_result(stage.name, result)
                    raise PipelineExecutionError(error_msg)

                # 단계 실행
                self.logger.info("Executing stage", stage=stage.name)
                start_time = datetime.now(UTC)

                try:
                    result = await stage.execute(context)
                    result.execution_time_ms = int(
                        (datetime.now(UTC) - start_time).total_seconds() * 1000
                    )

                    if result.is_failure():
                        raise PipelineExecutionError(
                            f"Stage {stage.name} failed: {result.error}"
                        )

                    context.add_stage_result(stage.name, result)
                    executed_stages.append(stage)

                    self.logger.info(
                        "Stage completed successfully",
                        stage=stage.name,
                        execution_time_ms=result.execution_time_ms,
                    )

                except Exception as e:
                    error_msg = f"Stage {stage.name} execution error: {str(e)}"
                    self.logger.error(error_msg, stage=stage.name, error=str(e))

                    result = StageResult(
                        status=StageStatus.FAILED,
                        error=error_msg,
                        execution_time_ms=int(
                            (datetime.now(UTC) - start_time).total_seconds() * 1000
                        ),
                    )
                    context.add_stage_result(stage.name, result)
                    raise PipelineExecutionError(error_msg) from e

            # 성공적 완료
            self.status = PipelineStatus.COMPLETED
            context.completed_at = datetime.now(UTC)

            self.logger.info(
                "Pipeline completed successfully",
                pipeline_id=context.pipeline_id,
                execution_time_ms=context.get_execution_time_ms(),
                stages_executed=len(executed_stages),
            )

            return context

        except Exception as e:
            # 실패 시 롤백 수행
            self.status = PipelineStatus.FAILED
            context.completed_at = datetime.now(UTC)

            self.logger.error(
                "Pipeline failed, performing rollback",
                pipeline_id=context.pipeline_id,
                error=str(e),
                executed_stages=[s.name for s in executed_stages],
            )

            # 실행된 단계들을 역순으로 롤백
            for stage in reversed(executed_stages):
                try:
                    await stage.rollback(context)
                    self.logger.info("Stage rollback completed", stage=stage.name)
                except Exception as rollback_error:
                    self.logger.error(
                        "Stage rollback failed",
                        stage=stage.name,
                        error=str(rollback_error),
                    )

            raise

    def get_stage_names(self) -> list[str]:
        """파이프라인 단계 이름 목록 반환"""
        return [stage.name for stage in self.stages]

    def reset(self) -> None:
        """파이프라인 상태 초기화"""
        self.status = PipelineStatus.IDLE


class PipelineExecutionError(Exception):
    """파이프라인 실행 오류"""

    pass


class PipelineBuilder:
    """파이프라인 빌더 (Builder 패턴)"""

    def __init__(self, name: str):
        self.pipeline = Pipeline(name)

    def add_stage(self, stage: PipelineStage) -> "PipelineBuilder":
        """단계 추가"""
        self.pipeline.add_stage(stage)
        return self

    def add_collection_stage(self, **kwargs) -> "PipelineBuilder":
        """수집 단계 추가"""
        from .stages import CollectionStage

        stage = CollectionStage(**kwargs)
        return self.add_stage(stage)

    def add_preprocessing_stage(self, **kwargs) -> "PipelineBuilder":
        """전처리 단계 추가"""
        from .stages import PreprocessingStage

        stage = PreprocessingStage(**kwargs)
        return self.add_stage(stage)

    def add_enrichment_stage(self, **kwargs) -> "PipelineBuilder":
        """보강 단계 추가"""
        from .stages import EnrichmentStage

        stage = EnrichmentStage(**kwargs)
        return self.add_stage(stage)

    def add_validation_stage(self, **kwargs) -> "PipelineBuilder":
        """검증 단계 추가"""
        from .stages import ValidationStage

        stage = ValidationStage(**kwargs)
        return self.add_stage(stage)

    def build(self) -> Pipeline:
        """파이프라인 빌드"""
        return self.pipeline
