"""
Archive old race_odds rows before optionally deleting them.

The default mode is read-only: it counts candidate rows and estimates size.
Export and delete are explicit steps so production data is not removed by accident.

Usage:
    uv run python scripts/archive_race_odds.py --before 20260101
    uv run python scripts/archive_race_odds.py --keep-months 6 --export
    uv run python scripts/archive_race_odds.py --keep-months 6 --export --delete --yes
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import asyncio
import gzip
import os
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import asyncpg

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
API_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_DIR))
os.chdir(API_DIR)

from config import settings  # noqa: E402


DEFAULT_ARCHIVE_DIR = API_DIR.parent.parent / "data" / "archive" / "race_odds"
COPY_COLUMNS = (
    "id",
    "race_id",
    "pool",
    "chul_no",
    "chul_no2",
    "chul_no3",
    "odds",
    "rc_date",
    "source",
    "collected_at",
)


@dataclass(frozen=True)
class ArchiveStats:
    rows: int
    estimated_total_bytes: int
    min_date: str | None
    max_date: str | None


def normalize_database_url(database_url: str) -> str:
    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def resolve_cutoff(before: str | None, keep_months: int | None) -> str:
    if before and keep_months:
        raise ValueError("Use either --before or --keep-months, not both.")
    if before:
        validate_yyyymmdd(before)
        return before
    if not keep_months or keep_months < 1:
        raise ValueError("Provide --before YYYYMMDD or --keep-months N.")

    return month_cutoff(date.today(), keep_months)


def month_cutoff(today: date, keep_months: int) -> str:
    """Return YYYYMM01 cutoff keeping the current month plus N-1 prior months."""
    month_index = today.year * 12 + today.month - keep_months + 1
    cutoff_year = (month_index - 1) // 12
    cutoff_month = (month_index - 1) % 12 + 1
    return f"{cutoff_year:04d}{cutoff_month:02d}01"


def validate_yyyymmdd(value: str) -> None:
    try:
        datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise ValueError(f"Invalid date {value!r}; expected YYYYMMDD.") from exc


async def connect() -> asyncpg.Connection:
    return await asyncpg.connect(normalize_database_url(settings.database_url))


async def load_stats(conn: asyncpg.Connection, cutoff: str) -> ArchiveStats:
    row = await conn.fetchrow(
        """
        WITH candidate AS (
            SELECT count(*) AS rows, min(rc_date) AS min_date, max(rc_date) AS max_date
            FROM race_odds
            WHERE rc_date < $1
        ),
        table_size AS (
            SELECT
                pg_total_relation_size('race_odds')::numeric
                / NULLIF(reltuples::numeric, 0) AS bytes_per_row
            FROM pg_class
            WHERE oid = 'race_odds'::regclass
        )
        SELECT
            candidate.rows,
            coalesce(round(candidate.rows * table_size.bytes_per_row), 0)::bigint
                AS estimated_total_bytes,
            candidate.min_date,
            candidate.max_date
        FROM candidate CROSS JOIN table_size
        """,
        cutoff,
    )
    if row is None:
        return ArchiveStats(
            rows=0, estimated_total_bytes=0, min_date=None, max_date=None
        )
    return ArchiveStats(
        rows=row["rows"],
        estimated_total_bytes=row["estimated_total_bytes"],
        min_date=row["min_date"],
        max_date=row["max_date"],
    )


def pretty_bytes(size: int) -> str:
    value = float(size)
    for unit in ("bytes", "kB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "bytes" else f"{int(value)} bytes"
        value /= 1024
    return f"{value:.1f} GB"


def archive_path(archive_dir: Path, cutoff: str) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return archive_dir / f"race_odds_before_{cutoff}_{timestamp}.csv.gz"


async def export_rows(conn: asyncpg.Connection, cutoff: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    columns = ", ".join(COPY_COLUMNS)
    query = f"""
        SELECT {columns}
        FROM race_odds
        WHERE rc_date < $1
        ORDER BY rc_date, race_id, pool, chul_no, chul_no2, chul_no3, source
    """
    with gzip.open(output_path, "wb") as output:
        await conn.copy_from_query(
            query,
            cutoff,
            output=output,
            format="csv",
            header=True,
        )


async def delete_rows(conn: asyncpg.Connection, cutoff: str, batch_size: int) -> int:
    deleted_total = 0
    while True:
        result = await conn.execute(
            """
            DELETE FROM race_odds
            WHERE ctid IN (
                SELECT ctid
                FROM race_odds
                WHERE rc_date < $1
                LIMIT $2
            )
            """,
            cutoff,
            batch_size,
        )
        deleted = int(result.rsplit(" ", 1)[-1])
        deleted_total += deleted
        print(f"deleted batch={deleted} total={deleted_total}", flush=True)
        if deleted < batch_size:
            return deleted_total


async def analyze_table(conn: asyncpg.Connection) -> None:
    await conn.execute("ANALYZE race_odds")


async def run(args: argparse.Namespace) -> None:
    cutoff = resolve_cutoff(args.before, args.keep_months)
    output_path = archive_path(Path(args.archive_dir), cutoff)

    conn = await connect()
    try:
        stats = await load_stats(conn, cutoff)
        print(f"cutoff: rc_date < {cutoff}")
        print(f"candidate rows: {stats.rows}")
        print(f"candidate date range: {stats.min_date}..{stats.max_date}")
        print(f"estimated removable size: {pretty_bytes(stats.estimated_total_bytes)}")

        if stats.rows == 0:
            return

        if args.export:
            print(f"exporting: {output_path}")
            await export_rows(conn, cutoff, output_path)
            print(f"exported bytes: {pretty_bytes(output_path.stat().st_size)}")
        elif args.delete:
            raise ValueError("--delete requires --export in the same invocation.")

        if args.delete:
            if not args.yes:
                raise ValueError("--delete requires --yes.")
            deleted = await delete_rows(conn, cutoff, args.batch_size)
            print(f"deleted rows: {deleted}")
            if args.analyze:
                await analyze_table(conn)
                print("analyzed race_odds")

            print(
                "physical disk space may require a maintenance-window "
                "VACUUM FULL or partition rewrite to be returned to the provider."
            )
    finally:
        await conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Archive old race_odds rows.")
    cutoff_group = parser.add_mutually_exclusive_group(required=True)
    cutoff_group.add_argument("--before", help="Archive rows with rc_date < YYYYMMDD.")
    cutoff_group.add_argument(
        "--keep-months",
        type=int,
        help="Keep recent N calendar months and archive older rows.",
    )
    parser.add_argument(
        "--archive-dir",
        default=str(DEFAULT_ARCHIVE_DIR),
        help="Directory for gzip CSV exports.",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export candidate rows to gzip CSV.",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete exported candidate rows in batches.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Required with --delete.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50_000,
        help="Rows per delete batch.",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Run ANALYZE race_odds after deleting rows.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
