"""
Tests covering uncovered lines in:
- routers/jobs_v2.py (lines 71-101, 118-163, 179-186)
- services/job_service.py (lines 108-111, 130, 133, 155-158, 256-257, 284, 298, 311, 331-334, 359-367, 383, 434, 440, 447-448, 462-465, 504-507, 522-574)
- pipelines/data_pipeline.py (lines 147-163, 199-218, 224-225, 234-246, 315-322)
"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from httpx import AsyncClient

from models.database_models import Job, JobLog, JobStatus, JobType
from pipelines.base import PipelineContext, StageResult, StageStatus
from pipelines.data_pipeline import DataProcessingPipeline, PipelineOrchestrator
from services.job_service import JobService

# ---------------------------------------------------------------------------
# routers/jobs_v2.py
# ---------------------------------------------------------------------------


class TestJobsRouterListJobs:
    """GET /api/v2/jobs/ - lines 71-101"""

    @pytest.mark.asyncio
    async def test_list_jobs_returns_dto_with_job_data(
        self, authenticated_client: AsyncClient, db_session
    ):
        """list_jobs converts DB models to DTOs and returns JobListResponse."""
        job = Job(
            type=JobType.COLLECTION,
            status=JobStatus.PENDING,
            parameters={"race_date": "20240101"},
            created_by="test-api-key-123",
            progress=25,
            current_step="collecting",
            total_steps=3,
            retry_count=1,
            tags=["test"],
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        resp = await authenticated_client.get("/api/v2/jobs/?limit=10&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert data["limit"] == 10
        assert data["offset"] == 0

        found = [j for j in data["jobs"] if j["job_id"] == job.job_id]
        assert len(found) == 1
        dto = found[0]
        assert dto["type"] == "collection"
        assert dto["status"] == "pending"
        assert dto["progress"] == 25
        assert dto["current_step"] == "collecting"
        assert dto["total_steps"] == 3
        assert dto["retry_count"] == 1
        assert dto["tags"] == ["test"]
        assert dto["created_by"] == "test-api-key-123"
        assert dto["parameters"] == {"race_date": "20240101"}

    @pytest.mark.asyncio
    async def test_list_jobs_empty(self, authenticated_client: AsyncClient):
        """list_jobs with no data returns empty list."""
        resp = await authenticated_client.get("/api/v2/jobs/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["jobs"] == []
        assert data["total"] == 0


class TestJobsRouterGetJob:
    """GET /api/v2/jobs/{job_id} - lines 118-163"""

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, authenticated_client: AsyncClient):
        """get_job returns 404 for missing job."""
        resp = await authenticated_client.get("/api/v2/jobs/nonexistent-id")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_job_with_logs(
        self, authenticated_client: AsyncClient, db_session
    ):
        """get_job returns job detail with logs."""
        job = Job(
            type=JobType.COLLECTION,
            status=JobStatus.COMPLETED,
            parameters={"meet": 1},
            created_by="test-api-key-123",
            progress=100,
            retry_count=0,
            tags=[],
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        log = JobLog(
            job_id=job.job_id,
            level="INFO",
            message="Started collecting",
            log_metadata={"step": 1},
        )
        db_session.add(log)
        await db_session.commit()

        resp = await authenticated_client.get(f"/api/v2/jobs/{job.job_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["job"]["job_id"] == job.job_id
        assert data["job"]["status"] == "completed"
        assert data["job"]["type"] == "collection"
        assert len(data["logs"]) >= 1
        assert data["logs"][0]["level"] == "INFO"
        assert data["logs"][0]["message"] == "Started collecting"

    @pytest.mark.asyncio
    async def test_get_job_exception_returns_500(
        self, authenticated_client: AsyncClient, db_session
    ):
        """get_job returns 500 when service raises unexpected exception."""
        with patch(
            "routers.jobs_v2.job_service.get_job",
            new_callable=AsyncMock,
            side_effect=RuntimeError("db crash"),
        ):
            resp = await authenticated_client.get("/api/v2/jobs/some-job-id")
            assert resp.status_code == 500
            assert "db crash" in resp.json()["detail"]


class TestJobsRouterCancelJob:
    """POST /api/v2/jobs/{job_id}/cancel - lines 179-186"""

    @pytest.mark.asyncio
    async def test_cancel_job_success(
        self, authenticated_client: AsyncClient, db_session
    ):
        """cancel_job returns success message."""
        job = Job(
            type=JobType.COLLECTION,
            status=JobStatus.PENDING,
            parameters={},
            created_by="test-api-key-123",
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        resp = await authenticated_client.post(f"/api/v2/jobs/{job.job_id}/cancel")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Job cancelled successfully"

    @pytest.mark.asyncio
    async def test_cancel_job_not_found(self, authenticated_client: AsyncClient):
        """cancel_job returns 404 for missing job."""
        resp = await authenticated_client.post("/api/v2/jobs/nonexistent-id/cancel")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_job_exception_returns_500(
        self, authenticated_client: AsyncClient
    ):
        """cancel_job returns 500 when service raises unexpected exception."""
        with patch(
            "routers.jobs_v2.job_service.cancel_job",
            new_callable=AsyncMock,
            side_effect=RuntimeError("task runner down"),
        ):
            resp = await authenticated_client.post("/api/v2/jobs/some-job-id/cancel")
            assert resp.status_code == 500
            assert "task runner down" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# services/job_service.py
# ---------------------------------------------------------------------------


class TestJobServiceCreateJobException:
    """create_job exception path - lines 108-111"""

    @pytest.mark.asyncio
    async def test_create_job_rollback_on_exception(self, db_session):
        """create_job rolls back and re-raises on commit failure."""
        service = JobService()

        original_commit = db_session.commit

        async def failing_commit():
            raise RuntimeError("commit failed")

        db_session.commit = failing_commit

        with pytest.raises(RuntimeError, match="commit failed"):
            await service.create_job(
                job_type=JobType.COLLECTION.value,
                parameters={"race_date": "20240101"},
                owner_ref="tester",
                db=db_session,
            )

        db_session.commit = original_commit


class TestJobServiceStartJob:
    """start_job - lines 130, 133, 155-158"""

    @pytest.mark.asyncio
    async def test_start_job_not_found(self, db_session):
        """start_job raises ValueError for missing job."""
        service = JobService()
        with pytest.raises(ValueError, match="Job not found"):
            await service.start_job("nonexistent-id", db_session)

    @pytest.mark.asyncio
    async def test_start_job_already_started(self, db_session):
        """start_job raises ValueError for non-pending job."""
        service = JobService()
        job = Job(
            type=JobType.COLLECTION,
            status=JobStatus.PROCESSING,
            parameters={},
            created_by="tester",
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        with pytest.raises(ValueError, match="already started"):
            await service.start_job(job.job_id, db_session)

    @pytest.mark.asyncio
    async def test_start_job_exception_rollback(self, monkeypatch, db_session):
        """start_job rolls back on dispatch failure."""
        service = JobService()
        job = Job(
            type=JobType.COLLECTION,
            status=JobStatus.PENDING,
            parameters={"race_date": "20240101", "meet": 1, "race_numbers": [1]},
            created_by="tester",
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        async def failing_dispatch(_self, _job):
            raise RuntimeError("dispatch failed")

        monkeypatch.setattr(JobService, "_dispatch_task", failing_dispatch)

        with pytest.raises(RuntimeError, match="dispatch failed"):
            await service.start_job(job.job_id, db_session)


class TestJobServiceGetJobStatus:
    """get_job_status - lines 256-257"""

    @pytest.mark.asyncio
    async def test_get_job_status_bg_task_failure(self, db_session):
        """get_job_status logs warning when background task status fails."""
        service = JobService()
        job = Job(
            type=JobType.COLLECTION,
            status=JobStatus.PROCESSING,
            parameters={},
            created_by="tester",
        )
        job.task_id = "task-fail"
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        with patch(
            "services.job_service.get_task_status",
            new_callable=AsyncMock,
            side_effect=RuntimeError("redis down"),
        ):
            status = await service.get_job_status(job.job_id, db_session)
            assert status is not None
            assert status["task_status"] is None
            assert status["job_id"] == job.job_id


class TestJobServiceCalculateProgress:
    """_calculate_progress - lines 284, 298"""

    def test_queued_status_returns_5(self):
        """_calculate_progress returns 5 for queued status."""
        service = JobService()
        job = SimpleNamespace(status="queued", type="collection")
        assert service._calculate_progress(job, None) == 5

    def test_unknown_status_returns_0(self):
        """_calculate_progress returns 0 for unknown status."""
        service = JobService()
        job = SimpleNamespace(status="some_unknown_status", type="collection")
        assert service._calculate_progress(job, None) == 0

    def test_completed_returns_100(self):
        """_calculate_progress returns 100 for completed."""
        service = JobService()
        job = SimpleNamespace(status="completed", type="collection")
        assert service._calculate_progress(job, None) == 100

    def test_failed_returns_0(self):
        """_calculate_progress returns 0 for failed."""
        service = JobService()
        job = SimpleNamespace(status="failed", type="collection")
        assert service._calculate_progress(job, None) == 0

    def test_pending_returns_0(self):
        """_calculate_progress returns 0 for pending."""
        service = JobService()
        job = SimpleNamespace(status="pending", type="collection")
        assert service._calculate_progress(job, None) == 0

    def test_processing_non_pipeline_returns_50(self):
        """_calculate_progress returns 50 for processing non-full_pipeline."""
        service = JobService()
        job = SimpleNamespace(status="processing", type="collection")
        assert service._calculate_progress(job, None) == 50


class TestJobServiceGetJobLogs:
    """get_job_logs - line 311"""

    @pytest.mark.asyncio
    async def test_get_job_logs_returns_list(self, db_session):
        """get_job_logs returns a list of JobLog objects."""
        service = JobService()
        job = Job(
            type=JobType.COLLECTION,
            status=JobStatus.PENDING,
            parameters={},
            created_by="tester",
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        log1 = JobLog(
            job_id=job.job_id, level="INFO", message="step 1", log_metadata={}
        )
        log2 = JobLog(
            job_id=job.job_id, level="ERROR", message="step 2 failed", log_metadata={}
        )
        db_session.add_all([log1, log2])
        await db_session.commit()

        logs = await service.get_job_logs(job.job_id, db_session)
        assert isinstance(logs, list)
        assert len(logs) == 2


class TestJobServiceAddJobLogException:
    """add_job_log exception path - lines 331-334"""

    @pytest.mark.asyncio
    async def test_add_job_log_rollback_on_exception(self, db_session):
        """add_job_log rolls back and re-raises on commit failure."""
        service = JobService()
        job = Job(
            type=JobType.COLLECTION,
            status=JobStatus.PENDING,
            parameters={},
            created_by="tester",
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        original_commit = db_session.commit

        async def failing_commit():
            raise RuntimeError("log commit failed")

        db_session.commit = failing_commit

        with pytest.raises(RuntimeError, match="log commit failed"):
            await service.add_job_log(
                job.job_id, "INFO", "test message", {"key": "value"}, db_session
            )

        db_session.commit = original_commit


class TestJobServiceListJobs:
    """list_jobs / list_jobs_with_total - lines 359-367, 383"""

    @pytest.mark.asyncio
    async def test_list_jobs_delegates_to_list_jobs_with_total(self, db_session):
        """list_jobs returns just the job list (no total)."""
        service = JobService()
        job = Job(
            type=JobType.COLLECTION,
            status=JobStatus.PENDING,
            parameters={},
            created_by="tester",
        )
        db_session.add(job)
        await db_session.commit()

        jobs = await service.list_jobs(db=db_session, owner_ref="tester")
        assert isinstance(jobs, list)
        assert len(jobs) == 1

    @pytest.mark.asyncio
    async def test_list_jobs_with_total_job_type_filter(self, db_session):
        """list_jobs_with_total filters by job_type."""
        service = JobService()
        j1 = Job(
            type=JobType.COLLECTION,
            status=JobStatus.PENDING,
            parameters={},
            created_by="tester",
        )
        j2 = Job(
            type=JobType.ENRICHMENT,
            status=JobStatus.PENDING,
            parameters={},
            created_by="tester",
        )
        db_session.add_all([j1, j2])
        await db_session.commit()

        jobs, total = await service.list_jobs_with_total(
            db=db_session, job_type="collection"
        )
        assert total == 1
        assert all(
            (j.type.value if hasattr(j.type, "value") else j.type) == "collection"
            for j in jobs
        )


class TestJobServiceCancelJob:
    """cancel_job - lines 434, 440, 447-448, 462-465"""

    @pytest.mark.asyncio
    async def test_cancel_job_not_found(self, db_session):
        """cancel_job returns False for missing job."""
        service = JobService()
        result = await service.cancel_job("nonexistent", db_session)
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_job_already_completed(self, db_session):
        """cancel_job returns False for already completed job."""
        service = JobService()
        job = Job(
            type=JobType.COLLECTION,
            status=JobStatus.COMPLETED,
            parameters={},
            created_by="tester",
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        result = await service.cancel_job(job.job_id, db_session)
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_job_cancel_task_failure(self, db_session):
        """cancel_job succeeds even when cancel_task raises."""
        service = JobService()
        job = Job(
            type=JobType.COLLECTION,
            status=JobStatus.PROCESSING,
            parameters={},
            created_by="tester",
        )
        job.task_id = "task-to-cancel"
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        with patch(
            "services.job_service.cancel_task",
            new_callable=AsyncMock,
            side_effect=RuntimeError("cancel failed"),
        ):
            result = await service.cancel_job(job.job_id, db_session)
            assert result is True

    @pytest.mark.asyncio
    async def test_cancel_job_exception_returns_false(self, db_session):
        """cancel_job returns False when an unexpected exception occurs."""
        service = JobService()

        with patch.object(
            service,
            "get_job",
            new_callable=AsyncMock,
            side_effect=RuntimeError("db error"),
        ):
            result = await service.cancel_job("some-id", db_session)
            assert result is False


class TestJobServiceCleanupOldJobsException:
    """cleanup_old_jobs exception path - lines 504-507"""

    @pytest.mark.asyncio
    async def test_cleanup_old_jobs_exception_returns_zero(self, db_session):
        """cleanup_old_jobs returns 0 when an exception occurs."""
        service = JobService()

        original_execute = db_session.execute

        async def failing_execute(stmt, *args, **kwargs):
            raise RuntimeError("query failed")

        db_session._inner.execute = failing_execute

        result = await service.cleanup_old_jobs(db_session, days=7)
        assert result == 0

        db_session._inner.execute = original_execute


class TestJobServiceGetJobStatistics:
    """get_job_statistics - lines 522-574"""

    @pytest.mark.asyncio
    async def test_get_job_statistics_full_path(self, db_session):
        """get_job_statistics returns statistics for all statuses and types."""
        service = JobService()

        j1 = Job(
            type=JobType.COLLECTION,
            status=JobStatus.COMPLETED,
            parameters={},
            created_by="owner-a",
        )
        j2 = Job(
            type=JobType.ENRICHMENT,
            status=JobStatus.FAILED,
            parameters={},
            created_by="owner-a",
        )
        j3 = Job(
            type=JobType.COLLECTION,
            status=JobStatus.PENDING,
            parameters={},
            created_by="owner-b",
        )
        db_session.add_all([j1, j2, j3])
        await db_session.commit()

        stats = await service.get_job_statistics(db_session)
        assert stats["total_jobs"] == 3
        assert "status_counts" in stats
        assert "type_counts" in stats
        assert "recent_jobs_24h" in stats
        assert "timestamp" in stats
        assert stats["status_counts"]["completed"] >= 1
        assert stats["status_counts"]["failed"] >= 1

    @pytest.mark.asyncio
    async def test_get_job_statistics_with_owner_ref(self, db_session):
        """get_job_statistics filters by owner_ref."""
        service = JobService()

        j1 = Job(
            type=JobType.COLLECTION,
            status=JobStatus.COMPLETED,
            parameters={},
            created_by="owner-a",
        )
        j2 = Job(
            type=JobType.COLLECTION,
            status=JobStatus.PENDING,
            parameters={},
            created_by="owner-b",
        )
        db_session.add_all([j1, j2])
        await db_session.commit()

        stats = await service.get_job_statistics(db_session, owner_ref="owner-a")
        assert stats["total_jobs"] == 1

    @pytest.mark.asyncio
    async def test_get_job_statistics_exception_returns_error(self, db_session):
        """get_job_statistics returns error dict on exception."""
        service = JobService()

        with patch.object(
            db_session,
            "execute",
            new_callable=AsyncMock,
            side_effect=RuntimeError("stats query failed"),
        ):
            stats = await service.get_job_statistics(db_session)
            assert "error" in stats
            assert "stats query failed" in stats["error"]
            assert "timestamp" in stats


# ---------------------------------------------------------------------------
# pipelines/data_pipeline.py
# ---------------------------------------------------------------------------


class TestDataProcessingPipelineProcessRaceData:
    """process_race_data with all pipeline_type values - lines 147-163"""

    @pytest.fixture
    def mock_kra_api(self):
        return Mock()

    @pytest.fixture
    def mock_db(self):
        return Mock()

    @pytest.mark.asyncio
    async def test_process_race_data_standard(self, mock_kra_api, mock_db):
        """process_race_data creates standard pipeline and executes it."""
        mock_pipeline = AsyncMock()
        mock_pipeline.execute = AsyncMock(
            return_value=PipelineContext(race_date="20240101", meet=1, race_number=1)
        )

        with patch.object(
            DataProcessingPipeline,
            "create_standard_pipeline",
            return_value=mock_pipeline,
        ):
            ctx = await DataProcessingPipeline.process_race_data(
                race_date="20240101",
                meet=1,
                race_number=1,
                kra_api_service=mock_kra_api,
                db_session=mock_db,
                pipeline_type="standard",
            )
            assert ctx.race_date == "20240101"
            mock_pipeline.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_process_race_data_collection_only(self, mock_kra_api, mock_db):
        """process_race_data creates collection_only pipeline."""
        mock_pipeline = AsyncMock()
        mock_pipeline.execute = AsyncMock(
            return_value=PipelineContext(race_date="20240101", meet=1, race_number=1)
        )

        with patch.object(
            DataProcessingPipeline,
            "create_collection_only_pipeline",
            return_value=mock_pipeline,
        ):
            ctx = await DataProcessingPipeline.process_race_data(
                race_date="20240101",
                meet=1,
                race_number=1,
                kra_api_service=mock_kra_api,
                db_session=mock_db,
                pipeline_type="collection_only",
            )
            assert ctx.race_date == "20240101"
            mock_pipeline.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_process_race_data_enrichment_only(self, mock_kra_api, mock_db):
        """process_race_data creates enrichment_only pipeline."""
        mock_pipeline = AsyncMock()
        mock_pipeline.execute = AsyncMock(
            return_value=PipelineContext(race_date="20240101", meet=1, race_number=1)
        )

        with patch.object(
            DataProcessingPipeline,
            "create_enrichment_pipeline",
            return_value=mock_pipeline,
        ):
            ctx = await DataProcessingPipeline.process_race_data(
                race_date="20240101",
                meet=1,
                race_number=1,
                kra_api_service=mock_kra_api,
                db_session=mock_db,
                pipeline_type="enrichment_only",
            )
            assert ctx.race_date == "20240101"
            mock_pipeline.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_process_race_data_unknown_type_raises(self, mock_kra_api, mock_db):
        """process_race_data raises ValueError for unknown pipeline type."""
        with pytest.raises(ValueError, match="Unknown pipeline type"):
            await DataProcessingPipeline.process_race_data(
                race_date="20240101",
                meet=1,
                race_number=1,
                kra_api_service=mock_kra_api,
                db_session=mock_db,
                pipeline_type="invalid",
            )


class TestPipelineOrchestratorProcessRaceBatch:
    """process_race_batch - lines 199-218, 224-225, 234-246"""

    @pytest.fixture
    def mock_kra_api(self):
        return Mock()

    @pytest.fixture
    def mock_db(self):
        return Mock()

    @pytest.fixture
    def orchestrator(self, mock_kra_api, mock_db):
        return PipelineOrchestrator(mock_kra_api, mock_db)

    @pytest.mark.asyncio
    async def test_process_race_batch_success(self, orchestrator):
        """process_race_batch returns contexts for each request."""
        mock_ctx = PipelineContext(race_date="20240101", meet=1, race_number=1)

        with patch.object(
            DataProcessingPipeline,
            "process_race_data",
            new_callable=AsyncMock,
            return_value=mock_ctx,
        ):
            results = await orchestrator.process_race_batch(
                [{"race_date": "20240101", "meet": 1, "race_number": 1}]
            )
            assert len(results) == 1
            assert results[0].race_date == "20240101"

    @pytest.mark.asyncio
    async def test_process_race_batch_exception_in_single_race(self, orchestrator):
        """process_race_batch captures exceptions as failed contexts."""

        async def failing_process(*args, **kwargs):
            raise RuntimeError("pipeline exploded")

        with patch.object(
            DataProcessingPipeline,
            "process_race_data",
            side_effect=failing_process,
        ):
            results = await orchestrator.process_race_batch(
                [{"race_date": "20240101", "meet": 1, "race_number": 2}]
            )
            assert len(results) == 1
            assert results[0].metadata.get("failed") is True
            assert "pipeline exploded" in results[0].metadata.get("error", "")

    @pytest.mark.asyncio
    async def test_process_race_batch_mixed_results(self, orchestrator):
        """process_race_batch handles mix of success and failure."""
        call_count = 0

        async def mixed_process(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if kwargs.get("race_number", args[2] if len(args) > 2 else 0) == 2:
                raise RuntimeError("race 2 failed")
            return PipelineContext(
                race_date=kwargs.get("race_date", args[0]),
                meet=kwargs.get("meet", args[1]),
                race_number=kwargs.get("race_number", args[2]),
            )

        with patch.object(
            DataProcessingPipeline,
            "process_race_data",
            side_effect=mixed_process,
        ):
            results = await orchestrator.process_race_batch(
                [
                    {"race_date": "20240101", "meet": 1, "race_number": 1},
                    {"race_date": "20240101", "meet": 1, "race_number": 2},
                ]
            )
            assert len(results) == 2
            failed = [r for r in results if r.metadata.get("failed")]
            assert len(failed) >= 1


class TestPipelineOrchestratorStatusSummary:
    """get_pipeline_status_summary stage_stats - lines 315-322"""

    @pytest.fixture
    def orchestrator(self):
        return PipelineOrchestrator(Mock(), Mock())

    def test_stage_stats_calculation(self, orchestrator):
        """get_pipeline_status_summary calculates per-stage stats."""
        ctx1 = PipelineContext(race_date="20240101", meet=1, race_number=1)
        ctx1.add_stage_result("collection", StageResult(status=StageStatus.COMPLETED))
        ctx1.add_stage_result("enrichment", StageResult(status=StageStatus.COMPLETED))

        ctx2 = PipelineContext(race_date="20240101", meet=1, race_number=2)
        ctx2.add_stage_result("collection", StageResult(status=StageStatus.COMPLETED))
        ctx2.add_stage_result(
            "enrichment", StageResult(status=StageStatus.FAILED, error="bad data")
        )

        summary = orchestrator.get_pipeline_status_summary([ctx1, ctx2])
        assert summary["total_races"] == 2
        assert summary["stage_statistics"]["collection"]["success"] == 2
        assert summary["stage_statistics"]["collection"]["failed"] == 0
        assert summary["stage_statistics"]["collection"]["total"] == 2
        assert summary["stage_statistics"]["enrichment"]["success"] == 1
        assert summary["stage_statistics"]["enrichment"]["failed"] == 1
        assert summary["stage_statistics"]["enrichment"]["total"] == 2

    def test_stage_stats_with_execution_times(self, orchestrator):
        """get_pipeline_status_summary calculates average execution time."""
        ctx1 = PipelineContext(race_date="20240101", meet=1, race_number=1)
        ctx1.started_at = datetime(2024, 1, 1, 10, 0, 0)
        ctx1.completed_at = datetime(2024, 1, 1, 10, 0, 2)

        ctx2 = PipelineContext(race_date="20240101", meet=1, race_number=2)
        ctx2.started_at = datetime(2024, 1, 1, 10, 0, 0)
        ctx2.completed_at = datetime(2024, 1, 1, 10, 0, 4)

        summary = orchestrator.get_pipeline_status_summary([ctx1, ctx2])
        assert summary["average_execution_time_ms"] == 3000.0
        assert summary["total_execution_time_ms"] == 6000

    def test_stage_stats_no_execution_times(self, orchestrator):
        """get_pipeline_status_summary handles missing execution times."""
        ctx = PipelineContext(race_date="20240101", meet=1, race_number=1)
        summary = orchestrator.get_pipeline_status_summary([ctx])
        assert summary["average_execution_time_ms"] is None
        assert summary["total_execution_time_ms"] is None
