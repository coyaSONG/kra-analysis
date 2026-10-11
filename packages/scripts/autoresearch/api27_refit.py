"""Separately reviewed API-only fixed refit; never replace frozen M0."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import numpy as np

from autoresearch import api_training_opportunity as opportunity
from autoresearch import restricted_ablation as numerical
from autoresearch import restricted_cohort as cohort
from autoresearch.observed_history_seed import save
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.versioned_result_observations import source_hashes

REVIEW_PATH = cohort.ROOT / "data/contracts/api27_training_review_v1.json"
ARM = "API27_fixed_v1"
RECIPE = {
    **{
        k: v
        for k, v in numerical.RECIPE.items()
        if k
        not in {
            "feature_contract",
            "selection_policy",
            "train_date",
            "development_date",
            "evaluation_status",
        }
    },
    "feature_contract": "api26_original_14_columns_v1",
    "selection_policy": "whole_roster_unique_top3_versioned_observation_v1",
    "training_scope": "all_reviewed_27_races_no_parameter_search",
    "evaluation_status": "not_evaluated_requires_separate_future_protocol",
}


def implementation():
    result = cohort.implementation()
    result["source_sha256"].update(source_hashes())
    for module in (opportunity, opportunity.inference):
        path = Path(module.__file__)
        result["source_sha256"][f"autoresearch/{path.name}"] = cohort.sha256(
            path.read_bytes()
        )
    result["source_sha256"]["autoresearch/api27_refit.py"] = cohort.sha256(
        Path(__file__).read_bytes()
    )
    return result


def validate_records(records):
    ids = [r["race_id"] for r in records]
    if not records or ids != sorted(set(ids)):
        raise ValueError("api27_inventory_identity_conflict")
    selected = []
    for race in records:
        rows = race["feature_rows"]
        if not 3 <= len(rows) <= 20 or any(
            len({r[key] for r in rows}) != len(rows) for key in ("chul_no", "horse_id")
        ):
            raise ValueError("api27_roster_conflict")
        for row in rows:
            if (
                type(row["chul_no"]) is not int
                or not 1 <= row["chul_no"] <= 20
                or cohort.horse_id(row["horse_id"]) != row["horse_id"]
                or set(row["features"]) != set(cohort.API_COLUMNS)
            ):
                raise ValueError("api27_feature_identity_schema_conflict")
            features = row["features"]
            for key in cohort.API_FIELDS:
                value = cohort.numeric(features[key], key)
                if features[key] != value or features[f"{key}_missing"] is not (
                    value is None
                ):
                    raise ValueError("api27_feature_value_conflict")
            counts = [features[k] for k in ("ord1CntT", "ord2CntT", "ord3CntT")]
            starts = features["rcCntT"]
            if starts is not None and sum(x for x in counts if x is not None) > starts:
                raise ValueError("api27_place_count_exceeds_starts")
        labels = race["observed_top3"]
        candidate = race["potential_unique_top3_training_candidate"]
        if type(candidate) is not bool:
            raise ValueError("api27_candidate_flag_invalid")
        if candidate:
            if (
                race["reasons"]
                or race["whole_roster_label_join_exact"] is not True
                or race["result_status"] != "unique_top3_observed"
                or not isinstance(labels, list)
                or len(labels) != len(set(labels))
                or len(labels) != 3
                or not set(labels) <= {r["horse_id"] for r in rows}
                or not timestamp(race["source"]["available_at"])
                <= timestamp(race["source_publication_bound"])
                < timestamp(race["cutoff"])
            ):
                raise ValueError("api27_candidate_evidence_conflict")
            selected.append(
                {"race_id": race["race_id"], "feature_rows": rows, "label_top3": labels}
            )
        elif not race["reasons"] or labels is not None:
            raise ValueError("api27_exclusion_evidence_conflict")
    if not selected:
        raise ValueError("api27_empty_training_selection")
    return selected


def corpus_from_report(report):
    """Canonical evidence excludes only volatile publication retrieval details."""
    selected = validate_records(report["ledger"])
    if (
        report["format_version"] != "kra-api-only-training-opportunity-v1"
        or report["outcome_plan_sha256"] != opportunity.OUTCOME_PLAN_SHA
        or report["outcome_policy_sha256"] != opportunity.OUTCOME_POLICY_SHA
        or report["outcome_sources_sha256"] != opportunity.OUTCOME_SOURCES_SHA
        or report["training_approved"] is not False
        or report["model_fit_performed"] is not False
        or report["counts_as_70_percent_evidence"] is not False
        or report["candidate_race_count"] != len(selected)
        or report["candidate_runner_count"]
        != sum(len(r["feature_rows"]) for r in selected)
        or report["race_count"] != len(report["ledger"])
        or report["runner_count"]
        != sum(len(r["feature_rows"]) for r in report["ledger"])
    ):
        raise ValueError("api27_report_contract_conflict")
    # The exact corpus is reviewed, and CLI fit always repeats the raw replay.
    return {
        "format_version": "kra-api27-corpus-v1",
        "evidence": {k: v for k, v in report.items() if k != "witness_audit"},
        "input_plan_sha256": opportunity.PLAN_SHA,
        "input_bundle_sha256": opportunity.BUNDLE_SHA,
        "training_approved": False,
    }


@dataclass(frozen=True)
class Admitted:
    corpus_bytes: bytes
    review_bytes: bytes
    implementation_bytes: bytes

    def require_unchanged(self):
        if (
            cohort.encoded(implementation()) != self.implementation_bytes
            or REVIEW_PATH.read_bytes() != self.review_bytes
        ):
            raise ValueError("api27_approval_changed_after_admission")


def admit(corpus):
    raw = cohort.encoded(corpus)
    review_raw = cohort.read_bytes(REVIEW_PATH, limit=cohort.MAX_MANIFEST_BYTES)
    review = cohort.parse_json(review_raw)
    current = cohort.encoded(implementation())
    records = corpus["evidence"]["ledger"]
    selected = validate_records(records)
    if (
        corpus != corpus_from_report(corpus["evidence"])
        or review.get("format_version") != "kra-api27-review-v1"
        or review.get("purpose") != "research_fit_only"
        or review.get("arm") != ARM
        or review.get("corpus_sha256") != cohort.sha256(raw)
        or review.get("implementation_sha256") != cohort.sha256(current)
        or review.get("recipe_sha256") != cohort.sha256(cohort.encoded(RECIPE))
        or review.get("source_review_complete") is not True
        or review.get("label_version_review_complete") is not True
        or review.get("selected_race_ids") != [r["race_id"] for r in selected]
        or review.get("selected_runner_count")
        != sum(len(r["feature_rows"]) for r in selected)
        or review.get("inventory_race_ids") != [r["race_id"] for r in records]
        or review.get("model_promoted") is not False
    ):
        raise ValueError("unreviewed_api27_refit")
    return Admitted(raw, review_raw, current)


def run(admitted, directory):
    admitted.require_unchanged()
    races = validate_records(
        cohort.parse_json(admitted.corpus_bytes)["evidence"]["ledger"]
    )
    directory.mkdir(parents=True, exist_ok=False)
    estimator, consumed = numerical.fit(races, "M0")
    # M0 here is the old helper's API14 selector, not the frozen forward model.
    estimator["recipe"] = RECIPE
    model = {
        "format_version": "kra-api27-research-model-v1",
        "arm": ARM,
        "estimator": estimator,
        "corpus_sha256": cohort.sha256(admitted.corpus_bytes),
        "review_sha256": cohort.sha256(
            cohort.encoded(cohort.parse_json(admitted.review_bytes))
        ),
        "repository_review_sha256": cohort.sha256(admitted.review_bytes),
        "implementation_sha256": cohort.sha256(admitted.implementation_bytes),
        "model_promoted": False,
        "counts_as_70_percent_evidence": False,
    }
    pins = {
        "model.json": save(directory / "model.json", model),
        "matrix.json": save(directory / "matrix.json", consumed),
        "corpus.json": save(
            directory / "corpus.json", cohort.parse_json(admitted.corpus_bytes)
        ),
        "review.json": save(
            directory / "review.json", cohort.parse_json(admitted.review_bytes)
        ),
        "implementation.json": save(
            directory / "implementation.json",
            cohort.parse_json(admitted.implementation_bytes),
        ),
    }
    restored = opportunity.inference.pinned_json(
        directory / "model.json", pins["model.json"]
    )
    values, _, _ = numerical.input_matrix(races, "M0")
    if not np.array_equal(
        numerical.score_model(restored["estimator"], values),
        numerical.score_model(estimator, values),
    ) or numerical.predict(restored["estimator"], races) != numerical.predict(
        estimator, races
    ):
        raise ValueError("api27_saved_model_inference_mismatch")
    for name, expected in pins.items():
        if (
            cohort.sha256(
                cohort.read_bytes(directory / name, limit=cohort.MAX_MANIFEST_BYTES)
            )
            != expected
        ):
            raise ValueError("api27_saved_artifact_changed")
    admitted.require_unchanged()
    receipt = {
        "format_version": "kra-api27-fit-receipt-v1",
        "status": "completed",
        "completed_at": datetime.now(UTC).isoformat(),
        "arm": ARM,
        "recipe": RECIPE,
        "artifacts": pins,
        "selected_races": len(races),
        "selected_rows": len(consumed["y"]),
        "positive_labels": sum(consumed["y"]),
        "iterations": estimator["iterations"],
        "model_promoted": False,
        "counts_as_70_percent_evidence": False,
        "evaluation_status": RECIPE["evaluation_status"],
    }
    save(directory / "receipt.json", receipt)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "fit"))
    for name in ("plan", "bundle", "outcome-plan", "archive-root", "output-dir"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args(argv)
    directory = args.output_dir / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ") + "_" + uuid4().hex[:12]
    )
    directory.mkdir(parents=True, exist_ok=False)
    report = opportunity.prepare(
        args.plan, args.bundle, args.outcome_plan, args.archive_root, directory
    )
    report_sha = save(directory / "replay-report.json", report)
    corpus = corpus_from_report(report)
    corpus_sha = save(directory / "corpus.json", corpus)
    result = {
        "directory": str(directory),
        "corpus_sha256": corpus_sha,
        "replay_report_sha256": report_sha,
    }
    if args.command == "fit":
        result["fit"] = run(admit(corpus), directory / "fit")
        result["fit_receipt_sha256"] = cohort.sha256(
            (directory / "fit/receipt.json").read_bytes()
        )
        save(directory / "run-manifest.json", result)
    print(cohort.encoded(result).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
