"""Original historical measurements, not features, fits or future validation."""

import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from pathlib import Path

from autoresearch import longitudinal_history_inventory as inventory
from autoresearch import sectional_arithmetic_audit as arithmetic
from autoresearch.restricted_cohort import encoded

REPORT = {
    "path": "docs/research/experiments/2026-10-20-longitudinal-readiness/report.json",
    "sha256": "a338c67f005c1ff56d3ab418f44073d7d76de0a2e3b879d7172a2a8f430e9701",
}
METRICS = ("total", "initial_200", "final_600")
READY = {
    "total": "positive_total",
    "initial_200": "exact_endpoint",
    "final_600": "exact_endpoint",
}


def operand(raw):
    try:
        value = arithmetic.seconds(raw)
    except (ValueError, TypeError):
        return {"status": "malformed", "seconds": None}
    return {
        "status": "blank" if value is None else "positive" if value > 0 else "zero",
        "seconds": str(value) if value is not None else None,
    }


def clock_order(kind, distance, values):
    if kind == "jeju":
        return []
    if kind == "seoul":
        raw = values["seoul"]
        points = [
            (200, raw[0]),
            (distance - 600, raw[4]),
            (distance - 200, raw[6]),
            (distance, raw[-1]),
        ]
    else:
        labels = arithmetic.source.headers("busan_cumulative", distance)[1]
        raw = values["busan_cumulative"]
        points = [
            (int(label[:-1]), value)
            for label, value in zip(labels, raw[:-1], strict=True)
            if label != "-"
        ] + [(distance, raw[-1])]
    observed = sorted((p, v) for p, v in points if v != "")
    return [
        {
            "relation": "cumulative_order",
            "start_m": a,
            "end_m": b,
            "raw_start": x,
            "raw_end": y,
            "status": "cumulative_clock_order_conflict",
        }
        for (a, x), (b, y) in zip(observed, observed[1:], strict=False)
        if not 0 < arithmetic.seconds(x) < arithmetic.seconds(y)
    ]


def measure(kind, distance, values):
    widths = {
        "seoul": {"seoul": 10},
        "jeju": {"jeju": 8},
        "busan": {"busan_segment": 9, "busan_cumulative": 8},
    }
    expected = widths.get(kind)
    if (
        expected is None
        or set(values) != set(expected)
        or any(len(values[k]) != width for k, width in expected.items())
    ):
        raise ValueError("invalid_measurement_shape")
    cells = {k: [operand(v) for v in row] for k, row in values.items()}
    checks, issues, order_conflicts = [], [], []
    if any(c["status"] == "malformed" for row in cells.values() for c in row):
        issues.append("malformed_operand")
    else:
        try:
            checks = arithmetic.evaluate(kind, distance, values)
            order_conflicts = clock_order(kind, distance, values)
            if order_conflicts:
                issues.append("cumulative_clock_order_conflict")
        except ValueError as exc:
            issues.append(str(exc))
    bad = {
        "arithmetic_conflict",
        "nonpositive_value",
        "nonincreasing_clock",
        "unsupported_endpoint_with_value",
    }
    issues.extend(sorted({c["status"] for c in checks if c["status"] in bad}))
    totals = [row[-1] for row in values.values()]
    if len(set(totals)) != 1:
        issues.append("timing_total_disagreement")
    total = operand(totals[0])
    if total["status"] != "positive":
        issues.append("invalid_total")
    metrics = {k: {"status": "withheld_conflict", "seconds": None} for k in METRICS}
    if not issues:
        metrics["total"] = {"status": "positive_total", "seconds": total["seconds"]}
        if kind == "jeju":
            for metric in METRICS[1:]:
                metrics[metric]["status"] = "unverified_jeju_endpoints"
        else:
            raw = values["busan_segment" if kind == "busan" else "seoul"]
            for metric, index, relation in (
                ("initial_200", 0, "initial_200"),
                ("final_600", 6 if kind == "busan" else 7, "final_600"),
            ):
                duration = operand(raw[index])
                check = next((c for c in checks if c["relation"] == relation), None)
                status = (
                    duration["status"]
                    if duration["status"] != "positive"
                    else "invalid_segment"
                    if distance <= (200 if metric == "initial_200" else 600)
                    or arithmetic.seconds(raw[index]) >= arithmetic.seconds(totals[0])
                    else "label_only_no_independent_counterpart"
                    if kind == "seoul" and metric == "initial_200"
                    else "exact_endpoint"
                    if check and check["status"] == "exact"
                    else "missing_or_unverified_endpoint"
                )
                metrics[metric] = {
                    "status": status,
                    "seconds": duration["seconds"]
                    if status
                    in ("exact_endpoint", "label_only_no_independent_counterpart")
                    else None,
                }
    return {
        "raw_time_columns": values,
        "operand_counts": dict(
            Counter(c["status"] for row in cells.values() for c in row)
        ),
        "check_counts": dict(Counter(c["status"] for c in checks)),
        "exceptions": [c for c in checks if c["status"] in bad] + order_conflicts,
        "issues": issues,
        "measurements": metrics,
    }


def summarize(rows):
    by_horse, by_group, by_month = (
        defaultdict(list),
        defaultdict(list),
        defaultdict(list),
    )
    seen = set()
    for r in rows:
        key = r["race_id"], r["horse_id"]
        if not key[1] or key in seen:
            raise ValueError("duplicate_or_missing_measurement_identity")
        seen.add(key)
        by_horse[r["horse_id"]].append(r)
        by_group[f"{r['meet']}:{r['distance_m']}"].append(r)
        by_month[r["race_id"][:6]].append(r)

    def counts(members):
        return {
            "rows": len(members),
            "races": len({r["race_id"] for r in members}),
            "statuses": {
                metric: dict(
                    Counter(r["measurements"][metric]["status"] for r in members)
                )
                for metric in METRICS
            },
            "issues": dict(Counter(v for r in members for v in r["issues"])),
        }

    pairs = Counter()
    for r in rows:
        prior = [
            p
            for p in by_horse[r["horse_id"]]
            if p["meet"] == r["meet"]
            and p["distance_m"] == r["distance_m"]
            and 1
            <= (
                date.fromisoformat(r["race_id"][:8])
                - date.fromisoformat(p["race_id"][:8])
            ).days
            <= 180
        ]
        support = {
            metric: sum(
                p["measurements"][metric]["status"] == READY[metric] for p in prior
            )
            if r["measurements"][metric]["status"] == READY[metric]
            else 0
            for metric in METRICS
        }
        pairs.update({k: int(v > 0) for k, v in support.items()})
    return {
        **counts(rows),
        "tiers": dict(Counter(r["tier"] for r in rows)),
        "by_venue_distance": {k: counts(v) for k, v in sorted(by_group.items())},
        "by_month": {k: counts(v) for k, v in sorted(by_month.items())},
        "structural_rows_with_verified_measurement_prior": dict(pairs),
        "operand_counts": dict(
            sum((Counter(r["operand_counts"]) for r in rows), Counter())
        ),
        "check_counts": dict(
            sum((Counter(r["check_counts"]) for r in rows), Counter())
        ),
    }


def audit(root=Path(".")):
    root = Path(root)
    pinned = json.loads(inventory.pinned_path(root, REPORT).read_bytes())
    replay = inventory.audit(root)
    for key in ("source_pins", "race_ledger", "sources", "counts", "tiers"):
        if json.loads(encoded(replay[key])) != pinned[key]:
            raise ValueError("inventory_evidence_changed")
    guide = arithmetic.replay_guide(root / arithmetic.GUIDE_ROOT)
    records, conditions, _ = inventory.load(root)
    by_race = defaultdict(list)
    for r in records:
        by_race[r["race_id"]].append(r)
    observations = []
    for rid, members in sorted(by_race.items()):
        evidence = replay["sources"][rid]
        condition = conditions[rid]
        layout = evidence["layout"]["status"]
        parsed = {}
        if layout == "recognized_literal_layout":
            directory = root / evidence["directory"]
            receipt = json.loads(
                inventory.pinned_path(directory, evidence["receipt"]).read_bytes()
            )
            html = (
                inventory.pinned_path(directory, evidence["raw"])
                .read_bytes()
                .decode(receipt["encoding"], errors="strict")
            )
            roster = {r["chul_no"]: r for r in inventory.parse_detail(html)["rows"]}
            kind = {"1": "seoul", "2": "jeju", "3": "busan"}[rid.split("_")[1]]
            kinds = ["busan_segment", "busan_cumulative"] if kind == "busan" else [kind]
            timings = [
                t
                for t in inventory.tables(html)
                if t.caption.strip().startswith(inventory.TIME_CAPTION)
            ]
            parsed = {
                k: arithmetic.source.timing_rows(t, k, condition["distance_m"], roster)
                for k, t in zip(kinds, timings, strict=True)
            }
            gates = {r["horse_id"]: g for g, r in roster.items()}
        for row in sorted(members, key=lambda r: r["horse_id"]):
            measured = (
                measure(
                    kind,
                    condition["distance_m"],
                    {k: parsed[k][gates[row["horse_id"]]] for k in kinds},
                )
                if parsed
                else {
                    "raw_time_columns": {},
                    "operand_counts": {},
                    "check_counts": {},
                    "exceptions": [],
                    "issues": [],
                    "measurements": {
                        k: {"status": layout, "seconds": None} for k in METRICS
                    },
                }
            )
            observations.append(
                {
                    **row,
                    "meet": rid.split("_")[1],
                    "distance_m": condition["distance_m"],
                    "source_layout": evidence["layout"],
                    **measured,
                }
            )
    summary = summarize(observations)
    if any(summary[k] != pinned[k] for k in ("rows", "races", "tiers")):
        raise ValueError("measurement_population_changed")
    return {
        "format_version": "longitudinal-time-operands-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "implementation_sha256": inventory.digest(Path(__file__).read_bytes()),
        "arithmetic_implementation_sha256": inventory.digest(
            Path(arithmetic.__file__).read_bytes()
        ),
        "inventory_report": REPORT,
        "sectional_definition_source": guide,
        "source_pins": replay["source_pins"],
        "sources": replay["sources"],
        **summary,
        "observations": observations,
        "fits": 0,
        "network_requests": 0,
        "training_approved": False,
        "api_raw_replayed_this_audit": False,
        "historical_prerace_verified": False,
        "october_16_18_outcomes_loaded": False,
        "existing_exclusions_changed": False,
        "future_target_coverage": None,
        "future_dates_and_n": None,
        "accuracy": None,
        "counts_as_70_percent_evidence": False,
    }


if __name__ == "__main__":
    print(encoded(audit()).decode(), end="")
