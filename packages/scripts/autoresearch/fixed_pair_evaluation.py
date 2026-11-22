"""Read-only full-card comparison of an approved M0/API27 pair and pinned results."""

import argparse
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

from autoresearch import api27_evaluation as paired
from autoresearch import condition_forward_publication as publication
from autoresearch import fixed_pair_forward as forward
from autoresearch import fixed_pair_forward_contract as contract
from autoresearch import local_m0_evaluation as base
from autoresearch import prerace_conditions as conditions
from autoresearch import versioned_result_observations as results
from autoresearch.api27_forward import ARM as API27_ARM
from autoresearch.condition_training_admission import read
from autoresearch.kra_entry_scope_intake import now
from autoresearch.kra_race_card_pdf_replay import (
    archive_path,
    checked_digest,
    replay_entry_pages,
)
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import encoded, parse_json, sha256

FORMAT = "kra-fixed-pair-prospective-evaluation-v1"
ARMS = {"M0": "M0", "API27": API27_ARM}
STATUSES = ("verified_hit", "verified_miss", "pending_evidence", "undefined_target")
UNVERIFIED = (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError)


def authorities(root, study, receipt, archive, proofs):
    protocol_raw, approval_raw = (
        read(archive / f"{role}-publication" / "published-document.md")
        for role in ("protocol", "approval")
    )
    protocol = contract.canonical(protocol_raw)
    contract.require(
        all(
            sha256(raw) == checked_digest(proof[1])
            for raw, proof in zip((protocol_raw, approval_raw), proofs, strict=True)
        )
        and protocol["study_id"] == study
        and protocol["format_version"] == contract.PROTOCOL
        and encoded(protocol["models"]) == encoded(contract.MODELS)
        and encoded(protocol["policy"]) == encoded(contract.POLICY),
        "fixed_pair_evaluation_authority_conflict",
    )
    verified, binding = contract.source(
        root,
        receipt,
        schedule_sha256=protocol["source"]["schedule_sha256"],
        first_cutoff=protocol["first_block_cutoff"],
        packet_sha256=protocol["source"]["input_packet_sha256"],
        input_pr=protocol["source"]["input_publication"]["pull_number"],
    )
    races = {item["race"]["race_id"]: item for item in verified["bindings"]}
    cutoff = timestamp(verified["first_block_cutoff"])
    slot = protocol["prediction_slot"]
    contract.require(
        sorted(races) == protocol["race_ids"]
        and len(races) == len(verified["bindings"]) == verified["race_count"]
        and verified["race_dates"] == protocol["race_dates"]
        and verified["first_block_cutoff"] == protocol["first_block_cutoff"]
        and binding == protocol["source"]
        and all(day > "20261018" for day in verified["race_dates"])
        and timestamp(binding["input_publication"]["merged_at"])
        <= timestamp(protocol["created_at"])
        < cutoff
        and slot
        == {
            "repository": contract.REPOSITORY,
            "document": contract.path_for(study, "prediction"),
            "pull_number": contract.pull_number(slot["pull_number"]),
        },
        "fixed_pair_evaluation_frozen_scope_conflict",
    )
    checked_digest(protocol["runtime_sha256"])
    review = contract.verify_documents(
        archive,
        study,
        tuple(p[0] for p in proofs),
        protocol_raw,
        approval_raw,
        collect=False,
    )
    return protocol, races, review


def prediction(root, receipt, archive, protocol, review, pair_sha, models, evaluated):
    report = {
        "state": "public_prediction_unverified",
        "pair_sha256": pair_sha,
        "external": None,
        "frozen_model_replay_verified": False,
    }
    if pair_sha is None:
        return report | {"reason": "no_selected_publication_evidence"}, {}
    slot = protocol["prediction_slot"]
    directory = archive / "prediction-publication"
    try:
        raw, external = publication.replay(
            directory, slot["pull_number"], slot["document"], checked_digest(pair_sha)
        )
        merged = base.publication_bound((raw, external), pair_sha, evaluated)
        pull = parse_json(read(directory / "pull.json"))
        contract.require(
            pull.get("user", {}).get("login", "").lower() == contract.OWNER.lower()
            and timestamp(pull["created_at"]) <= timestamp(protocol["created_at"]),
            "fixed_pair_evaluation_public_slot_not_prebound",
        )
    except UNVERIFIED as exc:
        return report | {"reason": type(exc).__name__}, {}
    report["external"] = external
    if merged >= timestamp(protocol["first_block_cutoff"]):
        return report | {"state": "proven_late_in_bound_slot", "reason": None}, {}
    report["state"] = "timely_public_bytes_inference_unverified"
    if models is None:
        return report | {"reason": "no_original_model_artifacts_selected"}, {}
    try:
        contract.require(
            timestamp(review["approval"]["merged_at"]) <= merged,
            "fixed_pair_evaluation_prediction_before_approval",
        )
        _, local_protocol, local_raw, info = forward.verify_local(
            root, protocol["study_id"], receipt, models
        )
        contract.require(
            local_protocol == protocol
            and local_raw == raw
            and info["pair_sha256"] == pair_sha
            and sha256(encoded(protocol)) == parse_json(raw)["protocol_sha256"]
            and timestamp(info["observed_at"]) <= merged,
            "fixed_pair_evaluation_public_local_mismatch",
        )
    except UNVERIFIED as exc:
        return report | {"reason": type(exc).__name__}, {}
    return report | {
        "state": "timely_public_pair_verified",
        "frozen_model_replay_verified": True,
        "reason": None,
    }, {item["race_id"]: item["predictions"] for item in parse_json(raw)["races"]}


def outcome_version(races, protocol, plan_ref):
    if plan_ref is None:
        return {}, {}, [], [], None
    path, pin = plan_ref
    plan = base.pinned(path, checked_digest(pin))
    contract.require(
        plan["race_dates"] == protocol["race_dates"]
        and plan["schedule_sha256"] == protocol["source"]["schedule_sha256"],
        "fixed_pair_evaluation_result_plan_not_original_scope",
    )
    result = results.replay_plan(path, pin)
    contract.require(
        result["observation_policy_sha256"] == base.OUTCOME_POLICY_SHA
        and result["implementation_sha256"] == base.OUTCOME_ADAPTER_SHA
        and results.value_hash(result["observation_source_sha256"])
        == base.OUTCOME_SOURCES_SHA,
        "fixed_pair_evaluation_result_policy_changed",
    )
    items = {item["race_id"]: item for item in result["ledger"]}
    contract.require(
        items.keys() == races.keys()
        and len(items) == len(result["ledger"]) == result["scheduled_race_count"]
        and all(
            item["scheduled_runner_count"] == races[rid]["race"]["runners"]
            for rid, item in items.items()
        ),
        "fixed_pair_evaluation_result_population_changed",
    )
    return (
        items,
        base.result_capture_evidence(plan, result),
        result["extra_api_races"],
        result["extra_official_races"],
        {
            "plan_sha256": pin,
            "seed_sha256": plan["seed_sha256"],
            "official_archive_sha256": plan["official_archive_sha256"],
            "source_implementation_sha256": base.OUTCOME_SOURCES_SHA,
        },
    )


def outcome_evidence(binding, outcome, captures, evaluated):
    if outcome is None:
        return None, [], None
    race = binding["race"]
    records = outcome["api_records"]
    used = [
        captures[key] for key in sorted({r["source_capture_sha256"] for r in records})
    ]
    official = outcome["official_source"]
    times = [timestamp(r["source_available_at"]) for r in records]
    times.extend(timestamp(ref["capture_completed_at"]) for ref in used)
    if official is not None:
        times.append(timestamp(official["capture"]["completed_at"]))
    contract.require(
        all(
            ref["race_date"] == race["race_date"] and ref["meet"] == race["meet"]
            for ref in used
        )
        and all(timestamp(race["scheduled_start_at"]) <= t <= evaluated for t in times),
        "fixed_pair_evaluation_result_identity_or_clock_conflict",
    )
    declared = {
        (r["chul_no"], r["horse_id"]) for r in binding["shared_input"]["feature_rows"]
    }
    recorded = {(r["chul_no"], r["horse_id"]) for r in records}
    web = {
        (r["chul_no"], r["horse_id"])
        for r in (outcome["official_observation"] or {}).get("rows", [])
    }
    roster = {
        "declared_count": len(declared),
        "api_record_count": len(recorded),
        "official_record_count": len(web),
        "declared_not_in_api_result": len(declared - recorded),
        "unexpected_api_or_official_identity": len((recorded | web) - declared),
    }
    if roster["unexpected_api_or_official_identity"]:
        return None, used, roster
    return outcome, used, roster


def context_from_inputs(root, races):
    scopes, context = {}, {}
    for rid, binding in races.items():
        race, ref = binding["race"], binding["entry_manifest"]
        key = ref["path"], ref["sha256"], race["race_date"], race["meet"]
        if key not in scopes:
            raw, _, _ = replay_entry_pages(
                archive_path(ref["path"], archive_root=root),
                archive_root=root,
                meet=race["meet"],
                race_date=race["race_date"],
                expected_sha256=ref["sha256"],
            )
            by_race = defaultdict(list)
            for entry in raw:
                by_race[int(entry["rcNo"])].append(entry)
            scopes[key] = by_race
        entries = scopes[key][race["race_no"]]
        contract.require(
            len(entries) == race["runners"], "fixed_pair_context_roster_changed"
        )
        context[rid] = {
            "physical_meet": race["meet"],
            "distance_m": conditions.unanimous(
                entries, "rcDist", conditions.distance_value
            )["value"],
            "class_text": conditions.unanimous(entries, "rank", conditions.class_value)[
                "value"
            ],
        }
    return context


def score_slot(report, slot, outcome, race, population, evaluated):
    evidence, trio = "pending_evidence", None
    if report["state"] == "proven_late_in_bound_slot":
        evidence = "proven_late"
    elif report["state"] == "timely_public_pair_verified":
        if slot["status"] == "submitted":
            evidence, trio = "published_before_cutoff", slot["horse_ids"]
        else:
            evidence = "published_explicit_non_submission"
    status, _ = base.classify(
        {
            "status": "missing_prediction"
            if evidence in {"proven_late", "published_explicit_non_submission"}
            else evidence,
            "local_combination": trio,
        },
        outcome,
        race,
        evaluated=evaluated,
        population_verified=population,
    )
    return {
        "prediction_evidence": evidence,
        "selected_horse_ids": trio,
        "evaluation_status": status,
    }


def diagnostic(ledger):
    report = {}
    for field in ("distance_m", "class_text", "physical_meet"):
        groups = defaultdict(list)
        for row in ledger:
            value = row["pre_race_context"][field]
            groups["unknown" if value is None else str(value)].append(row)
        report[field] = {
            key: {
                "race_count": len(rows),
                "arm_counts": {
                    arm: count(rows, actual) for arm, actual in ARMS.items()
                },
            }
            for key, rows in sorted(groups.items())
        }
    return report


def count(rows, arm):
    counts = Counter(row[arm]["evaluation_status"] for row in rows)
    return {key: counts[key] for key in STATUSES}


def summarize(races, protocol, report, slots, contexts, plan_ref, evaluated):
    outcomes, captures, extra_api, extra_web, version = outcome_version(
        races, protocol, plan_ref
    )
    population = not (extra_api or extra_web)
    ledger = []
    for rid, binding in sorted(races.items()):
        race = binding["race"]
        raw = outcomes.get(rid)
        outcome, used, roster = outcome_evidence(binding, raw, captures, evaluated)
        state = (
            outcome["status"]
            if outcome
            else ("input_result_roster_conflict" if raw else "source_missing")
        )
        row = {
            "race_id": rid,
            "outcome_status": state,
            "target_defined": True
            if state == "unique_top3_observed"
            else False
            if state == "void_reported_no_top3"
            else None,
            "observed_top3_horse_ids": outcome["observed_top3_horse_ids"]
            if outcome
            else None,
            "result_observation_id": raw["result_observation_id"] if raw else None,
            "result_observation_reasons": raw["reasons"] if raw else [],
            "result_exception_notes": raw["exception_notes"] if raw else {},
            "pre_race_context": contexts[rid],
            "roster_comparison": roster,
            "api_result_captures": used,
            "official_result_evidence": {
                key: raw["official_source"][key] for key in ("receipt", "capture")
            }
            if raw and raw["official_source"]
            else None,
        }
        for arm, actual in ARMS.items():
            row[actual] = score_slot(
                report,
                slots.get(rid, {}).get(arm),
                outcome,
                race,
                population,
                evaluated,
            )
        ledger.append(row)
    metrics = paired.paired_metrics(ledger, population)
    delta = metrics["api27_minus_m0_exact_rate"]
    return {
        "result_version": version,
        "frozen_race_count": len(races),
        "full_population_verified": population,
        "extra_api_result_ids": extra_api,
        "extra_official_result_ids": extra_web,
        "arms": {
            arm: {
                "counts": count(ledger, actual),
                "denominator": metrics["arms"][actual]["denominator"],
                "exact_accuracy": metrics["arms"][actual]["exact_hit_rate"],
            }
            for arm, actual in ARMS.items()
        },
        "fully_paired": metrics["fully_paired"],
        "paired_counts": metrics["paired_counts"],
        "api27_minus_m0_pp": None if delta is None else 100 * delta,
        "descriptive_winner": None
        if delta is None
        else ("API27" if delta > 0 else "M0" if delta < 0 else "tie"),
        "diagnostic_counts_only": diagnostic(ledger),
        "ledger": ledger,
    }


def version_difference(prior, current):
    rows = {row["race_id"]: row for row in current["ledger"]}
    changes, changed_targets, changed_scores = [], [], []
    for old in prior["ledger"]:
        rid = old["race_id"]
        new = rows[rid]
        if old["result_observation_id"] != new["result_observation_id"]:
            changes.append(
                {
                    "race_id": rid,
                    "prior_observation_id": old["result_observation_id"],
                    "new_observation_id": new["result_observation_id"],
                    "prior_status": old["outcome_status"],
                    "new_status": new["outcome_status"],
                    "prior_top3": old["observed_top3_horse_ids"],
                    "new_top3": new["observed_top3_horse_ids"],
                }
            )
        if any(
            old[a]["evaluation_status"] != new[a]["evaluation_status"]
            for a in ARMS.values()
        ):
            changed_scores.append(rid)
        if old["observed_top3_horse_ids"] != new["observed_top3_horse_ids"] or (
            old["target_defined"] != new["target_defined"]
        ):
            changed_targets.append(rid)
    return {
        "prior_result_version": prior["result_version"],
        "prior_arms": prior["arms"],
        "prior_paired_counts": prior["paired_counts"],
        "prior_api27_minus_m0_pp": prior["api27_minus_m0_pp"],
        "prior_descriptive_winner": prior["descriptive_winner"],
        "descriptive_winner_changed": prior["descriptive_winner"]
        != current["descriptive_winner"]
        if prior["fully_paired"] and current["fully_paired"]
        else None,
        "full_comparison_availability_changed": prior["fully_paired"]
        != current["fully_paired"],
        "changed_observations": changes,
        "changed_target_race_ids": changed_targets,
        "changed_evaluation_race_ids": changed_scores,
    }


def evaluate(
    root,
    study,
    receipt,
    archive,
    proofs,
    models,
    *,
    pair_sha=None,
    plan=None,
    prior=None,
):
    evaluated = now()
    protocol, races, review = authorities(root, study, receipt, archive, proofs)
    contract.require(
        all(timestamp(w["retrieved_at"]) <= evaluated for w in review.values()),
        "fixed_pair_evaluation_authority_clock_conflict",
    )
    proof, slots = prediction(
        root, receipt, archive, protocol, review, pair_sha, models, evaluated
    )
    contexts = context_from_inputs(root, races)
    current = summarize(races, protocol, proof, slots, contexts, plan, evaluated)
    old = None
    if prior is not None:
        contract.require(
            plan is not None and prior[1] != plan[1],
            "fixed_pair_evaluation_distinct_result_versions_required",
        )
        old = summarize(races, protocol, proof, slots, contexts, prior, evaluated)
    return {
        "format_version": FORMAT,
        "study_id": study,
        "evaluated_at": evaluated.isoformat(),
        "implementation_sha256": sha256(Path(__file__).read_bytes()),
        "frozen_population_sha256": sha256(encoded(protocol["race_ids"])),
        "first_block_cutoff": protocol["first_block_cutoff"],
        "input_packet_sha256": protocol["source"]["input_packet_sha256"],
        "analysis_protocol": protocol["analysis"],
        "authority": review,
        "prediction": proof,
        "selected_outcome_policy_sha256": base.OUTCOME_POLICY_SHA,
        **current,
        "previous_version_comparison": version_difference(old, current)
        if old
        else None,
        "sample": {
            "blocks": 1,
            "race_days": len(protocol["race_dates"]),
            "venue_days": len(
                {(r["race"]["race_date"], r["race"]["meet"]) for r in races.values()}
            ),
            "confidence_interval": None,
            "uncertainty": "single_block_shared_conditions_descriptive_not_future_generalization",
        },
        "official_finality_verified": False,
        "model_promoted": False,
        "target_reached_beyond_this_block_established": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "study",
        "receipt",
        "receipt-sha256",
        "protocol-sha256",
        "approval-sha256",
    ):
        parser.add_argument("--" + name, required=True)
    for role in ("protocol", "approval"):
        parser.add_argument(f"--{role}-pull", type=int, required=True)
    for name in (
        "m0-model-dir",
        "api27-model-dir",
        "authority-dir",
        "outcome-plan",
        "prior-outcome-plan",
    ):
        parser.add_argument("--" + name, type=Path)
    for name in ("pair-sha256", "outcome-sha256", "prior-outcome-sha256"):
        parser.add_argument("--" + name)
    args = parser.parse_args(argv)
    if (args.m0_model_dir is None) != (args.api27_model_dir is None):
        parser.error("select both original model directories or neither")
    for path, digest in (
        (args.outcome_plan, args.outcome_sha256),
        (args.prior_outcome_plan, args.prior_outcome_sha256),
    ):
        if (path is None) != (digest is None):
            parser.error("select each result plan together with its exact SHA-256")
    root = Path.cwd()
    report = evaluate(
        root,
        args.study,
        {"path": args.receipt, "sha256": args.receipt_sha256},
        args.authority_dir or forward.ledger_for(root, args.study),
        (
            (args.protocol_pull, args.protocol_sha256),
            (args.approval_pull, args.approval_sha256),
        ),
        {"M0": args.m0_model_dir, "API27": args.api27_model_dir}
        if args.m0_model_dir is not None
        else None,
        pair_sha=args.pair_sha256,
        plan=(args.outcome_plan, args.outcome_sha256) if args.outcome_plan else None,
        prior=(args.prior_outcome_plan, args.prior_outcome_sha256)
        if args.prior_outcome_plan
        else None,
    )
    sys.stdout.buffer.write(encoded(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
