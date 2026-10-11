"""Pure observed-event features; never manufacture a complete actual start history."""

from __future__ import annotations

from datetime import datetime, timedelta

from shared.kra_race_identity import validate_race_identity

H0 = (
    "observed_ranked_finish_count_90d",
    "observed_win_count_90d",
    "observed_top3_count_90d",
    "top3_fraction_among_observed_ranked_finishes_90d",
    "observed_unresolved_count_90d",
)
H1_ADDITIONS = (
    "observed_ranked_finish_count_30d",
    "days_since_last_observed_ranked_finish_90d",
    "last_observed_rank_90d",
    "mean_last_three_observed_ranks_90d",
    "has_unresolved_after_last_observed_ranked_finish",
)


def project_history(race: dict, seed: dict) -> dict:
    """Keep roster membership fixed; callers supply a source-replayed seed view."""
    day, meet, number = race["race_id"].split("_")
    validate_race_identity(int(meet), day, int(number))
    target = datetime.strptime(day, "%Y%m%d")
    start, recent = target - timedelta(days=90), target - timedelta(days=30)
    lower, recent_day = start.strftime("%Y%m%d"), recent.strftime("%Y%m%d")
    requested = {
        ((start + timedelta(days=i)).strftime("%Y%m%d"), venue)
        for i in range(90)
        for venue in (1, 2, 3, 4)
    }
    coverage = {(r["day"], r["meet"]): r for r in seed["inventory"]}
    if len(coverage) != len(seed["inventory"]):
        raise ValueError("duplicate_history_coverage")
    missing = sorted(
        key
        for key in requested
        if key not in coverage
        or coverage[key]["status"] not in ("api_reported_rows", "empty_unconfirmed")
    )
    roster = race["roster"]
    ids = [r["horse_id"] for r in roster]
    gates = [r["chul_no"] for r in roster]
    if (
        not 3 <= len(roster) <= 20
        or len(set(ids)) != len(roster)
        or len(set(gates)) != len(roster)
        or any(type(g) is not int or not 1 <= g <= 20 for g in gates)
        or any(
            not isinstance(h, str)
            or not h.isascii()
            or not h.isdecimal()
            or not 0 < int(h) < 100_000_000
            or str(int(h)) != h
            for h in ids
        )
    ):
        raise ValueError("invalid_history_target_roster")
    events, seen = [], set()
    for row in seed["records"]:
        event_day, venue, race_no = row["race_id"].split("_")
        if not lower <= event_day < day:
            continue
        validate_race_identity(int(venue), event_day, int(race_no))
        key = (row["race_id"], row["horse_id"])
        if key in seen:
            raise ValueError("duplicate_history_runner_event")
        seen.add(key)
        source = coverage.get((event_day, int(venue)))
        if (
            source is None
            or source["status"] != "api_reported_rows"
            or source["result"]["sha256"] != row["source_capture_sha256"]
            or source["available_at"] != row["source_available_at"]
        ):
            raise ValueError("history_event_source_mismatch")
        events.append(row)
    output = []
    for runner in sorted(roster, key=lambda r: r["chul_no"]):
        history = sorted(
            [r for r in events if r["horse_id"] == runner["horse_id"]],
            key=lambda r: (r["race_id"][:8], int(r["race_id"].split("_")[2])),
        )
        ranked = [r for r in history if r["evidence"] == "ranked_finish_observed"]
        unresolved = [r for r in history if r["evidence"] == "unresolved"]
        if len(ranked) + len(unresolved) != len(history):
            raise ValueError("unknown_history_event_state")
        ranks = [int(r["raw_ord"]) for r in ranked]
        if any(not 1 <= r <= 20 for r in ranks):
            raise ValueError("invalid_observed_rank")
        last = ranked[-1] if ranked else None
        last_day = last["race_id"][:8] if last else None
        last_rank_unique = (
            last and sum(r["race_id"][:8] == last_day for r in ranked) == 1
        )
        three_boundary_unique = len(ranked) <= 3 or (
            ranked[-3]["race_id"][:8] != ranked[-4]["race_id"][:8]
        )
        # Dates alone cannot order two same-day observations for one horse.
        unresolved_after = None
        if last:
            if any(r["race_id"][:8] > last_day for r in unresolved):
                unresolved_after = True
            elif not any(r["race_id"][:8] == last_day for r in unresolved):
                unresolved_after = False
        values = {
            H0[0]: len(ranked),
            H0[1]: sum(r == 1 for r in ranks),
            H0[2]: sum(r <= 3 for r in ranks),
            H0[3]: sum(r <= 3 for r in ranks) / len(ranks) if ranks else None,
            H0[4]: len(unresolved),
            H1_ADDITIONS[0]: sum(r["race_id"][:8] >= recent_day for r in ranked),
            H1_ADDITIONS[1]: (
                target - datetime.strptime(last["race_id"][:8], "%Y%m%d")
            ).days
            if last
            else None,
            H1_ADDITIONS[2]: ranks[-1] if last_rank_unique else None,
            H1_ADDITIONS[3]: sum(ranks[-3:]) / len(ranks[-3:])
            if ranks and three_boundary_unique
            else None,
            H1_ADDITIONS[4]: unresolved_after,
        }
        if missing:
            values = dict.fromkeys(values)
        output.append(
            {
                "chul_no": runner["chul_no"],
                "horse_id": runner["horse_id"],
                "features": {
                    **values,
                    **{f"{k}_missing": v is None for k, v in values.items()},
                    "gate": runner["chul_no"],
                    "physical_meet": int(meet),
                    "roster_size": len(roster),
                    "response_window_incomplete": bool(missing),
                },
                "lineage": [
                    {
                        k: r[k]
                        for k in (
                            "race_id",
                            "chul_no",
                            "source_capture_sha256",
                            "source_available_at",
                        )
                    }
                    for r in history
                ],
            }
        )
    return {
        "race_id": race["race_id"],
        "lookback_start": lower,
        "lookback_end_exclusive": day,
        "missing_response_units": [{"day": d, "meet": m} for d, m in missing],
        "feature_rows": output,
        "historical_pre_race_availability_verified": False,
        "complete_actual_start_history_verified": False,
        "training_approved": False,
    }
