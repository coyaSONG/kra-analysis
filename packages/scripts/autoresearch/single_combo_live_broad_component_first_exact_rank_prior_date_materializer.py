"""Strict live materializer for broad-component first-exact rank selector."""

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

from autoresearch.single_combo_live_row_cache_rank_pattern_prior_date_materializer import (  # noqa: E501
    DEFAULT_CACHE_DIR,
    LIVE_SOURCE_SELECTION_CONTRACT,
    _best_selector,
    _candidate_context,
    _candidate_race_ids,
    _dict,
    _int,
    _read_json,
    _source_context,
    _write_json,
)

DEFAULT_SOURCE_TARGET = DEFAULT_CACHE_DIR / (
    "clean_release_current_best_broad_component_first_exact_rank_prior_date_"
    "selector_rerun_repro_diagnostic.json"
)
DEFAULT_LIVE_SOURCE = (
    DEFAULT_CACHE_DIR
    / "single_combo_live_frontier_artifact_combo_prior_date_predictions.json"
)
DEFAULT_CANDIDATE_FEATURES = (
    DEFAULT_CACHE_DIR
    / "single_combo_live_probability_current_miss_candidate_features.json"
)
DEFAULT_OUTPUT = (
    DEFAULT_CACHE_DIR
    / "single_combo_live_broad_component_first_exact_rank_prior_date_predictions.json"
)

PARENT_ACTION = (
    "port_locked_best_broad_component_first_exact_rank_prior_date_source_to_live_runner"
)
CHILD_ACTION = (
    "port_locked_best_frontier_artifact_combo_prior_date_source_to_live_runner"
)


def _recommended_next_action(
    *,
    live_source_context: dict[str, Any],
    candidate_status: str,
    status: str,
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
                    child_recommended.get("queue_priority_score", 94.96)
                ),
                "reason": (
                    child_recommended.get("reason")
                    or "The frontier artifact combo source reported a downstream live-port dependency."
                ),
                "upstream_action": PARENT_ACTION,
            }
        return {
            "action": CHILD_ACTION,
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.96,
            "reason": (
                "The broad-component first-exact rank live source cannot emit "
                "predictions until the frontier artifact combo prior-date source "
                "is materialized with the exact contract."
            ),
        }
    if candidate_status != "passed":
        return {
            "action": "repair_live_candidate_features_before_broad_component_first_exact_rank_prior_date_port",
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.94,
            "reason": (
                "The broad-component first-exact rank selector needs complete live "
                "full-combo candidate features and live records before scoring can be trusted."
            ),
        }
    if (
        status
        == "blocked_pending_broad_component_first_exact_rank_prior_date_prediction_logic"
    ):
        return {
            "action": "implement_locked_best_broad_component_first_exact_rank_prior_date_prediction_logic",
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.92,
            "reason": (
                "The source and candidate live inputs are available, but the locked "
                "HGB broad-component first-exact rank prediction logic has not been ported yet."
            ),
        }
    return {
        "action": "inspect_broad_component_first_exact_rank_prior_date_live_materializer_gap",
        "blocking": False,
        "classification": "background_modeling_candidate",
        "queue_priority_score": 94.9,
        "reason": (
            "The broad-component first-exact rank materializer reached an unexpected "
            "coverage state and needs inspection before unblocking its parent."
        ),
    }


def _status_for_source(live_source_context: dict[str, Any]) -> str | None:
    if live_source_context.get("status") == "passed":
        return None
    if live_source_context.get("exists") and _dict(
        live_source_context.get("recommended_next_action")
    ).get("action"):
        return "blocked_live_source_child_dependency"
    return "blocked_missing_live_source_artifact"


def build_artifact(
    *,
    source_target_path: Path = DEFAULT_SOURCE_TARGET,
    live_source_path: Path = DEFAULT_LIVE_SOURCE,
    candidate_features_path: Path = DEFAULT_CANDIDATE_FEATURES,
) -> dict[str, Any]:
    source_target = _dict(_read_json(source_target_path))
    selector = _best_selector(source_target)
    live_source_context = _source_context(live_source_path)
    candidate_context = _candidate_context(candidate_features_path)
    candidate_coverage = _dict(candidate_context.get("coverage"))
    expected_race_count = _int(candidate_coverage.get("expected_race_count")) or 0
    race_ids = _candidate_race_ids(candidate_context)
    pre_status = _status_for_source(live_source_context)

    if pre_status is not None:
        status = pre_status
    elif candidate_context["status"] != "passed":
        status = "blocked_incomplete_live_candidate_features"
    else:
        status = "blocked_pending_broad_component_first_exact_rank_prior_date_prediction_logic"

    coverage = {
        "status": "blocked",
        "expected_race_count": expected_race_count,
        "predicted_race_count": 0,
        "coverage_rate": 0.0 if expected_race_count else None,
        "missing_race_ids": race_ids,
        "race_ids": race_ids,
    }
    recommended = _recommended_next_action(
        candidate_status=str(candidate_context.get("status")),
        live_source_context=live_source_context,
        status=status,
    )
    return {
        "format_version": "single-combo-live-broad-component-first-exact-rank-prior-date-materializer-v1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "status": status,
        "diagnostic_only": True,
        "counts_as_70_percent_evidence": False,
        "counts_as_forward_test_evidence": False,
        "counts_as_56_46_chain_validation": False,
        "selection_contract": "one_unordered_top3_combo_per_race",
        "source_selection_contract": "one_unordered_top3_combo_per_race",
        "source_target_selection_contract": selector.get("selection_contract"),
        "expected_source_selection_contract": LIVE_SOURCE_SELECTION_CONTRACT,
        "selector_spec": selector.get("selector_spec"),
        "selector_type": selector.get("selector_type"),
        "model_spec": selector.get("model_spec"),
        "source_target_artifact": str(source_target_path),
        "offline_source_artifact": selector.get("source_artifact"),
        "live_source_context": live_source_context,
        "candidate_feature_context": candidate_context,
        "coverage": coverage,
        "predictions_by_window": {},
        "selector_diagnostics": {
            "selector": "broad_component_first_exact_rank_prior_date",
            "candidate": selector.get("candidate"),
            "selector_spec": selector.get("selector_spec"),
            "model_spec": selector.get("model_spec"),
            "summary": selector.get("summary"),
            "window_diagnostics": selector.get("window_diagnostics"),
            "selection_uses_target_labels": False,
            "history_uses_completed_prior_outcomes": False,
            "prediction_logic_pending_after_source_materialization": (
                live_source_context.get("status") == "passed"
                and candidate_context.get("status") == "passed"
            ),
        },
        "recommended_next_action": recommended,
        "policy": {
            "ranker_must_not_be_treated_as_pass_through": True,
            "hgb_model_prediction_logic_must_be_ported_before_emit": True,
            "active_live_labels_must_not_be_used": True,
            "do_not_substitute_champion_clean_top3_for_locked_source": True,
            "diagnostic_shadow_substitution_must_not_unblock_locked_parent": True,
            "required_sources_must_be_materialized_before_prediction": True,
            "same_day_result_history_updates_without_contract_forbidden": True,
            "counts_as_70_percent_evidence": False,
        },
        "blocked_reason": recommended["reason"],
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
