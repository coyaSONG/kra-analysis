"""Explicitly install or run the official-card B0 forward collection path."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import asyncpg

from services.forward_ledger import (
    ForwardLedger,
    b0_payload,
    canonical,
    digest,
    identifier,
    implementation_digest,
    install,
    timestamp,
)


def payload_from_capture(
    race: dict[str, Any], universe_hash: str, path: Path, root: Path
) -> str:
    from autoresearch.kra_race_card_pdf_replay import archive_path, replay_entry_pages
    from shared.kra_entry_sheet import build_entry_snapshot

    path = archive_path(path, archive_root=root)
    rows, manifest, evidence = replay_entry_pages(
        path,
        archive_root=root,
        meet=race["meet"],
        race_date=race["race_date"],
    )
    entry = build_entry_snapshot(
        rows,
        meet=race["meet"],
        race_date=race["race_date"],
        race_no=race["race_no"],
        collected_at=timestamp(manifest["collected_at"]),
    )
    expected_time = (
        timestamp(race["scheduled_start_at"])
        .astimezone(ZoneInfo("Asia/Seoul"))
        .strftime("%H%M")
    )
    if (
        entry["scheduled_start_time"] != expected_time
        or len(entry["entries"]) != race["runners"]
    ):
        raise ValueError("entry_conflicts_with_frozen_schedule")
    return b0_payload(
        race_id=race["race_id"],
        universe_sha256=universe_hash,
        entries=entry["entries"],
        source={**evidence, "available_at": entry["collected_at"]},
    )


async def run_day(args: argparse.Namespace) -> dict[str, Any]:
    from autoresearch.kra_entry_sheet_snapshot import collect_entry_sheet_snapshot
    from autoresearch.kra_race_card_pdf_replay import parse_json
    from autoresearch.kra_schedule_snapshot import (
        collect_schedule_snapshot,
        freeze_universe_candidate,
        replay_schedule_snapshot,
    )

    identifier(args.study)
    root = args.archive.resolve()
    directory = root / args.study
    directory.mkdir(parents=True, exist_ok=True)
    runtime_dsn, owner_dsn = os.getenv(args.runtime_env), os.getenv(args.owner_env)
    ledger = ForwardLedger(runtime_dsn, schema=args.schema) if runtime_dsn else None
    stored = await ledger.get_study(args.study) if ledger else None
    if stored:
        if stored["synthetic"] or stored["race_date"] != args.race_date:
            raise ValueError("operational_study_identity_conflict")
        universe = parse_json(stored["payload"].encode())
        await ledger.observe_study(args.study)
    else:
        capture = await collect_schedule_snapshot(output_dir=directory / "schedules")
        report = replay_schedule_snapshot(capture, race_date=args.race_date)
        if report["status"] != "reconciled" or report["source_failures"]:
            return {
                "status": "awaiting_card",
                "race_date": args.race_date,
                "schedule_capture": str(capture),
                "schedule_status": report["status"],
                "future_submissions_started": False,
            }
        if not ledger or not owner_dsn:
            return {
                "status": "awaiting_database_configuration",
                "race_date": args.race_date,
                "schedule_capture": str(capture),
                "future_submissions_started": False,
            }
        candidate = (
            directory / f"universe_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%f')}.json"
        )
        freeze_universe_candidate(capture, race_date=args.race_date, output=candidate)
        universe = parse_json(candidate.read_bytes())
        universe["b0_implementation_sha256"] = implementation_digest()
        owner = await asyncpg.connect(owner_dsn, timeout=15, statement_cache_size=0)
        try:
            observation = await ledger.freeze(owner, args.study, universe)
        finally:
            await owner.close()
        if not observation["timely"]:
            return {
                "status": "universe_commit_timeliness_unproven",
                "future_submissions_started": False,
            }
    assert ledger is not None
    if universe.get("b0_implementation_sha256") != implementation_digest():
        raise ValueError("frozen_b0_implementation_changed")
    universe_hash = digest(canonical(universe))
    failures = []
    for race in universe["races"]:
        race_id = race["race_id"]
        request_path = directory / f"request_{race_id}.json"
        try:
            existing = await ledger.get_submission(args.study, race_id)
            if existing:
                payload = existing["payload"]
            elif request_path.exists():
                payload = request_path.read_text()
                saved = parse_json(payload.encode())
                rebuilt = payload_from_capture(
                    race, universe_hash, Path(saved["source"]["manifest_path"]), root
                )
                if payload != rebuilt:
                    raise ValueError("saved_request_evidence_mismatch")
            else:
                if datetime.now(UTC) >= timestamp(race["feature_cutoff_at"]):
                    raise ValueError("forward_deadline_passed")
                credentials = {"api_key": args.api_key_file.read_text()}
                remaining = (
                    timestamp(race["feature_cutoff_at"]) - datetime.now(UTC)
                ).total_seconds()
                async with asyncio.timeout(min(60, max(0, remaining))):
                    captured = await collect_entry_sheet_snapshot(
                        meet=race["meet"],
                        race_date=race["race_date"],
                        race_no=race["race_no"],
                        output_dir=directory / "entries",
                        **credentials,
                    )
                payload = payload_from_capture(
                    race, universe_hash, Path(captured["manifest_path"]), root
                )
                with request_path.open("x", encoding="utf-8") as stream:
                    stream.write(payload)
            await ledger.submit(args.study, race_id, payload)
        except (
            ValueError,
            KeyError,
            OSError,
            asyncpg.PostgresError,
            TimeoutError,
        ) as exc:
            # Library errors can embed connection details. Persist only a bounded type.
            failures.append({"race_id": race_id, "error_type": type(exc).__name__})
    rows = await ledger.report(args.study)
    return {
        "status": "reconciled"
        if len(rows) == len(universe["races"])
        and all(r["status"] == "timely_committed" for r in rows)
        and not failures
        else "incomplete",
        "study_id": args.study,
        "race_count": len(universe["races"]),
        "ledger": rows,
        "attempt_failures": failures,
        "counts_as_accuracy_evidence": False,
        "future_submissions_started": any(
            r["status"] == "timely_committed" for r in rows
        ),
    }


async def execute(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "run":
        return await run_day(args)
    owner = await asyncpg.connect(
        os.environ[args.owner_env], timeout=15, statement_cache_size=0
    )
    try:
        await install(owner, args.runtime_role, schema=args.schema)
    finally:
        await owner.close()
    return {"status": "installed", "schema": args.schema}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("install")
    setup.add_argument("--runtime-role", required=True)
    run = commands.add_parser("run")
    run.add_argument("--runtime-env", default="KRA_FORWARD_RUNTIME_DSN")
    run.add_argument("--study", required=True)
    run.add_argument("--race-date", required=True)
    run.add_argument("--archive", type=Path, required=True)
    run.add_argument("--api-key-file", type=Path, required=True)
    for command in (setup, run):
        command.add_argument("--owner-env", default="KRA_FORWARD_OWNER_DSN")
        command.add_argument("--schema", default="research_forward")
    args = parser.parse_args(argv)
    try:
        result = asyncio.run(execute(args))
    except (ValueError, KeyError, OSError, asyncpg.PostgresError, TimeoutError) as exc:
        result = {"status": "failed", "error_type": type(exc).__name__}
    if args.command == "run":
        args.archive.mkdir(parents=True, exist_ok=True)
        report_path = (
            args.archive / f"run_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%f')}.json"
        )
        with report_path.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, sort_keys=True, default=str)
            stream.write("\n")
        result["report_path"] = str(report_path)
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result["status"] in ("installed", "reconciled") else 2


if __name__ == "__main__":
    raise SystemExit(main())
