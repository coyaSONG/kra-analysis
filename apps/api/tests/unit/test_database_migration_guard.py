import pytest

from infrastructure import database


@pytest.mark.asyncio
async def test_require_migration_manifest_accepts_matching_manifest(monkeypatch):
    monkeypatch.setattr(
        database,
        "get_active_migration_names",
        lambda: ["001_unified_schema.sql", "006_canonical_job_status_backfill.sql"],
    )
    monkeypatch.setattr(
        database, "get_required_migration_head", lambda: "006_canonical_job_status_backfill.sql"
    )
    monkeypatch.setattr(database, "get_legacy_conflict_tables", lambda: ["collection_jobs"])

    async def fake_applied_migrations():
        return {
            "001_unified_schema.sql": "abc",
            "006_canonical_job_status_backfill.sql": "def",
        }

    async def fake_public_tables():
        return {"jobs", "job_logs", "usage_events"}

    monkeypatch.setattr(database, "get_applied_migrations", fake_applied_migrations)
    monkeypatch.setattr(database, "get_public_table_names", fake_public_tables)

    await database.require_migration_manifest()


@pytest.mark.asyncio
async def test_require_migration_manifest_rejects_missing_manifest_rows(monkeypatch):
    monkeypatch.setattr(
        database,
        "get_active_migration_names",
        lambda: ["001_unified_schema.sql", "006_canonical_job_status_backfill.sql"],
    )
    monkeypatch.setattr(
        database, "get_required_migration_head", lambda: "006_canonical_job_status_backfill.sql"
    )

    async def fake_applied_migrations():
        return {"001_unified_schema.sql": "abc"}

    monkeypatch.setattr(database, "get_applied_migrations", fake_applied_migrations)

    with pytest.raises(RuntimeError, match="missing manifest rows"):
        await database.require_migration_manifest()


@pytest.mark.asyncio
async def test_require_migration_manifest_rejects_unexpected_migration_names(monkeypatch):
    monkeypatch.setattr(
        database,
        "get_active_migration_names",
        lambda: ["001_unified_schema.sql", "006_canonical_job_status_backfill.sql"],
    )
    monkeypatch.setattr(
        database, "get_required_migration_head", lambda: "006_canonical_job_status_backfill.sql"
    )

    async def fake_applied_migrations():
        return {
            "001_unified_schema.sql": "abc",
            "006_canonical_job_status_backfill.sql": "def",
            "001_initial_schema.sql": "legacy",
        }

    monkeypatch.setattr(database, "get_applied_migrations", fake_applied_migrations)

    with pytest.raises(RuntimeError, match="unexpected migration names"):
        await database.require_migration_manifest()


@pytest.mark.asyncio
async def test_require_migration_manifest_rejects_mixed_legacy_state(monkeypatch):
    monkeypatch.setattr(
        database,
        "get_active_migration_names",
        lambda: ["001_unified_schema.sql", "006_canonical_job_status_backfill.sql"],
    )
    monkeypatch.setattr(
        database, "get_required_migration_head", lambda: "006_canonical_job_status_backfill.sql"
    )
    monkeypatch.setattr(database, "get_legacy_conflict_tables", lambda: ["collection_jobs"])

    async def fake_applied_migrations():
        return {
            "001_unified_schema.sql": "abc",
            "006_canonical_job_status_backfill.sql": "def",
        }

    async def fake_public_tables():
        return {"jobs", "job_logs", "collection_jobs"}

    monkeypatch.setattr(database, "get_applied_migrations", fake_applied_migrations)
    monkeypatch.setattr(database, "get_public_table_names", fake_public_tables)

    with pytest.raises(RuntimeError, match="mixed legacy/unified state"):
        await database.require_migration_manifest()


@pytest.mark.asyncio
async def test_require_migration_manifest_rejects_missing_schema_migrations_history(
    monkeypatch,
):
    async def boom():
        raise RuntimeError("relation does not exist")

    monkeypatch.setattr(database, "get_applied_migrations", boom)

    with pytest.raises(RuntimeError, match="schema_migrations table missing or unreadable"):
        await database.require_migration_manifest()


@pytest.mark.asyncio
async def test_init_db_raises_in_production_when_migration_guard_fails(monkeypatch):
    async def boom():
        raise RuntimeError("guard failed")

    monkeypatch.setattr(database.settings, "environment", "production")
    monkeypatch.setattr(database, "database_url", "postgresql+asyncpg://example/db")
    monkeypatch.setattr(database, "require_migration_manifest", boom)

    with pytest.raises(RuntimeError, match="guard failed"):
        await database.init_db()


@pytest.mark.asyncio
async def test_init_db_raises_in_development_when_migration_guard_fails(monkeypatch):
    async def boom():
        raise RuntimeError("guard failed")

    monkeypatch.setattr(database.settings, "environment", "development")
    monkeypatch.setattr(database, "database_url", "postgresql+asyncpg://example/db")
    monkeypatch.setattr(database, "require_migration_manifest", boom)

    with pytest.raises(RuntimeError, match="guard failed"):
        await database.init_db()
