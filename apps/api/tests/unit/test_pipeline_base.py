"""
Tests for Pipeline Base Classes
"""

from datetime import datetime

import pytest

from pipelines.base import (
    Pipeline,
    PipelineBuilder,
    PipelineContext,
    PipelineExecutionError,
    PipelineStage,
    PipelineStatus,
    StageResult,
    StageStatus,
)


class MockStage(PipelineStage):
    """Mock stage for testing"""

    def __init__(self, name: str, should_fail: bool = False, should_skip: bool = False):
        super().__init__(name)
        self.should_fail = should_fail
        self.should_skip_flag = should_skip
        self.executed = False
        self.rolled_back = False

    async def validate_prerequisites(self, context: PipelineContext) -> bool:
        return True

    async def execute(self, context: PipelineContext) -> StageResult:
        self.executed = True
        if self.should_fail:
            return StageResult(status=StageStatus.FAILED, error="Mock stage failure")

        return StageResult(
            status=StageStatus.COMPLETED, data={"mock_data": f"data_from_{self.name}"}
        )

    def should_skip(self, context: PipelineContext) -> bool:
        return self.should_skip_flag

    async def rollback(self, context: PipelineContext) -> None:
        self.rolled_back = True


class TestPipelineContext:
    """Test PipelineContext functionality"""

    def test_pipeline_context_creation(self):
        """PipelineContext should be created with basic race information"""
        context = PipelineContext(race_date="20240101", meet=1, race_number=5)

        assert context.race_date == "20240101"
        assert context.meet == 1
        assert context.race_number == 5
        assert context.get_race_id() == "20240101_1_5"

    def test_stage_result_management(self):
        """PipelineContext should manage stage results properly"""
        context = PipelineContext(race_date="20240101", meet=1, race_number=5)

        result = StageResult(status=StageStatus.COMPLETED, data={"test": "data"})

        context.add_stage_result("test_stage", result)

        assert "test_stage" in context.stage_results
        assert context.get_stage_result("test_stage") == result
        assert context.is_stage_completed("test_stage") is True
        assert context.is_stage_completed("nonexistent_stage") is False

    def test_execution_time_calculation(self):
        """PipelineContext should calculate execution time correctly"""
        context = PipelineContext(race_date="20240101", meet=1, race_number=5)

        start_time = datetime(2024, 1, 1, 10, 0, 0)
        end_time = datetime(2024, 1, 1, 10, 0, 5)  # 5 seconds later

        context.started_at = start_time
        context.completed_at = end_time

        execution_time = context.get_execution_time_ms()
        assert execution_time == 5000  # 5 seconds = 5000 ms


class TestStageResult:
    """Test StageResult functionality"""

    def test_stage_result_success(self):
        """StageResult should correctly identify success"""
        result = StageResult(status=StageStatus.COMPLETED)
        assert result.is_success() is True
        assert result.is_failure() is False

    def test_stage_result_failure(self):
        """StageResult should correctly identify failure"""
        result = StageResult(status=StageStatus.FAILED, error="Test error")
        assert result.is_success() is False
        assert result.is_failure() is True


class TestPipeline:
    """Test Pipeline functionality"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_pipeline_execution_success(self):
        """Pipeline should execute all stages successfully"""
        stage1 = MockStage("stage1")
        stage2 = MockStage("stage2")

        pipeline = Pipeline("test_pipeline")
        pipeline.add_stages([stage1, stage2])

        context = PipelineContext(race_date="20240101", meet=1, race_number=5)

        result_context = await pipeline.execute(context)

        assert pipeline.status == PipelineStatus.COMPLETED
        assert stage1.executed is True
        assert stage2.executed is True
        assert result_context.is_stage_completed("stage1")
        assert result_context.is_stage_completed("stage2")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_pipeline_execution_failure(self):
        """Pipeline should handle stage failures and perform rollback"""
        stage1 = MockStage("stage1")
        stage2 = MockStage("stage2", should_fail=True)
        stage3 = MockStage("stage3")

        pipeline = Pipeline("test_pipeline")
        pipeline.add_stages([stage1, stage2, stage3])

        context = PipelineContext(race_date="20240101", meet=1, race_number=5)

        with pytest.raises(PipelineExecutionError):
            await pipeline.execute(context)

        assert pipeline.status == PipelineStatus.FAILED
        assert stage1.executed is True
        assert stage2.executed is True
        assert stage3.executed is False  # Should not execute after failure
        assert stage1.rolled_back is True  # Should be rolled back
        assert stage2.rolled_back is False  # Failed stage shouldn't rollback

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_pipeline_stage_skipping(self):
        """Pipeline should skip stages when should_skip returns True"""
        stage1 = MockStage("stage1")
        stage2 = MockStage("stage2", should_skip=True)
        stage3 = MockStage("stage3")

        pipeline = Pipeline("test_pipeline")
        pipeline.add_stages([stage1, stage2, stage3])

        context = PipelineContext(race_date="20240101", meet=1, race_number=5)

        result_context = await pipeline.execute(context)

        assert pipeline.status == PipelineStatus.COMPLETED
        assert stage1.executed is True
        assert stage2.executed is False  # Should be skipped
        assert stage3.executed is True
        assert result_context.get_stage_result("stage2").status == StageStatus.SKIPPED

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_pipeline_prerequisite_failure(self):
        """Pipeline should fail when prerequisites are not met"""

        class FailingPrereqStage(MockStage):
            async def validate_prerequisites(self, context: PipelineContext) -> bool:
                return False

        stage1 = MockStage("stage1")
        stage2 = FailingPrereqStage("stage2")

        pipeline = Pipeline("test_pipeline")
        pipeline.add_stages([stage1, stage2])

        context = PipelineContext(race_date="20240101", meet=1, race_number=5)

        with pytest.raises(PipelineExecutionError) as exc_info:
            await pipeline.execute(context)

        assert "Prerequisites not met" in str(exc_info.value)
        assert pipeline.status == PipelineStatus.FAILED
        assert stage1.rolled_back is True

    def test_pipeline_builder(self):
        """PipelineBuilder should create pipelines correctly"""
        builder = PipelineBuilder("test_pipeline")
        stage1 = MockStage("stage1")
        stage2 = MockStage("stage2")

        pipeline = builder.add_stage(stage1).add_stage(stage2).build()

        assert pipeline.name == "test_pipeline"
        assert len(pipeline.stages) == 2
        assert pipeline.stages[0] == stage1
        assert pipeline.stages[1] == stage2

    def test_pipeline_stage_names(self):
        """Pipeline should return correct stage names"""
        stage1 = MockStage("stage1")
        stage2 = MockStage("stage2")

        pipeline = Pipeline("test_pipeline")
        pipeline.add_stages([stage1, stage2])

        stage_names = pipeline.get_stage_names()
        assert stage_names == ["stage1", "stage2"]

    def test_pipeline_reset(self):
        """Pipeline should reset status correctly"""
        pipeline = Pipeline("test_pipeline")
        pipeline.status = PipelineStatus.COMPLETED

        pipeline.reset()
        assert pipeline.status == PipelineStatus.IDLE
