from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.run_metadata import (
    build_run_metadata,
    validate_run_metadata,
    write_run_metadata_artifact,
)


def test_build_run_metadata_includes_required_fields(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_SHA", "abc1234")

    metadata = build_run_metadata(
        prompt_version="v10.0",
        dataset_id="snapshot-20260222",
        mode="evaluation",
        seed=7,
    )

    assert metadata["commit_sha"] == "abc1234"
    assert metadata["prompt_version"] == "v10.0"
    assert metadata["data_snapshot_id"] == "snapshot-20260222"
    assert metadata["seed"] == 7
    assert metadata["mode"] == "evaluation"
    assert "created_at" in metadata


def test_validate_run_metadata_rejects_missing_required_key() -> None:
    ok, errors = validate_run_metadata(
        {
            "commit_sha": "abc",
            "prompt_version": "v1",
            "seed": 42,
            "mode": "evaluation",
        }
    )

    assert ok is False
    assert "missing:data_snapshot_id" in errors


def test_write_run_metadata_artifact_persists_json(tmp_path: Path) -> None:
    metadata = {
        "commit_sha": "abc",
        "prompt_version": "v1",
        "data_snapshot_id": "snapshot-1",
        "seed": 42,
        "mode": "evaluation",
        "created_at": "2026-02-22T00:00:00+00:00",
    }

    out_path = write_run_metadata_artifact(
        metadata=metadata,
        output_dir=tmp_path,
        filename="run_metadata_test.json",
    )

    assert out_path.exists()
    loaded = json.loads(out_path.read_text(encoding="utf-8"))
    assert loaded["data_snapshot_id"] == "snapshot-1"
    assert loaded["seed"] == 42
