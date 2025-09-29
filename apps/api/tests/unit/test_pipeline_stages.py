"""
Tests for Pipeline Stages
"""

from unittest.mock import AsyncMock, Mock

import pytest

from pipelines.base import PipelineContext, StageStatus
from pipelines.stages import (
    CollectionStage,
    PreprocessingStage,
    ValidationStage,
)
from services.kra_api_service import KRAAPIService


class TestCollectionStage:
    """Test CollectionStage functionality"""

    @pytest.fixture
    def mock_kra_api_service(self):
        return Mock(spec=KRAAPIService)

    @pytest.fixture
    def mock_db_session(self):
        return Mock()

    @pytest.fixture
    def collection_stage(self, mock_kra_api_service, mock_db_session):
        return CollectionStage(mock_kra_api_service, mock_db_session)

    @pytest.fixture
    def pipeline_context(self):
        return PipelineContext(race_date="20240101", meet=1, race_number=5)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_prerequisites_success(
        self, collection_stage, pipeline_context
    ):
        """CollectionStage should validate prerequisites successfully"""
        result = await collection_stage.validate_prerequisites(pipeline_context)
        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_prerequisites_missing_service(
        self, mock_db_session, pipeline_context
    ):
        """CollectionStage should fail validation when KRA API service is missing"""
        stage = CollectionStage(None, mock_db_session)
        result = await stage.validate_prerequisites(pipeline_context)
        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_prerequisites_missing_session(
        self, mock_kra_api_service, pipeline_context
    ):
        """CollectionStage should fail validation when DB session is missing"""
        stage = CollectionStage(mock_kra_api_service, None)
        result = await stage.validate_prerequisites(pipeline_context)
        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_prerequisites_invalid_params(self, collection_stage):
        """CollectionStage should fail validation with invalid race parameters"""
        context = PipelineContext(race_date="", meet=0, race_number=0)
        result = await collection_stage.validate_prerequisites(context)
        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_success(self, collection_stage, pipeline_context):
        """CollectionStage should execute successfully"""
        # Mock the collection service
        mock_collected_data = {
            "race_date": "20240101",
            "meet": 1,
            "race_number": 5,
            "horses": [{"hr_no": "001", "hr_name": "Test Horse", "win_odds": 5.2}],
        }

        collection_stage.collection_service.collect_race_data = AsyncMock(
            return_value=mock_collected_data
        )

        result = await collection_stage.execute(pipeline_context)

        assert result.status == StageStatus.COMPLETED
        assert pipeline_context.raw_data == mock_collected_data
        assert result.metadata["horses_count"] == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_failure(self, collection_stage, pipeline_context):
        """CollectionStage should handle execution failure"""
        collection_stage.collection_service.collect_race_data = AsyncMock(
            side_effect=Exception("Collection failed")
        )

        result = await collection_stage.execute(pipeline_context)

        assert result.status == StageStatus.FAILED
        assert "Collection failed" in result.error

    def test_should_skip_with_existing_data(self, collection_stage, pipeline_context):
        """CollectionStage should skip when raw data already exists"""
        pipeline_context.raw_data = {"existing": "data"}
        assert collection_stage.should_skip(pipeline_context) is True

    def test_should_not_skip_without_data(self, collection_stage, pipeline_context):
        """CollectionStage should not skip when no raw data exists"""
        assert collection_stage.should_skip(pipeline_context) is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rollback(self, collection_stage, pipeline_context):
        """CollectionStage should clear raw data on rollback"""
        pipeline_context.raw_data = {"some": "data"}
        await collection_stage.rollback(pipeline_context)
        assert pipeline_context.raw_data is None


class TestPreprocessingStage:
    """Test PreprocessingStage functionality"""

    @pytest.fixture
    def preprocessing_stage(self):
        return PreprocessingStage()

    @pytest.fixture
    def pipeline_context_with_raw_data(self):
        context = PipelineContext(race_date="20240101", meet=1, race_number=5)
        context.raw_data = {
            "horses": [
                {"hr_no": "001", "win_odds": 5.2},  # Valid
                {"hr_no": "002", "win_odds": 0},  # Invalid (기권/제외마)
                {"hr_no": "003", "win_odds": 3.1},  # Valid
                {"hr_no": "004", "win_odds": "invalid"},  # Invalid format
            ]
        }
        return context

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_prerequisites_success(
        self, preprocessing_stage, pipeline_context_with_raw_data
    ):
        """PreprocessingStage should validate prerequisites successfully"""
        result = await preprocessing_stage.validate_prerequisites(
            pipeline_context_with_raw_data
        )
        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_prerequisites_no_raw_data(self, preprocessing_stage):
        """PreprocessingStage should fail validation without raw data"""
        context = PipelineContext(race_date="20240101", meet=1, race_number=5)
        result = await preprocessing_stage.validate_prerequisites(context)
        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_success(
        self, preprocessing_stage, pipeline_context_with_raw_data
    ):
        """PreprocessingStage should filter invalid horses successfully"""
        result = await preprocessing_stage.execute(pipeline_context_with_raw_data)

        assert result.status == StageStatus.COMPLETED
        assert pipeline_context_with_raw_data.preprocessed_data is not None

        # Should filter out horses with win_odds = 0 or invalid format
        horses = pipeline_context_with_raw_data.preprocessed_data["horses"]
        assert len(horses) == 2  # Only 2 valid horses

        valid_horse_numbers = [horse["hr_no"] for horse in horses]
        assert "001" in valid_horse_numbers
        assert "003" in valid_horse_numbers
        assert "002" not in valid_horse_numbers  # Filtered out (win_odds = 0)
        assert "004" not in valid_horse_numbers  # Filtered out (invalid format)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_failure(self, preprocessing_stage):
        """PreprocessingStage should handle execution failure"""
        context = PipelineContext(race_date="20240101", meet=1, race_number=5)
        context.raw_data = None  # This will cause an error

        result = await preprocessing_stage.execute(context)
        assert result.status == StageStatus.FAILED

    def test_should_skip_with_existing_data(self, preprocessing_stage):
        """PreprocessingStage should skip when preprocessed data already exists"""
        context = PipelineContext(race_date="20240101", meet=1, race_number=5)
        context.preprocessed_data = {"existing": "data"}
        assert preprocessing_stage.should_skip(context) is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rollback(self, preprocessing_stage):
        """PreprocessingStage should clear preprocessed data on rollback"""
        context = PipelineContext(race_date="20240101", meet=1, race_number=5)
        context.preprocessed_data = {"some": "data"}
        await preprocessing_stage.rollback(context)
        assert context.preprocessed_data is None


class TestValidationStage:
    """Test ValidationStage functionality"""

    @pytest.fixture
    def validation_stage(self):
        return ValidationStage(min_horses=2, min_quality_score=0.5)

    @pytest.fixture
    def pipeline_context_with_enriched_data(self):
        context = PipelineContext(race_date="20240101", meet=1, race_number=5)
        context.enriched_data = {
            "race_date": "20240101",
            "meet": 1,
            "race_number": 5,
            "horses": [
                {
                    "hr_no": "001",
                    "hr_name": "Horse 1",
                    "win_odds": 5.2,
                    "jk_no": "J001",
                    "tr_no": "T001",
                    "past_stats": {"wins": 2},
                    "jockey_stats": {"win_rate": 0.2},
                    "trainer_stats": {"win_rate": 0.15},
                },
                {
                    "hr_no": "002",
                    "hr_name": "Horse 2",
                    "win_odds": 3.1,
                    "jk_no": "J002",
                    "tr_no": "T002",
                    "past_stats": {"wins": 1},
                    "jockey_stats": {"win_rate": 0.18},
                    "trainer_stats": {"win_rate": 0.12},
                },
            ],
        }
        return context

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_prerequisites_success(
        self, validation_stage, pipeline_context_with_enriched_data
    ):
        """ValidationStage should validate prerequisites successfully"""
        result = await validation_stage.validate_prerequisites(
            pipeline_context_with_enriched_data
        )
        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_validate_prerequisites_no_enriched_data(self, validation_stage):
        """ValidationStage should fail validation without enriched data"""
        context = PipelineContext(race_date="20240101", meet=1, race_number=5)
        result = await validation_stage.validate_prerequisites(context)
        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_success(
        self, validation_stage, pipeline_context_with_enriched_data
    ):
        """ValidationStage should validate data successfully"""
        result = await validation_stage.execute(pipeline_context_with_enriched_data)

        assert result.status == StageStatus.COMPLETED
        assert pipeline_context_with_enriched_data.validation_result is not None
        assert pipeline_context_with_enriched_data.validation_result["is_valid"] is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_insufficient_horses(
        self, pipeline_context_with_enriched_data
    ):
        """ValidationStage should fail with insufficient horses"""
        validation_stage = ValidationStage(min_horses=5, min_quality_score=0.5)

        result = await validation_stage.execute(pipeline_context_with_enriched_data)

        assert result.status == StageStatus.FAILED
        assert "Insufficient horses" in result.error

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_low_quality(self):
        """ValidationStage should fail with low quality score"""
        validation_stage = ValidationStage(min_horses=2, min_quality_score=0.9)

        # Create context with low quality data (missing required fields)
        context = PipelineContext(race_date="20240101", meet=1, race_number=5)
        context.enriched_data = {
            "race_date": "20240101",
            "meet": 1,
            "race_number": 5,
            "horses": [
                {
                    "hr_no": "001",
                    # Missing hr_name, win_odds, jk_no, tr_no, and enrichment fields
                },
                {
                    "hr_no": "002",
                    "hr_name": "Horse 2",
                    # Missing other required fields
                },
            ],
        }

        result = await validation_stage.execute(context)

        assert result.status == StageStatus.FAILED
        assert "Low quality score" in result.error

    def test_should_skip_with_existing_validation(self, validation_stage):
        """ValidationStage should skip when validation result already exists"""
        context = PipelineContext(race_date="20240101", meet=1, race_number=5)
        context.validation_result = {"is_valid": True}
        assert validation_stage.should_skip(context) is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rollback(self, validation_stage):
        """ValidationStage should clear validation result on rollback"""
        context = PipelineContext(race_date="20240101", meet=1, race_number=5)
        context.validation_result = {"is_valid": True}
        await validation_stage.rollback(context)
        assert context.validation_result is None
