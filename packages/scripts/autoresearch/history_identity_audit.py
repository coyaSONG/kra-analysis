"""Diagnose full-roster collisions without resolving unknown event identities."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from shared.kra_race_identity import validate_race_identity

from autoresearch.kra_race_card_pdf_replay import parse_json
from autoresearch.kra_result_snapshot import replay_result_pages
from autoresearch.observed_history_seed import (
    SEED_FORMAT,
    digest,
    exclusive,
    implementation,
    pinned_path,
    replay,
    save,
)


def _integer(value, maximum: int) -> int:
    if type(value) is int:
        result = value
    elif isinstance(value, str) and value.isascii() and value.isdecimal():
        result = int(value)
    else:
        raise ValueError("invalid_collision_identity")
    if not 1 <= result <= maximum:
        raise ValueError("invalid_collision_identity")
    return result


def group_rows(rows: list[dict], day: str) -> dict[int, dict[tuple[int, str], dict]]:
    """Keys are within-capture references, never inferred physical race IDs."""
    validate_race_identity(1, day, 1)
    groups, gates, horses = defaultdict(dict), set(), set()
    for row in rows:
        if str(_integer(row.get("rcDate"), 20991231)) != day:
            raise ValueError("collision_row_date_mismatch")
        number = _integer(row.get("rcNo"), 20)
        gate = _integer(row.get("chulNo"), 20)
        horse = str(_integer(row.get("hrNo"), 99_999_999))
        if (number, gate) in gates or (number, horse) in horses:
            raise ValueError("duplicate_collision_runner")
        gates.add((number, gate))
        horses.add((number, horse))
        groups[number][(gate, horse)] = row
    return dict(groups)


def compare_fields(left: dict, right: dict) -> dict:
    if not left or left.keys() != right.keys():
        raise ValueError("collision_requires_exact_roster")
    differences = Counter()
    for key, row in left.items():
        other = right[key]
        for field in row.keys() | other.keys():
            # Missing, null, bool, integer and float remain different raw evidence.
            if (
                field not in row
                or field not in other
                or json.dumps(row[field], sort_keys=True, allow_nan=False)
                != json.dumps(other[field], sort_keys=True, allow_nan=False)
            ):
                differences[field] += 1
    fields = {k for rows in (left, right) for row in rows.values() for k in row}
    return {
        "paired_row_count": len(left),
        "changed_field_row_counts": dict(sorted(differences.items())),
        "identical_fields_across_all_pairs": sorted(fields - differences.keys()),
        "identity_resolution": "not_resolved_by_roster_match",
    }


def audit_history(root: Path, seed_path: Path, seed_sha256: str) -> dict:
    root = root.resolve()
    original = seed_path.read_bytes()
    if digest(original) != seed_sha256:
        raise ValueError("collision_seed_pin_mismatch")
    seed = parse_json(original)
    if seed.get("format_version") != SEED_FORMAT:
        raise ValueError("unsupported_collision_seed")
    current = replay(root)
    ignored = {"implementation", "materialized_at"}
    if {k: v for k, v in seed.items() if k not in ignored} != {
        k: v for k, v in current.items() if k not in ignored
    }:
        raise ValueError("collision_seed_replay_mismatch")
    return audit_replayed_seed(root, seed, seed_sha256)


def audit_replayed_seed(root: Path, seed: dict, seed_sha256: str) -> dict:
    """Audit a caller-verified latest or explicitly selected-source seed."""
    root = root.resolve()
    admitted, unbound, source_pins = [], [], []
    for unit in seed["inventory"]:
        if unit["status"] not in ("api_reported_rows", "identity_unresolved"):
            continue
        path = pinned_path(root, unit["result"])
        raw = replay_result_pages(path)
        if raw["capture_manifest_sha256"] != unit["result"]["sha256"]:
            raise ValueError("collision_source_changed_during_replay")
        source_pins.append(
            {
                "result": unit["result"],
                "entry": unit.get("entry"),
                "page_pins": raw["page_pins"],
                "captured_at": raw["manifest"]["capture_completed_at"],
            }
        )
        for number, rows in sorted(group_rows(raw["rows"], unit["day"]).items()):
            item = {
                "requested_day": unit["day"],
                "requested_meet": unit["meet"],
                "returned_race_no": number,
                "source_capture_sha256": unit["result"]["sha256"],
                "identity_status": unit["status"],
                "rows": rows,
            }
            if unit["status"] == "api_reported_rows":
                item["race_id"] = f"{unit['day']}_{unit['meet']}_{number}"
                admitted.append(item)
            else:
                unbound.append(item)
    index = defaultdict(list)
    for item in admitted:
        index[frozenset(item["rows"])].append(item)

    def reference(item):
        return {k: v for k, v in item.items() if k != "rows"}

    def candidates(item):
        return [
            {
                **reference(other),
                **compare_fields(item["rows"], other["rows"]),
            }
            for other in index[frozenset(item["rows"])]
            if other is not item
        ]

    unresolved = [
        {**reference(item), "row_count": len(item["rows"]), "matches": candidates(item)}
        for item in unbound
    ]
    observed_collisions = [
        {**reference(item), "matches": matches}
        for item in admitted
        if (matches := candidates(item))
    ]
    affected_ids = {r["race_id"] for r in observed_collisions}
    pairs = {
        tuple(sorted((item["race_id"], match["race_id"])))
        for item in observed_collisions
        for match in item["matches"]
    }
    return {
        "format_version": "kra-history-identity-audit-v1",
        "seed_sha256": seed_sha256,
        "plan_sha256": seed["plan_sha256"],
        "implementation": {
            **implementation(),
            "audit_sha256": digest(Path(__file__).read_bytes()),
        },
        "inventory": seed["inventory"],
        "source_pins": source_pins,
        "observed_race_count": len(admitted),
        "observed_row_count": len(seed["records"]),
        "observed_collision_group_count": len(affected_ids),
        "observed_collision_pair_count": len(pairs),
        "observed_collision_row_count": sum(
            row["race_id"] in affected_ids for row in seed["records"]
        ),
        "unbound_row_count": sum(r["row_count"] for r in unresolved),
        "unbound_group_count": len(unresolved),
        "unbound_groups_with_matches": sum(bool(r["matches"]) for r in unresolved),
        "unbound_groups_with_multiple_matches": sum(
            len(r["matches"]) > 1 for r in unresolved
        ),
        "unbound_groups": unresolved,
        "observed_collision_groups": observed_collisions,
        "source_review_required": bool(observed_collisions)
        or any(
            unit["status"] not in ("api_reported_rows", "empty_unconfirmed")
            for unit in seed["inventory"]
        ),
        "automatic_identity_resolution_allowed": False,
        "complete_actual_start_history_verified": False,
        "historical_pre_race_availability_verified": False,
        "training_approved": False,
        "counts_as_70_percent_evidence": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--seed-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    with exclusive(args.root):
        report = audit_history(args.root, args.seed, args.seed_sha256)
        sha256 = save(args.output, report)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "sha256": sha256,
                **{k: v for k, v in report.items() if k.endswith("_count")},
                "unbound_groups_with_matches": report["unbound_groups_with_matches"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
