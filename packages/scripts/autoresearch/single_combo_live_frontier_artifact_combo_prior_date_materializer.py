"""Materialize live frontier artifact-combo prior-date source."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_CACHE_DIR = Path(".cache/autoresearch")
DEFAULT_SOURCE_TARGET = DEFAULT_CACHE_DIR / (
    "clean_release_frontier_artifact_combo_prior_date_selector_rerun_repro_diagnostic.json"
)
DEFAULT_LIVE_SOURCE = (
    DEFAULT_CACHE_DIR / "single_combo_live_current_best_fallback_predictions.json"
)
DEFAULT_CANDIDATE_FEATURES = (
    DEFAULT_CACHE_DIR
    / "single_combo_live_probability_current_miss_candidate_features.json"
)
DEFAULT_OUTPUT = (
    DEFAULT_CACHE_DIR
    / "single_combo_live_frontier_artifact_combo_prior_date_predictions.json"
)

LIVE_SOURCE_SELECTION_CONTRACT = "live_current_best_fallback_predictions_by_window"
OUTPUT_SELECTION_CONTRACT = "one_unordered_top3_combo_per_race"
PARENT_ACTION = (
    "port_locked_best_frontier_artifact_combo_prior_date_source_to_live_runner"
)
CHILD_ACTION = "materialize_live_current_best_fallback_for_frontier_artifact_combo"


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
        "summary": _dict(best.get("summary")),
        "selection_contract": source_target.get("selection_contract"),
        "source_artifacts": _list(source_target.get("source_artifacts")),
        "source_names": _list(source_target.get("source_names")),
        "window_diagnostics": windows,
    }


def _window_prediction_count(payload: dict[str, Any]) -> int:
    total = 0
    for window_payload in _dict(payload.get("predictions_by_window")).values():
        total += len(_dict(window_payload))
    return total


def _source_context(path: Path) -> dict[str, Any]:
    payload = _dict(_read_json(path))
    coverage = _dict(payload.get("coverage"))
    predicted_count = _int(coverage.get("predicted_race_count"))
    if predicted_count is None:
        predicted_count = _window_prediction_count(payload)
    selection_contract = payload.get("selection_contract")
    status = "missing"
    if path.exists():
        if (
            payload.get("status") == "passed"
            and selection_contract == LIVE_SOURCE_SELECTION_CONTRACT
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
        "expected_selection_contract": LIVE_SOURCE_SELECTION_CONTRACT,
        "coverage": coverage,
        "predicted_race_count": predicted_count,
        "contract_match": selection_contract == LIVE_SOURCE_SELECTION_CONTRACT,
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


def _best_is_current_source_only(selector: dict[str, Any]) -> bool:
    windows = _list(selector.get("window_diagnostics"))
    if not windows:
        return False
    for window in windows:
        diagnostics = _dict(_dict(window).get("diagnostics"))
        try:
            selected_current_best_rate = float(
                diagnostics.get("selected_current_best_rate")
            )
        except (TypeError, ValueError):
            return False
        if selected_current_best_rate != 1.0:
            return False
        if diagnostics.get("selection_uses_labels") is not False:
            return False
    return True


def _recommended_next_action(
    *,
    source_context: dict[str, Any],
    candidate_status: str,
    status: str,
    ready_to_pass_through: bool,
) -> dict[str, Any]:
    if source_context.get("status") != "passed":
        child_recommended = _dict(source_context.get("recommended_next_action"))
        child_action = child_recommended.get("action")
        if isinstance(child_action, str) and child_action:
            return {
                "action": child_action,
                "blocking": bool(child_recommended.get("blocking", False)),
                "classification": child_recommended.get(
                    "classification", "background_modeling_candidate"
                ),
                "queue_priority_score": float(
                    child_recommended.get("queue_priority_score", 94.98)
                ),
                "reason": (
                    child_recommended.get("reason")
                    or "The live current-best fallback source reported a downstream dependency."
                ),
                "upstream_action": PARENT_ACTION,
            }
        return {
            "action": CHILD_ACTION,
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.98,
            "reason": (
                "The frontier artifact-combo source needs the live current-best "
                "fallback predictions materialized with full coverage."
            ),
        }
    if candidate_status != "passed":
        return {
            "action": "repair_live_candidate_features_before_frontier_artifact_combo_prior_date_port",
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.96,
            "reason": (
                "The frontier artifact-combo source needs complete live full-combo "
                "candidate features and live records before pass-through can be trusted."
            ),
        }
    if ready_to_pass_through:
        return {
            "action": "materialize_locked_best_broad_component_first_exact_rank_from_passed_frontier_artifact_combo",
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.94,
            "reason": (
                "The frontier selector's locked best chose the current source in "
                "every validation window, so the current-best live source can unblock "
                "the broad-component parent."
            ),
        }
    if status == "blocked_pending_frontier_artifact_combo_prior_date_prediction_logic":
        return {
            "action": "implement_locked_best_frontier_artifact_combo_prior_date_prediction_logic",
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": 94.94,
            "reason": (
                "The live current-best source is available, but the frontier selector "
                "cannot be safely reduced to pass-through from the locked diagnostics."
            ),
        }
    return {
        "action": "inspect_frontier_artifact_combo_prior_date_live_materializer_gap",
        "blocking": False,
        "classification": "background_modeling_candidate",
        "queue_priority_score": 94.92,
        "reason": (
            "The frontier artifact-combo materializer reached an unexpected coverage "
            "state and needs inspection before unblocking its parent."
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
    current_source_only = _best_is_current_source_only(selector)
    source_ready = source_context["status"] == "passed"
    candidates_ready = candidate_context["status"] == "passed"
    ready_to_pass_through = (
        source_ready
        and candidates_ready
        and current_source_only
        and predicted_race_count == expected_race_count
        and expected_race_count > 0
    )

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
        predictions_payload: dict[str, Any] = predictions
    elif (
        not source_ready
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
    elif not source_ready:
        status = "blocked_missing_live_source_artifact"
        coverage = {
            "status": "blocked",
            "expected_race_count": expected_race_count,
            "predicted_race_count": 0,
            "coverage_rate": 0.0 if expected_race_count else None,
            "missing_race_ids": race_ids,
        }
        predictions_payload = {}
    elif not candidates_ready:
        status = "blocked_incomplete_live_candidate_features"
        coverage = {
            "status": "blocked",
            "expected_race_count": expected_race_count,
            "predicted_race_count": 0,
            "coverage_rate": 0.0 if expected_race_count else None,
            "missing_race_ids": race_ids,
        }
        predictions_payload = {}
    elif not current_source_only:
        status = "blocked_pending_frontier_artifact_combo_prior_date_prediction_logic"
        coverage = {
            "status": "blocked",
            "expected_race_count": expected_race_count,
            "predicted_race_count": 0,
            "coverage_rate": 0.0 if expected_race_count else None,
            "missing_race_ids": race_ids,
        }
        predictions_payload = {}
    else:
        status = "blocked_frontier_artifact_combo_prior_date_coverage_gap"
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

    recommended = _recommended_next_action(
        candidate_status=str(candidate_context.get("status")),
        ready_to_pass_through=ready_to_pass_through,
        source_context=source_context,
        status=status,
    )
    return {
        "format_version": "single-combo-live-frontier-artifact-combo-prior-date-materializer-v1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "status": status,
        "diagnostic_only": status != "passed",
        "counts_as_70_percent_evidence": False,
        "counts_as_forward_test_evidence": False,
        "counts_as_56_46_chain_validation": False,
        "selection_contract": OUTPUT_SELECTION_CONTRACT,
        "source_selection_contract": OUTPUT_SELECTION_CONTRACT,
        "source_target_selection_contract": selector.get("selection_contract"),
        "expected_live_source_selection_contract": LIVE_SOURCE_SELECTION_CONTRACT,
        "selector_spec": selector.get("selector_spec"),
        "source_target_artifact": str(source_target_path),
        "source_target_source_artifacts": selector.get("source_artifacts"),
        "source_target_source_names": selector.get("source_names"),
        "live_source_context": source_context,
        "candidate_feature_context": candidate_context,
        "coverage": coverage,
        "predictions_by_window": predictions_payload,
        "selector_diagnostics": {
            "selector": "frontier_artifact_combo_prior_date",
            "candidate": selector.get("candidate"),
            "selector_spec": selector.get("selector_spec"),
            "summary": selector.get("summary"),
            "window_diagnostics": selector.get("window_diagnostics"),
            "best_selected_current_source_in_all_windows": current_source_only,
            "selection_uses_target_labels": False,
            "history_uses_completed_prior_outcomes": False,
        },
        "recommended_next_action": recommended,
        "policy": {
            "pass_through_requires_best_selected_current_source_rate_one": True,
            "pass_through_source_is_live_current_best_fallback": True,
            "active_live_labels_must_not_be_used": True,
            "do_not_substitute_unverified_frontier_sources": True,
            "diagnostic_shadow_substitution_must_not_count_as_70_percent": True,
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
