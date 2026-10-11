"""Exercise the actual venue migration in disposable PostgreSQL schemas."""

import os
from urllib.parse import urlsplit
from uuid import uuid4

import asyncpg
import pytest
import pytest_asyncio

from infrastructure.migration_manifest import get_migrations_dir
from scripts.apply_migrations import apply_migration, ensure_schema_migrations_table

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]
MIGRATION = get_migrations_dir() / "008_add_yeongcheon_meet.sql"


@pytest_asyncio.fixture
async def postgres_connection():
    dsn = os.environ.get("KRA_MIGRATION_TEST_DSN")
    if not dsn:
        if os.environ.get("CI"):
            pytest.fail("CI must configure KRA_MIGRATION_TEST_DSN")
        pytest.skip("Isolated PostgreSQL migration DSN is not configured")
    parsed = urlsplit(dsn)
    if (
        parsed.scheme != "postgresql"
        or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        or parsed.path != "/test_db"
    ):
        pytest.fail("Migration tests require the loopback test_db service")
    connection = await asyncpg.connect(dsn, timeout=10)
    schema = f"yeongcheon_migration_test_{uuid4().hex}"
    try:
        await connection.execute(f'CREATE SCHEMA "{schema}"')
        await connection.execute(f'SET search_path TO "{schema}"')
        await connection.execute(
            """
            CREATE TABLE races (
                race_id VARCHAR(50) PRIMARY KEY,
                date VARCHAR(8) NOT NULL,
                meet INTEGER NOT NULL CHECK (meet IN (1, 2, 3)),
                race_number INTEGER NOT NULL,
                CONSTRAINT unique_race UNIQUE (date, meet, race_number)
            )
            """
        )
        yield connection
    finally:
        try:
            await connection.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        finally:
            await connection.close()


async def test_venue_migration_preserves_rows_and_other_constraints(
    postgres_connection,
):
    connection = postgres_connection
    insert = "INSERT INTO races VALUES ($1, $2, $3, $4)"
    await connection.execute(insert, "existing-busan", "20261011", 3, 1)
    with pytest.raises(asyncpg.CheckViolationError):
        await connection.execute(insert, "blocked-four", "20261011", 4, 1)

    assert await apply_migration(connection, MIGRATION) is True
    assert (
        await connection.fetchval(
            "SELECT meet FROM races WHERE race_id = 'existing-busan'"
        )
        == 3
    )
    for meet in (1, 2, 3, 4):
        await connection.execute(insert, f"venue-{meet}", "20261011", meet, 2)
    for meet in (0, 5):
        with pytest.raises(asyncpg.CheckViolationError):
            await connection.execute(insert, f"invalid-{meet}", "20261011", meet, 3)
    with pytest.raises(asyncpg.UniqueViolationError):
        await connection.execute(insert, "duplicate-key", "20261011", 3, 1)
    assert await connection.fetchval("SELECT COUNT(*) FROM races") == 5


async def test_venue_migration_reapplication_is_idempotent(postgres_connection):
    connection = postgres_connection
    assert await apply_migration(connection, MIGRATION) is True
    assert await apply_migration(connection, MIGRATION) is False
    await connection.execute(MIGRATION.read_text())
    await connection.execute(MIGRATION.read_text())
    assert (
        await connection.fetchval(
            """
        SELECT COUNT(*) FROM pg_constraint
        WHERE conrelid = 'races'::regclass AND conname = 'races_meet_check'
        """
        )
        == 1
    )
    assert await connection.fetchval("SELECT COUNT(*) FROM schema_migrations") == 1
    await connection.execute(
        "INSERT INTO races VALUES ('four-after-repeat', '20261011', 4, 1)"
    )


async def test_failed_validation_rolls_back_constraint_and_bookkeeping(
    postgres_connection,
):
    connection = postgres_connection
    await connection.execute(
        """
        ALTER TABLE races DROP CONSTRAINT races_meet_check;
        ALTER TABLE races ADD CONSTRAINT races_meet_check
            CHECK (meet IN (1, 2, 3, 5));
        INSERT INTO races VALUES ('existing-unsupported', '20261011', 5, 1);
        """
    )
    await ensure_schema_migrations_table(connection)
    with pytest.raises(asyncpg.CheckViolationError):
        await apply_migration(connection, MIGRATION)
    assert await connection.fetchval("SELECT COUNT(*) FROM schema_migrations") == 0
    assert (
        await connection.fetchval(
            "SELECT meet FROM races WHERE race_id = 'existing-unsupported'"
        )
        == 5
    )
    with pytest.raises(asyncpg.CheckViolationError):
        await connection.execute(
            "INSERT INTO races VALUES ('four-after-failure', '20261011', 4, 1)"
        )
