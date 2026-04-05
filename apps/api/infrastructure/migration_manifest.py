"""Canonical migration manifest for the active unified schema chain."""

from pathlib import Path

ACTIVE_MIGRATIONS = [
    "001_unified_schema.sql",
    "002_add_prediction_created_by.sql",
    "003_add_race_odds.sql",
    "004_add_job_shadow_fields.sql",
    "005_add_usage_events.sql",
    "006_canonical_job_status_backfill.sql",
]

# Legacy baseline files remain in the repository as inactive artifacts so startup
# and tooling can reject mixed legacy/unified state explicitly.
INACTIVE_LEGACY_MIGRATIONS = [
    "001_initial_schema.sql",
]

# These tables only exist in the legacy baseline and should never coexist with
# a database that claims to be on the unified manifest.
LEGACY_CONFLICT_TABLES = [
    "collection_jobs",
    "horse_cache",
    "jockey_cache",
    "performance_analysis",
    "prompt_versions",
    "race_results",
    "trainer_cache",
]


def get_migrations_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "migrations"


def get_active_migration_names() -> list[str]:
    return list(ACTIVE_MIGRATIONS)


def get_active_migration_paths() -> list[Path]:
    migrations_dir = get_migrations_dir()
    return [migrations_dir / name for name in ACTIVE_MIGRATIONS]


def get_inactive_migration_names() -> list[str]:
    return list(INACTIVE_LEGACY_MIGRATIONS)


def get_inactive_migration_paths() -> list[Path]:
    migrations_dir = get_migrations_dir()
    return [migrations_dir / name for name in INACTIVE_LEGACY_MIGRATIONS]


def get_legacy_conflict_tables() -> list[str]:
    return list(LEGACY_CONFLICT_TABLES)


def get_required_migration_head() -> str | None:
    if not ACTIVE_MIGRATIONS:
        return None
    return ACTIVE_MIGRATIONS[-1]
