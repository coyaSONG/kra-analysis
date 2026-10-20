"""Profile raw historical time fields without fitting or defining speed features."""

import argparse
import math
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

from autoresearch.frozen_history_view import replay_frozen
from autoresearch.kra_result_snapshot import replay_result_pages
from autoresearch.observed_history_seed import digest, pinned_path
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import encoded

VERSION = "history-time-field-audit-v1"
STATES = (
    "absent",
    "null",
    "empty",
    "boolean",
    "nonnumeric",
    "nonfinite",
    "negative",
    "zero",
    "positive",
)


def state(row, field):
    if field not in row:
        return "absent"
    value = row[field]
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str) and not value.strip():
        return "empty"
    if type(value) not in (str, int, float):
        return "nonnumeric"
    try:
        number = float(value)
    except (ValueError, OverflowError):
        return "nonnumeric"
    if not math.isfinite(number):
        return "nonfinite"
    return "positive" if number > 0 else "zero" if number == 0 else "negative"


def key(row, day, meet):
    return (
        f"{day}_{meet}_{int(row['rcNo'])}",
        int(row["chulNo"]),
        str(int(row["hrNo"])),
    )


def join_rows(raw_rows, selected, day, meet):
    """The frozen replay validates identities first; never align by source order."""
    expected = {(r["race_id"], r["chul_no"], r["horse_id"]): r for r in selected}
    if len(expected) != len(selected):
        raise ValueError("time_audit_duplicate_selected_identity")
    seen, joined = set(), []
    for raw in raw_rows:
        identity = key(raw, day, meet)
        if identity in seen or identity not in expected:
            raise ValueError("time_audit_raw_identity_mismatch")
        seen.add(identity)
        selected_row = expected[identity]
        if encoded(raw.get("rcTime")) != encoded(selected_row["raw_rc_time"]):
            raise ValueError("time_audit_elapsed_value_changed")
        joined.append({"identity": identity, "raw": raw})
    if seen != set(expected):
        raise ValueError("time_audit_missing_raw_identity")
    return joined


def profile(rows):
    fields = sorted(
        {name for row in rows for name in row["raw"] if name.endswith("Time")}
        | {"rcTime"}
    )
    groups = defaultdict(list)
    for row in rows:
        groups[row["identity"][0].split("_")[1]].append(row)
    report = {}
    for meet, group in sorted(groups.items()):
        report[meet] = {
            "rows": len(group),
            "races": len({r["identity"][0] for r in group}),
            "fields": {},
        }
        for field in fields:
            counts = Counter(state(row["raw"], field) for row in group)
            report[meet]["fields"][field] = {s: counts[s] for s in STATES}
    return {"fields": fields, "by_meet": report}


def audit(root, seed_path, seed_sha, cutoff):
    root, seed_path = Path(root), Path(seed_path)
    if timestamp(cutoff) > datetime.now(UTC):
        raise ValueError("time_audit_future_source_bound")
    seed = replay_frozen(root, seed_path, seed_sha, cutoff=cutoff)
    records = defaultdict(list)
    for row in seed["records"]:
        records[row["source_capture_sha256"]].append(row)
    joined, captures = [], []
    skipped = Counter()
    for unit in seed["inventory"]:
        if unit["status"] != "api_reported_rows":
            skipped[unit["status"]] += 1
            continue
        path = pinned_path(root, unit["result"])
        raw = replay_result_pages(path)
        sha = unit["result"]["sha256"]
        if raw["capture_manifest_sha256"] != sha:
            raise ValueError("time_audit_capture_changed")
        joined.extend(
            join_rows(
                raw["rows"],
                records[sha],
                unit["day"],
                unit["meet"],
            )
        )
        captures.append(
            {
                "result": unit["result"],
                "available_at": unit["available_at"],
                "page_pins": raw["page_pins"],
            }
        )
    expected = {(r["race_id"], r["chul_no"], r["horse_id"]) for r in seed["records"]}
    actual = [r["identity"] for r in joined]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise ValueError("time_audit_incomplete_seed_join")
    dates = sorted({r["identity"][0][:8] for r in joined})
    return {
        "format_version": VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "seed_sha256": seed_sha,
        "source_local_clock_bound": cutoff,
        "source": "https://apis.data.go.kr/B551015/API214_1/RaceDetailResult_1",
        "implementation_sha256": digest(Path(__file__).read_bytes()),
        "rows": len(joined),
        "races": len({r["identity"][0] for r in joined}),
        "dates": dates,
        "seed_status_counts": seed["status_counts"],
        "non_row_units_retained_by_status": dict(sorted(skipped.items())),
        "row_evidence_counts": dict(
            sorted(Counter(r["evidence"] for r in seed["records"]).items())
        ),
        "captures": captures,
        **profile(joined),
        "interpretation": "raw_value_states_not_sectional_units_or_feature_eligibility",
        "all_seed_record_identities_joined": True,
        "historical_prerace_availability_verified": False,
        "complete_actual_start_history_verified": False,
        "field_units_verified": False,
        "sectional_cross_source_agreement_verified": False,
        "zero_semantics_verified": False,
        "target_outcomes_loaded": False,
        "fits": 0,
        "network_requests": 0,
        "training_approved": False,
        "models_modified": False,
        "accuracy": None,
        "counts_as_70_percent_evidence": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--source-bound", required=True)
    args = parser.parse_args(argv)
    result = audit(args.root, args.seed, args.sha256, args.source_bound)
    print(encoded(result).decode(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
