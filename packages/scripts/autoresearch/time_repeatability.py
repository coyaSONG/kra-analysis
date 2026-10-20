"""Descriptive lagged measurement associations, never model validation."""

import json
import platform
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from fractions import Fraction
from itertools import groupby
from pathlib import Path
from random import Random
from statistics import StatisticsError, correlation, median, quantiles

from autoresearch.observed_history_seed import digest, pinned_path
from autoresearch.restricted_cohort import encoded

SOURCE = {
    "path": "docs/research/experiments/2026-10-20-longitudinal-time/report.json",
    "sha256": "2ff4ef525c33a6f83e5aa2ecc9f14c9d5942f103386b34d2e4007f4fda1e6f7a",
}
ASSOCIATIONS = {
    "pace_recurrence": (0, 1),
    "rank_recurrence": (2, 3),
    "prior_pace_current_rank": (0, 3),
}


def key(row):
    return row["race_id"], row["horse_id"]


def day(row):
    return date.fromisoformat(row["race_id"][:8])


def quantities(rows):
    races, seen = defaultdict(list), set()
    for r in rows:
        if key(r) in seen or not r["horse_id"]:
            raise ValueError("duplicate_or_missing_identity")
        seen.add(key(r))
        day(r)
        if r["race_id"][:8] >= "20261016" or r["race_id"].split("_")[1] != r["meet"]:
            raise ValueError("wrong_historical_scope")
        if (
            type(r["rank"]) is not int
            or type(r["observed_roster_size"]) is not int
            or not 1 <= r["rank"] <= r["observed_roster_size"]
            or r["observed_roster_size"] < 2
            or type(r["distance_m"]) is not int
            or r["distance_m"] <= 600
        ):
            raise ValueError("invalid_historical_metadata")
        races[r["race_id"]].append(r)
    output, references = [], {}
    for rid, members in sorted(races.items()):
        if len({r["distance_m"] for r in members}) != 1:
            raise ValueError("mixed_race_distance")
        ratios = {}
        for r in members:
            m = r["measurements"]
            if (
                m["total"]["status"] == "positive_total"
                and m["final_600"]["status"] == "exact_endpoint"
            ):
                total, final = (
                    Fraction(m["total"]["seconds"]),
                    Fraction(m["final_600"]["seconds"]),
                )
                if not 0 < final < total:
                    raise ValueError("invalid_approved_duration")
                ratios[key(r)] = 600 * total / (r["distance_m"] * final)
        state = (
            "incomplete_reference"
            if len(ratios) != len(members)
            else "insufficient_reference"
            if len(members) < 3
            else "usable"
        )
        center = median(ratios.values()) if state == "usable" else None
        references[rid] = {
            "status": state,
            "members": [list(key(r)) for r in sorted(members, key=key)],
            "median_ratio": str(center) if center is not None else None,
        }
        for r in sorted(members, key=key):
            ratio = ratios.get(key(r))
            output.append(
                {
                    "race_id": rid,
                    "horse_id": r["horse_id"],
                    "meet": r["meet"],
                    "distance_m": r["distance_m"],
                    "tier": r["tier"],
                    "rank_fraction": str(
                        Fraction(r["rank"] - 1, r["observed_roster_size"] - 1)
                    ),
                    "raw_ratio": str(ratio) if ratio is not None else None,
                    "centered_ratio": str(ratio - center)
                    if center is not None
                    else None,
                    "measurement_status": state,
                    "source_measurement_status": r["measurements"]["final_600"][
                        "status"
                    ],
                }
            )
    return output, references


def pair_rows(rows):
    horses = defaultdict(list)
    for r in rows:
        horses[r["horse_id"]].append(r)
    output = []
    for r in sorted(rows, key=key):
        candidates = [
            p
            for p in horses[r["horse_id"]]
            if p["meet"] == r["meet"]
            and p["distance_m"] == r["distance_m"]
            and 1 <= (day(r) - day(p)).days <= 180
        ]
        latest_day = max((day(p) for p in candidates), default=None)
        latest = [p for p in candidates if day(p) == latest_day]
        selection = (
            "no_prior"
            if not latest
            else "ambiguous_latest"
            if len(latest) > 1
            else "selected"
        )
        prior = latest[0] if selection == "selected" else None
        status = selection
        if prior is not None:
            missing_current, missing_prior = (
                r["centered_ratio"] is None,
                prior["centered_ratio"] is None,
            )
            status = (
                "both_unavailable"
                if missing_current and missing_prior
                else "current_unavailable"
                if missing_current
                else "prior_unavailable"
                if missing_prior
                else "paired"
            )
        output.append(
            {
                **r,
                "prior_selection": selection,
                "pair_status": status,
                "prior_identity": list(key(prior)) if prior else None,
                "prior_age_days": (day(r) - day(prior)).days if prior else None,
                "prior_measurement_status": prior["measurement_status"]
                if prior
                else None,
                "prior_centered_ratio": prior["centered_ratio"] if prior else None,
                "prior_rank_fraction": prior["rank_fraction"] if prior else None,
            }
        )
    return output


def ranks(values):
    result = [0.0] * len(values)
    offset = 0
    for _, items in groupby(
        sorted(enumerate(values), key=lambda p: p[1]), key=lambda p: p[1]
    ):
        tied = list(items)
        midrank = offset + (len(tied) + 1) / 2
        for i, _ in tied:
            result[i] = midrank
        offset += len(tied)
    return result


def associations(vectors):
    if len(vectors) < 3:
        return dict.fromkeys(ASSOCIATIONS)
    ranked = [ranks([v[c] for v in vectors]) for c in range(4)]
    output = {}
    for label, (a, b) in ASSOCIATIONS.items():
        try:
            output[label] = correlation(ranked[a], ranked[b])
        except StatisticsError:
            output[label] = None
    return output


def vectors(rows):
    return [
        tuple(
            Fraction(r[k])
            for k in (
                "prior_centered_ratio",
                "centered_ratio",
                "prior_rank_fraction",
                "rank_fraction",
            )
        )
        for r in rows
        if r["pair_status"] == "paired"
    ]


def summarize(rows):
    paired = [r for r in rows if r["pair_status"] == "paired"]
    return {
        "rows": len(rows),
        "races": len({r["race_id"] for r in rows}),
        "pair_status": dict(Counter(r["pair_status"] for r in rows)),
        "measurement_status": dict(Counter(r["measurement_status"] for r in rows)),
        "complete_pairs": len(paired),
        "paired_horses": len({r["horse_id"] for r in paired}),
        "paired_current_races": len({r["race_id"] for r in paired}),
        "spearman": associations(vectors(paired)),
    }


def bootstrap(rows, draws=1000, seed=20261020):
    paired = [r for r in rows if r["pair_status"] == "paired"]
    raw = vectors(paired)
    # Ordinal labels preserve exact Fraction ordering/ties in every resample.
    orders = [
        {v: i for i, v in enumerate(sorted({r[c] for r in raw}))} for c in range(4)
    ]
    clusters = defaultdict(list)
    for row, values in zip(paired, raw, strict=True):
        clusters[row["horse_id"]].append(
            tuple(orders[c][v] for c, v in enumerate(values))
        )
    names, rng = sorted(clusters), Random(seed)
    samples = {k: [] for k in ASSOCIATIONS}
    for _ in range(draws):
        chosen = (
            [v for name in rng.choices(names, k=len(names)) for v in clusters[name]]
            if names
            else []
        )
        result = associations(chosen)
        for k, value in result.items():
            samples[k].append(value)
    intervals = {}
    for k, values in samples.items():
        defined = [v for v in values if v is not None]
        interval = None
        if len(names) >= 2 and draws >= 2 and len(defined) == draws:
            q = quantiles(defined, n=40, method="inclusive")
            interval = [q[0], q[-1]]
        intervals[k] = {
            "defined_draws": len(defined),
            "undefined_draws": draws - len(defined),
            "nominal_95_percentile_interval": interval,
        }
    return {
        "draws": draws,
        "seed": seed,
        "resampling_unit": "horse",
        "clusters": len(names),
        "intervals": intervals,
        "race_and_calendar_dependence_resolved": False,
    }


def analyze(source):
    prepared, references = quantities(source["observations"])
    rows = pair_rows(prepared)
    summary = summarize(rows)
    if summary["rows"] != source["rows"] or summary["races"] != source["races"]:
        raise ValueError("population_changed")
    groups = sorted({f"{r['meet']}:{r['distance_m']}" for r in rows})
    months = sorted({r["race_id"][:6] for r in rows})
    return {
        **summary,
        "tiers": dict(Counter(r["tier"] for r in rows)),
        "by_venue_distance": {
            g: summarize([r for r in rows if f"{r['meet']}:{r['distance_m']}" == g])
            for g in groups
        },
        "leave_one_current_month_out": {
            m: summarize([r for r in rows if r["race_id"][:6] != m]) for m in months
        },
        "horse_cluster_bootstrap": bootstrap(rows),
        "references": references,
        "observations": rows,
    }


def audit(root=Path(".")):
    source = json.loads(pinned_path(Path(root), SOURCE).read_bytes())
    return {
        "format_version": "historical-time-repeatability-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "python_version": platform.python_version(),
        "implementation_sha256": digest(Path(__file__).read_bytes()),
        "source_report": SOURCE,
        "policy": {
            "prior": "latest_structural_same_horse_venue_distance_1_180_days",
            "fallback_from_missing": False,
            "same_latest_day": "ambiguous",
            "quantity": "600*total/(distance*final600)-same_race_admitted_median",
            "reference": "all_admitted_members_valid_and_count_at_least_three",
            "rank": "(rank-1)/(observed_roster_size-1)",
        },
        **analyze(source),
        "fits": 0,
        "network_requests": 0,
        "historical_prerace_verified": False,
        "october_16_18_outcomes_loaded": False,
        "incremental_predictive_value_verified": False,
        "training_approved": False,
        "future_dates_and_n": None,
        "accuracy": None,
        "counts_as_70_percent_evidence": False,
    }


if __name__ == "__main__":
    print(encoded(audit()).decode(), end="")
