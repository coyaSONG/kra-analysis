"""Tests for source-pool overlap-2 aggregate train-surface helpers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import (  # noqa: E402
    single_combo_source_pool_overlap2_aggregate_train_surface as surface,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_resolve_specs_round_trips_current_best_selector() -> None:
    source_group, selector = surface._resolve_specs(
        source_group_spec_name="src100/match/rankw0",
        selector_spec_name="add0.25/drop0.25/pair0.1/bias0.4",
    )

    assert source_group.name == "src100/match/rankw0"
    assert selector.name == "add0.25/drop0.25/pair0.1/bias0.4"


def test_patch_diagnostic_artifact_adds_safe_train_predictions(tmp_path: Path) -> None:
    diagnostic = tmp_path / "diagnostic.json"
    source = tmp_path / "source.json"
    surface_path = tmp_path / "surface.json"
    output = tmp_path / "patched.json"
    _write_json(
        diagnostic,
        {
            "format_version": "diagnostic-v1",
            "source_artifact": "old-source.json",
            "predictions_by_window": {"dev": {"e1": [1, 2, 3]}},
            "counts_as_70_percent_evidence": True,
        },
    )
    surface_payload = {
        "format_version": "surface-v1",
        "source_artifact_target": str(diagnostic),
        "train_predictions_by_window": {"dev": {"r1": [1, 2, 4]}},
        "train_prediction_capture": {"status": "captured"},
    }

    patched = surface.patch_diagnostic_artifact(
        diagnostic_artifact=diagnostic,
        source_artifact=source,
        surface_payload=surface_payload,
        surface_output=surface_path,
        patched_output=output,
    )

    assert patched["source_artifact"] == str(source)
    assert patched["original_source_artifact"] == "old-source.json"
    assert patched["train_prediction_contract"] == surface.TRAIN_PREDICTION_CONTRACT
    assert patched["train_predictions_by_window"]["dev"]["r1"] == [1, 2, 4]
    assert patched["train_prediction_capture"]["race_count_by_window"] == {"dev": 1}
    assert patched["counts_as_70_percent_evidence"] is False
