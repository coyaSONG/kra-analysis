"""Read-only whole-block comparison of frozen M0 packets and versioned results."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import httpx

from autoresearch import local_m0_forward as forward
from autoresearch import local_m0_inference as inference
from autoresearch.observed_history_seed import digest, pinned_path, save
from autoresearch.prerace_hash_witness import collect_publication, timestamp
from autoresearch.versioned_result_observations import replay_plan, value_hash

CONTRACT_SHA = "ffd068ed7c507e2cf0bef63ed2dcbebf01fdcdd0e38d89c849d03d60c448f59c"
OUTCOME_POLICY_SHA = "389f4cffa53f5e7172383aa9e452fd53cf8afeb6091a4728379cb8b2e8a3bd28"
OUTCOME_ADAPTER_SHA = "93b4a40c6788f3441dacc342bfc23d902104af6c80c096d811f98ad8a84a8b02"
OUTCOME_SOURCES_SHA = "2d9f1a7aeb847048c371408aad35ac52b170526a0871acaec21fcba538d1bb3c"
FORMAT = "kra-local-m0-evaluation-v1"


def pinned(path, expected):
    raw = inference.read_bytes(path, limit=inference.MAX_MANIFEST_BYTES)
    if digest(raw) != expected:
        raise ValueError("evaluation_artifact_pin_mismatch")
    return inference.parse_json(raw)


def observation(path, expected, packet_sha, created, cutoff, evaluated):
    value = pinned(path, expected)
    observed = timestamp(value["observed_at"])
    if value["packet_sha256"] != packet_sha or not created <= observed <= evaluated:
        raise ValueError("evaluation_readback_conflict")
    return {**value, "locally_timely": observed < cutoff}


def result_capture_evidence(plan, outcome_report):
    """Combined availability may be later than the API214 response itself."""
    needed = {
        record["source_capture_sha256"]
        for row in outcome_report["ledger"]
        for record in row["api_records"]
    }
    selected = pinned(Path(plan["seed_path"]), plan["seed_sha256"])
    root = Path(plan["seed_root"])
    captures = {}
    for unit in selected["inventory"]:
        ref = unit.get("result")
        if ref is None or ref["sha256"] not in needed:
            continue
        manifest = pinned(pinned_path(root, ref), ref["sha256"])
        if ref["sha256"] in captures:
            raise ValueError("evaluation_duplicate_result_capture")
        captures[ref["sha256"]] = {
            "manifest": ref,
            "race_date": manifest["race_date"],
            "meet": manifest["meet"],
            "capture_completed_at": manifest["capture_completed_at"],
        }
    if set(captures) != needed:
        raise ValueError("evaluation_result_capture_not_in_selected_inventory")
    return captures


def publication_bound(publication, commitment_sha, evaluated):
    if publication is None:
        return None
    raw, witness = publication
    if digest(raw) != commitment_sha or witness["document_sha256"] != commitment_sha:
        raise ValueError("evaluation_publication_not_selected_commitment")
    merged, retrieved = (
        timestamp(witness["merged_at"]),
        timestamp(witness["retrieved_at"]),
    )
    if not merged <= retrieved <= evaluated:
        raise ValueError("evaluation_publication_clock_conflict")
    return merged


def read_prediction(
    root, day, race, slot, study_sha, model, receipt, evaluated, published
):
    packet_path = day / f"prediction_{race['race_id']}.json"
    result = {"status": "pending_evidence", "local_combination": None}
    if "packet_sha256" not in slot:
        result["status"] = (
            "not_bound_by_commitment" if packet_path.exists() else "missing_prediction"
        )
        return result
    try:
        pinned(packet_path, slot["packet_sha256"])
        packet = forward.recover_packet(
            packet_path, race, model, receipt, root, study_sha
        )
        if digest(forward.encoded(packet)) != slot["packet_sha256"]:
            raise ValueError("evaluation_packet_changed_during_replay")
        result["local_combination"] = packet["prediction"]["horse_ids"]
        result["packet_sha256"] = slot["packet_sha256"]
        if "observation_sha256" not in slot:
            result["reason"] = "readback_not_bound_by_commitment"
            return result
        observed = observation(
            day / f"observation_{race['race_id']}.json",
            slot["observation_sha256"],
            slot["packet_sha256"],
            timestamp(packet["computed_at"]),
            timestamp(race["feature_cutoff_at"]),
            evaluated,
        )
        result["local_observation"] = observed
        if not observed["locally_timely"]:
            result["reason"] = "local_persistence_timeliness_unproven"
            return result
        if published is not None and timestamp(
            observed["observed_at"]
        ) <= published < timestamp(race["feature_cutoff_at"]):
            result["status"] = "published_before_cutoff"
        else:
            result.update(
                status="locally_timely_only",
                reason="independent_pre_cutoff_existence_unproven",
            )
    except (ValueError, KeyError, TypeError, OSError) as exc:
        result.update(status="invalid_or_unavailable_packet", reason=type(exc).__name__)
        if isinstance(exc, ValueError):
            result["reason"] = str(exc)
    return result


def aggregate(ledger, *, full_population_verified):
    counts = dict(Counter(row["evaluation_status"] for row in ledger))
    if set(counts) - {
        "verified_hit",
        "verified_miss",
        "pending_evidence",
        "undefined_target",
    }:
        raise ValueError("evaluation_unknown_status")
    n = len(ledger) if full_population_verified else None
    h, f, q, d = (
        counts.get(k, 0)
        for k in (
            "verified_hit",
            "verified_miss",
            "pending_evidence",
            "undefined_target",
        )
    )
    binary_defined = bool(ledger) and all(
        row["target_defined"] is True for row in ledger
    )
    complete = n is not None and n > 0 and q == d == 0 and binary_defined
    return {
        "denominator": n,
        "known_ledger_races": len(ledger),
        "counts": counts,
        "verified_hit_share_full_universe": h / n if n else None,
        "exact_hit_rate": h / n if complete else None,
        "evidence_identification_bounds": [h / n, (h + q) / n]
        if n and binary_defined
        else None,
        "bounds_kind": "missing_binary_evidence_not_confidence_interval"
        if n and binary_defined
        else None,
        "fully_evaluated": complete,
        "counts_as_70_percent_evidence": complete,
        "target_reached_in_selected_observation": complete and h / n >= 0.7,
        "defined_binary_races": sum(row["target_defined"] is True for row in ledger),
        "target_definition_unknown_count": sum(
            row["target_defined"] is None for row in ledger
        ),
        "undefined_target_count": d,
    }


def classify(prediction, outcome, race, *, evaluated, population_verified):
    diagnostic = None
    if (
        outcome
        and outcome["status"] == "unique_top3_observed"
        and prediction["local_combination"]
    ):
        diagnostic = (
            prediction["local_combination"] == outcome["observed_top3_horse_ids"]
        )
    if outcome and outcome["status"] == "void_reported_no_top3":
        return "undefined_target", diagnostic
    if not outcome or outcome["status"] != "unique_top3_observed":
        return "pending_evidence", diagnostic
    if not population_verified:
        return "pending_evidence", diagnostic
    if prediction["status"] == "published_before_cutoff":
        return "verified_hit" if diagnostic else "verified_miss", diagnostic
    if prediction["status"] == "missing_prediction" and evaluated >= timestamp(
        race["feature_cutoff_at"]
    ):
        return "verified_miss", diagnostic
    return "pending_evidence", diagnostic


def evaluate(
    root,
    model_dir,
    commitment_path,
    commitment_sha,
    *,
    outcome_plan=None,
    outcome_sha=None,
    publication=None,
    evaluated_at=None,
):
    """publication must come from collect_publication, never an approval flag."""
    evaluated = evaluated_at or datetime.now(UTC)
    evaluated = timestamp(evaluated.isoformat())
    root = root.resolve()
    if root.name != inference.SERIES:
        raise ValueError("evaluation_requires_canonical_series")
    original = pinned(root / "contract.json", CONTRACT_SHA)
    if original != forward.contract():
        raise ValueError("evaluation_inference_contract_changed")
    commitment = pinned(commitment_path, commitment_sha)
    if (
        commitment.get("format_version") != "kra-local-m0-commitment-v1"
        or commitment["series"] != inference.SERIES
        or commitment["contract_sha256"] != CONTRACT_SHA
        or commitment["model_sha256"] != inference.MODEL_SHA
        or [d["race_date"] for d in commitment["days"]] != list(inference.DATES)
    ):
        raise ValueError("evaluation_commitment_contract_conflict")
    if (outcome_plan is None) != (outcome_sha is None):
        raise ValueError("evaluation_outcome_plan_and_pin_required_together")
    outcomes = {}
    api_captures = {}
    outcome_report = None
    if outcome_plan is not None:
        plan = pinned(outcome_plan, outcome_sha)
        if plan["race_dates"] != list(inference.DATES):
            raise ValueError("evaluation_historical_or_wrong_outcome_dates")
        outcome_report = replay_plan(outcome_plan, outcome_sha)
        if (
            outcome_report["observation_policy_sha256"] != OUTCOME_POLICY_SHA
            or outcome_report["implementation_sha256"] != OUTCOME_ADAPTER_SHA
        ):
            raise ValueError("evaluation_outcome_policy_changed")
        if (
            value_hash(outcome_report["observation_source_sha256"])
            != OUTCOME_SOURCES_SHA
        ):
            raise ValueError("evaluation_outcome_implementation_changed")
        api_captures = result_capture_evidence(plan, outcome_report)
        outcomes = {r["race_id"]: r for r in outcome_report["ledger"]}
        if len(outcomes) != len(outcome_report["ledger"]):
            raise ValueError("evaluation_duplicate_outcome_race")
    model, receipt = inference.load_model(model_dir)
    published = publication_bound(publication, commitment_sha, evaluated)
    days, races, observations = [], [], []
    for selected in commitment["days"]:
        date = selected["race_date"]
        directory = root / date
        if "study_sha256" not in selected:
            days.append(
                {
                    "race_date": date,
                    "status": "population_not_bound",
                    "race_count": None,
                }
            )
            continue
        study = pinned(directory / "study.json", selected["study_sha256"])
        forward.verify_study(study, CONTRACT_SHA)
        if study["universe"]["race_date"] != date:
            raise ValueError("evaluation_study_date_conflict")
        members = study["universe"]["races"]
        ids = [r["race_id"] for r in members]
        slots = {r["race_id"]: r for r in selected["races"]}
        if (
            len(set(ids)) != len(ids)
            or len(slots) != len(selected["races"])
            or set(slots) != set(ids)
            or selected["race_count"] != len(ids)
        ):
            raise ValueError("evaluation_commitment_population_conflict")
        observed = observation(
            directory / "study_observation.json",
            selected["study_observation_sha256"],
            selected["study_sha256"],
            timestamp(study["created_at"]),
            min(timestamp(r["feature_cutoff_at"]) for r in members),
            evaluated,
        )
        observations.append(observed)
        days.append(
            {
                "race_date": date,
                "status": "population_replayed",
                "race_count": len(ids),
                "study_sha256": selected["study_sha256"],
            }
        )
        for race in members:
            if timestamp(receipt["completed_at"]) >= timestamp(
                race["feature_cutoff_at"]
            ):
                raise ValueError("evaluation_model_fitted_after_target")
            prediction = read_prediction(
                root,
                directory,
                race,
                slots[race["race_id"]],
                selected["study_sha256"],
                model,
                receipt,
                evaluated,
                published,
            )
            races.append((race, prediction))
    local_whole = len(observations) == len(inference.DATES) and bool(races)
    if local_whole:
        first_cutoff = min(timestamp(r["feature_cutoff_at"]) for r, _ in races)
        local_whole = (
            max(timestamp(r["observed_at"]) for r in observations) < first_cutoff
        )
    expected_membership = (
        "locally_frozen_before_first_block_cutoff"
        if local_whole
        else "complete_block_freeze_not_proven"
    )
    if commitment["block_membership_status"] != expected_membership:
        raise ValueError("evaluation_commitment_block_status_conflict")
    population_verified = bool(
        local_whole
        and published is not None
        and max(timestamp(r["observed_at"]) for r in observations)
        <= published
        < first_cutoff
    )
    ledger = []
    for race, prediction in races:
        outcome = outcomes.get(race["race_id"])
        capture_evidence = []
        if outcome and outcome["official_source"]:
            capture_evidence = [
                api_captures[key]
                for key in sorted(
                    {r["source_capture_sha256"] for r in outcome["api_records"]}
                )
            ]
            if any(
                c["race_date"] != race["race_date"] or c["meet"] != race["meet"]
                for c in capture_evidence
            ):
                raise ValueError("evaluation_result_capture_identity_conflict")
            times = [
                timestamp(r["source_available_at"]) for r in outcome["api_records"]
            ]
            times.extend(timestamp(c["capture_completed_at"]) for c in capture_evidence)
            times.append(
                timestamp(outcome["official_source"]["capture"]["completed_at"])
            )
            if not all(
                timestamp(race["scheduled_start_at"]) <= t <= evaluated for t in times
            ):
                raise ValueError("evaluation_outcome_capture_time_conflict")
        status, diagnostic = classify(
            prediction,
            outcome,
            race,
            evaluated=evaluated,
            population_verified=population_verified,
        )
        ledger.append(
            {
                "race_id": race["race_id"],
                "prediction": prediction,
                "outcome": outcome,
                "api214_capture_evidence": capture_evidence,
                "evaluation_status": status,
                "local_combination_match_diagnostic": diagnostic,
                "target_defined": True
                if outcome and outcome["status"] == "unique_top3_observed"
                else False
                if outcome and outcome["status"] == "void_reported_no_top3"
                else None,
            }
        )
    extra = sorted(set(outcomes) - {r["race_id"] for r, _ in races})
    issues = []
    if not local_whole:
        issues.append("complete_block_not_locally_frozen_before_first_cutoff")
    if not population_verified:
        issues.append("complete_block_pre_cutoff_publication_unproven")
    if outcome_report and (
        extra
        or outcome_report["extra_api_races"]
        or outcome_report["extra_official_races"]
    ):
        issues.append("extra_result_races_require_population_reconciliation")
        population_verified = False
        for row in ledger:
            if row["evaluation_status"] in ("verified_hit", "verified_miss"):
                row["evaluation_status"] = "pending_evidence"
    return {
        "format_version": FORMAT,
        "series": inference.SERIES,
        "contract_sha256": CONTRACT_SHA,
        "commitment_sha256": commitment_sha,
        "evaluated_at": evaluated.isoformat(),
        "outcome_plan_sha256": outcome_sha,
        "outcome_implementation": outcome_report["observation_source_sha256"]
        if outcome_report
        else None,
        "publication": publication[1] if publication else None,
        "local_whole_block_replayed": bool(local_whole),
        "full_population_verified": population_verified,
        "days": days,
        "ledger": ledger,
        "extra_outcome_races": extra,
        "extra_api_result_races": outcome_report["extra_api_races"]
        if outcome_report
        else [],
        "extra_official_result_races": outcome_report["extra_official_races"]
        if outcome_report
        else [],
        "population_verification_issues": issues,
        "metrics": aggregate(ledger, full_population_verified=population_verified),
        "official_finality_verified": False,
        "trust_basis": "live_github_hash_existence_bound_and_selected_official_result_versions",
        "implementation_sha256": digest(Path(__file__).read_bytes()),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--commitment", type=Path, required=True)
    parser.add_argument("--commitment-sha256", required=True)
    parser.add_argument("--outcome-plan", type=Path)
    parser.add_argument("--outcome-plan-sha256")
    parser.add_argument("--publication-pr", type=int)
    parser.add_argument("--publication-document")
    parser.add_argument("--witness-directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.resolve().is_relative_to(args.root.resolve()) or (
        args.witness_directory
        and args.witness_directory.resolve().is_relative_to(args.root.resolve())
    ):
        parser.error("evaluation outputs must be outside the canonical archive")
    publication = None
    options = (args.publication_pr, args.publication_document, args.witness_directory)
    if any(v is not None for v in options):
        if any(v is None for v in options):
            parser.error("publication requires PR, document and new witness directory")
        args.witness_directory.mkdir(parents=True, exist_ok=False)
        with httpx.Client(timeout=30, follow_redirects=False) as client:
            publication = collect_publication(
                args.witness_directory,
                number=args.publication_pr,
                document=args.publication_document,
                client=client,
            )
    result = evaluate(
        args.root,
        args.model_dir,
        args.commitment,
        args.commitment_sha256,
        outcome_plan=args.outcome_plan,
        outcome_sha=args.outcome_plan_sha256,
        publication=publication,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report_sha = save(args.output, result)
    print(
        json.dumps(
            {k: v for k, v in result.items() if k != "ledger"}
            | {"report_sha256": report_sha},
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["metrics"]["fully_evaluated"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
