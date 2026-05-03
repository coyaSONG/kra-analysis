#!/usr/bin/env python3
"""Adopt an existing unified Supabase schema into the migration manifest.

This is for databases that already have the early unified tables but do not
have schema_migrations history. It validates the expected 001-003 objects,
records those migrations, and can then apply the remaining active migrations.
"""

import argparse
import asyncio
import sys
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.migration_manifest import (  # noqa: E402
    get_active_migration_paths,
    get_legacy_conflict_tables,
)
from scripts.apply_migrations import (  # noqa: E402
    MIGRATIONS_TABLE,
    apply_migration,
    compute_checksum,
    ensure_schema_migrations_table,
    get_applied_migrations,
    get_connection,
)

# The current legacy Supabase database can have 001 and 003 objects without
# schema_migrations history, while 002 may still be missing. Adopt only objects
# that are validated below; apply_remaining will run the gaps in manifest order.
ADOPT_BASELINE = (
    "001_unified_schema.sql",
    "003_add_race_odds.sql",
)

REQUIRED_TABLES = {
    "api_keys",
    "job_logs",
    "jobs",
    "predictions",
    "prompt_templates",
    "race_odds",
    "races",
}

REQUIRED_COLUMNS = {
    "race_odds": {"race_id", "pool", "chul_no", "odds", "rc_date", "source"},
    "races": {"race_id", "date", "meet", "race_number", "result_status"},
    "jobs": {"job_id", "type", "status", "created_by"},
}

REQUIRED_INDEXES = {
    "idx_race_odds_race_pool",
    "idx_race_odds_date_pool_source",
    "unique_race",
}


async def fetch_public_tables(conn: asyncpg.Connection) -> set[str]:
    rows = await conn.fetch(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        """
    )
    return {row["table_name"] for row in rows}


async def fetch_columns(conn: asyncpg.Connection) -> dict[str, set[str]]:
    rows = await conn.fetch(
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
        """
    )
    columns: dict[str, set[str]] = {}
    for row in rows:
        columns.setdefault(row["table_name"], set()).add(row["column_name"])
    return columns


async def fetch_indexes(conn: asyncpg.Connection) -> set[str]:
    rows = await conn.fetch(
        """
        SELECT indexname
        FROM pg_indexes
        WHERE schemaname = 'public'
        """
    )
    return {row["indexname"] for row in rows}


async def validate_existing_baseline(conn: asyncpg.Connection) -> None:
    tables = await fetch_public_tables(conn)
    missing_tables = sorted(REQUIRED_TABLES - tables)
    if missing_tables:
        raise RuntimeError(f"Missing tables required for adoption: {missing_tables}")

    legacy_tables = sorted(set(get_legacy_conflict_tables()) & tables)
    if legacy_tables:
        raise RuntimeError(f"Legacy/unified mixed state detected: {legacy_tables}")

    columns = await fetch_columns(conn)
    missing_columns = {
        table: sorted(required - columns.get(table, set()))
        for table, required in REQUIRED_COLUMNS.items()
        if required - columns.get(table, set())
    }
    if missing_columns:
        raise RuntimeError(f"Missing columns required for adoption: {missing_columns}")

    indexes = await fetch_indexes(conn)
    missing_indexes = sorted(REQUIRED_INDEXES - indexes)
    if missing_indexes:
        raise RuntimeError(f"Missing indexes required for adoption: {missing_indexes}")


async def adopt_baseline(conn: asyncpg.Connection, *, dry_run: bool) -> list[str]:
    active_paths = {path.name: path for path in get_active_migration_paths()}
    missing_files = [name for name in ADOPT_BASELINE if name not in active_paths]
    if missing_files:
        raise RuntimeError(
            f"Adopt baseline files missing from manifest: {missing_files}"
        )

    await validate_existing_baseline(conn)

    applied = await get_applied_migrations(conn, create_if_missing=False)
    if applied:
        print(f"Existing migration history found: {sorted(applied)}")
        return []

    adopted: list[str] = []
    if dry_run:
        for name in ADOPT_BASELINE:
            print(f"[DRY RUN] Would record applied migration: {name}")
            adopted.append(name)
        return adopted

    async with conn.transaction():
        await ensure_schema_migrations_table(conn)
        await conn.fetchval(
            "SELECT pg_advisory_xact_lock(hashtext($1))",
            "reconcile_existing_supabase_schema",
        )
        for name in ADOPT_BASELINE:
            checksum = compute_checksum(active_paths[name])
            await conn.execute(
                f"""
                INSERT INTO {MIGRATIONS_TABLE}(name, checksum)
                VALUES($1, $2)
                ON CONFLICT (name) DO NOTHING
                """,
                name,
                checksum,
            )
            adopted.append(name)
            print(f"Recorded existing migration: {name}")
    return adopted


async def apply_remaining(
    conn: asyncpg.Connection, *, dry_run: bool, pretend_applied: set[str] | None = None
) -> list[str]:
    applied = await get_applied_migrations(conn, create_if_missing=not dry_run)
    applied_names = set(applied) | (pretend_applied or set())
    changed: list[str] = []
    for path in get_active_migration_paths():
        if path.name in applied_names:
            continue
        success = await apply_migration(conn, path, dry_run=dry_run)
        if success:
            changed.append(path.name)
    return changed


async def analyze_hot_tables(conn: asyncpg.Connection, *, dry_run: bool) -> None:
    for table in ("races", "race_odds", "jobs", "usage_events"):
        exists = await conn.fetchval(
            "SELECT to_regclass($1) IS NOT NULL", f"public.{table}"
        )
        if not exists:
            continue
        if dry_run:
            print(f"[DRY RUN] Would ANALYZE {table}")
            continue
        await conn.execute(f"ANALYZE {table}")
        print(f"Analyzed table: {table}")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Adopt an existing Supabase schema into schema_migrations."
    )
    parser.add_argument("--execute", action="store_true", help="Apply changes")
    parser.add_argument(
        "--apply-remaining",
        action="store_true",
        help="Apply active migrations not yet recorded after adoption",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Run ANALYZE on hot tables after reconciliation",
    )
    args = parser.parse_args()
    dry_run = not args.execute

    if dry_run:
        print("DRY RUN: no database changes will be made.")

    conn = await get_connection()
    try:
        adopted = await adopt_baseline(conn, dry_run=dry_run)
        changed: list[str] = []
        if args.apply_remaining:
            changed = await apply_remaining(
                conn, dry_run=dry_run, pretend_applied=set(adopted)
            )
        if args.analyze:
            await analyze_hot_tables(conn, dry_run=dry_run)

        print("Summary")
        print(f"  adopted: {adopted}")
        print(f"  applied: {changed}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
