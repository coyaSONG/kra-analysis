"""Strict live materializer for the feature-extended source-pool ranker."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from autoresearch import (
    clean_release_current_best_all_allowed_source_pool_ranker_feature_extension_prior_date_selector_diagnostic as extension,
)
from autoresearch import (
    single_combo_live_all_allowed_source_pool_ranker_prior_date_materializer as base_materializer,
)

DEFAULT_CACHE_DIR = base_materializer.DEFAULT_CACHE_DIR
DEFAULT_SOURCE_TARGET = DEFAULT_CACHE_DIR / (
    "clean_release_current_best_all_allowed_source_pool_ranker_feature_extension_"
    "prior_date_selector_rerun_repro_diagnostic.json"
)
DEFAULT_LIVE_SOURCE = base_materializer.DEFAULT_LIVE_SOURCE
DEFAULT_CANDIDATE_FEATURES = base_materializer.DEFAULT_CANDIDATE_FEATURES
DEFAULT_TRAIN_SURFACE = (
    DEFAULT_CACHE_DIR
    / "single_combo_source_pool_ranker_feature_extension_prior_date_train_surface.json"
)
DEFAULT_OUTPUT = (
    DEFAULT_CACHE_DIR
    / "single_combo_live_all_allowed_source_pool_ranker_feature_extension_predictions.json"
)

PARENT_ACTION = (
    "port_locked_best_all_allowed_source_pool_ranker_feature_extension_source_to_live_runner"
)


def _rewrite_recommended_next_action(payload: dict[str, Any]) -> dict[str, Any]:
    recommended = base_materializer._dict(payload.get("recommended_next_action"))
    action = recommended.get("action")
    if payload.get("status") == "passed":
        return {
            "action": "materialize_locked_best_source_pool_variant_calibration_from_passed_feature_extension_ranker",
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.79,
            "reason": (
                "The locked feature-extended source-pool ranker emitted complete "
                "pre-race live predictions; proceed to variant calibration."
            ),
        }
    if action == "repair_all_allowed_source_pool_ranker_train_surface_before_live_port":
        return {
            **recommended,
            "action": "repair_all_allowed_source_pool_ranker_feature_extension_train_surface_before_live_port",
            "reason": (
                "The live scorer needs the frozen feature-extended source-pool "
                "ranker train surface to rebuild the prior-date HGB history."
            ),
        }
    if action == "implement_locked_best_all_allowed_source_pool_ranker_prior_date_prediction_logic":
        return {
            **recommended,
            "action": "implement_locked_best_all_allowed_source_pool_ranker_feature_extension_prediction_logic",
            "reason": (
                "The source and candidate live inputs are available, but the locked "
                "feature-extended HGB source-pool ranker prediction logic has not "
                "been ported yet."
            ),
        }
    return recommended


def build_artifact(
    *,
    source_target_path: Path = DEFAULT_SOURCE_TARGET,
    live_source_path: Path = DEFAULT_LIVE_SOURCE,
    candidate_features_path: Path = DEFAULT_CANDIDATE_FEATURES,
    train_surface_path: Path = DEFAULT_TRAIN_SURFACE,
) -> dict[str, Any]:
    payload = base_materializer.build_artifact(
        candidate_features_path=candidate_features_path,
        candidate_rows_builder=extension._enhanced_candidate_rows_for_race,
        live_source_path=live_source_path,
        source_target_path=source_target_path,
        train_surface_path=train_surface_path,
    )
    status = str(payload.get("status") or "")
    if status == "blocked_missing_all_allowed_source_pool_ranker_train_surface":
        payload["status"] = (
            "blocked_missing_all_allowed_source_pool_ranker_feature_extension_train_surface"
        )
    payload["format_version"] = (
        "single-combo-live-all-allowed-source-pool-ranker-feature-extension-v1"
    )
    payload["feature_extension"] = {
        "adds_race_local_source_ranks": True,
        "adds_fallback_margins": True,
        "adds_horse_pair_aggregates": True,
    }
    payload["recommended_next_action"] = _rewrite_recommended_next_action(payload)
    payload["blocked_reason"] = (
        None if payload.get("status") == "passed" else payload["recommended_next_action"]["reason"]
    )
    diagnostics = base_materializer._dict(payload.get("selector_diagnostics"))
    diagnostics["selector"] = "source_pool_ranker_feature_extension_prior_date"
    diagnostics["feature_extension"] = payload["feature_extension"]
    payload["selector_diagnostics"] = diagnostics
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-target", type=Path, default=DEFAULT_SOURCE_TARGET)
    parser.add_argument("--live-source", type=Path, default=DEFAULT_LIVE_SOURCE)
    parser.add_argument(
        "--candidate-features",
        type=Path,
        default=DEFAULT_CANDIDATE_FEATURES,
    )
    parser.add_argument("--train-surface", type=Path, default=DEFAULT_TRAIN_SURFACE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = build_artifact(
        candidate_features_path=args.candidate_features,
        live_source_path=args.live_source,
        source_target_path=args.source_target,
        train_surface_path=args.train_surface,
    )
    payload["output_path"] = str(args.output)
    base_materializer._write_json(args.output, payload)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "recommended_next_action": payload["recommended_next_action"]["action"],
                "status": payload["status"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
