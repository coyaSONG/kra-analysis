import pytest

from infrastructure import database


@pytest.mark.asyncio
async def test_require_migration_manifest_accepts_matching_manifest(monkeypatch):
    monkeypatch.setattr(
        database,
        "get_active_migration_names",
        lambda: ["001_unified_schema.sql", "005_add_usage_events.sql"],
    )
    monkeypatch.setattr(
        database, "get_required_migration_head", lambda: "005_add_usage_events.sql"
    )

    async def fake_applied_migrations():
        return {
            "001_unified_schema.sql": "abc",
            "005_add_usage_events.sql": "def",
        }

    monkeypatch.setattr(database, "get_applied_migrations", fake_applied_migrations)

    await database.require_migration_manifest()


@pytest.mark.asyncio
async def test_require_migration_manifest_rejects_mismatch(monkeypatch):
    monkeypatch.setattr(
        database,
        "get_active_migration_names",
        lambda: ["001_unified_schema.sql", "005_add_usage_events.sql"],
    )
    monkeypatch.setattr(
        database, "get_required_migration_head", lambda: "005_add_usage_events.sql"
    )

    async def fake_applied_migrations():
        return {"004_add_job_shadow_fields.sql": "abc"}

    monkeypatch.setattr(database, "get_applied_migrations", fake_applied_migrations)

    with pytest.raises(RuntimeError, match="Database migration manifest mismatch"):
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
