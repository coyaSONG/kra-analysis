"""Replay an original input witness and result version for development review."""

import argparse
import json
from collections import Counter
from pathlib import Path

from autoresearch import fixed_pair_evaluation as evidence
from autoresearch import fixed_pair_forward_contract as inputs
from autoresearch.kra_entry_scope_intake import now
from autoresearch.kra_race_card_pdf_replay import archive_path, checked_digest
from autoresearch.observed_history_seed import save
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import API_COLUMNS, encoded, sha256

FORMAT = "kra-api26-whole-card-learning-replay-v1"
CANDIDATE = "kra-api26-whole-card-development-candidate-v1"


def _target(binding, original, captures, observed):
    outcome, used, roster = evidence.outcome_evidence(
        binding, original, captures, observed
    )
    status = original["status"] if original else "result_version_not_selected"
    official = original["official_source"] if original else None
    row = {
        "race_id": binding["race"]["race_id"],
        "result_observation_id": original["result_observation_id"]
        if original
        else None,
        "result_status": status,
        "result_reasons": original["reasons"] if original else [],
        "result_exception_notes": original["exception_notes"] if original else {},
        "roster_comparison": roster,
        "api_result_captures": used,
        "official_result_evidence": (
            {key: official[key] for key in ("receipt", "capture")} if official else None
        ),
    }
    if roster and roster["unexpected_api_or_official_identity"]:
        return row | {"join_state": "input_result_identity_conflict"}, None
    if not outcome or status != "unique_top3_observed":
        return row | {"join_state": status}, None
    # A unique top three alone does not establish the full declaration join.
    if not (
        roster["declared_count"]
        == roster["api_record_count"]
        == roster["official_record_count"]
        and roster["declared_not_in_api_result"] == 0
    ):
        return row | {"join_state": "incomplete_result_roster"}, None
    target = outcome["observed_top3_horse_ids"]
    declared = {r["horse_id"] for r in binding["shared_input"]["feature_rows"]}
    if (
        type(target) is not list
        or len(target) != 3
        or not set(target) <= declared
        or target != sorted(set(target), key=int)
    ):
        raise ValueError("whole_card_learning_target_identity_conflict")
    return row | {"join_state": "joined"}, {
        "race_id": row["race_id"],
        "horse_ids": target,
        "result_observation_id": row["result_observation_id"],
    }


def replay(
    root,
    receipt,
    *,
    schedule_sha256,
    first_cutoff,
    packet_sha256,
    input_pr,
    result_plan=None,
):
    """Return a whole-card report and, only if complete, an unapproved candidate."""
    observed = now()
    root = root.resolve()
    verified, source = inputs.source(
        root,
        receipt,
        schedule_sha256=schedule_sha256,
        first_cutoff=first_cutoff,
        packet_sha256=packet_sha256,
        input_pr=input_pr,
    )
    bindings = {b["race"]["race_id"]: b for b in verified["bindings"]}
    if (
        not bindings
        or len(bindings) != len(verified["bindings"])
        or len(bindings) != verified["race_count"]
    ):
        raise ValueError("whole_card_learning_input_population_conflict")
    plan_ref = None
    if result_plan is not None:
        path = archive_path(result_plan[0], archive_root=root)
        plan_ref = path, checked_digest(result_plan[1])
    outcomes, captures, extra_api, extra_web, version = evidence.outcome_version(
        bindings,
        {"race_dates": verified["race_dates"], "source": source},
        plan_ref,
    )
    if version is not None:
        version = version | {"plan_path": str(plan_ref[0].relative_to(root))}
    context = evidence.context_from_inputs(root, bindings)
    ledger, targets = [], []
    for race_id, binding in sorted(bindings.items()):
        row, target = _target(binding, outcomes.get(race_id), captures, observed)
        ledger.append(row | {"pre_race_context": context[race_id]})
        if target is not None:
            targets.append(target)

    holds = []
    if len(targets) != len(bindings):
        holds.append("not_all_declared_races_have_joined_targets")
    if extra_api or extra_web:
        holds.append("selected_result_version_has_out_of_scope_races")
    report = {
        "format_version": FORMAT,
        "implementation_sha256": sha256(Path(__file__).read_bytes()),
        "readback_started_at": observed.isoformat(),
        "first_block_cutoff": verified["first_block_cutoff"],
        "race_dates": verified["race_dates"],
        "population_sha256": sha256(encoded(sorted(bindings))),
        "race_count": len(bindings),
        "declaration_count": verified["declaration_count"],
        "api26_feature_missing_counts": verified["feature_missing_counts"],
        "source": source | {"intake_receipt": verified["intake_receipt"]},
        "result_version": version,
        "extra_api_result_ids": extra_api,
        "extra_official_result_ids": extra_web,
        "join_counts": dict(sorted(Counter(r["join_state"] for r in ledger).items())),
        "candidate_ready_for_review": not holds,
        "hold_reasons": holds,
        "ledger": ledger,
        "training_approved": False,
        "model_fit_or_prediction_attempted": False,
        "counts_as_70_percent_evidence": False,
    }
    if holds:
        return report, None

    candidate = {
        "format_version": CANDIDATE,
        "report": report,
        "feature_columns": list(API_COLUMNS),
        "input_races": [
            {
                "race": b["race"],
                "entry_manifest": b["entry_manifest"],
                "pre_race_context": context[race_id],
                "shared_input": b["shared_input"],
            }
            for race_id, b in sorted(bindings.items())
        ],
        "target_races": targets,
    }
    return report, candidate


def seal(root, receipt, **selected):
    """Save one local version, never making it an approved training input."""
    report, candidate = replay(root, receipt, **selected)
    if candidate is None:
        return report, None
    root = root.resolve()
    ref = report["source"]["intake_receipt"]
    parent = (root / ref["path"]).parent
    plan_sha = report["result_version"]["plan_sha256"]
    path = parent / f"development-candidate-{plan_sha}.json"
    materialized = now()
    if materialized < timestamp(report["readback_started_at"]):
        raise ValueError("whole_card_learning_materialization_clock_conflict")
    candidate["materialized_at"] = materialized.isoformat()
    digest = save(path, candidate)
    return report, {"path": str(path.relative_to(root)), "sha256": digest}


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--receipt", required=True)
    cli.add_argument("--receipt-sha256", required=True)
    cli.add_argument("--schedule-sha256", required=True)
    cli.add_argument("--first-cutoff", required=True)
    cli.add_argument("--packet-sha256", required=True)
    cli.add_argument("--input-pr", type=int, required=True)
    cli.add_argument("--result-plan")
    cli.add_argument("--result-plan-sha256")
    cli.add_argument("--seal", action="store_true")
    args = cli.parse_args(argv)
    if bool(args.result_plan) != bool(args.result_plan_sha256):
        cli.error("--result-plan and --result-plan-sha256 must be supplied together")
    result_plan = (
        (args.result_plan, args.result_plan_sha256) if args.result_plan else None
    )
    operation = seal if args.seal else replay
    report, output = operation(
        Path.cwd(),
        {"path": args.receipt, "sha256": args.receipt_sha256},
        schedule_sha256=args.schedule_sha256,
        first_cutoff=args.first_cutoff,
        packet_sha256=args.packet_sha256,
        input_pr=args.input_pr,
        result_plan=result_plan,
    )
    if args.seal:
        report = report | {"sealed_candidate": output}
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
    return 0 if report["candidate_ready_for_review"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
