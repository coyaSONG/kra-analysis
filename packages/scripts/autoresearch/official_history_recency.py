"""Offline supported recency candidates, not training or performance approval."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

from autoresearch import official_history_support as support
from autoresearch.observed_history_seed import digest, save

CONTRACT = "official_supported_recency_v1"
FIELDS = (
    "observed_supported_ranked_finish_count_30d",
    "days_since_last_observed_supported_ranked_date_90d",
    "last_observed_supported_rank_90d",
    "mean_last_three_observed_supported_ranks_90d",
    "has_linked_api_unresolved_after_last_supported_ranked_date",
)


def project_recency(base):
    """Consume the freshly replayed support report, never an approval flag."""
    groups = {g["race_id"]: g for g in base["groups"]}
    if len(groups) != len(base["groups"]):
        raise ValueError("recency_duplicate_group")
    races = []
    for race in base["races"]:
        day, meet, _ = race["race_id"].split("_")
        target = datetime.strptime(day, "%Y%m%d")
        lower = (target - timedelta(days=90)).strftime("%Y%m%d")
        recent = (target - timedelta(days=30)).strftime("%Y%m%d")
        old = race["observed_partial_v1"]
        legacy = old["legacy_projection"]
        if (old["lookback_start"], old["lookback_end_exclusive"]) != (lower, day):
            raise ValueError("recency_window_mismatch")
        rows = []
        expected = {(r["chul_no"], r["horse_id"]) for r in old["feature_rows"]}
        members = race["official_supported_partial_v1"]
        actual = {(r["chul_no"], r["horse_id"]) for r in members}
        if actual != expected or len(actual) != len(members):
            raise ValueError("recency_roster_mismatch")
        missing = legacy["missing_response_units"]
        for runner in members:
            ranked, unresolved, withheld, seen = [], [], [], set()
            for kind, links in (
                ("ranked", runner["used_ranked_lineage"]),
                ("unresolved", runner["linked_unresolved_lineage"]),
                ("withheld", runner["withheld_lineage"]),
            ):
                for link in links:
                    identity = link["race_id"]
                    if identity in seen or not lower <= identity[:8] < day:
                        raise ValueError("recency_invalid_lineage_window_or_duplicate")
                    seen.add(identity)
                    group = groups[identity]
                    if kind == "withheld":
                        withheld.append(link)
                        continue
                    matches = [
                        r
                        for r in group["rows"]
                        if r["horse_id"] == runner["horse_id"]
                        and r["chul_no"] == link["chul_no"]
                    ]
                    if (
                        group["official_event_support"] != "confirmed"
                        or group["roster_support"] != "exact"
                        or len(matches) != 1
                    ):
                        raise ValueError("recency_lineage_not_supported")
                    row = matches[0]
                    evidence = {
                        **link,
                        "official_receipt": group["evidence"]["receipt"],
                    }
                    if kind == "ranked":
                        if not row["ranked_feature_supported"]:
                            raise ValueError("recency_rank_not_supported")
                        rank = int(row["official_row"]["rank_text"])
                        if not 1 <= rank <= 20:
                            raise ValueError("recency_invalid_rank")
                        ranked.append({**evidence, "rank": rank})
                    else:
                        if not row["event_linked_api_unresolved"]:
                            raise ValueError("recency_unresolved_not_linked")
                        unresolved.append(evidence)
            ranked.sort(key=lambda r: r["race_id"])
            ranks = [r["rank"] for r in ranked]
            last_day = ranked[-1]["race_id"][:8] if ranked else None
            last_unique = (
                bool(ranked) and sum(r["race_id"][:8] == last_day for r in ranked) == 1
            )
            boundary_unique = len(ranked) <= 3 or (
                ranked[-3]["race_id"][:8] != ranked[-4]["race_id"][:8]
            )
            unresolved_after = None
            if last_day:
                if any(r["race_id"][:8] > last_day for r in unresolved):
                    unresolved_after = True
                elif not any(r["race_id"][:8] == last_day for r in unresolved):
                    unresolved_after = False
            values = (
                sum(r["race_id"][:8] >= recent for r in ranked),
                (target - datetime.strptime(last_day, "%Y%m%d")).days
                if last_day
                else None,
                ranks[-1] if last_unique else None,
                sum(ranks[-3:]) / len(ranks[-3:])
                if ranks and boundary_unique
                else None,
                unresolved_after,
            )
            features = dict(zip(FIELDS, values, strict=True))
            features.update(
                {f"{k}_missing": v is None for k, v in features.copy().items()}
            )
            features.update(
                gate=runner["chul_no"],
                physical_meet=int(meet),
                roster_size=len(members),
                response_window_incomplete=bool(missing),
                response_30d_window_incomplete=any(r["day"] >= recent for r in missing),
                withheld_observation_count_90d=len(withheld),
                withheld_on_or_after_last_supported_date=any(
                    last_day is None or r["race_id"][:8] >= last_day for r in withheld
                ),
                last_supported_rank_same_day_ambiguous=bool(ranked) and not last_unique,
                last_three_boundary_same_day_ambiguous=not boundary_unique,
            )
            rows.append(
                {
                    "horse_id": runner["horse_id"],
                    "chul_no": runner["chul_no"],
                    "features": features,
                    "base_90d_features": runner["features"],
                    "ranked_lineage": ranked,
                    "linked_unresolved_lineage": unresolved,
                    "withheld_lineage": withheld,
                }
            )
        races.append(
            {
                "race_id": race["race_id"],
                "lookback_start": lower,
                "recent_start": recent,
                "lookback_end_exclusive": day,
                "response_unit_status_counts": old["response_unit_status_counts"],
                "missing_response_units": missing,
                "feature_rows": rows,
            }
        )
    if len({r["race_id"] for r in races}) != len(races) or not races:
        raise ValueError("recency_invalid_target_membership")
    return races


def materialize(*args, **kwargs):
    base = support.materialize(*args, **kwargs)
    races = project_recency(base)
    return {
        "format_version": "kra-official-supported-recency-v1",
        "feature_contract": CONTRACT,
        "feature_fields": list(FIELDS),
        "implementation_sha256": digest(Path(__file__).read_bytes()),
        "support_projection": base,
        "race_count": len(races),
        "runner_count": sum(len(r["feature_rows"]) for r in races),
        "races": races,
        "zero_count_meaning": "no_supported_observations_in_selected_sources",
        "recency_meaning": "calendar_days_since_observed_supported_date_not_true_rest",
        "scope": "all_pinned_diagnostic_rosters_not_future_national_universe",
        "training_approved": False,
        "historical_pre_race_availability_verified": False,
        "complete_actual_start_history_verified": False,
        "independent_timestamp_verified": False,
        "prediction_registration_verified": False,
        "counts_as_70_percent_evidence": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--seed-sha256", required=True)
    parser.add_argument("--archive-dir", type=Path, required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--corpus-sha256", required=True)
    parser.add_argument("--history-source-cutoff")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = materialize(
        args.root,
        args.seed,
        args.seed_sha256,
        args.archive_dir,
        args.archive_sha256,
        args.corpus,
        args.corpus_sha256,
        cutoff=args.history_source_cutoff,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sha = save(args.output, result)
    print(
        json.dumps(
            {
                "sha256": sha,
                "race_count": result["race_count"],
                "runner_count": result["runner_count"],
                "training_approved": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
