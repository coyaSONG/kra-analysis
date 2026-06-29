"""Materialize or block live cross-surface union race-context source."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from autoresearch.single_combo_live_entity_history_overlay_prior_date_materializer import (  # noqa: E501
    DEFAULT_CACHE_DIR,
    _best_selector,
    _candidate_context,
    _candidate_race_ids,
    _dict,
    _int,
    _read_json,
    _source_context,
    _window_prediction_count,
    _write_json,
)

DEFAULT_SOURCE_TARGET = DEFAULT_CACHE_DIR / (
    "clean_release_current_best_cross_surface_union_race_context_prior_date_"
    "selector_rerun_repro_diagnostic.json"
)
DEFAULT_LIVE_SOURCE = (
    DEFAULT_CACHE_DIR
    / "single_combo_live_broad_component_first_exact_rank_prior_date_predictions.json"
)
DEFAULT_CANDIDATE_FEATURES = (
    DEFAULT_CACHE_DIR
    / "single_combo_live_probability_current_miss_candidate_features.json"
)
DEFAULT_OUTPUT = (
    DEFAULT_CACHE_DIR
    / "single_combo_live_cross_surface_union_race_context_prior_date_predictions.json"
)

EXPECTED_SOURCE_SELECTION_CONTRACT = "one_unordered_top3_combo_per_race"
PARENT_ACTION = (
    "port_locked_best_cross_surface_union_race_context_prior_date_source_to_live_runner"
)
CHILD_ACTION = (
    "port_locked_best_broad_component_first_exact_rank_prior_date_source_to_live_runner"
)


def _recommended_next_action(
    *,
    live_source_context: dict[str, Any],
    candidate_status: str,
    ready_to_pass_through: bool,
) -> dict[str, Any]:
    if live_source_context.get("status") != "passed":
        child_recommended = _dict(live_source_context.get("recommended_next_action"))
        child_action = child_recommended.get("action")
        if isinstance(child_action, str) and child_action:
            return {
                "action": child_action,
                "blocking": bool(child_recommended.get("blocking", False)),
                "classification": child_recommended.get(
                    "classification", "background_modeling_candidate"
                ),
                "queue_priority_score": float(
                    child_recommended.get("queue_priority_score", 94.94)
                ),
                "reason": (
                    child_recommended.get("reason")
                    or "The broad-component first-exact rank source reported a downstream live-port dependency."
                ),
                "upstream_action": PARENT_ACTION,
            }
        return {
            "action": CHILD_ACTION,
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.94,
            "reason": (
                "The cross-surface union race-context source cannot emit "
                "predictions until the broad-component first-exact rank prior-date "
                "source is materialized with the exact contract."
            ),
        }
    if candidate_status != "passed":
        return {
            "action": "repair_live_candidate_features_before_cross_surface_union_race_context_prior_date_port",
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.92,
            "reason": (
                "The cross-surface union race-context source needs complete live "
                "full-combo candidate features and live records before pass-through "
                "can be trusted."
            ),
        }
    if ready_to_pass_through:
        return {
            "action": "materialize_locked_best_entity_history_overlay_from_passed_cross_surface_union_race_context",
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.9,
            "reason": (
                "The fallback-only cross-surface union race-context source has been "
                "materialized and can now unblock the entity-history overlay parent."
            ),
        }
    return {
        "action": "inspect_cross_surface_union_race_context_prior_date_pass_through_coverage_gap",
        "blocking": False,
        "classification": "background_modeling_candidate",
        "queue_priority_score": 94.88,
        "reason": (
            "The cross-surface union race-context source is present, but its live "
            "prediction coverage does not match the current candidate race universe."
        ),
    }


def build_artifact(
    *,
    source_target_path: Path = DEFAULT_SOURCE_TARGET,
    live_source_path: Path = DEFAULT_LIVE_SOURCE,
    candidate_features_path: Path = DEFAULT_CANDIDATE_FEATURES,
) -> dict[str, Any]:
    source_target = _dict(_read_json(source_target_path))
    source_payload = _dict(_read_json(live_source_path))
    selector = _best_selector(source_target)
    source_context = _source_context(live_source_path)
    candidate_context = _candidate_context(candidate_features_path)
    candidate_coverage = _dict(candidate_context.get("coverage"))
    expected_race_count = _int(candidate_coverage.get("expected_race_count")) or 0
    race_ids = _candidate_race_ids(candidate_context)
    predictions = _dict(source_payload.get("predictions_by_window"))
    predicted_race_count = _window_prediction_count(
        {"predictions_by_window": predictions}
    )
    ready_to_pass_through = (
        source_context["status"] == "passed"
        and candidate_context["status"] == "passed"
        and predicted_race_count == expected_race_count
        and expected_race_count > 0
    )
    recommended = _recommended_next_action(
        candidate_status=str(candidate_context.get("status")),
        live_source_context=source_context,
        ready_to_pass_through=ready_to_pass_through,
    )
    predictions_payload: dict[str, Any] = predictions
    if ready_to_pass_through:
        status = "passed"
        coverage = {
            "status": "passed",
            "expected_race_count": expected_race_count,
            "predicted_race_count": predicted_race_count,
            "coverage_rate": 1.0,
            "missing_race_ids": [],
            "race_ids": race_ids,
        }
    elif (
        source_context["status"] != "passed"
        and source_context.get("exists")
        and _dict(source_context.get("recommended_next_action")).get("action")
    ):
        status = "blocked_live_source_child_dependency"
        coverage = {
            "status": "blocked",
            "expected_race_count": expected_race_count,
            "predicted_race_count": 0,
            "coverage_rate": 0.0 if expected_race_count else None,
            "missing_race_ids": race_ids,
        }
        predictions_payload = {}
    elif source_context["status"] != "passed":
        status = "blocked_missing_live_source_artifact"
        coverage = {
            "status": "blocked",
            "expected_race_count": expected_race_count,
            "predicted_race_count": 0,
            "coverage_rate": 0.0 if expected_race_count else None,
            "missing_race_ids": race_ids,
        }
        predictions_payload = {}
    elif candidate_context["status"] != "passed":
        status = "blocked_incomplete_live_candidate_features"
        coverage = {
            "status": "blocked",
            "expected_race_count": expected_race_count,
            "predicted_race_count": 0,
            "coverage_rate": 0.0 if expected_race_count else None,
            "missing_race_ids": race_ids,
        }
        predictions_payload = {}
    else:
        status = "blocked_cross_surface_union_race_context_prior_date_coverage_gap"
        coverage = {
            "status": "blocked",
            "expected_race_count": expected_race_count,
            "predicted_race_count": predicted_race_count,
            "coverage_rate": (
                round(predicted_race_count / expected_race_count, 6)
                if expected_race_count
                else None
            ),
            "missing_race_ids": race_ids,
        }
        predictions_payload = {}
    return {
        "format_version": "single-combo-live-cross-surface-union-race-context-prior-date-materializer-v1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "status": status,
        "diagnostic_only": status != "passed",
        "counts_as_70_percent_evidence": False,
        "counts_as_forward_test_evidence": False,
        "counts_as_56_46_chain_validation": False,
        "selection_contract": "one_unordered_top3_combo_per_race",
        "source_selection_contract": selector.get("selection_contract"),
        "expected_source_selection_contract": EXPECTED_SOURCE_SELECTION_CONTRACT,
        "selector_spec": selector.get("selector_spec"),
        "source_target_artifact": str(source_target_path),
        "source_target_source_artifact": selector.get("source_artifact"),
        "live_source_context": source_context,
        "candidate_feature_context": candidate_context,
        "coverage": coverage,
        "predictions_by_window": predictions_payload,
        "selector_diagnostics": {
            "selector": "fallback_only",
            "candidate": selector.get("candidate"),
            "selector_spec": selector.get("selector_spec"),
            "summary": selector.get("summary"),
            "window_diagnostics": selector.get("window_diagnostics"),
            "selection_uses_target_labels": False,
            "history_uses_completed_prior_outcomes": False,
        },
        "recommended_next_action": recommended,
        "policy": {
            "fallback_only_ranker_may_pass_through_materialized_source": True,
            "do_not_substitute_champion_clean_top3_for_locked_source": True,
            "diagnostic_shadow_substitution_must_not_unblock_locked_parent": True,
            "required_source_must_be_materialized_before_prediction": True,
            "active_live_labels_must_not_be_used": True,
            "prior_date_history_must_not_include_current_or_future_labels": True,
            "same_day_result_history_updates_without_contract_forbidden": True,
            "counts_as_70_percent_evidence": False,
        },
        "blocked_reason": None if status == "passed" else recommended["reason"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-target", type=Path, default=DEFAULT_SOURCE_TARGET)
    parser.add_argument("--live-source", type=Path, default=DEFAULT_LIVE_SOURCE)
    parser.add_argument(
        "--candidate-features",
        type=Path,
        default=DEFAULT_CANDIDATE_FEATURES,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = build_artifact(
        candidate_features_path=args.candidate_features,
        live_source_path=args.live_source,
        source_target_path=args.source_target,
    )
    payload["output_path"] = str(args.output)
    _write_json(args.output, payload)
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
