"""Actual PostgreSQL: independent connections, restricted role and race locks."""

import asyncio
import json
import os
import sys
from argparse import Namespace
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import asyncpg
import httpx
import pytest
import pytest_asyncio

from services.forward_ledger import (
    ForwardLedger,
    b0_payload,
    canonical,
    digest,
    implementation_digest,
    install,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


@pytest_asyncio.fixture
async def database():
    dsn = os.getenv("KRA_MIGRATION_TEST_DSN")
    if not dsn:
        if os.getenv("CI"):
            pytest.fail("CI requires the disposable PostgreSQL test_db service")
        pytest.skip("Loopback test_db not configured")
    parsed = urlsplit(dsn)
    if (
        parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        or parsed.path != "/test_db"
    ):
        pytest.fail("Forward tests only accept loopback test_db")
    owner = await asyncpg.connect(dsn)
    token = uuid4().hex
    schema, role = f"forward_test_{token}", f"forward_role_{token}"
    await owner.execute(f"CREATE ROLE {role} LOGIN PASSWORD 'synthetic-local-test'")
    host = f"[{parsed.hostname}]" if parsed.hostname == "::1" else parsed.hostname
    runtime = urlunsplit(
        (
            "postgresql",
            f"{role}:synthetic-local-test@{host}:{parsed.port or 5432}",
            "/test_db",
            "",
            "",
        )
    )
    try:
        await install(owner, role, schema=schema)
        yield owner, ForwardLedger(runtime, schema=schema), dsn
    finally:
        await owner.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        await owner.execute(f"DROP ROLE {role}")
        await owner.close()


async def freeze(database, *, seconds=60):
    owner, ledger, _ = database
    now = await owner.fetchval("SELECT clock_timestamp()")
    deadline = now + timedelta(seconds=seconds)
    universe = {
        "race_date": "20300101",
        "b0_implementation_sha256": implementation_digest(),
        "races": [
            {"race_id": f"20300101_1_{n}", "feature_cutoff_at": deadline.isoformat()}
            for n in (1, 2)
        ],
    }
    result = await ledger.freeze(owner, "study", universe, synthetic=True)
    assert result["timely"]
    payload = b0_payload(
        race_id="20300101_1_1",
        universe_sha256=digest(canonical(universe)),
        entries=[{"chulNo": n, "hrNo": str(n)} for n in (10, 2, 1, 3)],
        source={"manifest_sha256": "b" * 64, "available_at": now.isoformat()},
    )
    return universe, payload, deadline


async def test_service_commits_then_witnesses_and_preserves_missing_races(database):
    _, ledger, _ = database
    universe, payload, _ = await freeze(database)
    first = await ledger.submit("study", "20300101_1_1", payload)
    assert first["observation"]["timely"]
    assert first["submission"]["sha256"] == digest(payload)
    assert first == await ledger.submit("study", "20300101_1_1", payload)
    rows = await ledger.report("study")
    assert len(rows) == len(universe["races"]) == 2
    assert [r["status"] for r in rows] == ["timely_committed", "missing_submission"]
    assert (await ledger.get_submission("study", "20300101_1_1"))["payload"] == payload


async def test_concurrent_same_payload_returns_one_original_receipt(database):
    owner, ledger, _ = database
    _, payload, _ = await freeze(database)
    first, second = await asyncio.gather(
        ledger.submit("study", "20300101_1_1", payload),
        ledger.submit("study", "20300101_1_1", payload),
    )
    assert first == second
    assert (
        await owner.fetchval(f"SELECT count(*) FROM {ledger.schema}.submissions") == 1
    )


async def test_conflicting_payload_cannot_replace_or_add_an_arm(database):
    owner, ledger, _ = database
    _, payload, _ = await freeze(database)
    other = json.loads(payload)
    other["source"]["manifest_sha256"] = "c" * 64
    results = await asyncio.gather(
        ledger.submit("study", "20300101_1_1", payload),
        ledger.submit("study", "20300101_1_1", canonical(other)),
        return_exceptions=True,
    )
    assert sum(isinstance(r, asyncpg.RaiseError) for r in results) == 1
    assert (
        await owner.fetchval(f"SELECT count(*) FROM {ledger.schema}.submissions") == 1
    )
    with pytest.raises(asyncpg.RaiseError, match="conflict"):
        await ledger.submit("study", "20300101_1_1", "{}")


async def test_same_transaction_and_savepoint_cannot_witness_own_insert(database):
    _, ledger, _ = database
    _, payload, _ = await freeze(database)
    connection = await ledger.connect()
    try:
        async with connection.transaction():
            await connection.fetchval(
                f"SELECT {ledger.schema}.submit($1,$2,$3)",
                "study",
                "20300101_1_1",
                payload,
            )
            with pytest.raises(asyncpg.RaiseError, match="own_transaction"):
                async with connection.transaction():
                    await connection.fetchval(
                        f"SELECT {ledger.schema}.observe($1,$2)",
                        "study",
                        "20300101_1_1",
                    )
            other = await ledger.connect()
            try:
                assert (
                    await other.fetchval(
                        f"SELECT count(*) FROM {ledger.schema}.submissions"
                    )
                    == 0
                )
            finally:
                await other.close()
        # Simulate lost ACK: the next service call retrieves the original payload.
        result = await ledger.submit("study", "20300101_1_1", payload)
        assert result["observation"]["timely"]
    finally:
        await connection.close()


async def test_lock_wait_crossing_deadline_cannot_use_transaction_start(database):
    owner, ledger, _ = database
    _, payload, deadline = await freeze(database, seconds=1)
    transaction = owner.transaction()
    await transaction.start()
    await owner.fetchrow(
        f"SELECT * FROM {ledger.schema}.members WHERE race_id='20300101_1_1' FOR UPDATE"
    )
    pending = asyncio.create_task(ledger.submit("study", "20300101_1_1", payload))
    await owner.execute(
        "SELECT pg_sleep(GREATEST(0,EXTRACT(EPOCH FROM ($1::timestamptz-clock_timestamp()))) + 0.1)",
        deadline,
    )
    await transaction.commit()
    with pytest.raises(asyncpg.RaiseError, match="deadline_passed"):
        await pending
    assert (
        await owner.fetchval(f"SELECT count(*) FROM {ledger.schema}.submissions") == 0
    )


async def test_insert_before_but_commit_after_deadline_remains_unproven(database):
    _, ledger, _ = database
    _, payload, deadline = await freeze(database, seconds=1)
    connection = await ledger.connect()
    try:
        async with connection.transaction():
            await connection.fetchval(
                f"SELECT {ledger.schema}.submit($1,$2,$3)",
                "study",
                "20300101_1_1",
                payload,
            )
            await connection.execute(
                "SELECT pg_sleep(GREATEST(0,EXTRACT(EPOCH FROM ($1::timestamptz-clock_timestamp()))) + 0.1)",
                deadline,
            )
        result = await ledger.submit("study", "20300101_1_1", payload)
        assert not result["observation"]["timely"]
        assert (await ledger.report("study"))[0][
            "status"
        ] == "commit_timeliness_unproven"
    finally:
        await connection.close()


async def test_runtime_cannot_write_tables_or_freeze_aliases(database):
    owner, ledger, owner_dsn = database
    universe, payload, _ = await freeze(database)
    connection = await ledger.connect()
    try:
        for table in (
            "studies",
            "members",
            "submissions",
            "observations",
            "study_observations",
        ):
            for statement in (
                f"DELETE FROM {ledger.schema}.{table}",
                f"TRUNCATE {ledger.schema}.{table}",
            ):
                with pytest.raises(asyncpg.InsufficientPrivilegeError):
                    await connection.execute(statement)
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await connection.execute(
                f"INSERT INTO {ledger.schema}.members VALUES ('study','alias',clock_timestamp())"
            )
        with pytest.raises(asyncpg.UniqueViolationError):
            await ledger.freeze(owner, "alias", universe, synthetic=True)
        with pytest.raises(ValueError, match="privilege"):
            await ForwardLedger(owner_dsn, schema=ledger.schema).connect()
        await ledger.submit("study", "20300101_1_1", payload)
        with pytest.raises(asyncpg.RaiseError, match="append_only"):
            await owner.execute(
                f"UPDATE {ledger.schema}.submissions SET payload='changed'"
            )
    finally:
        await connection.close()


@pytest.mark.parametrize(
    "change",
    ["selection", "arm", "identity", "late_source", "universe", "implementation"],
)
async def test_database_rejects_invalid_payload_even_without_python_validator(
    database, change
):
    _, ledger, _ = database
    _, payload, deadline = await freeze(database)
    body = json.loads(payload)
    if change == "selection":
        body["selection"] = ["1", "2", "10"]
    elif change == "arm":
        body["arm_id"] = "second_try"
    elif change == "identity":
        body["roster"][1]["horse_id"] = "1"
    elif change == "late_source":
        body["source"]["available_at"] = deadline.isoformat()
    elif change == "universe":
        body["universe_sha256"] = "0" * 64
    elif change == "implementation":
        body["implementation_sha256"] = "0" * 64
    with pytest.raises(asyncpg.RaiseError):
        await ledger.submit("study", "20300101_1_1", canonical(body))


@pytest.mark.parametrize("missing_venue", [None, 4])
async def test_official_capture_to_database_runner_and_restart(
    database, tmp_path, monkeypatch, missing_venue
):
    # All HTTP bytes are synthetic; only the PostgreSQL transaction behavior is real.
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "packages/scripts"))
    from autoresearch import kra_entry_sheet_snapshot as entries
    from autoresearch import kra_schedule_snapshot as schedules
    from autoresearch.tests.test_kra_schedule import page
    from shared.kra_schedule import SOURCE_URLS

    from scripts.run_forward_b0 import run_day

    _, ledger, owner_dsn = database
    monkeypatch.setenv("FORWARD_TEST_OWNER", owner_dsn)
    monkeypatch.setenv("FORWARD_TEST_RUNTIME", ledger.dsn)
    original_schedule = schedules.collect_schedule_snapshot
    original_entries = entries.collect_entry_sheet_snapshot
    requests = []

    def respond(request):
        if request.url.host == "race.kra.co.kr":
            source = next(
                k for k, url in SOURCE_URLS.items() if str(request.url) == url
            )
            return httpx.Response(
                200,
                content=page(
                    source, dates=dict.fromkeys((1, 2, 3, 4), "2030/01/04(금)")
                ),
                headers={"content-type": "text/html; charset=utf-8"},
            )
        meet = int(request.url.params["meet"])
        requests.append(meet)
        rows = [
            {
                "meet": meet,
                "rcDate": "20300104",
                "rcNo": 1,
                "chulNo": n,
                "hrNo": str(meet * 100 + n),
                "hrName": f"horse{n}",
                "stTime": "1200",
                "dusu": 10,
            }
            for n in range(1, 11)
        ]
        if meet == missing_venue:
            rows = rows[:2]
        return httpx.Response(
            200,
            json={
                "response": {
                    "header": {"resultCode": "00"},
                    "body": {
                        "pageNo": 1,
                        "numOfRows": 100,
                        "totalCount": len(rows),
                        "items": {"item": rows},
                    },
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:

        async def capture_schedule(**kwargs):
            return await original_schedule(client=client, **kwargs)

        async def capture_entries(**kwargs):
            return await original_entries(client=client, **kwargs)

        monkeypatch.setattr(schedules, "collect_schedule_snapshot", capture_schedule)
        monkeypatch.setattr(entries, "collect_entry_sheet_snapshot", capture_entries)
        key = tmp_path / "synthetic-key"
        key.write_text("synthetic-collector-fixture")
        args = Namespace(
            study="operational_path_test",
            archive=tmp_path,
            runtime_env="FORWARD_TEST_RUNTIME",
            owner_env="FORWARD_TEST_OWNER",
            schema=ledger.schema,
            race_date="20300104",
            api_key_file=key,
        )
        first = await run_day(args)
        assert first["race_count"] == len(first["ledger"]) == 4
        assert not first["counts_as_accuracy_evidence"]
        assert first["status"] == ("incomplete" if missing_venue else "reconciled")
        assert requests == [1, 2, 3, 4]
        if missing_venue:
            assert first["ledger"][-1]["status"] == "missing_submission"
        else:
            key.unlink()
            second = await run_day(args)
            assert second == first
            assert requests == [1, 2, 3, 4]


async def test_lost_universe_observation_can_be_recovered(database, monkeypatch):
    owner, ledger, _ = database
    now = await owner.fetchval("SELECT clock_timestamp()")
    universe = {
        "race_date": "20300101",
        "races": [
            {
                "race_id": "20300101_1_1",
                "feature_cutoff_at": (now + timedelta(seconds=60)).isoformat(),
            }
        ],
    }
    real_connect = ledger.connect

    async def disconnected():
        raise ConnectionError("synthetic disconnect after owner commit")

    monkeypatch.setattr(ledger, "connect", disconnected)
    with pytest.raises(ConnectionError):
        await ledger.freeze(owner, "study", universe, synthetic=True)
    assert await owner.fetchval(f"SELECT count(*) FROM {ledger.schema}.studies") == 1
    assert (
        await owner.fetchval(f"SELECT count(*) FROM {ledger.schema}.study_observations")
        == 0
    )
    monkeypatch.setattr(ledger, "connect", real_connect)
    observation = await ledger.observe_study("study")
    assert observation["timely"]
    assert observation == await ledger.freeze(owner, "study", universe, synthetic=True)
