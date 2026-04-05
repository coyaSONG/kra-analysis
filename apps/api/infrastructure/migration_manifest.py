"""
Canonical migration manifest for the active unified schema chain.
"""

from pathlib import Path

ACTIVE_MIGRATIONS = [
    "001_unified_schema.sql",
    "002_add_prediction_created_by.sql",
    "003_add_race_odds.sql",
    "004_add_job_shadow_fields.sql",
    "005_add_usage_events.sql",
    "006_canonical_job_status_backfill.sql",
]


def get_migrations_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "migrations"


def get_active_migration_names() -> list[str]:
    return list(ACTIVE_MIGRATIONS)


def get_active_migration_paths() -> list[Path]:
    migrations_dir = get_migrations_dir()
    return [migrations_dir / name for name in ACTIVE_MIGRATIONS]


def get_required_migration_head() -> str | None:
    if not ACTIVE_MIGRATIONS:
        return None
    return ACTIVE_MIGRATIONS[-1]
