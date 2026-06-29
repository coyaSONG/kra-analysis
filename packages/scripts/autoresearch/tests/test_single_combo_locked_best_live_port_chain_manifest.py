"""Locked-best live-port chain manifest tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import (  # noqa: E402
    single_combo_locked_best_live_port_chain_manifest as manifest,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_build_manifest_reports_first_missing_live_dependency(tmp_path: Path) -> None:
    audit = tmp_path / "audit.json"
    _write_json(
        audit,
        {
            "first_non_copy_source_selector": {"depth": 4},
            "source_chain_nodes": [
                {
                    "copy_layer": False,
                    "depth": 4,
                    "path": (
                        ".cache/autoresearch/"
                        "clean_release_current_best_broad_component_threshold_gate_"
                        "after_pairwise_broad_reanchor_rerun_repro_diagnostic.json"
                    ),
                    "selection_contract": "threshold_gate",
                    "selector_spec": "rule",
                    "source_artifact": "source.json",
                }
            ],
        },
    )

    result = manifest.build_manifest(
        live_cache_dir=tmp_path / "live-cache",
        materialization_audit_path=audit,
    )

    assert result["status"] == "blocked_unmaterialized_live_source_dependency"
    assert result["node_count"] == 1
    assert result["nodes"][0]["live_artifact"]["status"] == "missing"
    assert result["recommended_next_action"]["action"] == (
        "port_locked_best_threshold_gate_fallback_source_to_live_runner"
    )


def test_build_manifest_maps_online_gain_delta_dependency(tmp_path: Path) -> None:
    audit = tmp_path / "audit.json"
    _write_json(
        audit,
        {
            "first_non_copy_source_selector": {"depth": 9},
            "source_chain_nodes": [
                {
                    "copy_layer": False,
                    "depth": 9,
                    "path": (
                        ".cache/autoresearch/"
                        "clean_release_current_best_full_combo_online_gain_gate_"
                        "after_delta_online_reanchor_rerun_repro_diagnostic.json"
                    ),
                    "selection_contract": "online_gain_gate",
                    "selector_spec": "rule",
                    "source_artifact": "source.json",
                }
            ],
        },
    )

    result = manifest.build_manifest(
        live_cache_dir=tmp_path / "live-cache",
        materialization_audit_path=audit,
    )

    assert result["status"] == "blocked_unmaterialized_live_source_dependency"
    assert result["node_count"] == 1
    assert result["nodes"][0]["live_artifact"]["status"] == "missing"
    assert result["recommended_next_action"]["action"] == (
        "port_locked_best_full_combo_online_gain_gate_delta_online_source_to_live_runner"
    )


def test_build_manifest_maps_delta_switch_after_online_gain_dependency(
    tmp_path: Path,
) -> None:
    audit = tmp_path / "audit.json"
    _write_json(
        audit,
        {
            "first_non_copy_source_selector": {"depth": 10},
            "source_chain_nodes": [
                {
                    "copy_layer": False,
                    "depth": 10,
                    "path": (
                        ".cache/autoresearch/"
                        "clean_release_current_best_full_combo_delta_switch_"
                        "after_online_gain_reanchor_rerun_repro_diagnostic.json"
                    ),
                    "selection_contract": "delta_switch",
                    "selector_spec": "rule",
                    "source_artifact": "source.json",
                }
            ],
        },
    )

    result = manifest.build_manifest(
        live_cache_dir=tmp_path / "live-cache",
        materialization_audit_path=audit,
    )

    assert result["status"] == "blocked_unmaterialized_live_source_dependency"
    assert result["node_count"] == 1
    assert result["nodes"][0]["live_artifact"]["status"] == "missing"
    assert result["recommended_next_action"]["action"] == (
        "port_locked_best_full_combo_delta_switch_after_online_gain_source_to_live_runner"
    )


def test_build_manifest_maps_online_gain_after_full_combo_delta_dependency(
    tmp_path: Path,
) -> None:
    audit = tmp_path / "audit.json"
    _write_json(
        audit,
        {
            "first_non_copy_source_selector": {"depth": 11},
            "source_chain_nodes": [
                {
                    "copy_layer": False,
                    "depth": 11,
                    "path": (
                        ".cache/autoresearch/"
                        "clean_release_current_best_full_combo_online_gain_gate_"
                        "after_full_combo_delta_reanchor_rerun_repro_diagnostic.json"
                    ),
                    "selection_contract": "online_gain_gate",
                    "selector_spec": "rule",
                    "source_artifact": "source.json",
                }
            ],
        },
    )

    result = manifest.build_manifest(
        live_cache_dir=tmp_path / "live-cache",
        materialization_audit_path=audit,
    )

    assert result["status"] == "blocked_unmaterialized_live_source_dependency"
    assert result["node_count"] == 1
    assert result["nodes"][0]["live_artifact"]["status"] == "missing"
    assert result["recommended_next_action"]["action"] == (
        "port_locked_best_full_combo_online_gain_after_full_combo_delta_source_to_live_runner"
    )


def test_build_manifest_maps_delta_switch_after_broad_rank_segment_dependency(
    tmp_path: Path,
) -> None:
    audit = tmp_path / "audit.json"
    _write_json(
        audit,
        {
            "first_non_copy_source_selector": {"depth": 12},
            "source_chain_nodes": [
                {
                    "copy_layer": False,
                    "depth": 12,
                    "path": (
                        ".cache/autoresearch/"
                        "clean_release_current_best_full_combo_delta_switch_"
                        "after_broad_rank_segment_reanchor_rerun_repro_diagnostic.json"
                    ),
                    "selection_contract": "delta_switch",
                    "selector_spec": "rule",
                    "source_artifact": "source.json",
                }
            ],
        },
    )

    result = manifest.build_manifest(
        live_cache_dir=tmp_path / "live-cache",
        materialization_audit_path=audit,
    )

    assert result["status"] == "blocked_unmaterialized_live_source_dependency"
    assert result["node_count"] == 1
    assert result["nodes"][0]["live_artifact"]["status"] == "missing"
    assert result["recommended_next_action"]["action"] == (
        "port_locked_best_full_combo_delta_switch_after_broad_rank_segment_source_to_live_runner"
    )


def test_build_manifest_maps_row_cache_rank_pattern_after_broad_rank_segment_dependency(
    tmp_path: Path,
) -> None:
    audit = tmp_path / "audit.json"
    _write_json(
        audit,
        {
            "first_non_copy_source_selector": {"depth": 13},
            "source_chain_nodes": [
                {
                    "copy_layer": False,
                    "depth": 13,
                    "path": (
                        ".cache/autoresearch/"
                        "clean_release_current_best_row_cache_rank_pattern_"
                        "after_broad_rank_segment_reanchor_prior_date_selector_"
                        "rerun_repro_diagnostic.json"
                    ),
                    "selection_contract": "one_unordered_top3_combo_per_race",
                    "selector_spec": "fallback_only",
                    "source_artifact": "source.json",
                }
            ],
        },
    )

    result = manifest.build_manifest(
        live_cache_dir=tmp_path / "live-cache",
        materialization_audit_path=audit,
    )

    assert result["status"] == "blocked_unmaterialized_live_source_dependency"
    assert result["node_count"] == 1
    assert result["nodes"][0]["live_artifact"]["status"] == "missing"
    assert result["recommended_next_action"]["action"] == (
        "port_locked_best_row_cache_rank_pattern_after_broad_rank_segment_source_to_live_runner"
    )


def test_build_manifest_maps_broad_component_rank_segment_after_row_cache_dependency(
    tmp_path: Path,
) -> None:
    audit = tmp_path / "audit.json"
    _write_json(
        audit,
        {
            "first_non_copy_source_selector": {"depth": 14},
            "source_chain_nodes": [
                {
                    "copy_layer": False,
                    "depth": 14,
                    "path": (
                        ".cache/autoresearch/"
                        "clean_release_current_best_broad_component_rank_segment_"
                        "aggressive_after_row_cache_rank_pattern_reanchor_"
                        "prior_date_selector_rerun_repro_diagnostic.json"
                    ),
                    "selection_contract": "broad_component_rank_segment",
                    "selector_spec": "rule",
                    "source_artifact": "source.json",
                }
            ],
        },
    )

    result = manifest.build_manifest(
        live_cache_dir=tmp_path / "live-cache",
        materialization_audit_path=audit,
    )

    assert result["status"] == "blocked_unmaterialized_live_source_dependency"
    assert result["node_count"] == 1
    assert result["nodes"][0]["live_artifact"]["status"] == "missing"
    assert result["recommended_next_action"]["action"] == (
        "port_locked_best_broad_component_rank_segment_after_row_cache_rank_pattern_source_to_live_runner"
    )


def test_build_manifest_maps_row_cache_rank_pattern_after_source_pool_dependency(
    tmp_path: Path,
) -> None:
    audit = tmp_path / "audit.json"
    _write_json(
        audit,
        {
            "first_non_copy_source_selector": {"depth": 15},
            "source_chain_nodes": [
                {
                    "copy_layer": False,
                    "depth": 15,
                    "path": (
                        ".cache/autoresearch/"
                        "clean_release_current_best_row_cache_rank_pattern_"
                        "after_source_pool_reanchor_prior_date_selector_"
                        "rerun_repro_diagnostic.json"
                    ),
                    "selection_contract": "one_unordered_top3_combo_per_race",
                    "selector_spec": "fallback_only",
                    "source_artifact": "source.json",
                }
            ],
        },
    )

    result = manifest.build_manifest(
        live_cache_dir=tmp_path / "live-cache",
        materialization_audit_path=audit,
    )

    assert result["status"] == "blocked_unmaterialized_live_source_dependency"
    assert result["node_count"] == 1
    assert result["nodes"][0]["live_artifact"]["status"] == "missing"
    assert result["recommended_next_action"]["action"] == (
        "port_locked_best_row_cache_rank_pattern_after_source_pool_source_to_live_runner"
    )


def test_build_manifest_maps_source_pool_ranker_after_overlap2_dependency(
    tmp_path: Path,
) -> None:
    audit = tmp_path / "audit.json"
    _write_json(
        audit,
        {
            "first_non_copy_source_selector": {"depth": 16},
            "source_chain_nodes": [
                {
                    "copy_layer": False,
                    "depth": 16,
                    "path": (
                        ".cache/autoresearch/"
                        "clean_release_current_best_all_allowed_source_pool_ranker_"
                        "after_overlap2_aggregate_prior_date_selector_"
                        "rerun_repro_diagnostic.json"
                    ),
                    "selection_contract": "one_unordered_top3_combo_per_race",
                    "selector_spec": "fallback_only",
                    "source_artifact": "source.json",
                }
            ],
        },
    )

    result = manifest.build_manifest(
        live_cache_dir=tmp_path / "live-cache",
        materialization_audit_path=audit,
    )

    assert result["status"] == "blocked_unmaterialized_live_source_dependency"
    assert result["node_count"] == 1
    assert result["nodes"][0]["live_artifact"]["status"] == "missing"
    assert result["recommended_next_action"]["action"] == (
        "port_locked_best_source_pool_ranker_overlap2_source_to_live_runner"
    )


def test_build_manifest_maps_source_pool_overlap2_aggregate_dependency(
    tmp_path: Path,
) -> None:
    audit = tmp_path / "audit.json"
    _write_json(
        audit,
        {
            "first_non_copy_source_selector": {"depth": 17},
            "source_chain_nodes": [
                {
                    "copy_layer": False,
                    "depth": 17,
                    "path": (
                        ".cache/autoresearch/"
                        "clean_release_current_best_all_allowed_source_pool_"
                        "overlap2_aggregate_selector_after_source_meta_extension_"
                        "prior_date_selector_rerun_repro_diagnostic.json"
                    ),
                    "selection_contract": "one_unordered_top3_combo_per_race",
                    "selector_spec": "fallback_only",
                    "source_artifact": "source.json",
                }
            ],
        },
    )

    result = manifest.build_manifest(
        live_cache_dir=tmp_path / "live-cache",
        materialization_audit_path=audit,
    )

    assert result["status"] == "blocked_unmaterialized_live_source_dependency"
    assert result["node_count"] == 1
    assert result["nodes"][0]["live_artifact"]["status"] == "missing"
    assert result["recommended_next_action"]["action"] == (
        "port_locked_best_source_pool_overlap2_aggregate_source_to_live_runner"
    )


def test_build_manifest_maps_source_pool_source_meta_extension_dependency(
    tmp_path: Path,
) -> None:
    audit = tmp_path / "audit.json"
    _write_json(
        audit,
        {
            "first_non_copy_source_selector": {"depth": 18},
            "source_chain_nodes": [
                {
                    "copy_layer": False,
                    "depth": 18,
                    "path": (
                        ".cache/autoresearch/"
                        "clean_release_current_best_all_allowed_source_pool_ranker_"
                        "source_meta_extension_after_variant_calibration_"
                        "prior_date_selector_rerun_repro_diagnostic.json"
                    ),
                    "selection_contract": "one_unordered_top3_combo_per_race",
                    "selector_spec": "fallback_only",
                    "source_artifact": "source.json",
                }
            ],
        },
    )

    result = manifest.build_manifest(
        live_cache_dir=tmp_path / "live-cache",
        materialization_audit_path=audit,
    )

    assert result["status"] == "blocked_unmaterialized_live_source_dependency"
    assert result["node_count"] == 1
    assert result["nodes"][0]["live_artifact"]["status"] == "missing"
    assert result["recommended_next_action"]["action"] == (
        "port_locked_best_source_pool_source_meta_extension_source_to_live_runner"
    )


def test_build_manifest_maps_source_pool_variant_calibration_dependency(
    tmp_path: Path,
) -> None:
    audit = tmp_path / "audit.json"
    _write_json(
        audit,
        {
            "first_non_copy_source_selector": {"depth": 19},
            "source_chain_nodes": [
                {
                    "copy_layer": False,
                    "depth": 19,
                    "path": (
                        ".cache/autoresearch/"
                        "clean_release_current_best_source_pool_ranker_"
                        "variant_calibration_prior_date_selector_"
                        "rerun_repro_diagnostic.json"
                    ),
                    "selection_contract": "one_unordered_top3_combo_per_race",
                    "selector_spec": None,
                    "source_artifact": None,
                }
            ],
        },
    )

    result = manifest.build_manifest(
        live_cache_dir=tmp_path / "live-cache",
        materialization_audit_path=audit,
    )

    assert result["status"] == "blocked_unmaterialized_live_source_dependency"
    assert result["node_count"] == 1
    assert result["nodes"][0]["live_artifact"]["status"] == "missing"
    assert result["recommended_next_action"]["action"] == (
        "port_locked_best_source_pool_variant_calibration_source_to_live_runner"
    )


def test_build_manifest_maps_variant_calibration_input_dependencies(
    tmp_path: Path,
) -> None:
    cases = [
        (
            "clean_release_current_best_all_allowed_source_pool_ranker_"
            "prior_date_selector_rerun_repro_diagnostic.json",
            "port_locked_best_all_allowed_source_pool_ranker_prior_date_source_to_live_runner",
        ),
        (
            "clean_release_current_best_all_allowed_source_pool_ranker_"
            "feature_extension_prior_date_selector_rerun_repro_diagnostic.json",
            "port_locked_best_all_allowed_source_pool_ranker_feature_extension_source_to_live_runner",
        ),
        (
            "clean_release_current_best_row_cache_rank_pattern_"
            "prior_date_selector_rerun_repro_diagnostic.json",
            "port_locked_best_row_cache_rank_pattern_prior_date_source_to_live_runner",
        ),
        (
            "clean_release_current_best_entity_history_pair_overlay_"
            "prior_date_selector_rerun_repro_diagnostic.json",
            "port_locked_best_entity_history_pair_overlay_prior_date_source_to_live_runner",
        ),
        (
            "clean_release_current_best_entity_history_overlay_"
            "prior_date_selector_rerun_repro_diagnostic.json",
            "port_locked_best_entity_history_overlay_prior_date_source_to_live_runner",
        ),
        (
            "clean_release_current_best_cross_surface_union_race_context_"
            "prior_date_selector_rerun_repro_diagnostic.json",
            "port_locked_best_cross_surface_union_race_context_prior_date_source_to_live_runner",
        ),
    ]
    for artifact_name, expected_action in cases:
        audit = tmp_path / f"{artifact_name}.audit.json"
        _write_json(
            audit,
            {
                "first_non_copy_source_selector": {"depth": 20},
                "source_chain_nodes": [
                    {
                        "copy_layer": False,
                        "depth": 20,
                        "path": f".cache/autoresearch/{artifact_name}",
                        "selection_contract": "one_unordered_top3_combo_per_race",
                        "selector_spec": "fixture",
                        "source_artifact": None,
                    }
                ],
            },
        )

        result = manifest.build_manifest(
            live_cache_dir=tmp_path / "live-cache",
            materialization_audit_path=audit,
        )

        assert result["status"] == "blocked_unmaterialized_live_source_dependency"
        assert result["node_count"] == 1
        assert result["nodes"][0]["live_artifact"]["status"] == "missing"
        assert result["recommended_next_action"]["action"] == expected_action
