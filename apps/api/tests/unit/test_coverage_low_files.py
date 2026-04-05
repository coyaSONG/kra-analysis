import asyncio
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from infrastructure import background_tasks

# =========================================================================
# 1. infrastructure/migration_manifest.py
# =========================================================================


class TestMigrationManifest:
    def test_get_migrations_dir_returns_path(self):
        from infrastructure.migration_manifest import get_migrations_dir

        result = get_migrations_dir()
        assert isinstance(result, Path)
        assert result.name == "migrations"

    def test_get_active_migration_names_returns_list_of_strings(self):
        from infrastructure.migration_manifest import get_active_migration_names

        names = get_active_migration_names()
        assert isinstance(names, list)
        assert len(names) > 0
        assert all(isinstance(n, str) for n in names)
        assert names[0] == "001_unified_schema.sql"

    def test_get_active_migration_names_returns_copy(self):
        from infrastructure.migration_manifest import (
            ACTIVE_MIGRATIONS,
            get_active_migration_names,
        )

        names = get_active_migration_names()
        names.append("fake.sql")
        assert "fake.sql" not in ACTIVE_MIGRATIONS

    def test_get_active_migration_paths_returns_full_paths(self):
        from infrastructure.migration_manifest import get_active_migration_paths

        paths = get_active_migration_paths()
        assert isinstance(paths, list)
        assert len(paths) > 0
        assert all(isinstance(p, Path) for p in paths)
        assert paths[0].name == "001_unified_schema.sql"
        assert paths[0].parent.name == "migrations"

    def test_get_required_migration_head_returns_last_name(self):
        from infrastructure.migration_manifest import get_required_migration_head

        head = get_required_migration_head()
        assert head is not None
        assert head == "005_add_usage_events.sql"

    def test_get_required_migration_head_returns_none_when_empty(self, monkeypatch):
        import infrastructure.migration_manifest as mm

        monkeypatch.setattr(mm, "ACTIVE_MIGRATIONS", [])
        assert mm.get_required_migration_head() is None


# =========================================================================
# 2. routers/health.py
# =========================================================================


class TestGetOptionalRedis:
    def test_returns_redis_when_available(self, monkeypatch):
        import routers.health as health_mod

        fake_redis = MagicMock()
        monkeypatch.setattr(health_mod, "get_redis", lambda: fake_redis)
        assert health_mod.get_optional_redis() is fake_redis

    def test_returns_none_on_runtime_error(self, monkeypatch):
        import routers.health as health_mod

        monkeypatch.setattr(
            health_mod, "get_redis", MagicMock(side_effect=RuntimeError("not init"))
        )
        assert health_mod.get_optional_redis() is None


class TestDetailedHealthBranches:
    async def test_redis_ping_raises_exception(self, api_app, authenticated_client):
        import routers.health as health_mod

        class BadPingRedis:
            def ping(self):
                raise ConnectionError("down")

        api_app.dependency_overrides[health_mod.get_optional_redis] = (
            lambda: BadPingRedis()
        )
        try:
            r = await authenticated_client.get("/health/detailed")
            assert r.status_code == 200
            assert r.json()["redis"] == "unhealthy"
        finally:
            api_app.dependency_overrides.pop(health_mod.get_optional_redis, None)

    async def test_redis_without_ping_attr(self, api_app, authenticated_client):
        import routers.health as health_mod

        class NoPingRedis:
            pass

        api_app.dependency_overrides[health_mod.get_optional_redis] = (
            lambda: NoPingRedis()
        )
        try:
            r = await authenticated_client.get("/health/detailed")
            assert r.status_code == 200
            # redis has no ping attr -> redis_ok = True
            assert r.json()["redis"] == "healthy"
        finally:
            api_app.dependency_overrides.pop(health_mod.get_optional_redis, None)

    async def test_redis_is_none_falls_back_to_check_redis_connection(
        self, api_app, authenticated_client, monkeypatch
    ):
        import routers.health as health_mod

        api_app.dependency_overrides[health_mod.get_optional_redis] = lambda: None
        monkeypatch.setattr(
            health_mod, "check_redis_connection", AsyncMock(return_value=False)
        )
        try:
            r = await authenticated_client.get("/health/detailed")
            assert r.status_code == 200
            assert r.json()["redis"] == "unhealthy"
        finally:
            api_app.dependency_overrides.pop(health_mod.get_optional_redis, None)


# =========================================================================
# 3. bootstrap/runtime.py
# =========================================================================


class TestObservabilityFacadeRenderMetrics:
    def test_render_metrics_returns_prometheus_format(self):
        from bootstrap.runtime import ObservabilityFacade

        facade = ObservabilityFacade(
            process_start_time=100.0,
            task_stats_provider=lambda: {
                "active_tasks": 2,
                "failed_tasks": 1,
            },
            request_count_provider=lambda: 42,
        )

        result = facade.render_metrics(db_ok=True, now=200.0)
        assert isinstance(result, str)
        assert result.endswith("\n")
        assert "kra_requests_total 42" in result
        assert "kra_background_tasks_active 2" in result
        assert "kra_background_tasks_failed_total 1" in result
        assert "kra_database_up 1" in result
        assert "kra_uptime_seconds 100.00" in result

    def test_render_metrics_db_down(self):
        from bootstrap.runtime import ObservabilityFacade

        facade = ObservabilityFacade(
            task_stats_provider=lambda: {"active_tasks": 0, "failed_tasks": 0},
            request_count_provider=lambda: 0,
        )
        result = facade.render_metrics(db_ok=False, now=facade.process_start_time)
        assert "kra_database_up 0" in result


class TestGetCachedRuntime:
    def test_creates_runtime_when_none(self, monkeypatch):
        import bootstrap.runtime as rt

        monkeypatch.setattr(rt, "_runtime", None)
        result = rt._get_cached_runtime()
        assert isinstance(result, rt.AppRuntime)
        # Restore
        monkeypatch.setattr(rt, "_runtime", None)

    def test_returns_cached_instance(self, monkeypatch):
        import bootstrap.runtime as rt

        monkeypatch.setattr(rt, "_runtime", None)
        first = rt._get_cached_runtime()
        second = rt._get_cached_runtime()
        assert first is second
        monkeypatch.setattr(rt, "_runtime", None)


class TestGetRuntimeFallback:
    def test_falls_back_to_cached_when_no_state_runtime(self, monkeypatch):
        import bootstrap.runtime as rt

        monkeypatch.setattr(rt, "_runtime", None)

        mock_app = MagicMock()
        # state has no runtime attribute
        mock_app.state = MagicMock(spec=[])
        mock_request = MagicMock()
        mock_request.app = mock_app

        result = rt.get_runtime(mock_request)
        assert isinstance(result, rt.AppRuntime)
        monkeypatch.setattr(rt, "_runtime", None)


# =========================================================================
# 4. main_v2.py
# =========================================================================


class TestCreateRequiredDirectoriesException:
    async def test_continues_when_makedirs_raises(self, monkeypatch):
        from main_v2 import create_required_directories

        call_log = []

        def failing_makedirs(path, **kwargs):
            call_log.append(path)
            raise PermissionError(f"no access to {path}")

        monkeypatch.setattr(os, "makedirs", failing_makedirs)
        # Should not raise even though all makedirs calls fail
        await create_required_directories()
        assert len(call_log) >= 1


class TestLifespan:
    async def test_lifespan_calls_init_and_shutdown(self, monkeypatch):
        import main_v2

        init_db_mock = AsyncMock()
        init_redis_mock = AsyncMock()
        shutdown_bg_mock = AsyncMock()
        close_db_mock = AsyncMock()
        close_redis_mock = AsyncMock()
        create_dirs_mock = AsyncMock()

        monkeypatch.setattr(main_v2, "init_db", init_db_mock)
        monkeypatch.setattr(main_v2, "init_redis", init_redis_mock)
        monkeypatch.setattr(main_v2, "shutdown_background_tasks", shutdown_bg_mock)
        monkeypatch.setattr(main_v2, "close_db", close_db_mock)
        monkeypatch.setattr(main_v2, "close_redis", close_redis_mock)
        monkeypatch.setattr(main_v2, "create_required_directories", create_dirs_mock)

        app = MagicMock()
        async with main_v2.lifespan(app):
            init_db_mock.assert_awaited_once()
            init_redis_mock.assert_awaited_once()
            create_dirs_mock.assert_awaited_once()

        shutdown_bg_mock.assert_awaited_once()
        close_db_mock.assert_awaited_once()
        close_redis_mock.assert_awaited_once()

    async def test_lifespan_continues_when_redis_init_fails(self, monkeypatch):
        import main_v2

        monkeypatch.setattr(main_v2, "init_db", AsyncMock())
        monkeypatch.setattr(
            main_v2, "init_redis", AsyncMock(side_effect=ConnectionError("no redis"))
        )
        monkeypatch.setattr(main_v2, "shutdown_background_tasks", AsyncMock())
        monkeypatch.setattr(main_v2, "close_db", AsyncMock())
        monkeypatch.setattr(main_v2, "close_redis", AsyncMock())
        monkeypatch.setattr(main_v2, "create_required_directories", AsyncMock())

        app = MagicMock()
        # Should not raise even though Redis init fails
        async with main_v2.lifespan(app):
            pass


# =========================================================================
# 5. infrastructure/background_tasks.py
# =========================================================================


@pytest.fixture(autouse=True)
async def _cleanup_background_tasks():
    original_counters = dict(background_tasks._task_counters)
    background_tasks._running_tasks.clear()
    yield
    tasks = list(background_tasks._running_tasks.values())
    for task in tasks:
        if not task.done():
            task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    background_tasks._running_tasks.clear()
    background_tasks._task_counters.update(original_counters)


class TestRedisKey:
    def test_builds_prefixed_key(self):
        assert background_tasks._redis_key("abc-123") == "bgtask:abc-123"


class TestGetRedis:
    async def test_returns_redis_client(self, monkeypatch):
        import infrastructure.redis_client as rc

        sentinel = object()
        monkeypatch.setattr(rc, "redis_client", sentinel)
        result = await background_tasks._get_redis()
        assert result is sentinel


class TestSaveState:
    async def test_logs_warning_when_redis_is_none(self, monkeypatch):
        monkeypatch.setattr(
            background_tasks, "_get_redis", AsyncMock(return_value=None)
        )
        # Should not raise
        await background_tasks._save_state("tid", background_tasks.TaskState.PROCESSING)

    async def test_saves_to_redis(self, monkeypatch):
        mock_redis = AsyncMock()
        monkeypatch.setattr(
            background_tasks, "_get_redis", AsyncMock(return_value=mock_redis)
        )
        await background_tasks._save_state(
            "tid", background_tasks.TaskState.COMPLETED, result={"ok": True}
        )
        mock_redis.setex.assert_awaited_once()
        call_args = mock_redis.setex.await_args
        assert call_args[0][0] == "bgtask:tid"

    async def test_catches_setex_failure(self, monkeypatch):
        mock_redis = AsyncMock()
        mock_redis.setex.side_effect = ConnectionError("redis gone")
        monkeypatch.setattr(
            background_tasks, "_get_redis", AsyncMock(return_value=mock_redis)
        )
        # Should not raise
        await background_tasks._save_state(
            "tid", background_tasks.TaskState.FAILED, error="boom"
        )


class TestLoadState:
    async def test_returns_none_when_redis_unavailable(self, monkeypatch):
        monkeypatch.setattr(
            background_tasks, "_get_redis", AsyncMock(return_value=None)
        )
        assert await background_tasks._load_state("tid") is None

    async def test_returns_parsed_json(self, monkeypatch):
        import json

        payload = {"task_id": "tid", "state": "completed"}
        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps(payload)
        monkeypatch.setattr(
            background_tasks, "_get_redis", AsyncMock(return_value=mock_redis)
        )
        result = await background_tasks._load_state("tid")
        assert result == payload

    async def test_returns_none_when_key_missing(self, monkeypatch):
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        monkeypatch.setattr(
            background_tasks, "_get_redis", AsyncMock(return_value=mock_redis)
        )
        assert await background_tasks._load_state("tid") is None

    async def test_catches_get_failure(self, monkeypatch):
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = ConnectionError("redis gone")
        monkeypatch.setattr(
            background_tasks, "_get_redis", AsyncMock(return_value=mock_redis)
        )
        assert await background_tasks._load_state("tid") is None


class TestRunWithRetries:
    async def test_cancelled_error_sets_cancelled_state(self, monkeypatch):
        save_state = AsyncMock()
        monkeypatch.setattr(background_tasks, "_save_state", save_state)

        async def cancelling_func():
            raise asyncio.CancelledError()

        with pytest.raises(asyncio.CancelledError):
            await background_tasks._run_with_retries("tid", cancelling_func, (), {})

        saved_states = [call.args[1] for call in save_state.await_args_list]
        assert background_tasks.TaskState.CANCELLED in saved_states

    async def test_retries_exhausted_sets_failed_state(self, monkeypatch):
        save_state = AsyncMock()
        monkeypatch.setattr(background_tasks, "_save_state", save_state)
        monkeypatch.setattr(background_tasks, "_MAX_RETRIES", 2)
        monkeypatch.setattr(background_tasks, "_BASE_BACKOFF", 0.01)

        call_count = 0

        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("nope")

        with pytest.raises(ValueError, match="nope"):
            await background_tasks._run_with_retries("tid", always_fails, (), {})

        assert call_count == 2
        saved_states = [call.args[1] for call in save_state.await_args_list]
        assert background_tasks.TaskState.FAILED in saved_states


class TestSubmitTaskExceptionPaths:
    async def test_wrapper_swallows_cancelled_error(self, monkeypatch):
        save_state = AsyncMock()
        monkeypatch.setattr(background_tasks, "_save_state", save_state)

        async def cancelling_func():
            raise asyncio.CancelledError()

        task_id = background_tasks.submit_task(cancelling_func)
        task = background_tasks._running_tasks.get(task_id)
        # Wait for wrapper to complete (it swallows CancelledError)
        await asyncio.sleep(0.05)
        if task and not task.done():
            await task
        assert task_id not in background_tasks._running_tasks

    async def test_wrapper_swallows_general_exception(self, monkeypatch):
        save_state = AsyncMock()
        monkeypatch.setattr(background_tasks, "_save_state", save_state)
        monkeypatch.setattr(background_tasks, "_MAX_RETRIES", 1)
        monkeypatch.setattr(background_tasks, "_BASE_BACKOFF", 0.01)

        async def failing_func():
            raise RuntimeError("boom")

        task_id = background_tasks.submit_task(failing_func)
        task = background_tasks._running_tasks.get(task_id)
        if task:
            await task
        # Task cleaned itself up from _running_tasks
        assert task_id not in background_tasks._running_tasks


class TestGetTaskStatusEdgeCases:
    async def test_state_exists_but_no_asyncio_task(self, monkeypatch):
        monkeypatch.setattr(
            background_tasks,
            "_load_state",
            AsyncMock(
                return_value={
                    "task_id": "orphan",
                    "state": "completed",
                    "result": 42,
                    "error": None,
                }
            ),
        )
        status = await background_tasks.get_task_status("orphan")
        assert status is not None
        assert status["alive"] is False
        assert status["result"] == 42

    async def test_returns_none_when_not_found(self, monkeypatch):
        monkeypatch.setattr(
            background_tasks, "_load_state", AsyncMock(return_value=None)
        )
        assert await background_tasks.get_task_status("ghost") is None


class TestShutdownAll:
    async def test_cancels_running_tasks(self, monkeypatch):
        save_state = AsyncMock()
        monkeypatch.setattr(background_tasks, "_save_state", save_state)

        blocker = asyncio.Event()

        async def blocking():
            await blocker.wait()

        t1 = asyncio.create_task(blocking())
        t2 = asyncio.create_task(blocking())
        background_tasks._running_tasks["t1"] = t1
        background_tasks._running_tasks["t2"] = t2

        await background_tasks.shutdown_all()

        assert t1.cancelled() or t1.done()
        assert t2.cancelled() or t2.done()
        assert len(background_tasks._running_tasks) == 0

    async def test_shutdown_with_no_tasks(self):
        background_tasks._running_tasks.clear()
        await background_tasks.shutdown_all()
        assert len(background_tasks._running_tasks) == 0
