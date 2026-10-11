"""Read-only paired operational evaluation on the unchanged whole M0 universe."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import httpx

from autoresearch import api27_forward as companion
from autoresearch import local_m0_evaluation as base
from autoresearch import local_m0_forward as parent
from autoresearch import local_m0_inference as inference
from autoresearch.observed_history_seed import digest, save
from autoresearch.prerace_hash_witness import collect_publication, timestamp
from autoresearch.restricted_cohort import encoded


def read_prediction(
    root,
    parent_root,
    race,
    slot,
    model,
    receipt,
    study_sha,
    contract_sha,
    evaluated,
    published,
):
    directory = root / race["race_date"]
    path = directory / f"prediction_{race['race_id']}.json"
    result = {"status": "pending_evidence", "local_combination": None}
    if "packet_sha256" not in slot:
        result["status"] = (
            "not_bound_by_commitment" if path.exists() else "missing_prediction"
        )
        return result
    try:
        base.pinned(path, slot["packet_sha256"])
        packet = companion.recover(
            path, parent_root, race, model, receipt, study_sha, contract_sha, evaluated
        )
        if digest(encoded(packet)) != slot["packet_sha256"]:
            raise ValueError("api27_packet_changed_during_replay")
        result.update(
            local_combination=packet["prediction"]["horse_ids"],
            packet_sha256=slot["packet_sha256"],
        )
        if "observation_sha256" not in slot:
            result["reason"] = "readback_not_bound_by_commitment"
            return result
        observed = base.observation(
            directory / f"observation_{race['race_id']}.json",
            slot["observation_sha256"],
            slot["packet_sha256"],
            timestamp(packet["computed_at"]),
            timestamp(race["feature_cutoff_at"]),
            evaluated,
        )
        result["local_observation"] = observed
        if (
            observed["locally_timely"]
            and published is not None
            and timestamp(observed["observed_at"])
            <= published
            < timestamp(race["feature_cutoff_at"])
        ):
            result["status"] = "published_before_cutoff"
        else:
            result["reason"] = "timely_independent_publication_unproven"
    except (ValueError, OSError, KeyError, TypeError) as exc:
        result.update(
            status="invalid_or_unavailable_packet",
            reason=str(exc) if isinstance(exc, ValueError) else type(exc).__name__,
        )
    return result


def paired_metrics(ledger, population_verified):
    arms = {
        arm: base.aggregate(
            [
                {
                    "evaluation_status": row[arm]["evaluation_status"],
                    "target_defined": row["target_defined"],
                }
                for row in ledger
            ],
            full_population_verified=population_verified,
        )
        for arm in ("M0", companion.ARM)
    }
    complete = all(m["fully_evaluated"] for m in arms.values())
    paired = None
    delta = None
    if complete:
        counts = Counter()
        for row in ledger:
            a = row["M0"]["evaluation_status"] == "verified_hit"
            b = row[companion.ARM]["evaluation_status"] == "verified_hit"
            counts[
                "both"
                if a and b
                else "M0_only"
                if a
                else "API27_only"
                if b
                else "neither"
            ] += 1
        paired = {k: counts[k] for k in ("both", "M0_only", "API27_only", "neither")}
        delta = (paired["API27_only"] - paired["M0_only"]) / len(ledger)
    return {
        "arms": arms,
        "fully_paired": complete,
        "paired_counts": paired,
        "api27_minus_m0_exact_rate": delta,
        "estimand": "whole_universe_operational_success_with_shared_original_intake",
        "independent_acquisition_comparison": False,
        "model_promoted": False,
    }


def evaluate(
    root,
    parent_root,
    m0_dir,
    model_dir,
    parent_commitment,
    parent_sha,
    commitment_path,
    commitment_sha,
    *,
    outcome_plan=None,
    outcome_sha=None,
    m0_publication=None,
    publication=None,
    evaluated_at=None,
):
    evaluated = evaluated_at or parent.now()
    root, parent_root = root.resolve(), parent_root.resolve()
    if root.name != companion.SERIES:
        raise ValueError("api27_requires_canonical_series")
    current = companion.contract()
    contract_sha = digest(encoded(current))
    if base.pinned(root / "contract.json", contract_sha) != current:
        raise ValueError("api27_contract_conflict")
    selected = base.pinned(commitment_path, commitment_sha)
    if (
        selected["format_version"] != "kra-api27-commitment-v1"
        or selected["series"] != companion.SERIES
        or selected["contract_sha256"] != contract_sha
        or selected["model_sha256"] != companion.MODEL_SHA
        or selected["parent_commitment_sha256"] != parent_sha
        or [d["race_date"] for d in selected["days"]] != list(inference.DATES)
    ):
        raise ValueError("api27_commitment_contract_conflict")
    original = base.evaluate(
        parent_root,
        m0_dir,
        parent_commitment,
        parent_sha,
        outcome_plan=outcome_plan,
        outcome_sha=outcome_sha,
        publication=m0_publication,
        evaluated_at=evaluated,
    )
    _, contexts = companion.context(
        parent_root, m0_dir, parent_commitment, parent_sha, evaluated_at=evaluated
    )
    model, receipt = companion.load_model(model_dir)
    published = base.publication_bound(publication, commitment_sha, evaluated)
    if selected["local_whole_block_replayed"] != original["local_whole_block_replayed"]:
        raise ValueError("api27_block_status_conflict")
    races = []
    for day, ctx in zip(selected["days"], contexts, strict=True):
        ancestor = ctx["selected"]
        if day["race_count"] != ancestor["race_count"]:
            raise ValueError("api27_population_count_conflict")
        if not ctx["races"]:
            if day["races"] or "study_sha256" in day:
                raise ValueError("api27_unbound_population_claim")
            continue
        if any(
            day[k] != ancestor[k] for k in ("study_sha256", "study_observation_sha256")
        ):
            raise ValueError("api27_parent_study_conflict")
        slots = {r["race_id"]: r for r in day["races"]}
        if len(slots) != len(day["races"]) or set(slots) != {
            r["race_id"] for r in ctx["races"]
        }:
            raise ValueError("api27_full_membership_conflict")
        for race in ctx["races"]:
            if timestamp(receipt["completed_at"]) >= timestamp(
                race["feature_cutoff_at"]
            ):
                raise ValueError("api27_fitted_after_target")
            races.append((race, slots[race["race_id"]], day["study_sha256"]))
    whole = original["full_population_verified"]
    timely_companion_publication = bool(
        whole
        and races
        and published is not None
        and max(timestamp(c["observation"]["observed_at"]) for c in contexts)
        <= published
        < min(timestamp(r["feature_cutoff_at"]) for r, _, _ in races)
    )
    originals = {r["race_id"]: r for r in original["ledger"]}
    if set(originals) != {r["race_id"] for r, _, _ in races}:
        raise ValueError("api27_parent_evaluation_membership_conflict")
    ledger = []
    for race, slot, study_sha in races:
        m0 = originals[race["race_id"]]
        prediction = read_prediction(
            root,
            parent_root,
            race,
            slot,
            model,
            receipt,
            study_sha,
            contract_sha,
            evaluated,
            published if timely_companion_publication else None,
        )
        row = {
            "race_id": race["race_id"],
            "target_defined": m0["target_defined"],
            "outcome": m0["outcome"],
        }
        for arm, value in (("M0", m0["prediction"]), (companion.ARM, prediction)):
            status, diagnostic = base.classify(
                value,
                m0["outcome"],
                race,
                evaluated=evaluated,
                population_verified=whole,
            )
            row[arm] = {
                "prediction": value,
                "evaluation_status": status,
                "local_combination_match_diagnostic": diagnostic,
            }
        ledger.append(row)
    return {
        "format_version": "kra-api27-paired-evaluation-v1",
        "series": companion.SERIES,
        "contract_sha256": contract_sha,
        "commitment_sha256": commitment_sha,
        "parent_commitment_sha256": parent_sha,
        "evaluated_at": evaluated.isoformat(),
        "full_paired_population_verified": whole,
        "companion_commitment_published_before_block_cutoff": timely_companion_publication,
        "original_m0_report": original,
        "publication": publication[1] if publication else None,
        "ledger": ledger,
        "metrics": paired_metrics(ledger, whole),
        "official_finality_verified": False,
        "model_promoted": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "root",
        "parent-root",
        "m0-model-dir",
        "api27-model-dir",
        "parent-commitment",
        "commitment",
        "output",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    for name in ("parent-commitment-sha256", "commitment-sha256"):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--outcome-plan", type=Path)
    parser.add_argument("--outcome-plan-sha256")
    for prefix in ("m0", "api27"):
        parser.add_argument(f"--{prefix}-publication-pr", type=int)
        parser.add_argument(f"--{prefix}-publication-document")
    parser.add_argument("--witness-directory", type=Path)
    args = parser.parse_args(argv)
    outputs = [
        args.output,
        *([args.witness_directory] if args.witness_directory else []),
    ]
    for output in outputs:
        for source in (
            args.root,
            args.parent_root,
            args.m0_model_dir,
            args.api27_model_dir,
        ):
            if output.resolve().is_relative_to(
                source.resolve()
            ) or source.resolve().is_relative_to(output.resolve()):
                parser.error("evaluation outputs must not overlap source archives")
    publications = {}
    for prefix in ("m0", "api27"):
        number = getattr(args, f"{prefix}_publication_pr")
        document = getattr(args, f"{prefix}_publication_document")
        publications[prefix] = None
        if number is None and document is None:
            continue
        if number is None or document is None or args.witness_directory is None:
            parser.error("publication requires PR, document and new witness directory")
        directory = args.witness_directory / prefix
        directory.mkdir(parents=True, exist_ok=False)
        with httpx.Client(
            timeout=30, follow_redirects=False, trust_env=False
        ) as client:
            publications[prefix] = collect_publication(
                directory, number=number, document=document, client=client
            )
    result = evaluate(
        args.root,
        args.parent_root,
        args.m0_model_dir,
        args.api27_model_dir,
        args.parent_commitment,
        args.parent_commitment_sha256,
        args.commitment,
        args.commitment_sha256,
        outcome_plan=args.outcome_plan,
        outcome_sha=args.outcome_plan_sha256,
        m0_publication=publications["m0"],
        publication=publications["api27"],
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report_sha = save(args.output, result)
    print(encoded({"report_sha256": report_sha, "metrics": result["metrics"]}).decode())
    return 0 if result["metrics"]["fully_paired"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
