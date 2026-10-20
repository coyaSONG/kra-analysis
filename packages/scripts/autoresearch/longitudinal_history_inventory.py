"""Read-only structural repeat and original-table inventory, never a learner."""

import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from pathlib import Path

from shared.official_result_support import TIME_CAPTION, parse_detail, tables

from autoresearch import race_conditions, sectional_source_audit
from autoresearch.observed_history_seed import digest, pinned_path
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import encoded

PINS = (
    (
        ".cache/autoresearch/condition-form-research-20261013/run-1/history.json",
        "f718152b1465bea5990145ed30afb2402eaaba9ce2640a89163841e6211e5125",
    ),
    (
        ".cache/autoresearch/condition-form-research-20261013/run-1/conditions.json",
        "818f0be674ef148b9c83e46192a52686be1e5ba2805b5daf8c601134aaaa6123",
    ),
    (
        ".cache/autoresearch/history-gap-expansion-20261014/report-v2.json",
        "3302c5bb1abb62f70565535751991c01896b9b437e4160168ea3700fbbc09866",
    ),
    (
        ".cache/autoresearch/observed-history-extension-20260501-14/audit-report.json",
        "0ff580a8e1ff3123f2f18ffb226ceb7ebf6c759f071697fbde0e9ad67bbb85e3",
    ),
)
SOURCE_BOUND = "2026-10-16T01:20:00Z"


def load(root=Path(".")):
    documents = [
        json.loads(pinned_path(root, {"path": path, "sha256": sha}).read_bytes())
        for path, sha in PINS
    ]
    records = documents[0]["records"]
    conditions = dict(documents[1]["records"])
    directories = {}
    for rid, condition in conditions.items():
        provenance = condition["provenance"]
        directories[rid] = (
            Path(provenance["directory"]) / "details"
            if provenance.get("source") == "catalog"
            else Path(provenance["archive"])
        )
    for document, directory in zip(
        documents[2:],
        (
            Path(".cache/autoresearch/history-gap-expansion-20261014"),
            Path(".cache/autoresearch/observed-history-extension-20260501-14"),
        ),
        strict=True,
    ):
        part = document["extension_conditions"]
        if conditions.keys() & part.keys():
            raise ValueError("overlapping_condition_sources")
        records = records + document["extension_history"]
        conditions.update(part)
        for rid, condition in part.items():
            directories[rid] = directory / condition["provenance"].get(
                "archive", "official"
            )
    return records, conditions, directories


def layout(html, rid, distance, roster):
    meet = rid.split("_")[1]
    kinds = {"1": ["seoul"], "2": ["jeju"], "3": ["busan_segment", "busan_cumulative"]}
    if meet not in kinds:
        return {"status": "unsupported_physical_venue", "reason": meet}
    try:
        timing = [t for t in tables(html) if t.caption.strip().startswith(TIME_CAPTION)]
        if len(timing) != len(kinds[meet]):
            raise ValueError("timing_table_count")
        for kind, table in zip(kinds[meet], timing, strict=True):
            sectional_source_audit.timing_rows(table, kind, distance, roster)
    except ValueError as exc:
        return {"status": "unrecognized_layout", "reason": str(exc)}
    return {"status": "recognized_literal_layout", "reason": None}


def inspect_source(root, directory, rid, condition, members):
    directory = Path(root) / directory
    ref = condition["provenance"]["receipt"]
    receipt = json.loads(pinned_path(directory, ref).read_bytes())
    if timestamp(receipt["completed_at"]) >= timestamp(SOURCE_BOUND):
        raise ValueError("historical_source_after_bound")
    actual = race_conditions.from_capture(
        directory, rid, receipt, condition["provenance"]
    )
    if encoded(actual) != encoded(condition):
        raise ValueError("condition_replay_changed")
    result = {
        "directory": str(directory),
        "receipt": ref,
        "raw": receipt.get("raw"),
        "url": receipt["request"]["url"],
        "captured_at": receipt["completed_at"],
        "condition_status": condition["status"],
        "selected_rows": len(members),
    }
    if not members:
        return {**result, "layout": {"status": "not_in_supported_history"}}
    if condition["status"] != "observed":
        raise ValueError("selected_history_has_unknown_condition")
    html = (
        pinned_path(directory, receipt["raw"])
        .read_bytes()
        .decode(receipt["encoding"], errors="strict")
    )
    parsed = parse_detail(html)
    if parsed["event_support"] != "confirmed" or parsed["race_id"] != rid:
        raise ValueError("historical_event_not_confirmed")
    roster = {r["horse_id"]: r for r in parsed["rows"]}
    if len(roster) != len(parsed["rows"]):
        raise ValueError("duplicate_official_horse")
    for row in members:
        match = roster.get(row["horse_id"])
        if (
            match is None
            or match["rank_text"] != str(row["rank"])
            or row["observed_roster_size"] != len(roster)
        ):
            raise ValueError("historical_rank_roster_join_changed")
    return {
        **result,
        "official_roster_size": len(roster),
        "layout": layout(
            html,
            rid,
            condition["distance_m"],
            {r["chul_no"]: r for r in parsed["rows"]},
        ),
    }


def profile(records, conditions, sources):
    by_horse, by_race = defaultdict(list), defaultdict(list)
    seen = set()
    for row in records:
        rid, horse = row["race_id"], row["horse_id"]
        if not horse or (rid, horse) in seen:
            raise ValueError("duplicate_or_missing_history_identity")
        seen.add((rid, horse))
        date.fromisoformat(rid[:8])
        if rid[:8] >= "20261016":
            raise ValueError("history_reaches_october_evaluation")
        if row["tier"] not in ("dual_supported", "html_only"):
            raise ValueError("unknown_history_tier")
        if (
            type(row["rank"]) is not int
            or type(row["observed_roster_size"]) is not int
            or not 1 <= row["rank"] <= row["observed_roster_size"]
            or row["observed_roster_size"] < 2
        ):
            raise ValueError("invalid_supported_rank_or_roster_size")
        condition = conditions.get(rid, {})
        if (
            condition.get("status") != "observed"
            or str(condition["meet"]) != rid.split("_")[1]
        ):
            raise ValueError("missing_or_wrong_history_condition")
        by_horse[horse].append(row)
        by_race[rid].append(row)
    totals, groups, ledger = Counter(), defaultdict(Counter), {}
    for rid, members in sorted(by_race.items()):
        meet, distance = rid.split("_")[1], conditions[rid]["distance_m"]
        counters = Counter()
        histogram = Counter()
        for row in members:
            target_day = date.fromisoformat(rid[:8])
            prior = [
                p
                for p in by_horse[row["horse_id"]]
                if 1 <= (target_day - date.fromisoformat(p["race_id"][:8])).days <= 180
            ]
            exact = [
                p
                for p in prior
                if p["race_id"].split("_")[1] == meet
                and conditions[p["race_id"]]["distance_m"] == distance
            ]
            recognizable = [
                p
                for p in exact
                if sources[p["race_id"]]["layout"]["status"]
                == "recognized_literal_layout"
                and sources[rid]["layout"]["status"] == "recognized_literal_layout"
            ]
            histogram[len(exact)] += 1
            counters.update(
                rows=1,
                with_any_prior=int(bool(prior)),
                with_exact_prior=int(bool(exact)),
                with_three_exact_priors=int(len(exact) >= 3),
                with_recognized_layout_pair=int(bool(recognizable)),
            )
        ledger[rid] = {
            "meet": meet,
            "distance_m": distance,
            "class_text": conditions[rid]["class_text"],
            "tiers": dict(Counter(r["tier"] for r in members)),
            "counts": dict(counters),
            "exact_prior_count_histogram": dict(sorted(histogram.items())),
            "identity_sha256": digest(
                encoded(sorted((r["horse_id"], r["rank"]) for r in members))
            ),
        }
        totals.update(counters)
        groups[f"{meet}:{distance}"].update(counters)
    return {
        "rows": len(records),
        "races": len(by_race),
        "horses": len(by_horse),
        "dates": [min(by_race)[:8], max(by_race)[:8]] if by_race else [],
        "tiers": dict(Counter(r["tier"] for r in records)),
        "horse_start_histogram": dict(
            sorted(Counter(len(v) for v in by_horse.values()).items())
        ),
        "counts": dict(totals),
        "by_venue_distance": groups,
        "race_ledger": ledger,
    }


def audit(root=Path(".")):
    records, conditions, directories = load(root)
    members = defaultdict(list)
    for row in records:
        members[row["race_id"]].append(row)
    if not members.keys() <= conditions.keys():
        raise ValueError("missing_historical_condition")
    sources = {
        rid: inspect_source(root, directories[rid], rid, condition, members[rid])
        for rid, condition in sorted(conditions.items())
    }
    result = profile(records, conditions, sources)
    return {
        "format_version": "longitudinal-history-readiness-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "implementation_sha256": digest(Path(__file__).read_bytes()),
        "source_pins": [{"path": path, "sha256": sha} for path, sha in PINS],
        "source_clock_bound": SOURCE_BOUND,
        **result,
        "condition_registry_groups": len(conditions),
        "condition_registry_status": dict(
            Counter(c["status"] for c in conditions.values())
        ),
        "source_layout_status": dict(
            Counter(s["layout"]["status"] for s in sources.values())
        ),
        "source_clock_range": [
            min(timestamp(s["captured_at"]) for s in sources.values()).isoformat(),
            max(timestamp(s["captured_at"]) for s in sources.values()).isoformat(),
        ],
        "sources": sources,
        "fits": 0,
        "network_requests": 0,
        "october_16_18_outcomes_loaded": False,
        "new_sectional_api_crosscheck": False,
        "api_raw_replayed_this_audit": False,
        "new_sectional_arithmetic_verified": False,
        "historical_prerace_verified": False,
        "training_approved": False,
        "future_target_coverage": None,
        "accuracy": None,
        "counts_as_70_percent_evidence": False,
    }


if __name__ == "__main__":
    print(encoded(audit()).decode(), end="")
