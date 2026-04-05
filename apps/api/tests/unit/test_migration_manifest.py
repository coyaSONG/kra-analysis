from pathlib import Path

import infrastructure.migration_manifest as migration_manifest


def test_manifest_exposes_unified_chain_and_inactive_legacy_markers():
    assert migration_manifest.get_active_migration_names() == [
        "001_unified_schema.sql",
        "002_add_prediction_created_by.sql",
        "003_add_race_odds.sql",
        "004_add_job_shadow_fields.sql",
        "005_add_usage_events.sql",
        "006_canonical_job_status_backfill.sql",
    ]
    assert migration_manifest.get_required_migration_head() == (
        "006_canonical_job_status_backfill.sql"
    )
    assert "001_initial_schema.sql" not in migration_manifest.ACTIVE_MIGRATIONS
    assert migration_manifest.get_inactive_migration_names() == [
        "001_initial_schema.sql"
    ]
    assert set(migration_manifest.get_legacy_conflict_tables()) >= {
        "collection_jobs",
        "race_results",
        "prompt_versions",
    }


def test_manifest_paths_point_at_checked_in_migration_files():
    active_paths = migration_manifest.get_active_migration_paths()
    inactive_paths = migration_manifest.get_inactive_migration_paths()

    assert all(isinstance(path, Path) for path in active_paths + inactive_paths)
    assert active_paths[0].name == "001_unified_schema.sql"
    assert inactive_paths == [
        migration_manifest.get_migrations_dir() / "001_initial_schema.sql"
    ]
