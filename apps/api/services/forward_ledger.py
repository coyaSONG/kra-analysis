"""Fixed B0 payloads and explicit PostgreSQL commit-observation boundaries."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import asyncpg

ARM = "b0_numeric_gate_v1"
DEFAULT_SCHEMA = "research_forward"
SQL_PATH = Path(__file__).resolve().parents[1] / "infrastructure/forward_ledger.sql"


def identifier(value: str) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", value):
        raise ValueError("invalid_forward_sql_identifier")
    return value


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def implementation_digest() -> str:
    root = Path(__file__).resolve().parents[3]
    paths = [
        "apps/api/services/forward_ledger.py",
        "apps/api/infrastructure/forward_ledger.sql",
        "apps/api/scripts/run_forward_b0.py",
        "packages/scripts/shared/kra_entry_sheet.py",
        "packages/scripts/autoresearch/kra_race_card_pdf_replay.py",
    ]
    return digest(
        canonical(
            {
                path: hashlib.sha256((root / path).read_bytes()).hexdigest()
                for path in paths
            }
        )
    )


def timestamp(value: str) -> datetime:
    stamp = datetime.fromisoformat(value)
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("forward_timestamp_requires_timezone")
    return stamp.astimezone(UTC)


def b0_payload(
    *,
    race_id: str,
    universe_sha256: str,
    entries: list[dict[str, Any]],
    source: dict[str, Any],
) -> str:
    roster: list[dict[str, Any]] = []
    for row in entries:
        gate, raw_id = row["chulNo"], row["hrNo"]
        if type(gate) is not int or not 1 <= gate <= 20:
            raise ValueError("invalid_b0_gate")
        if not re.fullmatch(r"[0-9]{1,8}", str(raw_id)) or int(raw_id) == 0:
            raise ValueError("invalid_b0_horse_id")
        roster.append({"chul_no": gate, "horse_id": str(int(raw_id))})
    roster.sort(key=lambda row: row["chul_no"])
    if (
        not 3 <= len(roster) <= 20
        or len({r["chul_no"] for r in roster}) != len(roster)
        or len({r["horse_id"] for r in roster}) != len(roster)
    ):
        raise ValueError("incomplete_or_duplicate_b0_roster")
    return canonical(
        {
            "format_version": "kra-forward-b0-v1",
            "arm_id": ARM,
            "race_id": race_id,
            "universe_sha256": universe_sha256,
            "implementation_sha256": implementation_digest(),
            "roster": roster,
            "selection": [r["horse_id"] for r in roster[:3]],
            "source": source,
        }
    )


async def install(
    connection: asyncpg.Connection, runtime_role: str, *, schema: str = DEFAULT_SCHEMA
) -> None:
    schema, role = identifier(schema), identifier(runtime_role)
    owner = await connection.fetchval("SELECT current_user")
    if role == owner:
        raise ValueError("forward_runtime_must_not_be_owner")
    async with connection.transaction():
        await connection.execute(SQL_PATH.read_text().replace("__SCHEMA__", schema))
        await connection.execute(f"GRANT USAGE ON SCHEMA {schema} TO {role}")
        await connection.execute(
            f"GRANT SELECT ON ALL TABLES IN SCHEMA {schema} TO {role}"
        )
        for signature in (
            "submit(text,text,text)",
            "observe(text,text)",
            "observe_study(text)",
        ):
            await connection.execute(
                f"GRANT EXECUTE ON FUNCTION {schema}.{signature} TO {role}"
            )


class ForwardLedger:
    def __init__(self, runtime_dsn: str, *, schema: str = DEFAULT_SCHEMA):
        self.dsn = runtime_dsn
        self.schema = identifier(schema)

    async def connect(self) -> asyncpg.Connection:
        connection = await asyncpg.connect(self.dsn, timeout=15, statement_cache_size=0)
        try:
            # Reject owner/superuser or inherited writer access in the runtime path.
            for table in (
                "studies",
                "members",
                "submissions",
                "observations",
                "study_observations",
            ):
                writable = await connection.fetchval(
                    "SELECT has_table_privilege(current_user,$1,'INSERT,UPDATE,DELETE,TRUNCATE')",
                    f"{self.schema}.{table}",
                )
                if writable:
                    raise ValueError("forward_runtime_has_direct_write_privilege")
        except BaseException:
            await connection.close()
            raise
        return connection

    async def freeze(
        self,
        owner: asyncpg.Connection,
        study_id: str,
        universe: dict[str, Any],
        *,
        synthetic: bool = False,
    ) -> dict[str, Any]:
        payload = canonical(universe)
        races = universe["races"]
        if not races or len({r["race_id"] for r in races}) != len(races):
            raise ValueError("invalid_forward_universe")
        earliest = min(timestamp(r["feature_cutoff_at"]) for r in races)
        async with owner.transaction():
            existing = await owner.fetchrow(
                f"SELECT * FROM {self.schema}.studies WHERE study_id=$1", study_id
            )
            if existing:
                if existing["payload"] != payload or existing["synthetic"] != synthetic:
                    raise ValueError("forward_universe_conflict")
            else:
                now = await owner.fetchval("SELECT clock_timestamp()")
                if now >= earliest:
                    raise ValueError("forward_universe_deadline_passed")
                await owner.execute(
                    f"INSERT INTO {self.schema}.studies(study_id,race_date,synthetic,payload,sha256,earliest_cutoff) VALUES($1,$2,$3,$4,$5,$6)",
                    study_id,
                    universe["race_date"],
                    synthetic,
                    payload,
                    digest(payload),
                    earliest,
                )
                await owner.executemany(
                    f"INSERT INTO {self.schema}.members VALUES($1,$2,$3)",
                    [
                        (study_id, r["race_id"], timestamp(r["feature_cutoff_at"]))
                        for r in races
                    ],
                )
        connection = await self.connect()
        try:
            result = await connection.fetchval(
                f"SELECT {self.schema}.observe_study($1)", study_id
            )
            return json.loads(result)
        finally:
            await connection.close()

    async def get_study(self, study_id: str) -> dict[str, Any] | None:
        connection = await self.connect()
        try:
            row = await connection.fetchrow(
                f"SELECT * FROM {self.schema}.studies WHERE study_id=$1", study_id
            )
            return dict(row) if row else None
        finally:
            await connection.close()

    async def observe_study(self, study_id: str) -> dict[str, Any]:
        connection = await self.connect()
        try:
            return json.loads(
                await connection.fetchval(
                    f"SELECT {self.schema}.observe_study($1)", study_id
                )
            )
        finally:
            await connection.close()

    async def get_submission(
        self, study_id: str, race_id: str
    ) -> dict[str, Any] | None:
        connection = await self.connect()
        try:
            row = await connection.fetchrow(
                f"SELECT payload,sha256 FROM {self.schema}.submissions WHERE study_id=$1 AND race_id=$2 AND arm_id=$3",
                study_id,
                race_id,
                ARM,
            )
            return dict(row) if row else None
        finally:
            await connection.close()

    async def submit(self, study_id: str, race_id: str, payload: str) -> dict[str, Any]:
        connection = await self.connect()
        try:
            async with connection.transaction(isolation="read_committed"):
                result = json.loads(
                    await connection.fetchval(
                        f"SELECT {self.schema}.submit($1,$2,$3)",
                        study_id,
                        race_id,
                        payload,
                    )
                )
        finally:
            await connection.close()
        # A separate connection cannot read the first transaction's uncommitted write.
        witness = await self.connect()
        try:
            async with witness.transaction(isolation="read_committed"):
                observed = json.loads(
                    await witness.fetchval(
                        f"SELECT {self.schema}.observe($1,$2)", study_id, race_id
                    )
                )
            return {"submission": result, "observation": observed}
        finally:
            await witness.close()

    async def report(self, study_id: str) -> list[dict[str, Any]]:
        connection = await self.connect()
        try:
            rows = await connection.fetch(
                f"""
                SELECT m.race_id, m.cutoff_at, s.sha256, s.registered_at,
                       o.observed_committed_at, o.timely,
                       CASE WHEN s.sha256 IS NULL THEN 'missing_submission'
                            WHEN o.timely IS TRUE THEN 'timely_committed'
                            ELSE 'commit_timeliness_unproven' END AS status
                FROM {self.schema}.members m
                LEFT JOIN {self.schema}.submissions s USING(study_id,race_id)
                LEFT JOIN {self.schema}.observations o USING(study_id,race_id,arm_id)
                WHERE m.study_id=$1 ORDER BY m.race_id
            """,
                study_id,
            )
            return [dict(row) for row in rows]
        finally:
            await connection.close()
