"""Fixed historical-form selections; no fitting or pre-race performance claim."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from fractions import Fraction
from pathlib import Path

from shared.official_result_support import reconcile_group

from autoresearch import official_history_catalog as catalog
from autoresearch.frozen_history_view import replay_frozen
from autoresearch.observed_history_seed import digest, save
from autoresearch.official_history_support import replay_archive
from autoresearch.versioned_result_observations import observe_race, source_hashes

ARMS = ("gate", "dual90", "expanded90", "expanded180", "top3_90")
RECIPE = {
    "arms": list(ARMS),
    "rank_pseudo_count": 2,
    "rank_prior_mean": "1/2",
    "top3_pseudo_count": 2,
    "top3_prior_mean": "3/10",
}


def group_records(records):
    groups, horses, gates = defaultdict(list), set(), set()
    for row in records:
        identity, horse, gate = row["race_id"], row["horse_id"], row["chul_no"]
        if (identity, horse) in horses or (identity, gate) in gates:
            raise ValueError("form_duplicate_roster_member")
        horses.add((identity, horse))
        gates.add((identity, gate))
        groups[identity].append(row)
    return groups


def load_dual(spec):
    seed = replay_frozen(Path(spec["root"]), Path(spec["seed"]), spec["seed_sha256"])
    evidence = replay_archive(
        Path(spec["archive"]), spec["archive_sha256"], seed, spec["seed_sha256"]
    )
    rosters, outcomes, history = {}, {}, []
    for identity, members in sorted(group_records(seed["records"]).items()):
        official = evidence[identity]["parsed"]
        observation = observe_race(identity, len(members), members, official)
        # This is an archived roster, not the adapter's independent schedule.
        outcomes[identity] = {
            "status": observation["status"],
            "horse_ids": observation["observed_top3_horse_ids"],
            "reasons": observation["reasons"],
        }
        rosters[identity] = [
            {"horse_id": r["horse_id"], "chul_no": r["chul_no"]}
            for r in sorted(members, key=lambda r: r["chul_no"])
        ]
        support = reconcile_group(members, official)
        if observation["status"] == "source_conflict":
            continue
        for row in support["rows"]:
            if row["ranked_feature_supported"]:
                history.append(
                    {
                        "race_id": identity,
                        "horse_id": row["horse_id"],
                        "rank": int(row["official_row"]["rank_text"]),
                        "observed_roster_size": len(members),
                        "tier": "dual_supported",
                    }
                )
    return rosters, outcomes, history


def load_sources(plan):
    targets, outcomes, history = load_dual(plan["target"])
    earlier, _, extra = load_dual(plan["earlier"])
    if targets.keys() & earlier.keys() or max(earlier)[:8] >= min(targets)[:8]:
        raise ValueError("form_extension_not_disjoint_earlier")
    spec = plan["catalog"]
    html = catalog.replay(
        Path(spec["directory"]),
        spec["index_sha256"],
        spec["archive_sha256"],
        Path(spec["discovery"]),
    )
    sizes = {g["race_id"]: g["runner_count"] for g in html["groups"]}
    if (
        sizes.keys() & (targets.keys() | earlier.keys())
        or max(sizes)[:8] >= min(targets)[:8]
    ):
        raise ValueError("form_catalog_not_disjoint_earlier")
    history.extend(extra)
    history.extend(
        {
            "race_id": r["race_id"],
            "horse_id": r["horse_id"],
            "rank": int(r["rank_text"]),
            "observed_roster_size": sizes[r["race_id"]],
            "tier": "html_only",
        }
        for r in html["records"]
        if r["numeric_rank_time_observed"]
    )
    if (
        len(targets) != plan["expected_target_races"]
        or sum(map(len, targets.values())) != plan["expected_target_rows"]
    ):
        raise ValueError("form_target_membership_mismatch")
    return targets, outcomes, history


def index_history(history):
    indexed, seen, withheld = defaultdict(list), set(), 0
    for row in history:
        key = row["race_id"], row["horse_id"]
        if key in seen:
            raise ValueError("form_duplicate_history_member")
        seen.add(key)
        if row["tier"] not in ("dual_supported", "html_only"):
            raise ValueError("form_unknown_source_tier")
        rank, size = row["rank"], row["observed_roster_size"]
        if (
            type(rank) is not int
            or type(size) is not int
            or not 1 <= rank <= size
            or size < 2
        ):
            withheld += 1
            continue
        indexed[row["horse_id"]].append(row)
    return indexed, withheld


def prior_rows(rows, day, arm):
    window = 180 if arm == "expanded180" else 90
    lower = (datetime.strptime(day, "%Y%m%d") - timedelta(days=window)).strftime(
        "%Y%m%d"
    )
    return sorted(
        (
            r
            for r in rows
            if lower <= r["race_id"][:8] < day
            and (arm != "dual90" or r["tier"] == "dual_supported")
        ),
        key=lambda r: r["race_id"],
    )


def form_score(prior, arm):
    if arm == "gate":
        return Fraction(0)
    if arm == "top3_90":
        return (Fraction(3, 5) + sum(r["rank"] <= 3 for r in prior)) / (2 + len(prior))
    return (
        Fraction(1)
        + sum(1 - Fraction(r["rank"] - 1, r["observed_roster_size"] - 1) for r in prior)
    ) / (2 + len(prior))


def predict(targets, history):
    indexed, withheld = index_history(history)
    output, diagnostics = [], defaultdict(Counter)
    if not targets:
        raise ValueError("form_empty_targets")
    for identity, roster in sorted(targets.items()):
        if any(set(row) != {"horse_id", "chul_no"} for row in roster):
            raise ValueError("form_target_input_not_identity_only")
        group_records([{"race_id": identity, **row} for row in roster])
        arms = {}
        for arm in ARMS:
            rows = []
            for runner in sorted(roster, key=lambda r: r["chul_no"]):
                prior = (
                    []
                    if arm == "gate"
                    else prior_rows(indexed[runner["horse_id"]], identity[:8], arm)
                )
                score = form_score(prior, arm)
                rows.append(
                    {
                        **runner,
                        "score": float(score),
                        "score_fraction": str(score),
                        "prior_ids": [r["race_id"] for r in prior],
                        "prior_tiers": [r["tier"] for r in prior],
                    }
                )
            ordered = sorted(
                rows,
                key=lambda r: (
                    -Fraction(r["score_fraction"]),
                    r["chul_no"],
                    int(r["horse_id"]),
                ),
            )
            arms[arm] = {
                "horse_ids": [r["horse_id"] for r in ordered[:3]]
                if len(rows) >= 3
                else None,
                "status": "selected"
                if len(rows) >= 3
                else "insufficient_archived_roster",
                "rows": rows,
                "boundary_score_tie": len(ordered) > 3
                and Fraction(ordered[2]["score_fraction"])
                == Fraction(ordered[3]["score_fraction"]),
            }
            diagnostics[arm].update(
                {
                    "races": 1,
                    "runner_rows": len(rows),
                    "selection_count": int(len(rows) >= 3),
                    "boundary_score_ties": int(arms[arm]["boundary_score_tie"]),
                    "selected_without_prior": sum(
                        not r["prior_ids"] for r in ordered[:3]
                    )
                    if len(rows) >= 3
                    else 0,
                }
            )
            for row in rows:
                n = len(row["prior_ids"])
                diagnostics[arm][
                    f"prior_count_{min(n, 3)}{'_plus' if n >= 3 else ''}"
                ] += 1
                diagnostics[arm].update(
                    f"used_{tier}_observations" for tier in row["prior_tiers"]
                )
        output.append({"race_id": identity, "arms": arms})
    return {
        "ledger": output,
        "diagnostics": diagnostics,
        "invalid_rank_size_history_withheld": withheld,
    }


def evaluate(predictions, outcomes):
    ledger, totals, paired = (
        [],
        defaultdict(lambda: defaultdict(Counter)),
        defaultdict(lambda: defaultdict(Counter)),
    )
    identities = [r["race_id"] for r in predictions["ledger"]]
    if len(set(identities)) != len(identities) or set(identities) != set(outcomes):
        raise ValueError("form_outcome_population_mismatch")
    for prediction in predictions["ledger"]:
        identity = prediction["race_id"]
        outcome = outcomes[identity]
        answers = outcome["horse_ids"]
        if outcome["status"] == "unique_top3_observed" and (
            not answers or len(answers) != 3 or len(set(answers)) != 3
        ):
            raise ValueError("form_invalid_unique_outcome")
        states = {}
        for arm in ARMS:
            chosen = prediction["arms"][arm]["horse_ids"]
            state = "pending"
            if chosen is None:
                state = "execution_failure"
            elif outcome["status"] == "void_reported_no_top3":
                state = "undefined"
            elif outcome["status"] == "unique_top3_observed" and chosen is not None:
                if len(chosen) != 3 or len(set(chosen)) != 3:
                    raise ValueError("form_invalid_three_selection")
                state = "match" if set(chosen) == set(answers) else "mismatch"
            states[arm] = state
        for scope in ("all", f"month:{identity[:6]}", f"meet:{identity.split('_')[1]}"):
            for arm, state in states.items():
                totals[scope][arm].update({"races": 1, state: 1})
                a, b = states["dual90"], state
                paired_state = "not_comparable"
                if a in ("match", "mismatch") and b in ("match", "mismatch"):
                    paired_state = (
                        "both_match"
                        if a == b == "match"
                        else "baseline_only"
                        if a == "match"
                        else "candidate_only"
                        if b == "match"
                        else "neither_match"
                    )
                before = prediction["arms"]["dual90"]["horse_ids"]
                after = prediction["arms"][arm]["horse_ids"]
                paired[scope][arm].update(
                    {
                        "races": 1,
                        paired_state: 1,
                        "changed_combinations": int(
                            set(before or []) != set(after or [])
                        ),
                    }
                )
        ledger.append({"race_id": identity, "outcome": outcome, "states": states})
    return {"ledger": ledger, "totals": totals, "paired_vs_dual90": paired}


def run(plan_path, plan_sha, directory):
    plan = catalog.read_pin(plan_path, plan_sha)
    if (
        plan.get("format_version") != "history-form-exploration-plan-v1"
        or any(plan.get(k) != v for k, v in RECIPE.items())
        or plan.get("training_approved") is not False
        or plan.get("counts_as_70_percent_evidence") is not False
    ):
        raise ValueError("form_unrecognized_protocol")
    targets, outcomes, history = load_sources(plan)
    directory.mkdir(parents=True, exist_ok=False)
    flags = {
        "training_approved": False,
        "model_promoted": False,
        "historical_pre_race_availability_verified": False,
        "target_roster_prerace_verified": False,
        "counts_as_70_percent_evidence": False,
        "untouched_holdout": False,
        "prediction_success_rate": None,
        "complete_future_national_universe": False,
        "complete_actual_start_history_verified": False,
        "fit_count": 0,
    }
    implementations = source_hashes()
    for name in ("history_form_research.py", "official_history_catalog.py"):
        implementations[f"autoresearch/{name}"] = digest(
            Path(__file__).with_name(name).read_bytes()
        )
    common = {
        "plan_sha256": plan_sha,
        "recipe": RECIPE,
        "implementation": implementations,
        "scope": "retrospective_full_archived_population_not_national_forward_test",
        **flags,
    }
    target_rows = [
        {"race_id": identity, **row}
        for identity, roster in sorted(targets.items())
        for row in sorted(roster, key=lambda r: r["chul_no"])
    ]
    common["target_manifest_sha256"] = save(
        directory / "targets.json",
        {
            "membership_basis": "pinned_archived_result_roster",
            "plan_sha256": plan_sha,
            "rows": target_rows,
        },
    )
    common["history_view_sha256"] = save(
        directory / "history.json",
        {
            "plan_sha256": plan_sha,
            "records": history,
            **flags,
        },
    )
    predictions = predict(targets, history)
    prediction_sha = save(directory / "predictions.json", {**common, **predictions})
    report = {
        **common,
        "prediction_sha256": prediction_sha,
        "outcome_status_counts": dict(Counter(r["status"] for r in outcomes.values())),
        "diagnostics": predictions["diagnostics"],
        **evaluate(predictions, outcomes),
    }
    report_sha = save(directory / "report.json", report)
    return {
        "report_sha256": report_sha,
        "prediction_sha256": prediction_sha,
        "outcome_status_counts": report["outcome_status_counts"],
        "totals": report["totals"],
        "paired_vs_dual90": report["paired_vs_dual90"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.plan, args.plan_sha256, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
