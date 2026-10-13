"""Fixed condition-matched historical form; no fitting, tuning or promotion."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

from autoresearch import history_form_research as form
from autoresearch import race_conditions
from autoresearch.observed_history_seed import digest, save

ARMS = ("expanded90", "venue90", "distance90", "class90", "joint90")
RECIPE = {
    "arms": list(ARMS),
    "distance_tolerance_metres": 200,
    "class_rule": "exact_label_same_physical_venue",
    "condition_source": "pinned_official_dated_header_only",
    "missing_context_or_empty_eligible_history": "per_runner_expanded90_fallback",
    "window_days": 90,
    "rank_pseudo_count": 2,
    "rank_prior_mean": "1/2",
}
FLAGS = {
    "training_approved": False,
    "model_promoted": False,
    "historical_pre_race_availability_verified": False,
    "target_roster_prerace_verified": False,
    "target_conditions_prerace_verified": False,
    "counts_as_70_percent_evidence": False,
    "untouched_holdout": False,
    "complete_future_national_universe": False,
    "prediction_success_rate": None,
    "fit_count": 0,
}


def eligible(target, prior, arm):
    if arm not in ARMS:
        raise ValueError("condition_unknown_arm")
    if arm == "expanded90":
        return True
    if target.get("status") != "observed" or prior.get("status") != "observed":
        return False
    return (
        target["meet"] == prior["meet"]
        and (
            arm not in ("distance90", "joint90")
            or abs(target["distance_m"] - prior["distance_m"]) <= 200
        )
        and (
            arm not in ("class90", "joint90")
            or target["class_text"] == prior["class_text"]
        )
    )


def predict(targets, history, conditions):
    indexed, withheld = form.index_history(history)
    ledger, diagnostics = [], defaultdict(Counter)
    if not targets:
        raise ValueError("condition_empty_targets")
    for identity, roster in sorted(targets.items()):
        if any(set(r) != {"horse_id", "chul_no"} for r in roster):
            raise ValueError("condition_target_not_identity_only")
        form.group_records([{"race_id": identity, **r} for r in roster])
        target = conditions.get(identity, {})
        arms = {}
        for arm in ARMS:
            rows = []
            for runner in sorted(roster, key=lambda r: r["chul_no"]):
                prior = form.prior_rows(
                    indexed[runner["horse_id"]], identity[:8], "expanded90"
                )
                matched = [
                    r
                    for r in prior
                    if eligible(target, conditions.get(r["race_id"], {}), arm)
                ]
                fallback = None
                if arm != "expanded90":
                    if target.get("status") != "observed":
                        fallback = "missing_target_conditions"
                    elif not matched:
                        fallback = "no_eligible_prior"
                used = prior if fallback else matched
                score = form.form_score(used, "expanded90")
                rejected = Counter()
                for item in prior:
                    context = conditions.get(item["race_id"], {})
                    if arm == "expanded90" or eligible(target, context, arm):
                        rejected["eligible"] += 1
                    elif target.get("status") != "observed":
                        rejected["target_conditions_unknown"] += 1
                    elif context.get("status") != "observed":
                        rejected["prior_conditions_unknown"] += 1
                    else:
                        rejected["conditions_mismatch"] += 1
                score_changed = score != form.form_score(prior, "expanded90")
                rows.append(
                    {
                        **runner,
                        "score_fraction": str(score),
                        "prior_ids": [r["race_id"] for r in used],
                        "prior_tiers": [r["tier"] for r in used],
                        "eligible_prior_ids": [r["race_id"] for r in matched],
                        "fallback": fallback,
                        "baseline_prior_count": len(prior),
                        "prior_partition": dict(rejected),
                        "score_changed_vs_baseline": score_changed,
                    }
                )
                diagnostics[arm].update(
                    {
                        "runner_rows": 1,
                        "fallback_rows": int(fallback is not None),
                        "no_history_rows": int(not used),
                        "score_changed_rows": int(score_changed),
                        f"eligible_count_{min(len(matched), 3)}": 1,
                    }
                )
                diagnostics[arm].update(f"used_{r['tier']}" for r in used)
                diagnostics[arm].update(
                    {f"prior_{key}": value for key, value in rejected.items()}
                )
                if fallback:
                    diagnostics[arm][fallback] += 1
            ordered = sorted(
                rows,
                key=lambda r: (
                    -Fraction(r["score_fraction"]),
                    r["chul_no"],
                    int(r["horse_id"]),
                ),
            )
            tied = len(ordered) > 3 and Fraction(
                ordered[2]["score_fraction"]
            ) == Fraction(ordered[3]["score_fraction"])
            arms[arm] = {
                "horse_ids": [r["horse_id"] for r in ordered[:3]]
                if len(rows) >= 3
                else None,
                "rows": rows,
                "boundary_score_tie": tied,
            }
            diagnostics[arm].update(
                {
                    "races": 1,
                    "boundary_score_ties": int(tied),
                    "selected_with_fallback": sum(
                        r["fallback"] is not None for r in ordered[:3]
                    )
                    if len(rows) >= 3
                    else 0,
                }
            )
            if arm != "expanded90":
                fallback_count = sum(r["fallback"] is not None for r in rows)
                path = (
                    "all_fallback"
                    if fallback_count == len(rows)
                    else "mixed_paths"
                    if fallback_count
                    else "all_condition_scores"
                )
                diagnostics[arm][f"race_path_{path}"] += 1
        ledger.append({"race_id": identity, "arms": arms})
    return {
        "ledger": ledger,
        "diagnostics": diagnostics,
        "invalid_rank_size_history_withheld": withheld,
    }


def evaluate(predictions, outcomes):
    identities = [r["race_id"] for r in predictions["ledger"]]
    if len(set(identities)) != len(identities) or set(identities) != set(outcomes):
        raise ValueError("condition_outcome_population_mismatch")
    totals, paired, ledger = (
        defaultdict(lambda: defaultdict(Counter)),
        defaultdict(lambda: defaultdict(Counter)),
        [],
    )
    for prediction in predictions["ledger"]:
        identity = prediction["race_id"]
        outcome, states = outcomes[identity], {}
        answer = outcome["horse_ids"]
        if outcome["status"] == "unique_top3_observed" and (
            not answer or len(answer) != 3 or len(set(answer)) != 3
        ):
            raise ValueError("condition_invalid_unique_outcome")
        for arm in ARMS:
            chosen = prediction["arms"][arm]["horse_ids"]
            if chosen is not None and (len(chosen) != 3 or len(set(chosen)) != 3):
                raise ValueError("condition_invalid_selection")
            state = "pending"
            if chosen is None:
                state = "execution_failure"
            elif outcome["status"] == "void_reported_no_top3":
                state = "undefined"
            elif outcome["status"] == "unique_top3_observed":
                state = "match" if set(chosen) == set(answer) else "mismatch"
            states[arm] = state
        for scope in ("all", f"month:{identity[:6]}", f"meet:{identity.split('_')[1]}"):
            for arm, state in states.items():
                totals[scope][arm].update({"races": 1, state: 1})
                baseline = states["expanded90"]
                pair = "not_comparable"
                if baseline in ("match", "mismatch") and state in ("match", "mismatch"):
                    pair = (
                        "both_match"
                        if baseline == state == "match"
                        else "baseline_only"
                        if baseline == "match"
                        else "candidate_only"
                        if state == "match"
                        else "neither_match"
                    )
                before = prediction["arms"]["expanded90"]["horse_ids"]
                after = prediction["arms"][arm]["horse_ids"]
                paired[scope][arm].update(
                    {
                        "races": 1,
                        pair: 1,
                        "changed_combinations": int(
                            set(before or []) != set(after or [])
                        ),
                    }
                )
        ledger.append({"race_id": identity, "outcome": outcome, "states": states})
    return {"ledger": ledger, "totals": totals, "paired_vs_expanded90": paired}


def run(plan_path, plan_sha, directory):
    plan = form.catalog.read_pin(plan_path, plan_sha)
    if (
        plan.get("format_version") != "condition-form-exploration-plan-v1"
        or any(plan.get(k) != v for k, v in RECIPE.items())
        or any(
            plan.get(k) is not False
            for k in ("training_approved", "counts_as_70_percent_evidence")
        )
    ):
        raise ValueError("condition_unrecognized_protocol")
    source_plan = form.catalog.read_pin(
        Path(plan["source_plan"]), plan["source_plan_sha256"]
    )
    targets, outcomes, history = form.load_sources(source_plan)
    conditions = race_conditions.load_conditions(source_plan)
    directory.mkdir(parents=True, exist_ok=False)
    implementations = form.source_hashes()
    for name in (
        "condition_form_research.py",
        "race_conditions.py",
        "history_form_research.py",
        "official_history_catalog.py",
    ):
        implementations[f"autoresearch/{name}"] = digest(
            Path(__file__).with_name(name).read_bytes()
        )
    common = {
        **FLAGS,
        "plan_sha256": plan_sha,
        "recipe": RECIPE,
        "scope": "retrospective_full_archived_population",
        "implementation": implementations,
    }
    common["target_manifest_sha256"] = save(
        directory / "targets.json",
        {
            "membership_basis": "pinned_archived_result_roster",
            "plan_sha256": plan["source_plan_sha256"],
            "rows": [
                {"race_id": identity, **r}
                for identity, roster in sorted(targets.items())
                for r in sorted(roster, key=lambda r: r["chul_no"])
            ],
        },
    )
    common["history_sha256"] = save(
        directory / "history.json", {"records": history, **FLAGS}
    )
    common["conditions_sha256"] = save(
        directory / "conditions.json", {"records": conditions, **FLAGS}
    )
    predictions = predict(targets, history, conditions)
    common["prediction_sha256"] = save(
        directory / "predictions.json", {**common, **predictions}
    )
    report = {
        **common,
        "diagnostics": predictions["diagnostics"],
        "condition_status_counts": dict(
            Counter(r["status"] for r in conditions.values())
        ),
        "target_condition_status_counts": dict(
            Counter(conditions.get(k, {}).get("status", "unknown") for k in targets)
        ),
        "history_rows_without_observed_conditions": sum(
            conditions.get(r["race_id"], {}).get("status") != "observed"
            for r in history
        ),
        "target_condition_outcome_cross_counts": dict(
            Counter(
                f"{conditions.get(k, {}).get('status', 'unknown')}:{v['status']}"
                for k, v in outcomes.items()
            )
        ),
        **evaluate(predictions, outcomes),
    }
    report_sha = save(directory / "report.json", report)
    return {
        "report_sha256": report_sha,
        **{
            k: report[k]
            for k in (
                "prediction_sha256",
                "target_manifest_sha256",
                "condition_status_counts",
                "target_condition_status_counts",
                "totals",
                "paired_vs_expanded90",
                "diagnostics",
            )
        },
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
