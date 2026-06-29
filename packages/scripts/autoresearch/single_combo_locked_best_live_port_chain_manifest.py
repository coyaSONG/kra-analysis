"""Build a recursive live-port manifest for the locked-best source chain."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_CACHE_DIR = Path(".cache/autoresearch")
DEFAULT_MATERIALIZATION_AUDIT = (
    DEFAULT_CACHE_DIR
    / "single_combo_locked_best_live_runner_materialization_audit.json"
)
DEFAULT_OUTPUT = (
    DEFAULT_CACHE_DIR / "single_combo_locked_best_live_port_chain_manifest.json"
)

LIVE_ARTIFACT_BY_OFFLINE_FRAGMENT = {
    "full_combo_pairwise_online_guard_after_threshold_gate": (
        "single_combo_live_full_combo_pairwise_online_guard_after_threshold_gate_predictions.json"
    ),
    "broad_component_threshold_gate": (
        "single_combo_live_broad_component_threshold_gate_predictions.json"
    ),
    "full_combo_pairwise_online_guard_after_broad_candidate": (
        "single_combo_live_full_combo_pairwise_online_guard_after_broad_candidate_predictions.json"
    ),
    "broad_component_candidate_exact_prior_date_after_pairwise_online": (
        "single_combo_live_broad_component_candidate_exact_prior_date_after_pairwise_online_predictions.json"
    ),
    "full_combo_pairwise_online_guard_after_score_gate_delta_online": (
        "single_combo_live_full_combo_pairwise_online_guard_after_score_gate_delta_online_predictions.json"
    ),
    "full_combo_score_gate_after_delta_online": (
        "single_combo_live_full_combo_score_gate_after_delta_online_predictions.json"
    ),
    "full_combo_online_gain_gate_after_delta_online": (
        "single_combo_live_full_combo_online_gain_gate_after_delta_online_predictions.json"
    ),
    "full_combo_delta_switch_after_online_gain": (
        "single_combo_live_full_combo_delta_switch_after_online_gain_predictions.json"
    ),
    "full_combo_online_gain_gate_after_full_combo_delta": (
        "single_combo_live_full_combo_online_gain_gate_after_full_combo_delta_predictions.json"
    ),
    "full_combo_delta_switch_after_broad_rank_segment": (
        "single_combo_live_full_combo_delta_switch_after_broad_rank_segment_predictions.json"
    ),
    "row_cache_rank_pattern_after_broad_rank_segment": (
        "single_combo_live_row_cache_rank_pattern_after_broad_rank_segment_predictions.json"
    ),
    "broad_component_rank_segment_aggressive_after_row_cache_rank_pattern": (
        "single_combo_live_broad_component_rank_segment_after_row_cache_rank_pattern_predictions.json"
    ),
    "row_cache_rank_pattern_after_source_pool": (
        "single_combo_live_row_cache_rank_pattern_after_source_pool_predictions.json"
    ),
    "all_allowed_source_pool_ranker_after_overlap2_aggregate": (
        "single_combo_live_all_allowed_source_pool_ranker_after_overlap2_aggregate_predictions.json"
    ),
    "all_allowed_source_pool_overlap2_aggregate_selector_after_source_meta_extension": (
        "single_combo_live_all_allowed_source_pool_overlap2_aggregate_after_source_meta_extension_predictions.json"
    ),
    "all_allowed_source_pool_ranker_source_meta_extension_after_variant_calibration": (
        "single_combo_live_all_allowed_source_pool_ranker_source_meta_extension_after_variant_calibration_predictions.json"
    ),
    "source_pool_ranker_variant_calibration": (
        "single_combo_live_source_pool_ranker_variant_calibration_predictions.json"
    ),
    "all_allowed_source_pool_ranker_prior_date_selector": (
        "single_combo_live_all_allowed_source_pool_ranker_prior_date_predictions.json"
    ),
    "all_allowed_source_pool_ranker_feature_extension_prior_date_selector": (
        "single_combo_live_all_allowed_source_pool_ranker_feature_extension_predictions.json"
    ),
    "row_cache_rank_pattern_prior_date_selector": (
        "single_combo_live_row_cache_rank_pattern_prior_date_predictions.json"
    ),
    "entity_history_pair_overlay_prior_date_selector": (
        "single_combo_live_entity_history_pair_overlay_prior_date_predictions.json"
    ),
    "entity_history_overlay_prior_date_selector": (
        "single_combo_live_entity_history_overlay_prior_date_predictions.json"
    ),
    "cross_surface_union_race_context_prior_date_selector": (
        "single_combo_live_cross_surface_union_race_context_prior_date_predictions.json"
    ),
    "broad_component_first_exact_rank_prior_date_selector": (
        "single_combo_live_broad_component_first_exact_rank_prior_date_predictions.json"
    ),
}

ACTION_BY_LIVE_ARTIFACT = {
    "single_combo_live_full_combo_pairwise_online_guard_after_threshold_gate_predictions.json": (
        "port_locked_best_threshold_gate_fallback_source_to_live_runner"
    ),
    "single_combo_live_broad_component_threshold_gate_predictions.json": (
        "port_locked_best_threshold_gate_fallback_source_to_live_runner"
    ),
    "single_combo_live_full_combo_pairwise_online_guard_after_broad_candidate_predictions.json": (
        "port_locked_best_full_combo_pairwise_broad_candidate_source_to_live_runner"
    ),
    "single_combo_live_broad_component_candidate_exact_prior_date_after_pairwise_online_predictions.json": (
        "port_locked_best_broad_component_candidate_exact_prior_date_source_to_live_runner"
    ),
    "single_combo_live_full_combo_pairwise_online_guard_after_score_gate_delta_online_predictions.json": (
        "port_locked_best_full_combo_pairwise_score_gate_source_to_live_runner"
    ),
    "single_combo_live_full_combo_score_gate_after_delta_online_predictions.json": (
        "port_locked_best_full_combo_score_gate_delta_online_source_to_live_runner"
    ),
    "single_combo_live_full_combo_online_gain_gate_after_delta_online_predictions.json": (
        "port_locked_best_full_combo_online_gain_gate_delta_online_source_to_live_runner"
    ),
    "single_combo_live_full_combo_delta_switch_after_online_gain_predictions.json": (
        "port_locked_best_full_combo_delta_switch_after_online_gain_source_to_live_runner"
    ),
    "single_combo_live_full_combo_online_gain_gate_after_full_combo_delta_predictions.json": (
        "port_locked_best_full_combo_online_gain_after_full_combo_delta_source_to_live_runner"
    ),
    "single_combo_live_full_combo_delta_switch_after_broad_rank_segment_predictions.json": (
        "port_locked_best_full_combo_delta_switch_after_broad_rank_segment_source_to_live_runner"
    ),
    "single_combo_live_row_cache_rank_pattern_after_broad_rank_segment_predictions.json": (
        "port_locked_best_row_cache_rank_pattern_after_broad_rank_segment_source_to_live_runner"
    ),
    "single_combo_live_broad_component_rank_segment_after_row_cache_rank_pattern_predictions.json": (
        "port_locked_best_broad_component_rank_segment_after_row_cache_rank_pattern_source_to_live_runner"
    ),
    "single_combo_live_row_cache_rank_pattern_after_source_pool_predictions.json": (
        "port_locked_best_row_cache_rank_pattern_after_source_pool_source_to_live_runner"
    ),
    "single_combo_live_all_allowed_source_pool_ranker_after_overlap2_aggregate_predictions.json": (
        "port_locked_best_source_pool_ranker_overlap2_source_to_live_runner"
    ),
    "single_combo_live_all_allowed_source_pool_overlap2_aggregate_after_source_meta_extension_predictions.json": (
        "port_locked_best_source_pool_overlap2_aggregate_source_to_live_runner"
    ),
    "single_combo_live_all_allowed_source_pool_ranker_source_meta_extension_after_variant_calibration_predictions.json": (
        "port_locked_best_source_pool_source_meta_extension_source_to_live_runner"
    ),
    "single_combo_live_source_pool_ranker_variant_calibration_predictions.json": (
        "port_locked_best_source_pool_variant_calibration_source_to_live_runner"
    ),
    "single_combo_live_all_allowed_source_pool_ranker_prior_date_predictions.json": (
        "port_locked_best_all_allowed_source_pool_ranker_prior_date_source_to_live_runner"
    ),
    "single_combo_live_all_allowed_source_pool_ranker_feature_extension_predictions.json": (
        "port_locked_best_all_allowed_source_pool_ranker_feature_extension_source_to_live_runner"
    ),
    "single_combo_live_row_cache_rank_pattern_prior_date_predictions.json": (
        "port_locked_best_row_cache_rank_pattern_prior_date_source_to_live_runner"
    ),
    "single_combo_live_entity_history_pair_overlay_prior_date_predictions.json": (
        "port_locked_best_entity_history_pair_overlay_prior_date_source_to_live_runner"
    ),
    "single_combo_live_entity_history_overlay_prior_date_predictions.json": (
        "port_locked_best_entity_history_overlay_prior_date_source_to_live_runner"
    ),
    "single_combo_live_cross_surface_union_race_context_prior_date_predictions.json": (
        "port_locked_best_cross_surface_union_race_context_prior_date_source_to_live_runner"
    ),
    "single_combo_live_broad_component_first_exact_rank_prior_date_predictions.json": (
        "port_locked_best_broad_component_first_exact_rank_prior_date_source_to_live_runner"
    ),
}


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


def _live_artifact_for_node(
    node: dict[str, Any], *, live_cache_dir: Path
) -> Path | None:
    path = str(node.get("path") or "")
    for fragment, live_name in LIVE_ARTIFACT_BY_OFFLINE_FRAGMENT.items():
        if fragment in path:
            return live_cache_dir / live_name
    return None


def _live_status(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {
            "path": None,
            "exists": False,
            "status": "unknown_live_artifact_mapping",
            "source_status": None,
            "recommended_next_action": None,
        }
    payload = _dict(_read_json(path))
    source_status = payload.get("status")
    if not path.exists():
        status = "missing"
    elif source_status == "passed":
        status = "passed"
    elif isinstance(source_status, str) and source_status.startswith("blocked"):
        status = "blocked"
    else:
        status = "failed"
    return {
        "path": str(path),
        "exists": path.exists(),
        "status": status,
        "source_status": source_status,
        "selection_contract": payload.get("selection_contract"),
        "coverage": payload.get("coverage"),
        "recommended_next_action": payload.get("recommended_next_action"),
    }


def _default_action_for_live_path(live_path: str | None) -> str:
    if live_path:
        name = Path(live_path).name
        if name in ACTION_BY_LIVE_ARTIFACT:
            return ACTION_BY_LIVE_ARTIFACT[name]
    return "map_locked_best_live_port_source_dependency"


def _recommended_next_action(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    for node in nodes:
        live = _dict(node.get("live_artifact"))
        if live.get("status") == "passed":
            continue
        child_recommended = _dict(live.get("recommended_next_action"))
        action = child_recommended.get("action")
        if isinstance(action, str) and action:
            return {
                "action": action,
                "blocking": bool(child_recommended.get("blocking", False)),
                "classification": child_recommended.get(
                    "classification", "background_modeling_candidate"
                ),
                "queue_priority_score": float(
                    child_recommended.get("queue_priority_score", 94.5)
                ),
                "reason": (
                    child_recommended.get("reason")
                    or "A materialized live-port source dependency reported a downstream action."
                ),
                "blocked_depth": node.get("depth"),
                "blocked_offline_artifact": node.get("offline_artifact"),
                "blocked_live_artifact": live.get("path"),
                "manifest_resolution": "first_materialized_child_action",
            }
    for node in nodes:
        live = _dict(node.get("live_artifact"))
        if live.get("status") == "passed":
            continue
        child_recommended = _dict(live.get("recommended_next_action"))
        action = child_recommended.get("action")
        if not isinstance(action, str) or not action:
            action = _default_action_for_live_path(live.get("path"))
        return {
            "action": action,
            "blocking": False,
            "classification": "background_modeling_candidate",
            "queue_priority_score": float(
                child_recommended.get("queue_priority_score", 94.5)
            ),
            "reason": (
                child_recommended.get("reason")
                or "The locked-best live-port chain has an unmaterialized required source dependency."
            ),
            "blocked_depth": node.get("depth"),
            "blocked_offline_artifact": node.get("offline_artifact"),
            "blocked_live_artifact": live.get("path"),
        }
    return {
        "action": "implement_locked_best_live_runner_from_materialized_chain",
        "blocking": False,
        "classification": "background_modeling_candidate",
        "queue_priority_score": 94.3,
        "reason": "Every mapped live source dependency is materialized.",
    }


def build_manifest(
    *,
    materialization_audit_path: Path = DEFAULT_MATERIALIZATION_AUDIT,
    live_cache_dir: Path = DEFAULT_CACHE_DIR,
) -> dict[str, Any]:
    audit = _dict(_read_json(materialization_audit_path))
    first_non_copy = _dict(audit.get("first_non_copy_source_selector"))
    start_depth = first_non_copy.get("depth")
    raw_nodes = [
        _dict(node)
        for node in _list(audit.get("source_chain_nodes"))
        if not _dict(node).get("copy_layer")
        and (
            start_depth is None
            or int(_dict(node).get("depth") or 0) >= int(start_depth)
        )
    ]
    nodes: list[dict[str, Any]] = []
    for node in raw_nodes:
        live_artifact = _live_artifact_for_node(node, live_cache_dir=live_cache_dir)
        nodes.append(
            {
                "depth": node.get("depth"),
                "offline_artifact": node.get("path"),
                "selection_contract": node.get("selection_contract"),
                "selector_spec": node.get("selector_spec"),
                "source_artifact": node.get("source_artifact"),
                "switch_summary": node.get("switch_summary"),
                "live_artifact": _live_status(live_artifact),
            }
        )
    recommended = _recommended_next_action(nodes)
    passed_count = sum(
        1
        for node in nodes
        if _dict(node.get("live_artifact")).get("status") == "passed"
    )
    status = (
        "ready_to_materialize_locked_best_live_runner"
        if nodes and passed_count == len(nodes)
        else "blocked_unmaterialized_live_source_dependency"
    )
    return {
        "format_version": "single-combo-locked-best-live-port-chain-manifest-v1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "status": status,
        "diagnostic_only": True,
        "counts_as_70_percent_evidence": False,
        "materialization_audit_path": str(materialization_audit_path),
        "live_cache_dir": str(live_cache_dir),
        "node_count": len(nodes),
        "passed_live_node_count": passed_count,
        "nodes": nodes,
        "recommended_next_action": recommended,
        "policy": {
            "recursive_source_chain_must_be_materialized": True,
            "source_substitution_must_not_unblock_locked_parent": True,
            "diagnostic_only_artifacts_do_not_count_as_forward_evidence": True,
            "counts_as_70_percent_evidence": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--materialization-audit",
        type=Path,
        default=DEFAULT_MATERIALIZATION_AUDIT,
    )
    parser.add_argument("--live-cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = build_manifest(
        live_cache_dir=args.live_cache_dir,
        materialization_audit_path=args.materialization_audit,
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
