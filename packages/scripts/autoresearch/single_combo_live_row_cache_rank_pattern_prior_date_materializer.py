"""Strict live materializer for the row-cache rank-pattern prior-date selector."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_CACHE_DIR = Path(".cache/autoresearch")
DEFAULT_SOURCE_TARGET = DEFAULT_CACHE_DIR / (
    "clean_release_current_best_row_cache_rank_pattern_prior_date_"
    "selector_rerun_repro_diagnostic.json"
)
DEFAULT_LIVE_SOURCE = (
    DEFAULT_CACHE_DIR
    / "single_combo_live_entity_history_pair_overlay_prior_date_predictions.json"
)
DEFAULT_CANDIDATE_FEATURES = (
    DEFAULT_CACHE_DIR
    / "single_combo_live_probability_current_miss_candidate_features.json"
)
DEFAULT_OUTPUT = (
    DEFAULT_CACHE_DIR
    / "single_combo_live_row_cache_rank_pattern_prior_date_predictions.json"
)

LIVE_SOURCE_SELECTION_CONTRACT = "one_unordered_top3_combo_per_race"
PARENT_ACTION = (
    "port_locked_best_row_cache_rank_pattern_prior_date_source_to_live_runner"
)
CHILD_ACTION = (
    "port_locked_best_entity_history_pair_overlay_prior_date_source_to_live_runner"
)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coverage_rate(coverage: dict[str, Any]) -> float | None:
    try:
        return float(coverage.get("coverage_rate"))
    except (TypeError, ValueError):
        return None


def _window_prediction_count(payload: dict[str, Any]) -> int:
    total = 0
    for window_payload in _dict(payload.get("predictions_by_window")).values():
        total += len(_dict(window_payload))
    return total


def _best_selector(source_target: dict[str, Any]) -> dict[str, Any]:
    best = _dict(source_target.get("best"))
    windows: list[dict[str, Any]] = []
    for window in _list(best.get("windows")):
        window_dict = _dict(window)
        diagnostics = _dict(window_dict.get("diagnostics"))
        if diagnostics:
            windows.append(
                {
                    "name": window_dict.get("name"),
                    "diagnostics": diagnostics,
                }
            )
    return {
        "candidate": best.get("candidate"),
        "selector_spec": best.get("selector_spec"),
        "selector_type": best.get("selector_type") or "hgb_row_cache_rank_pattern",
        "model_spec": best.get("model_spec") or "hgb",
        "summary": _dict(best.get("summary")),
        "selection_contract": source_target.get("selection_contract"),
        "source_artifact": source_target.get("source_artifact"),
        "window_diagnostics": windows,
    }


def _source_context(path: Path) -> dict[str, Any]:
    payload = _dict(_read_json(path))
    coverage = _dict(payload.get("coverage"))
    selection_contract = payload.get("selection_contract")
    source_selection_contract = (
        payload.get("source_selection_contract") or selection_contract
    )
    predicted_count = _int(coverage.get("predicted_race_count"))
    if predicted_count is None:
        predicted_count = _window_prediction_count(payload)
    status = "missing"
    if path.exists():
        if (
            payload.get("status") == "passed"
            and source_selection_contract == LIVE_SOURCE_SELECTION_CONTRACT
            and _coverage_rate(coverage) == 1.0
            and predicted_count > 0
        ):
            status = "passed"
        else:
            status = "failed"
    return {
        "path": str(path),
        "exists": path.exists(),
        "status": status,
        "source_status": payload.get("status"),
        "selection_contract": selection_contract,
        "source_selection_contract": source_selection_contract,
        "expected_source_selection_contract": LIVE_SOURCE_SELECTION_CONTRACT,
        "coverage": coverage,
        "predicted_race_count": predicted_count,
        "contract_match": source_selection_contract == LIVE_SOURCE_SELECTION_CONTRACT,
        "diagnostic_only": payload.get("diagnostic_only"),
        "counts_as_70_percent_evidence": payload.get("counts_as_70_percent_evidence"),
        "recommended_next_action": payload.get("recommended_next_action"),
        "blocked_reason": payload.get("blocked_reason"),
    }


def _candidate_context(path: Path) -> dict[str, Any]:
    payload = _dict(_read_json(path))
    coverage = _dict(payload.get("coverage"))
    expected = _int(coverage.get("expected_race_count")) or 0
    candidate_count = _int(coverage.get("candidate_race_count")) or 0
    missing = _list(coverage.get("missing_race_ids"))
    current_candidates = _dict(payload.get("current_candidates_by_race"))
    live_records = _list(payload.get("live_records"))
    status = "missing"
    if path.exists():
        status = (
            "passed"
            if payload.get("status") == "passed"
            and expected > 0
            and candidate_count == expected
            and not missing
            and len(current_candidates) == expected
            and len(live_records) == expected
            else "failed"
        )
    return {
        "path": str(path),
        "exists": path.exists(),
        "status": status,
        "source_status": payload.get("status"),
        "coverage": coverage,
        "current_candidate_race_count": len(current_candidates),
        "live_record_count": len(live_records),
        "source_signal_window": payload.get("source_signal_window"),
        "target_dataset_path": payload.get("target_dataset_path"),
        "train_replay_contract": payload.get("train_replay_contract"),
    }


def _candidate_race_ids(candidate_context: dict[str, Any]) -> list[str]:
    coverage = _dict(candidate_context.get("coverage"))
    return [str(race_id) for race_id in _list(coverage.get("race_ids"))]


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
                    child_recommended.get("queue_priority_score", 94.88)
                ),
                "reason": (
                    child_recommended.get("reason")
                    or "The entity-history pair-overlay source reported a downstream live-port dependency."
                ),
                "upstream_action": PARENT_ACTION,
            }
        return {
            "action": CHILD_ACTION,
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.88,
            "reason": (
                "The row-cache rank-pattern live source cannot emit predictions "
                "until the entity-history pair-overlay prior-date source is "
                "materialized with the exact contract."
            ),
        }
    if candidate_status != "passed":
        return {
            "action": "repair_live_candidate_features_before_row_cache_rank_pattern_prior_date_port",
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.86,
            "reason": (
                "The row-cache rank-pattern selector needs complete live full-combo "
                "candidate features and live records before scoring can be trusted."
            ),
        }
    if status == "blocked_pending_row_cache_rank_pattern_prior_date_prediction_logic":
        return {
            "action": "implement_locked_best_row_cache_rank_pattern_prior_date_prediction_logic",
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.84,
            "reason": (
                "The source and candidate live inputs are available, but the locked "
                "HGB row-cache rank-pattern prediction logic has not been ported yet."
            ),
        }
    return {
        "action": "inspect_row_cache_rank_pattern_prior_date_live_materializer_gap",
        "blocking": False,
        "classification": "background_modeling_candidate",
        "queue_priority_score": 94.82,
        "reason": (
            "The row-cache rank-pattern materializer reached an unexpected coverage "
            "state and needs inspection before unblocking its parent."
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
        status = "blocked_pending_row_cache_rank_pattern_prior_date_prediction_logic"

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
        "format_version": "single-combo-live-row-cache-rank-pattern-prior-date-materializer-v1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "status": status,
        "diagnostic_only": True,
        "counts_as_70_percent_evidence": False,
        "counts_as_forward_test_evidence": False,
        "counts_as_56_46_chain_validation": False,
        "selection_contract": "one_unordered_top3_combo_per_race",
        "source_selection_contract": selector.get("selection_contract"),
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
            "selector": "row_cache_rank_pattern_prior_date",
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
