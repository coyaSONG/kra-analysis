from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import main_v2
from infrastructure import database


def _configure_non_test_runtime(
    monkeypatch: pytest.MonkeyPatch, database_url: str
):
    engine = create_async_engine(database_url, echo=False, poolclass=NullPool)
    session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    monkeypatch.setattr(database.settings, "environment", "development")
    monkeypatch.setattr(main_v2.settings, "environment", "development")
    monkeypatch.setattr(database.settings, "database_url", database_url)
    monkeypatch.setattr(main_v2.settings, "database_url", database_url)
    monkeypatch.setattr(database, "database_url", database_url)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "async_session_maker", session_maker)
    monkeypatch.setattr(main_v2, "async_session_maker", session_maker)
    monkeypatch.setattr(main_v2, "create_required_directories", AsyncMock())
    monkeypatch.setattr(main_v2, "init_redis", AsyncMock())
    monkeypatch.setattr(main_v2, "shutdown_background_tasks", AsyncMock())
    monkeypatch.setattr(main_v2, "close_redis", AsyncMock())

    return engine


@pytest.mark.asyncio
@pytest.mark.integration
async def test_bootstrap_manifest_proves_fresh_database_bootstrap(
    bootstrap_proof_database, monkeypatch: pytest.MonkeyPatch
):
    assert await bootstrap_proof_database.list_public_tables() == set()

    applied_migrations = await bootstrap_proof_database.apply_manifest()
    public_tables = await bootstrap_proof_database.list_public_tables()
    recorded_migrations = await bootstrap_proof_database.list_applied_migrations()

    assert applied_migrations[0] == "001_unified_schema.sql"
    assert applied_migrations[-1] == "006_canonical_job_status_backfill.sql"
    assert recorded_migrations == applied_migrations
    assert "schema_migrations" in public_tables
    assert {
        "api_keys",
        "job_logs",
        "jobs",
        "prompt_templates",
        "races",
        "usage_events",
    } <= public_tables

    engine = _configure_non_test_runtime(
        monkeypatch, bootstrap_proof_database.database_url
    )
    app = main_v2.create_app()
    monkeypatch.setattr(main_v2, "close_db", AsyncMock(side_effect=engine.dispose))

    async with app.router.lifespan_context(app):
        pass
