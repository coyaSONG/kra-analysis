"""Bounded append-only collection of observed results, not historical PIT proof."""

from __future__ import annotations

import argparse
import asyncio
import fcntl
import hashlib
import json
import os
import platform
import tempfile
from collections import Counter
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from importlib.metadata import version
from pathlib import Path

import httpx
from shared.kra_race_identity import validate_race_identity

from autoresearch.kra_entry_sheet_snapshot import (
    ENTRY_URL,
    collect_entry_sheet_snapshot,
)
from autoresearch.kra_race_card_pdf_replay import parse_json
from autoresearch.kra_result_snapshot import (
    RESULT_URL,
    collect_result_snapshot,
    replay_result_snapshot,
)

FORMAT = "kra-observed-history-plan-v1"
SEED_FORMAT = "kra-observed-history-seed-v1"
MEETS = (1, 2, 3, 4)
USABLE = {"api_reported_rows", "empty_unconfirmed"}
ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "autoresearch/observed_history_seed.py",
    "shared/observed_result_history.py",
    "autoresearch/kra_result_snapshot.py",
    "autoresearch/kra_entry_sheet_snapshot.py",
    "autoresearch/kra_race_card_pdf_replay.py",
    "shared/kra_result_history.py",
    "shared/kra_entry_sheet.py",
    "shared/kra_race_identity.py",
)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def save(path: Path, value: dict) -> str:
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    with tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=".history-partial-", delete=False
    ) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
            # A hard link publishes complete bytes atomically without overwriting.
            os.link(temporary, path)
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            temporary.unlink()
    return digest(raw)


def implementation() -> dict:
    return {
        "sources": {name: digest((ROOT / name).read_bytes()) for name in SOURCES},
        "python": platform.python_version(),
        "httpx": version("httpx"),
    }


def days(start: str, end: str) -> list[str]:
    validate_race_identity(1, start, 1)
    validate_race_identity(1, end, 1)
    first, last = (datetime.strptime(day, "%Y%m%d") for day in (start, end))
    count = (last - first).days + 1
    if not 1 <= count <= 366:
        raise ValueError("invalid_history_date_range")
    return [(first + timedelta(days=i)).strftime("%Y%m%d") for i in range(count)]


def make_plan(start: str, end: str, budget: int = 2000) -> dict:
    if type(budget) is not int or not 1 <= budget <= 2000:
        raise ValueError("invalid_history_request_budget")
    return {
        "format_version": FORMAT,
        "start": start,
        "end": end,
        "request_budget": budget,
        "implementation": implementation(),
        "units": [
            {"day": day, "meet": meet} for day in days(start, end) for meet in MEETS
        ],
    }


def load_plan(root: Path, *, require_current: bool = True) -> tuple[dict, str]:
    raw = (root / "plan.json").read_bytes()
    plan = parse_json(raw)
    expected = make_plan(plan["start"], plan["end"], plan["request_budget"])
    if not require_current:
        expected["implementation"] = plan["implementation"]
    if plan != expected:
        raise ValueError("history_plan_or_implementation_changed")
    return plan, digest(raw)


@contextmanager
def exclusive(root: Path):
    with (root / "collector.lock").open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def pin(root: Path, path: Path) -> dict:
    return {"path": str(path.relative_to(root)), "sha256": digest(path.read_bytes())}


def pinned_path(root: Path, item: dict) -> Path:
    path = root / item["path"]
    if Path(item["path"]).is_absolute() or not path.resolve().is_relative_to(
        root.resolve()
    ):
        raise ValueError("history_capture_path_escape")
    if path.is_symlink() or digest(path.read_bytes()) != item["sha256"]:
        raise ValueError("history_capture_pin_mismatch")
    return path


def inspect_receipt(root: Path, receipt: dict, unit: dict, plan_hash: str) -> dict:
    if receipt["plan_sha256"] != plan_hash or receipt["unit"] != unit:
        raise ValueError("history_receipt_membership_mismatch")
    result_path = pinned_path(root, receipt["result"])
    manifest = parse_json(result_path.read_bytes())
    if (manifest["race_date"], manifest["meet"]) != (unit["day"], unit["meet"]):
        raise ValueError("history_capture_identity_mismatch")
    entry_path = None
    if receipt["entry"] is not None:
        candidate = pinned_path(root, receipt["entry"])
        entry = parse_json(candidate.read_bytes())
        if entry.get("collection_status") == "captured":
            entry_path = candidate
    base = {**unit, "result": receipt["result"], "entry": receipt["entry"]}
    if manifest["status"] not in ("captured", "identity_unresolved"):
        return {**base, "status": "failed", "records": []}
    try:
        report = replay_result_snapshot(
            result_path, entry_capture=entry_path, archive_root=root
        )
    except ValueError as exc:
        if str(exc) not in ("missing_result_venue", "result_entry_roster_mismatch"):
            raise
        return {
            **base,
            "status": "identity_unresolved",
            "reason": str(exc),
            "records": [],
        }
    if report["capture_manifest_sha256"] != receipt["result"]["sha256"]:
        raise ValueError("history_capture_changed_during_replay")
    if (
        entry_path is not None
        and report["entry_binding_pins"][0]["manifest_sha256"]
        != receipt["entry"]["sha256"]
    ):
        raise ValueError("history_entry_changed_during_replay")
    return {
        **base,
        "status": report["population_status"],
        "available_at": report["combined_sources_available_at"],
        "page_pins": report["page_pins"],
        "entry_binding_pins": report["entry_binding_pins"],
        "records": report["records"],
    }


def receipts(root: Path, unit: dict) -> list[Path]:
    folder = root / "receipts" / f"{unit['day']}_{unit['meet']}"
    paths = sorted(folder.glob("*.json"))
    if [p.name for p in paths] != [f"{i:04d}.json" for i in range(1, len(paths) + 1)]:
        raise ValueError("history_receipt_sequence_gap")
    return paths


def request_count(root: Path, plan_hash: str) -> int:
    paths = sorted((root / "requests").glob("*.json"))
    for i, path in enumerate(paths, 1):
        row = parse_json(path.read_bytes())
        if (
            path.name != f"{i:06d}.json"
            or row["ordinal"] != i
            or row["plan_sha256"] != plan_hash
        ):
            raise ValueError("history_request_journal_mismatch")
    return len(paths)


async def collect(
    root: Path,
    api_key: str,
    *,
    retry_failed: bool = False,
    transport=None,
    delay: float = 1.0,
) -> dict:
    plan, plan_hash = load_plan(root)
    (root / "requests").mkdir(exist_ok=True)
    count = request_count(root, plan_hash)
    last_request, failures, completed = 0.0, 0, 0
    allowed = {(u["day"], u["meet"]) for u in plan["units"]}

    async def reserve(request: httpx.Request):
        nonlocal count, last_request
        url = str(request.url.copy_with(query=None))
        day, meet = request.url.params["rc_date"], int(request.url.params["meet"])
        if url not in (RESULT_URL, ENTRY_URL) or (day, meet) not in allowed:
            raise ValueError("unplanned_history_request")
        if count >= plan["request_budget"]:
            raise ValueError("history_request_budget_exhausted")
        loop = asyncio.get_running_loop()
        await asyncio.sleep(max(0.0, last_request + delay - loop.time()))
        count += 1
        save(
            root / "requests" / f"{count:06d}.json",
            {
                "ordinal": count,
                "plan_sha256": plan_hash,
                "day": day,
                "meet": meet,
                "page": int(request.url.params["pageNo"]),
                "source": "API214" if url == RESULT_URL else "API26",
                "reserved_at": datetime.now(UTC).isoformat(),
            },
        )
        last_request = loop.time()

    async with httpx.AsyncClient(
        timeout=30,
        follow_redirects=False,
        trust_env=False,
        transport=transport,
        event_hooks={"request": [reserve]},
    ) as client:
        for unit in plan["units"]:
            previous = receipts(root, unit)
            if previous:
                latest = inspect_receipt(
                    root, parse_json(previous[-1].read_bytes()), unit, plan_hash
                )
                if latest["status"] in USABLE or not retry_failed:
                    continue
            if count >= plan["request_budget"] or failures >= 3:
                break
            path = await collect_result_snapshot(
                meet=unit["meet"],
                race_date=unit["day"],
                api_key=api_key,
                output_dir=root / "results",
                client=client,
            )
            result = parse_json(path.read_bytes())
            entry_pin = None
            if (
                result["status"] == "identity_unresolved"
                and count < plan["request_budget"]
            ):
                try:
                    async with asyncio.timeout(300):
                        entry = await collect_entry_sheet_snapshot(
                            meet=unit["meet"],
                            race_date=unit["day"],
                            race_no=1,
                            api_key=api_key,
                            output_dir=root / "entries",
                            client=client,
                        )
                    entry_pin = pin(root, Path(entry["manifest_path"]))
                except TimeoutError:
                    pass
            receipt = {
                "plan_sha256": plan_hash,
                "unit": unit,
                "result": pin(root, path),
                "entry": entry_pin,
            }
            folder = root / "receipts" / f"{unit['day']}_{unit['meet']}"
            folder.mkdir(parents=True, exist_ok=True)
            save(folder / f"{len(previous) + 1:04d}.json", receipt)
            inspected = inspect_receipt(root, receipt, unit, plan_hash)
            failures = failures + 1 if inspected["status"] == "failed" else 0
            completed += 1
            print(
                json.dumps({**unit, "status": inspected["status"], "requests": count}),
                flush=True,
            )
    return {"new_units": completed, "request_reservations": count}


def replay(root: Path) -> dict:
    # Replaying old bytes is allowed; resuming collection still requires old code.
    plan, plan_hash = load_plan(root, require_current=False)
    inventory, records, seen = [], [], set()
    for unit in plan["units"]:
        paths = receipts(root, unit)
        inspected = (
            inspect_receipt(root, parse_json(paths[-1].read_bytes()), unit, plan_hash)
            if paths
            else {**unit, "status": "not_attempted", "records": []}
        )
        rows = inspected.pop("records")
        for row in rows:
            key = (row["race_id"], row["chul_no"])
            if key in seen:
                raise ValueError("duplicate_history_event")
            seen.add(key)
            records.append(
                {
                    **row,
                    "source_capture_sha256": inspected["result"]["sha256"],
                    "source_available_at": inspected["available_at"],
                }
            )
        inventory.append({**inspected, "observed_rows": len(rows)})
    return {
        "format_version": SEED_FORMAT,
        "plan_sha256": plan_hash,
        "collection_implementation": plan["implementation"],
        "implementation": implementation(),
        "materialized_at": datetime.now(UTC).isoformat(),
        "request_reservations": request_count(root, plan_hash),
        "status_counts": dict(Counter(r["status"] for r in inventory)),
        "inventory": inventory,
        "records": records,
        "complete_actual_start_history_verified": False,
        "historical_pre_race_availability_verified": False,
        "independent_timestamp_verified": False,
        "counts_as_70_percent_evidence": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("init", "collect", "export", "project"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--budget", type=int, default=2000)
    parser.add_argument("--api-key-file", type=Path)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--corpus-sha256")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.command == "init":
        plan = make_plan(args.start, args.end, args.budget)
        root.mkdir(parents=True, exist_ok=False)
        print(json.dumps({"plan_sha256": save(root / "plan.json", plan)}))
        return 0
    with exclusive(root):
        if args.command == "collect":
            if args.api_key_file is None:
                parser.error("collect requires --api-key-file")
            print(
                json.dumps(
                    asyncio.run(
                        collect(
                            root,
                            args.api_key_file.read_text(),
                            retry_failed=args.retry_failed,
                        )
                    )
                )
            )
            return 0
        if args.output is None:
            parser.error("export/project requires --output")
        seed = replay(root)
        output = seed
        if args.command == "project":
            from shared.observed_result_history import project_history

            if args.corpus is None or args.corpus_sha256 is None:
                parser.error("project requires --corpus and --corpus-sha256")
            raw = args.corpus.read_bytes()
            if digest(raw) != args.corpus_sha256:
                raise ValueError("history_roster_corpus_pin_mismatch")
            corpus = parse_json(raw)
            output = {
                "format_version": "kra-observed-history-projection-v1",
                "corpus_sha256": digest(raw),
                "seed": seed,
                "races": [
                    project_history(
                        {"race_id": r["race_id"], "roster": r["roster"]}, seed
                    )
                    for r in corpus["ledger"]
                ],
                "training_approved": False,
                "counts_as_70_percent_evidence": False,
            }
        print(
            json.dumps(
                {
                    "output": str(args.output),
                    "sha256": save(args.output, output),
                    "status_counts": seed["status_counts"],
                    "observed_rows": len(seed["records"]),
                }
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
