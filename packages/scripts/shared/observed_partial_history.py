"""Separate observed-record counts, without weakening the legacy H0 contract."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta

from shared.observed_result_history import project_history

CONTRACT = "observed_partial_v1"
FIELDS = (
    "ranked_finish_count_90d",
    "win_count_90d",
    "top3_count_90d",
    "top3_fraction_90d",
    "unresolved_status_count_90d",
)


def project_partial_history(race: dict, seed: dict) -> dict:
    """Requires a source-replayed seed; zero means no matching observations."""
    legacy = project_history(race, seed)
    lower, upper = legacy["lookback_start"], legacy["lookback_end_exclusive"]
    events = {
        (r["race_id"], r["horse_id"]): r
        for r in seed["records"]
        if lower <= r["race_id"][:8] < upper
    }
    coverage = {(r["day"], r["meet"]): r["status"] for r in seed["inventory"]}
    first = datetime.strptime(lower, "%Y%m%d")
    statuses = Counter(
        coverage.get(((first + timedelta(days=i)).strftime("%Y%m%d"), m), "missing")
        for i in range(90)
        for m in (1, 2, 3, 4)
    )
    output = []
    for runner in legacy["feature_rows"]:
        history = [
            events[(r["race_id"], runner["horse_id"])] for r in runner["lineage"]
        ]
        ranks = [
            int(r["raw_ord"])
            for r in history
            if r["evidence"] == "ranked_finish_observed"
        ]
        top3 = sum(r <= 3 for r in ranks)
        values = (
            len(ranks),
            sum(r == 1 for r in ranks),
            top3,
            top3 / len(ranks) if ranks else None,
            len(history) - len(ranks),
        )
        output.append(
            {
                "horse_id": runner["horse_id"],
                "chul_no": runner["chul_no"],
                "features": dict(zip(FIELDS, values, strict=True)),
                "observed_row_count": len(history),
                "ranked_denominator": len(ranks),
                "lineage": runner["lineage"],
            }
        )
    return {
        "race_id": race["race_id"],
        "contract": CONTRACT,
        "legacy_projection": legacy,
        "lookback_start": lower,
        "lookback_end_exclusive": upper,
        "response_unit_status_counts": dict(sorted(statuses.items())),
        "zero_count_meaning": "no_matching_observations_in_selected_sources",
        "feature_rows": output,
        "complete_actual_start_history_verified": False,
        "historical_pre_race_availability_verified": False,
        "training_approved": False,
    }
