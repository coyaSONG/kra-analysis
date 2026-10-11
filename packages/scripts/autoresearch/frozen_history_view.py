"""Replay selected capture versions, never the latest receipt or request journal."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from autoresearch.kra_race_card_pdf_replay import archive_path, parse_json, read_bytes
from autoresearch.observed_history_seed import (
    SEED_FORMAT,
    digest,
    inspect_receipt,
    load_plan,
    pinned_path,
)
from autoresearch.prerace_hash_witness import timestamp

CLAIMS = (
    "complete_actual_start_history_verified",
    "historical_pre_race_availability_verified",
    "independent_timestamp_verified",
    "counts_as_70_percent_evidence",
)


def _capture(root: Path, pin: dict, *, entry: bool, cutoff) -> None:
    path = pinned_path(root, pin)
    manifest = parse_json(path.read_bytes())
    # Failed captures can contain partial pages; their bytes must still match.
    for page in manifest["pages"]:
        raw_path = archive_path(
            page["raw_path"] if entry else path.parent / page["raw_file"],
            archive_root=root,
        )
        raw = read_bytes(raw_path, limit=5 * 1024 * 1024)
        if (
            type(page["byte_count"]) is not int
            or len(raw) != page["byte_count"]
            or digest(raw) != page["sha256"]
        ):
            raise ValueError("frozen_history_raw_pin_mismatch")
    if cutoff is not None:
        value = manifest.get("collected_at" if entry else "capture_completed_at")
        if not isinstance(value, str) or timestamp(value) > cutoff:
            raise ValueError("frozen_history_source_after_cutoff_or_unknown")


def replay_frozen(
    root: Path, seed_path: Path, seed_sha256: str, *, cutoff: str | None = None
) -> dict:
    """Cutoff bounds local source clocks only, not independent PIT evidence."""
    root = root.resolve()
    raw = seed_path.read_bytes()
    if digest(raw) != seed_sha256:
        raise ValueError("frozen_history_seed_pin_mismatch")
    seed = parse_json(raw)
    plan, plan_hash = load_plan(root, require_current=False)
    if (
        seed.get("format_version") != SEED_FORMAT
        or seed.get("plan_sha256") != plan_hash
        or seed.get("collection_implementation") != plan["implementation"]
        or any(seed.get(k) is not False for k in CLAIMS)
        or type(seed.get("request_reservations")) is not int
        or not 0 <= seed["request_reservations"] <= plan["request_budget"]
    ):
        raise ValueError("unsupported_frozen_history_seed")
    materialized = timestamp(seed["materialized_at"])
    bound = timestamp(cutoff) if cutoff is not None else None
    if bound is not None and materialized > bound:
        raise ValueError("frozen_history_seed_after_cutoff")
    inventory = seed["inventory"]
    if [{"day": r["day"], "meet": r["meet"]} for r in inventory] != plan["units"]:
        raise ValueError("frozen_history_inventory_membership_mismatch")
    rebuilt, records, seen = [], [], set()
    for selected, unit in zip(inventory, plan["units"], strict=True):
        if selected["status"] == "not_attempted":
            inspected = {**unit, "status": "not_attempted", "records": []}
        else:
            for kind in ("result", "entry"):
                if selected.get(kind) is not None:
                    _capture(root, selected[kind], entry=kind == "entry", cutoff=bound)
            inspected = inspect_receipt(
                root,
                {
                    "unit": unit,
                    "plan_sha256": plan_hash,
                    "result": selected["result"],
                    "entry": selected["entry"],
                },
                unit,
                plan_hash,
            )
        rows = inspected.pop("records")
        for row in rows:
            key = (row["race_id"], row["chul_no"])
            if key in seen:
                raise ValueError("duplicate_frozen_history_event")
            seen.add(key)
            records.append(
                {
                    **row,
                    "source_capture_sha256": inspected["result"]["sha256"],
                    "source_available_at": inspected["available_at"],
                }
            )
        rebuilt.append({**inspected, "observed_rows": len(rows)})
    # Python equality conflates True, 1 and 1.0; frozen evidence must not.
    reconstructed = [rebuilt, records, dict(Counter(r["status"] for r in rebuilt))]
    selected = [inventory, seed["records"], seed["status_counts"]]
    if json.dumps(reconstructed, sort_keys=True, allow_nan=False) != json.dumps(
        selected, sort_keys=True, allow_nan=False
    ):
        raise ValueError("frozen_history_source_replay_mismatch")
    return seed
