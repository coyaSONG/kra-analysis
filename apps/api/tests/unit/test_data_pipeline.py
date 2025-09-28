"""
Tests for Data Pipeline
"""

from unittest.mock import Mock

import pytest

from pipelines.base import PipelineContext
from pipelines.data_pipeline import DataProcessingPipeline, PipelineOrchestrator
from services.kra_api_service import KRAAPIService


class TestDataProcessingPipeline:
    """Test DataProcessingPipeline functionality"""

    @pytest.fixture
    def mock_kra_api_service(self):
        return Mock(spec=KRAAPIService)

    @pytest.fixture
    def mock_db_session(self):
        return Mock()

    def test_create_standard_pipeline(self, mock_kra_api_service, mock_db_session):
        """create_standard_pipeline should create pipeline with all stages"""
        pipeline = DataProcessingPipeline.create_standard_pipeline(
            mock_kra_api_service, mock_db_session
        )

        assert pipeline.name == "standard_data_processing"
        stage_names = pipeline.get_stage_names()
        assert "collection" in stage_names
        assert "preprocessing" in stage_names
        assert "enrichment" in stage_names
        assert "validation" in stage_names

    def test_create_collection_only_pipeline(
        self, mock_kra_api_service, mock_db_session
    ):
        """create_collection_only_pipeline should create pipeline with collection and preprocessing"""
        pipeline = DataProcessingPipeline.create_collection_only_pipeline(
            mock_kra_api_service, mock_db_session
        )

        assert pipeline.name == "collection_only"
        stage_names = pipeline.get_stage_names()
        assert "collection" in stage_names
        assert "preprocessing" in stage_names
        assert "enrichment" not in stage_names
        assert "validation" not in stage_names

    def test_create_enrichment_pipeline(self, mock_kra_api_service, mock_db_session):
        """create_enrichment_pipeline should create pipeline with enrichment and validation"""
        pipeline = DataProcessingPipeline.create_enrichment_pipeline(
            mock_kra_api_service, mock_db_session
        )

        assert pipeline.name == "enrichment_only"
        stage_names = pipeline.get_stage_names()
        assert "enrichment" in stage_names
        assert "validation" in stage_names
        assert "collection" not in stage_names
        assert "preprocessing" not in stage_names

    @pytest.mark.asyncio
    async def test_process_race_data_unknown_pipeline_type(
        self, mock_kra_api_service, mock_db_session
    ):
        """process_race_data should raise ValueError for unknown pipeline type"""
        with pytest.raises(ValueError) as exc_info:
            await DataProcessingPipeline.process_race_data(
                race_date="20240101",
                meet=1,
                race_number=5,
                kra_api_service=mock_kra_api_service,
                db_session=mock_db_session,
                pipeline_type="unknown_type",
            )

        assert "Unknown pipeline type" in str(exc_info.value)


class TestPipelineOrchestrator:
    """Test PipelineOrchestrator functionality"""

    @pytest.fixture
    def mock_kra_api_service(self):
        return Mock(spec=KRAAPIService)

    @pytest.fixture
    def mock_db_session(self):
        return Mock()

    @pytest.fixture
    def orchestrator(self, mock_kra_api_service, mock_db_session):
        return PipelineOrchestrator(mock_kra_api_service, mock_db_session)

    def test_get_pipeline_status_summary_empty(self, orchestrator):
        """get_pipeline_status_summary should handle empty context list"""
        summary = orchestrator.get_pipeline_status_summary([])

        assert summary["total_races"] == 0
        assert summary["successful"] == 0
        assert summary["failed"] == 0
        assert summary["success_rate"] == 0

    def test_get_pipeline_status_summary_with_data(self, orchestrator):
        """get_pipeline_status_summary should calculate statistics correctly"""
        # Create mock contexts
        successful_context = PipelineContext(
            race_date="20240101", meet=1, race_number=1
        )

        failed_context = PipelineContext(race_date="20240101", meet=1, race_number=2)
        failed_context.metadata["failed"] = True

        contexts = [successful_context, failed_context]
        summary = orchestrator.get_pipeline_status_summary(contexts)

        assert summary["total_races"] == 2
        assert summary["successful"] == 1
        assert summary["failed"] == 1
        assert summary["success_rate"] == 0.5

    @pytest.mark.asyncio
    async def test_process_race_batch_empty(self, orchestrator):
        """process_race_batch should handle empty race requests"""
        results = await orchestrator.process_race_batch([])
        assert results == []

    @pytest.mark.asyncio
    async def test_process_date_range_single_day(self, orchestrator):
        """process_date_range should handle single day correctly"""

        # Mock the process_race_batch method to avoid actual pipeline execution
        async def mock_process_race_batch(race_requests, pipeline_type, **kwargs):
            return [
                PipelineContext(
                    race_date=req["race_date"],
                    meet=req["meet"],
                    race_number=req["race_number"],
                )
                for req in race_requests
            ]

        orchestrator.process_race_batch = mock_process_race_batch

        results = await orchestrator.process_date_range(
            start_date="20240101",
            end_date="20240101",
            meets=[1],
            race_numbers=[1, 2],
            pipeline_type="collection_only",
        )

        # Should create 1 day * 1 meet * 2 races = 2 requests
        assert len(results) == 2
        assert all(ctx.race_date == "20240101" for ctx in results)
        assert any(ctx.race_number == 1 for ctx in results)
        assert any(ctx.race_number == 2 for ctx in results)
