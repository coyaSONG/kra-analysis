"""Fixed API27 companion using the original M0 intake, never a new collector."""

from __future__ import annotations

import argparse
from pathlib import Path
from uuid import uuid4

from autoresearch import local_m0_evaluation as base
from autoresearch import local_m0_forward as parent
from autoresearch import local_m0_inference as inference
from autoresearch.observed_history_seed import digest, exclusive, save
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import ROOT, encoded

SERIES = "api27_shared_20261016_18_v1"
ARM = "API27_fixed_v1"
MODEL_SHA = "5f33dfd1e45c493fc5edfd90a8250ac5e91bb841b29124e5988b657994dc17b4"
RECEIPT_SHA = "b91d7b85cef9038a742f2a68a616cc56c627793d5efa4046c21178d00a6833ea"
REHEARSAL_SHA = "619dfb72764a8ddb467047e3fd687b86f53cbb2d91d1c567d83ff2ed92985922"


def load_model(directory):
    model = base.pinned(directory / "model.json", MODEL_SHA)
    receipt = base.pinned(directory / "receipt.json", RECEIPT_SHA)
    if (
        model["format_version"] != "kra-api27-research-model-v1"
        or model["arm"] != ARM
        or receipt["status"] != "completed"
        or receipt["arm"] != ARM
        or receipt["artifacts"]["model.json"] != MODEL_SHA
        or model["estimator"]["recipe"] != receipt["recipe"]
        or model["estimator"]["columns"] != list(inference.API_COLUMNS)
        or any(
            r[:8] >= min(inference.DATES)
            for r in model["estimator"]["training_race_ids"]
        )
    ):
        raise ValueError("api27_forward_model_contract_conflict")
    for name in ("corpus", "review", "implementation"):
        expected = model[f"{name}_sha256"]
        if receipt["artifacts"][f"{name}.json"] != expected:
            raise ValueError("api27_forward_provenance_conflict")
        base.pinned(directory / f"{name}.json", expected)
    timestamp(receipt["completed_at"])
    return model["estimator"], receipt


def contract():
    sources = {}
    for name in ("api27_forward.py", "api27_evaluation.py", "local_m0_evaluation.py"):
        sources[name] = digest(
            (ROOT / "packages/scripts/autoresearch" / name).read_bytes()
        )
    return {
        "format_version": "kra-api27-forward-contract-v1",
        "series": SERIES,
        "parent_series": inference.SERIES,
        "parent_contract_sha256": base.CONTRACT_SHA,
        "parent_contract": parent.contract(),
        "race_dates": list(inference.DATES),
        "arm": ARM,
        "model_sha256": MODEL_SHA,
        "fit_receipt_sha256": RECEIPT_SHA,
        "sources": sources,
        "input_policy": "original_m0_reserved_api26_or_same_packet_source_no_new_capture",
        "m0_scoring_success_required": False,
        "population": "same_complete_national_three_day_block_not_success_subset",
        "selection": "first_single_unordered_three_no_fallback_no_overwrite",
        "publication": "exact_paired_commitments_before_first_block_cutoff",
        "comparison": "separate_full_population_arms_no_or_no_automatic_promotion",
        "trust": "cooperative_owner_canonical_files_local_clock_and_github_hash_bound",
        "model_promoted": False,
        "counts_as_70_percent_evidence": False,
    }


def context(root, model_dir, commitment_path, commitment_sha, *, evaluated_at=None):
    evaluated = evaluated_at or parent.now()
    report = base.evaluate(
        root, model_dir, commitment_path, commitment_sha, evaluated_at=evaluated
    )
    commitment = base.pinned(commitment_path, commitment_sha)
    days = []
    for selected in commitment["days"]:
        day = {"selected": selected, "races": []}
        if "study_sha256" in selected:
            directory = root / selected["race_date"]
            study = base.pinned(directory / "study.json", selected["study_sha256"])
            day["races"] = study["universe"]["races"]
            day["observation"] = base.observation(
                directory / "study_observation.json",
                selected["study_observation_sha256"],
                selected["study_sha256"],
                timestamp(study["created_at"]),
                min(timestamp(r["feature_cutoff_at"]) for r in day["races"]),
                evaluated,
            )
        days.append(day)
    return report, days


def shared_source(root, race, study_sha):
    directory = root / race["race_date"]
    reserved = directory / f"input_{race['race_id']}.json"
    packet = directory / f"prediction_{race['race_id']}.json"
    ref = parent.read(reserved) if reserved.exists() else None
    if packet.exists():
        original = parent.read(packet)
        source = original["prediction"]["source"]
        other = {
            "study_sha256": original["study_sha256"],
            "manifest_path": source["manifest_path"],
            "manifest_sha256": source["manifest_sha256"],
        }
        if ref is not None and ref != other:
            raise ValueError("api27_shared_source_references_disagree")
        ref = other
    if ref is None:
        raise ValueError("api27_shared_source_missing")
    if ref["study_sha256"] != study_sha:
        raise ValueError("api27_shared_source_wrong_study")
    projected = inference.project_capture(
        race,
        Path(ref["manifest_path"]),
        root,
        expected_sha256=ref["manifest_sha256"],
    )
    return ref, projected


def packet_for(race, projected, reference, model, study_sha, contract_sha, completed):
    return {
        "format_version": "kra-api27-forward-packet-v1",
        "series": SERIES,
        "arm": ARM,
        "model_sha256": MODEL_SHA,
        "fit_receipt_sha256": RECEIPT_SHA,
        "contract_sha256": contract_sha,
        "study_sha256": study_sha,
        "input_reference": reference,
        "feature_cutoff_at": race["feature_cutoff_at"],
        "computed_at": completed.isoformat(),
        "prediction": inference.score_capture(model, projected),
        "counts_as_70_percent_evidence": False,
    }


def check_times(race, projected, receipt, completed, observed_now):
    inference.check_prospective_times(race, projected, receipt, completed)
    if not timestamp(receipt["completed_at"]) <= completed <= observed_now:
        raise ValueError("api27_fit_computation_clock_conflict")


def recover(path, root, race, model, receipt, study_sha, contract_sha, evaluated):
    packet = parent.read(path)
    reference, projected = shared_source(root, race, study_sha)
    completed = timestamp(packet["computed_at"])
    check_times(race, projected, receipt, completed, evaluated)
    if packet != packet_for(
        race, projected, reference, model, study_sha, contract_sha, completed
    ):
        raise ValueError("api27_saved_packet_conflict")
    return packet


def run(root, parent_root, m0_dir, model_dir, commitment_path, commitment_sha):
    root = root.resolve() / SERIES
    parent_root = parent_root.resolve()
    for source in (parent_root, m0_dir.resolve(), model_dir.resolve()):
        if root.is_relative_to(source) or source.is_relative_to(root):
            raise ValueError("api27_output_overlaps_source")
    root.mkdir(parents=True, exist_ok=True)
    with exclusive(root):
        model, receipt = load_model(model_dir)
        current = contract()
        contract_sha = digest(encoded(current))
        contract_path = root / "contract.json"
        if contract_path.exists():
            if parent.read(contract_path) != current:
                raise ValueError("api27_forward_contract_changed")
        else:
            save(contract_path, current)
        original, contexts = context(
            parent_root, m0_dir, commitment_path, commitment_sha
        )
        days = []
        for ctx in contexts:
            selected = ctx["selected"]
            date = selected["race_date"]
            directory = root / date
            directory.mkdir(exist_ok=True)
            binding = directory / "study_ref.json"
            day = {"race_date": date, "race_count": selected["race_count"], "races": []}
            days.append(day)
            if not ctx["races"]:
                if binding.exists():
                    raise ValueError("api27_parent_commitment_regresses_population")
                day["status"] = "population_not_bound"
                continue
            ref = {k: selected[k] for k in ("study_sha256", "study_observation_sha256")}
            if binding.exists():
                if parent.read(binding) != ref:
                    raise ValueError("api27_parent_study_changed")
            else:
                save(binding, ref)
            day.update(ref)
            for race in ctx["races"]:
                path = directory / f"prediction_{race['race_id']}.json"
                observation = directory / f"observation_{race['race_id']}.json"
                slot = {"race_id": race["race_id"], "status": "missing_prediction"}
                day["races"].append(slot)
                try:
                    if not ctx["observation"]["locally_timely"]:
                        raise ValueError("api27_parent_population_late")
                    if not path.exists():
                        if parent.now() >= timestamp(race["feature_cutoff_at"]):
                            raise ValueError("api27_deadline_passed")
                        reference, projected = shared_source(
                            parent_root, race, selected["study_sha256"]
                        )
                        packet = packet_for(
                            race,
                            projected,
                            reference,
                            model,
                            selected["study_sha256"],
                            contract_sha,
                            parent.now(),
                        )
                        completed = parent.now()
                        check_times(race, projected, receipt, completed, completed)
                        packet["computed_at"] = completed.isoformat()
                        save(path, packet)
                    recover(
                        path,
                        parent_root,
                        race,
                        model,
                        receipt,
                        selected["study_sha256"],
                        contract_sha,
                        parent.now(),
                    )
                    observed = parent.observe_packet(
                        path, observation, race["feature_cutoff_at"]
                    )
                    slot.update(status=observed["status"])
                except (ValueError, OSError, KeyError, TypeError) as exc:
                    slot.update(
                        status="unavailable_or_invalid",
                        reason=str(exc)
                        if isinstance(exc, ValueError)
                        else type(exc).__name__,
                    )
                for name, file in (("packet", path), ("observation", observation)):
                    if file.exists():
                        slot[f"{name}_sha256"] = digest(file.read_bytes())
            day["status"] = (
                "locally_complete"
                if all(
                    r["status"] == "locally_observed_before_cutoff"
                    for r in day["races"]
                )
                else "incomplete"
            )
        if current != contract():
            raise ValueError("api27_implementation_changed_during_run")
        commitment = {
            "format_version": "kra-api27-commitment-v1",
            "series": SERIES,
            "contract_sha256": contract_sha,
            "model_sha256": MODEL_SHA,
            "parent_commitment_sha256": commitment_sha,
            "local_whole_block_replayed": original["local_whole_block_replayed"],
            "days": days,
            "counts_as_70_percent_evidence": False,
            "external_publication_verified": False,
        }
        attempt = parent.now().strftime("%Y%m%dT%H%M%S.%fZ") + "_" + uuid4().hex[:12]
        path = root / f"commitment_{attempt}.json"
        sha = save(path, commitment)
        return {"commitment_path": str(path), "commitment_sha256": sha, **commitment}


def rehearse(plan, m0_dir, model_dir):
    original = parent.rehearse(plan, REHEARSAL_SHA, m0_dir)
    model, _ = load_model(model_dir)
    for rows in [original["inventory"], *(d["ledger"] for d in original["days"])]:
        for row in rows:
            if "prediction" in row:
                projected = {
                    k: row["prediction"][k]
                    for k in ("race_id", "feature_rows", "source")
                }
                row["api27_prediction"] = inference.score_capture(model, projected)
    return {
        **original,
        "format_version": "kra-api27-paired-rehearsal-v1",
        "api27_model_sha256": MODEL_SHA,
        "performance": None,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("run", "rehearse"))
    for name in ("m0-model-dir", "api27-model-dir", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--parent-root", type=Path)
    parser.add_argument("--parent-commitment", type=Path)
    parser.add_argument("--parent-commitment-sha256")
    parser.add_argument("--plan", type=Path)
    args = parser.parse_args(argv)
    if args.command == "rehearse":
        if args.plan is None:
            parser.error("rehearse requires --plan")
        plan = base.pinned(args.plan, REHEARSAL_SHA)
        sources = [
            args.m0_model_dir,
            args.api27_model_dir,
            Path(plan["entry_archive_root"]),
            *(Path(c["path"]).parent for c in plan["schedule_captures"]),
        ]
        for source in sources:
            if args.output.resolve().is_relative_to(
                source.resolve()
            ) or source.resolve().is_relative_to(args.output.resolve()):
                parser.error("rehearsal output must not overlap sources")
        result = rehearse(args.plan, args.m0_model_dir, args.api27_model_dir)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        print({"output": str(args.output), "sha256": save(args.output, result)})
        return 0
    if not all(
        (args.parent_root, args.parent_commitment, args.parent_commitment_sha256)
    ):
        parser.error("run requires parent root and exact commitment path/hash")
    result = run(
        args.output,
        args.parent_root,
        args.m0_model_dir,
        args.api27_model_dir,
        args.parent_commitment,
        args.parent_commitment_sha256,
    )
    print(encoded(result).decode())
    return 0 if all(d["status"] == "locally_complete" for d in result["days"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
