"""
Direct handler invocation tests for router coverage.

Router handler bodies called through ASGI transport don't get traced by
pytest-cov.  Calling the async handler functions directly (with mocked
dependencies) ensures the lines inside each handler are covered.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from policy.principal import AuthenticatedPrincipal, PolicyLimits

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2025, 7, 1, 12, 0, 0, tzinfo=UTC)


def _make_principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        principal_id="test-pid",
        subject_id="test-sid",
        owner_ref="test-owner",
        credential_id="test-cred",
        display_name="tester",
        auth_method="api_key",
        permissions=frozenset({"jobs.list", "jobs.read", "jobs.cancel"}),
        limits=PolicyLimits(),
    )


def _make_job_row(**overrides):
    """Return a mock that looks like a SQLAlchemy Job row."""
    defaults = {
        "job_id": "job-1",
        "type": "collection",
        "status": "pending",
        "created_at": _NOW,
        "started_at": None,
        "completed_at": None,
        "progress": 0,
        "current_step": None,
        "total_steps": None,
        "result": None,
        "error_message": None,
        "retry_count": 0,
        "parameters": {"date": "20250701"},
        "created_by": "test-owner",
        "tags": [],
    }
    defaults.update(overrides)
    row = MagicMock()
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _make_log_row(**overrides):
    defaults = {
        "timestamp": _NOW,
        "level": "INFO",
        "message": "started",
        "log_metadata": None,
    }
    defaults.update(overrides)
    row = MagicMock()
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


# ===================================================================
# jobs_v2 handlers
# ===================================================================


class TestListJobsDirect:
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_returns_dto_list(self, monkeypatch):
        from routers import jobs_v2

        job_row = _make_job_row()
        mock_svc = AsyncMock()
        mock_svc.list_jobs_with_total.return_value = ([job_row], 1)
        monkeypatch.setattr(jobs_v2, "job_service", mock_svc)

        result = await jobs_v2.list_jobs(
            status=None,
            job_type=None,
            limit=50,
            offset=0,
            db=AsyncMock(),
            principal=_make_principal(),
        )

        assert result.total == 1
        assert len(result.jobs) == 1
        assert result.jobs[0].job_id == "job-1"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_service_raises_returns_500(self, monkeypatch):
        from routers import jobs_v2

        mock_svc = AsyncMock()
        mock_svc.list_jobs_with_total.side_effect = RuntimeError("db down")
        monkeypatch.setattr(jobs_v2, "job_service", mock_svc)

        with pytest.raises(HTTPException) as exc_info:
            await jobs_v2.list_jobs(
                status=None,
                job_type=None,
                limit=50,
                offset=0,
                db=AsyncMock(),
                principal=_make_principal(),
            )
        assert exc_info.value.status_code == 500


class TestGetJobDirect:
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_job_not_found_returns_404(self, monkeypatch):
        from routers import jobs_v2

        mock_svc = AsyncMock()
        mock_svc.get_job.return_value = None
        monkeypatch.setattr(jobs_v2, "job_service", mock_svc)

        with pytest.raises(HTTPException) as exc_info:
            await jobs_v2.get_job(
                job_id="missing",
                db=AsyncMock(),
                principal=_make_principal(),
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_job_found_with_logs(self, monkeypatch):
        from routers import jobs_v2

        job_row = _make_job_row()
        log_row = _make_log_row()
        mock_svc = AsyncMock()
        mock_svc.get_job.return_value = job_row
        mock_svc.get_job_logs.return_value = [log_row]
        monkeypatch.setattr(jobs_v2, "job_service", mock_svc)

        result = await jobs_v2.get_job(
            job_id="job-1",
            db=AsyncMock(),
            principal=_make_principal(),
        )

        assert result.job.job_id == "job-1"
        assert len(result.logs) == 1
        assert result.logs[0].message == "started"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_job_found_no_logs(self, monkeypatch):
        from routers import jobs_v2

        job_row = _make_job_row()
        mock_svc = AsyncMock()
        mock_svc.get_job.return_value = job_row
        mock_svc.get_job_logs.return_value = None
        monkeypatch.setattr(jobs_v2, "job_service", mock_svc)

        result = await jobs_v2.get_job(
            job_id="job-1",
            db=AsyncMock(),
            principal=_make_principal(),
        )

        assert result.job.job_id == "job-1"
        assert result.logs == []

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_reraises_http_exception(self, monkeypatch):
        from routers import jobs_v2

        mock_svc = AsyncMock()
        mock_svc.get_job.side_effect = HTTPException(
            status_code=403, detail="forbidden"
        )
        monkeypatch.setattr(jobs_v2, "job_service", mock_svc)

        with pytest.raises(HTTPException) as exc_info:
            await jobs_v2.get_job(
                job_id="job-1",
                db=AsyncMock(),
                principal=_make_principal(),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_unexpected_error_returns_500(self, monkeypatch):
        from routers import jobs_v2

        mock_svc = AsyncMock()
        mock_svc.get_job.side_effect = RuntimeError("boom")
        monkeypatch.setattr(jobs_v2, "job_service", mock_svc)

        with pytest.raises(HTTPException) as exc_info:
            await jobs_v2.get_job(
                job_id="job-1",
                db=AsyncMock(),
                principal=_make_principal(),
            )
        assert exc_info.value.status_code == 500


class TestCancelJobDirect:
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_cancel_not_found_returns_404(self, monkeypatch):
        from routers import jobs_v2

        mock_svc = AsyncMock()
        mock_svc.cancel_job.return_value = False
        monkeypatch.setattr(jobs_v2, "job_service", mock_svc)

        with pytest.raises(HTTPException) as exc_info:
            await jobs_v2.cancel_job(
                job_id="missing",
                db=AsyncMock(),
                principal=_make_principal(),
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_cancel_success(self, monkeypatch):
        from routers import jobs_v2

        mock_svc = AsyncMock()
        mock_svc.cancel_job.return_value = True
        monkeypatch.setattr(jobs_v2, "job_service", mock_svc)

        result = await jobs_v2.cancel_job(
            job_id="job-1",
            db=AsyncMock(),
            principal=_make_principal(),
        )

        assert result["message"] == "Job cancelled successfully"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_cancel_reraises_http_exception(self, monkeypatch):
        from routers import jobs_v2

        mock_svc = AsyncMock()
        mock_svc.cancel_job.side_effect = HTTPException(
            status_code=409, detail="conflict"
        )
        monkeypatch.setattr(jobs_v2, "job_service", mock_svc)

        with pytest.raises(HTTPException) as exc_info:
            await jobs_v2.cancel_job(
                job_id="job-1",
                db=AsyncMock(),
                principal=_make_principal(),
            )
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_cancel_unexpected_error_returns_500(self, monkeypatch):
        from routers import jobs_v2

        mock_svc = AsyncMock()
        mock_svc.cancel_job.side_effect = RuntimeError("boom")
        monkeypatch.setattr(jobs_v2, "job_service", mock_svc)

        with pytest.raises(HTTPException) as exc_info:
            await jobs_v2.cancel_job(
                job_id="job-1",
                db=AsyncMock(),
                principal=_make_principal(),
            )
        assert exc_info.value.status_code == 500


# ===================================================================
# health handlers
# ===================================================================


class TestDetailedHealthCheckDirect:
    """Call detailed_health_check directly to cover lines 45-52."""

    def _make_runtime(self):
        from bootstrap.runtime import AppRuntime, ObservabilityFacade

        return AppRuntime(
            settings=None,
            observability=ObservabilityFacade(
                task_stats_provider=lambda: {
                    "status": "healthy",
                    "active_tasks": 0,
                    "failed_tasks": 0,
                },
                request_count_provider=lambda: 0,
            ),
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_redis_ping_raises(self, monkeypatch):
        """redis.ping() raises -> explicit error state."""
        from routers import health as health_mod

        monkeypatch.setattr(
            health_mod, "check_database_connection", AsyncMock(return_value=True)
        )
        # settings.version used inside build_health_snapshot
        monkeypatch.setattr(health_mod.settings, "version", "test")

        redis = MagicMock()
        redis.ping.side_effect = ConnectionError("refused")

        result = await health_mod.detailed_health_check(
            redis=redis,
            db=AsyncMock(),
            runtime=self._make_runtime(),
        )

        assert result["redis"] == "error"
        assert result["status"] == "degraded"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_redis_no_ping_attr(self, monkeypatch):
        """An object without ping is treated as unavailable, not healthy."""
        from routers import health as health_mod

        monkeypatch.setattr(
            health_mod, "check_database_connection", AsyncMock(return_value=True)
        )
        monkeypatch.setattr(health_mod.settings, "version", "test")

        # An object without .ping
        redis = object()

        result = await health_mod.detailed_health_check(
            redis=redis,
            db=AsyncMock(),
            runtime=self._make_runtime(),
        )

        assert result["redis"] == "unavailable"
        assert result["status"] == "degraded"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_redis_none_reports_unavailable(self, monkeypatch):
        """A missing optional dependency is surfaced as unavailable."""
        from routers import health as health_mod

        monkeypatch.setattr(
            health_mod, "check_database_connection", AsyncMock(return_value=True)
        )
        monkeypatch.setattr(health_mod.settings, "version", "test")

        result = await health_mod.detailed_health_check(
            redis=None,
            db=AsyncMock(),
            runtime=self._make_runtime(),
        )

        assert result["redis"] == "unavailable"
        assert result["status"] == "degraded"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_redis_none_keeps_degraded_without_fallback_probe(self, monkeypatch):
        """A missing Redis dependency does not trigger a second probe path."""
        from routers import health as health_mod

        monkeypatch.setattr(
            health_mod, "check_database_connection", AsyncMock(return_value=True)
        )
        monkeypatch.setattr(health_mod.settings, "version", "test")

        result = await health_mod.detailed_health_check(
            redis=None,
            db=AsyncMock(),
            runtime=self._make_runtime(),
        )

        assert result["redis"] == "unavailable"
        assert result["status"] == "degraded"


# ===================================================================
# collection_v2 handlers
# ===================================================================


class TestGetCollectionStatusDirect:
    """Cover lines 145-148: successful return and exception path."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_returns_status(self, monkeypatch):
        """Line 145: CollectionStatus(**asdict(status_data))"""
        from routers import collection_v2
        from services.kra_collection_module import CollectionStatusSnapshot

        snapshot = CollectionStatusSnapshot(
            date="20250701",
            meet=1,
            total_races=11,
            collected_races=11,
            enriched_races=11,
            status="completed",
            collection_status="collected",
            enrichment_status="enriched",
            result_status=None,
            last_updated=_NOW,
        )

        mock_module = MagicMock()
        mock_module.queries.get_status = AsyncMock(return_value=snapshot)
        monkeypatch.setattr(collection_v2, "collection_module", mock_module)

        result = await collection_v2.get_collection_status(
            date="20250701",
            meet=1,
            db=AsyncMock(),
            principal=_make_principal(),
        )

        assert result.date == "20250701"
        assert result.total_races == 11

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_raises_500_on_error(self, monkeypatch):
        """Lines 146-148: exception -> HTTPException 500"""
        from routers import collection_v2

        mock_module = MagicMock()
        mock_module.queries.get_status = AsyncMock(side_effect=RuntimeError("db error"))
        monkeypatch.setattr(collection_v2, "collection_module", mock_module)

        with pytest.raises(HTTPException) as exc_info:
            await collection_v2.get_collection_status(
                date="20250701",
                meet=1,
                db=AsyncMock(),
                principal=_make_principal(),
            )
        assert exc_info.value.status_code == 500


class TestCollectRaceResultReraiseHTTPException:
    """Cover line 186: except HTTPException: raise inside collect_race_result."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_reraises_http_exception(self, monkeypatch):
        """Line 185-186: HTTPException re-raised directly."""
        from routers import collection_v2

        mock_module = MagicMock()
        mock_module.commands.collect_result = AsyncMock(
            side_effect=HTTPException(status_code=422, detail="bad input")
        )
        monkeypatch.setattr(collection_v2, "collection_module", mock_module)

        from models.collection_dto import ResultCollectionRequest

        request = ResultCollectionRequest(date="20250101", meet=1, race_number=1)

        with pytest.raises(HTTPException) as exc_info:
            await collection_v2.collect_race_result(
                request=request,
                db=AsyncMock(),
                principal=_make_principal(),
            )
        assert exc_info.value.status_code == 422
