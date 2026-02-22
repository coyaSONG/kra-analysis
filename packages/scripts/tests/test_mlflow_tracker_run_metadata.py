from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.mlflow_tracker import ExperimentTracker


def test_tracker_writes_run_metadata_artifact_when_mlflow_disabled(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "disabled")

    tracker = ExperimentTracker(experiment_name="test-run-metadata")
    assert tracker.enabled is False

    metadata = {
        "commit_sha": "abc",
        "prompt_version": "v1.0",
        "data_snapshot_id": "snapshot-1",
        "seed": 42,
        "mode": "evaluation",
    }
    out = tracker.log_run_metadata(
        run_metadata=metadata,
        artifact_name="run_metadata_test.json",
        local_output_dir=tmp_path,
    )

    assert out is not None
    out_path = Path(out)
    assert out_path.exists()
    loaded = json.loads(out_path.read_text(encoding="utf-8"))
    assert loaded["prompt_version"] == "v1.0"
    assert loaded["data_snapshot_id"] == "snapshot-1"
