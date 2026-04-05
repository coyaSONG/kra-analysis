from unittest.mock import AsyncMock

import pytest

import main_v2
from infrastructure import database


def _configure_non_test_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(database.settings, "environment", "development")
    monkeypatch.setattr(main_v2.settings, "environment", "development")
    monkeypatch.setattr(database, "database_url", "postgresql+asyncpg://example/db")
    monkeypatch.setattr(main_v2, "create_required_directories", AsyncMock())
    monkeypatch.setattr(main_v2, "init_redis", AsyncMock())
    monkeypatch.setattr(main_v2, "shutdown_background_tasks", AsyncMock())
    monkeypatch.setattr(main_v2, "close_db", AsyncMock())
    monkeypatch.setattr(main_v2, "close_redis", AsyncMock())


@pytest.mark.asyncio
@pytest.mark.integration
async def test_create_app_lifespan_rejects_missing_schema_migrations_history(
    monkeypatch: pytest.MonkeyPatch,
):
    _configure_non_test_startup(monkeypatch)

    async def missing_schema_history():
        raise RuntimeError("relation schema_migrations does not exist")

    monkeypatch.setattr(database, "get_applied_migrations", missing_schema_history)

    app = main_v2.create_app()

    with pytest.raises(
        RuntimeError,
        match="schema_migrations table missing or unreadable.*apply_migrations.py",
    ):
        async with app.router.lifespan_context(app):
            pass


@pytest.mark.asyncio
@pytest.mark.integration
async def test_create_app_lifespan_rejects_mixed_legacy_state_before_serving(
    monkeypatch: pytest.MonkeyPatch,
):
    _configure_non_test_startup(monkeypatch)
    monkeypatch.setattr(database, "get_legacy_conflict_tables", lambda: ["collection_jobs"])

    async def fake_applied_migrations():
        return {name: name for name in database.get_active_migration_names()}

    async def fake_public_tables():
        return {"jobs", "job_logs", "collection_jobs"}

    monkeypatch.setattr(database, "get_applied_migrations", fake_applied_migrations)
    monkeypatch.setattr(database, "get_public_table_names", fake_public_tables)

    app = main_v2.create_app()

    with pytest.raises(
        RuntimeError,
        match="mixed legacy/unified state.*apply_migrations.py",
    ):
        async with app.router.lifespan_context(app):
            pass
