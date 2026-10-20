"""Full-population descriptive time diagnostics; no fitting or live scoring."""

from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from fractions import Fraction
from itertools import combinations
from pathlib import Path
from statistics import median

from autoresearch import sectional_arithmetic_audit as arithmetic
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import encoded

METRICS = ("relative_time", "initial_speed_ratio", "final_speed_ratio")


def identity(row):
    return (row["race_id"], row["chul_no"], row["horse_id"])


def day(row):
    return date.fromisoformat(row["race_id"].split("_")[0])


def positive(value):
    if value is None:
        return None
    number = Fraction(value)
    return number if number > 0 else None


def prior_rows(rows, target, *, freeze=None, cutoff=None):
    """Diagnostic only: never infer historical publication from a later capture."""
    if len({identity(r) for r in rows}) != len(rows):
        raise ValueError("multiple_versions_require_pinned_selection")
    if (freeze is None) != (cutoff is None):
        raise ValueError("both_freeze_and_cutoff_required")
    if freeze is not None and timestamp(freeze) >= timestamp(cutoff):
        raise ValueError("freeze_must_precede_cutoff")
    selected = []
    for row in rows:
        age = (day(target) - day(row)).days
        if (
            row["horse_id"] != target["horse_id"]
            or row["meet"] != target["meet"]
            or row["distance_m"] != target["distance_m"]
            or not 1 <= age <= 180
            or row["history_eligibility"] != "supported"
        ):
            continue
        if freeze is not None:
            clocks = row["required_available_at"]
            if not clocks or any(
                clock is None or timestamp(clock) >= timestamp(freeze)
                for clock in clocks
            ):
                continue
        selected.append(row)
    return sorted(selected, key=identity)


def distribution(values):
    values = [v for v in values if v is not None]
    return {
        "n": len(values),
        "distinct": len(set(values)),
        "min": str(min(values)) if values else None,
        "median": str(median(values)) if values else None,
        "max": str(max(values)) if values else None,
    }


def rank_order(rows, metric):
    """Count ordering disagreement in completed historical races, not accuracy."""
    counts = Counter()
    for a, b in combinations(rows, 2):
        x, y = a["quantities"][metric], b["quantities"][metric]
        if x is None or y is None:
            counts["missing_pair"] += 1
            continue
        x, y = Fraction(x), Fraction(y)
        rank_sign = (a["rank"] > b["rank"]) - (a["rank"] < b["rank"])
        sign = (x > y) - (x < y)
        counts[
            "same_order"
            if sign == rank_sign
            else "rank_tie_only"
            if rank_sign == 0
            else "quantity_tie_only"
            if sign == 0
            else "opposite_order"
        ] += 1
    return dict(counts)


def describe(rows):
    if len({identity(r) for r in rows}) != len(rows) or any(
        not r["horse_id"] for r in rows
    ):
        raise ValueError("duplicate_or_missing_identity")
    races = defaultdict(list)
    for row in rows:
        races[row["race_id"]].append(row)
    output, references = [], {}
    for rid, members in sorted(races.items()):
        if len({r["chul_no"] for r in members}) != len(members) or len(
            {r["horse_id"] for r in members}
        ) != len(members):
            raise ValueError("duplicate_race_gate_or_horse")
        eligible = [r for r in members if r["history_eligibility"] == "supported"]
        times = [positive(r["total_seconds"]) for r in eligible]
        status = (
            "invalid_reference_time"
            if any(t is None for t in times)
            else "insufficient_comparators"
            if len(times) < 3
            else "usable"
        )
        reference = median(times) if status == "usable" else None
        reference_clocks = [
            clock for r in eligible for clock in r["required_available_at"]
        ]
        references[rid] = {
            "status": status,
            "members": [list(identity(r)) for r in sorted(eligible, key=identity)],
            "excluded": [
                {"identity": list(identity(r)), "reason": r["history_eligibility"]}
                for r in sorted(members, key=identity)
                if r["history_eligibility"] != "supported"
            ],
            "median_seconds": str(reference) if reference is not None else None,
        }
        for row in sorted(members, key=identity):
            values, reasons = dict.fromkeys(METRICS), {}
            if row["history_eligibility"] != "supported":
                reasons = dict.fromkeys(METRICS, row["history_eligibility"])
            else:
                total = positive(row["total_seconds"])
                if total is None:
                    reasons = dict.fromkeys(METRICS, "invalid_total")
                else:
                    if reference is not None:
                        values["relative_time"] = (total - reference) / reference
                    else:
                        reasons["relative_time"] = status
                    for metric, length, field in (
                        ("initial_speed_ratio", 200, "initial_seconds"),
                        ("final_speed_ratio", 600, "final_seconds"),
                    ):
                        duration = positive(row[field])
                        if duration is None:
                            reasons[metric] = row["pace_status"]
                        elif not 0 < length < row["distance_m"] or duration >= total:
                            reasons[metric] = "invalid_segment"
                        else:
                            values[metric] = (
                                Fraction(length)
                                * total
                                / (duration * row["distance_m"])
                            )
            output.append(
                {
                    **row,
                    # The relative quantity depends on every reference source.
                    "required_available_at": sorted(
                        set(row["required_available_at"] + reference_clocks),
                        key=lambda c: c or "",
                    ),
                    "quantities": {
                        k: str(v) if v is not None else None for k, v in values.items()
                    },
                    "missing_reasons": reasons,
                }
            )
    groups = {}
    for key in sorted({f"{r['meet']}:{r['distance_m']}" for r in output}):
        members = [r for r in output if f"{r['meet']}:{r['distance_m']}" == key]
        groups[key] = {
            "rows": len(members),
            "races": len({r["race_id"] for r in members}),
            "eligibility": dict(Counter(r["history_eligibility"] for r in members)),
            "quantities": {
                metric: {
                    **distribution(
                        [
                            Fraction(r["quantities"][metric])
                            if r["quantities"][metric] is not None
                            else None
                            for r in members
                        ]
                    ),
                    "missing_reasons": dict(
                        Counter(
                            r["missing_reasons"][metric]
                            for r in members
                            if metric in r["missing_reasons"]
                        )
                    ),
                }
                for metric in METRICS
            },
        }
    pair_counts = {metric: Counter() for metric in METRICS}
    for rid in races:
        members = [r for r in output if r["race_id"] == rid]
        for metric in METRICS:
            pair_counts[metric].update(rank_order(members, metric))
    repeats = Counter()
    for row in output:
        history = prior_rows(output, row)
        usable = {
            metric: sum(r["quantities"][metric] is not None for r in history)
            for metric in METRICS
        }
        row["structural_prior_support"] = {
            "count": len(history),
            "ids": [list(identity(r)) for r in history],
            "latest_age_days": min(
                ((day(row) - day(r)).days for r in history), default=None
            ),
            "usable_quantities": usable,
        }
        repeats["with_prior" if history else "without_prior"] += 1
        for metric, count in usable.items():
            repeats[f"{metric}_with_prior"] += count > 0
    horse_counts = Counter(r["horse_id"] for r in output)
    return {
        "rows": len(output),
        "races": len(races),
        "eligibility": dict(Counter(r["history_eligibility"] for r in output)),
        "by_venue_distance": groups,
        "reference_groups": references,
        "historical_rank_pair_order": pair_counts,
        "structural_repeat_counts": dict(repeats),
        "unique_horses": len(horse_counts),
        "horses_with_multiple_observations": sum(n > 1 for n in horse_counts.values()),
        "max_observations_per_horse": max(horse_counts.values(), default=0),
        "last_possible_history_day": (
            (max(day(r) for r in output) + timedelta(days=180)).isoformat()
            if output
            else None
        ),
        "observations": output,
    }


def audit(root=arithmetic.source.ROOT):
    root = Path(root)
    baseline = arithmetic.audit(root)
    if baseline["exceptions"]:
        raise ValueError("unresolved_endpoint_conflicts")
    source = arithmetic.source
    seed = arithmetic.replay_frozen(
        root, root / "seed.json", source.SEED_SHA, cutoff=source.BOUND
    )
    evidence = arithmetic.replay_archive(
        root / "official", source.HTML_SHA, seed, source.SEED_SHA, source.BOUND
    )
    selected = {identity(r): r for r in seed["records"]}
    eligibility = {identity(r): r for r in baseline["observations"]}
    if set(selected) != set(eligibility) or len(selected) != baseline["rows"]:
        raise ValueError("incomplete_time_population")
    rows = []
    for rid in sorted({r["race_id"] for r in seed["records"]}):
        unit = evidence[rid]
        receipt = unit["capture"]
        html = (
            arithmetic.pinned_path(root / "official", receipt["raw"])
            .read_bytes()
            .decode(receipt["encoding"], errors="strict")
        )
        condition = arithmetic.parse_conditions(html, rid)
        if condition["status"] != "observed":
            raise ValueError("unobserved_historical_condition")
        distance = condition["distance_m"]
        meet = rid.split("_")[1]
        kind = {"1": "seoul", "2": "jeju", "3": "busan"}[meet]
        kinds = ["busan_segment", "busan_cumulative"] if kind == "busan" else [kind]
        roster = {r["chul_no"]: r for r in unit["parsed"]["rows"]}
        timings = [
            t
            for t in arithmetic.tables(html)
            if t.caption.strip().startswith(arithmetic.TIME_CAPTION)
        ]
        parsed = {
            k: source.timing_rows(t, k, distance, roster)
            for k, t in zip(kinds, timings, strict=True)
        }
        for gate, runner in sorted(roster.items()):
            key = rid, gate, runner["horse_id"]
            record = selected[key]
            values = {k: parsed[k][gate] for k in kinds}
            checks = arithmetic.evaluate(kind, distance, values)
            exact_final = any(
                c["relation"] == "final_600" and c["status"] == "exact" for c in checks
            )
            raw = values["busan_segment" if kind == "busan" else kind]
            initial, final = (
                (raw[0], raw[7] if kind == "seoul" else raw[6])
                if kind != "jeju" and exact_final
                else ("", "")
            )
            rows.append(
                {
                    "race_id": rid,
                    "chul_no": gate,
                    "horse_id": runner["horse_id"],
                    "meet": meet,
                    "distance_m": distance,
                    "condition": condition,
                    "history_eligibility": eligibility[key]["history_eligibility"],
                    "rank": record["raw_ord"],
                    "total_seconds": str(arithmetic.seconds(raw[-1]))
                    if raw[-1]
                    else None,
                    "initial_seconds": str(arithmetic.seconds(initial))
                    if initial
                    else None,
                    "final_seconds": str(arithmetic.seconds(final)) if final else None,
                    "raw_time_columns": values,
                    "pace_status": (
                        "unverified_jeju_endpoints"
                        if kind == "jeju"
                        else "missing_or_invalid_endpoint"
                    ),
                    "required_available_at": [
                        record["source_available_at"],
                        receipt["completed_at"],
                        baseline["sectional_definition_source"]["capture_completed_at"],
                    ],
                }
            )
    result = describe(rows)
    if (
        result["rows"] != baseline["rows"]
        or result["eligibility"] != baseline["eligibility"]
    ):
        raise ValueError("time_population_or_exclusion_changed")
    return {
        "format_version": "time-information-feasibility-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "implementation_sha256": arithmetic.digest(Path(__file__).read_bytes()),
        "arithmetic_implementation_sha256": baseline["implementation_sha256"],
        "seed_sha256": source.SEED_SHA,
        "official_archive_sha256": source.HTML_SHA,
        "official_sources": baseline["official_sources"],
        "sectional_definition_source": baseline["sectional_definition_source"],
        "seed_status_counts": seed["status_counts"],
        **result,
        "fits": 0,
        "network_requests": 0,
        "target_outcomes_loaded": False,
        "training_approved": False,
        "historical_prerace_verified": False,
        "future_target_coverage": None,
        "future_dates_and_n": None,
        "accuracy": None,
        "counts_as_70_percent_evidence": False,
    }


if __name__ == "__main__":
    print(encoded(audit()).decode(), end="")
