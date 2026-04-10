from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from autoresearch.dataset_artifacts import (  # noqa: E402
    load_offline_evaluation_dataset,
    resolve_offline_evaluation_dataset_artifacts,
)
from autoresearch.holdout_dataset import build_dataset_manifest  # noqa: E402


def _snapshot_meta(*, race_id: str, race_date: str = "20250101") -> dict:
    entry_finalized_at = "2025-01-01T10:35:00+09:00"
    return {
        "race_id": race_id,
        "format_version": "holdout-snapshot-v1",
        "rule_version": "holdout-entry-finalization-rule-v1",
        "source_filter_basis": "entry_finalized_at",
        "scheduled_start_at": "2025-01-01T11:00:00+09:00",
        "operational_cutoff_at": "2025-01-01T10:50:00+09:00",
        "snapshot_ready_at": entry_finalized_at,
        "entry_finalized_at": entry_finalized_at,
        "selected_timestamp_field": "basic_data.collected_at",
        "selected_timestamp_value": entry_finalized_at,
        "timestamp_source": "snapshot_collected_at",
        "timestamp_confidence": "medium",
        "revision_id": None,
        "late_reissue_after_cutoff": False,
        "cutoff_unbounded": False,
        "replay_status": "strict",
        "include_in_strict_dataset": True,
        "hard_required_sources_present": True,
        "hard_required_source_status": {
            "API214_1": "present",
            "API72_2": "present",
            "API189_1": "present",
            "API9_1": "present",
        },
        "source_lookup": {
            "race_id": race_id,
            "race_date": race_date,
            "entry_snapshot_at": entry_finalized_at,
        },
    }


def _race_payload(*, race_id: str) -> dict:
    return {
        "race_id": race_id,
        "race_date": "20250101",
        "meet": "서울",
        "race_info": {
            "rcDate": "20250101",
            "rcNo": "1",
            "rcDist": 1200,
            "track": "건조",
            "weather": "맑음",
            "meet": "서울",
        },
        "horses": [
            {
                "chulNo": 1,
                "hrName": "테스트마1",
                "computed_features": {"horse_win_rate": 0.1},
            },
            {
                "chulNo": 2,
                "hrName": "테스트마2",
                "computed_features": {"horse_win_rate": 0.2},
            },
            {
                "chulNo": 3,
                "hrName": "테스트마3",
                "computed_features": {"horse_win_rate": 0.3},
            },
        ],
        "snapshot_meta": _snapshot_meta(race_id=race_id),
    }


def _write_dataset_artifacts(
    tmp_path: Path, *, dataset: str, races: list[dict], answers: dict
) -> None:
    timing_rows = [race["snapshot_meta"] for race in races]
    (tmp_path / f"{dataset}.json").write_text(
        json.dumps(races, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (tmp_path / f"{dataset}_answer_key.json").write_text(
        json.dumps(answers, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (tmp_path / f"{dataset}_manifest.json").write_text(
        json.dumps(
            build_dataset_manifest(
                mode=dataset,
                created_at="2026-04-10T12:00:00+09:00",
                races=timing_rows,
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def test_load_offline_evaluation_dataset_uses_only_separated_artifacts(
    tmp_path: Path,
) -> None:
    race = _race_payload(race_id="race-separated")
    _write_dataset_artifacts(
        tmp_path,
        dataset="holdout",
        races=[race],
        answers={"race-separated": [1, 2, 3]},
    )
    (tmp_path / "answer_key.json").write_text(
        json.dumps({"holdout": {"race-legacy": [9, 8, 7]}}, ensure_ascii=False),
        encoding="utf-8",
    )

    artifacts = resolve_offline_evaluation_dataset_artifacts(
        "holdout",
        artifact_root=tmp_path,
    )
    races, answers = load_offline_evaluation_dataset(artifacts)

    assert races == [race]
    assert answers == {"race-separated": [1, 2, 3]}


def test_resolve_offline_evaluation_dataset_artifacts_requires_manifest_match(
    tmp_path: Path,
) -> None:
    (tmp_path / "holdout.json").write_text("[]", encoding="utf-8")
    (tmp_path / "holdout_answer_key.json").write_text("{}", encoding="utf-8")
    (tmp_path / "holdout_manifest.json").write_text(
        json.dumps({"dataset": "mini_val"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError, match="dataset manifest does not match requested dataset"
    ):
        resolve_offline_evaluation_dataset_artifacts(
            "holdout",
            artifact_root=tmp_path,
        )


def test_resolve_offline_evaluation_dataset_artifacts_rejects_post_cutoff_snapshot_metadata(
    tmp_path: Path,
) -> None:
    race = _race_payload(race_id="race-post-cutoff")
    race["snapshot_meta"]["entry_finalized_at"] = "2025-01-01T10:55:00+09:00"
    race["snapshot_meta"]["snapshot_ready_at"] = "2025-01-01T10:55:00+09:00"
    race["snapshot_meta"]["source_lookup"]["entry_snapshot_at"] = (
        "2025-01-01T10:55:00+09:00"
    )
    _write_dataset_artifacts(
        tmp_path,
        dataset="holdout",
        races=[race],
        answers={"race-post-cutoff": [1, 2, 3]},
    )

    with pytest.raises(ValueError, match="timing audit failed"):
        resolve_offline_evaluation_dataset_artifacts(
            "holdout",
            artifact_root=tmp_path,
        )


def test_resolve_offline_evaluation_dataset_artifacts_rejects_temporal_manifest_mismatch(
    tmp_path: Path,
) -> None:
    race = _race_payload(race_id="race-mismatch")
    _write_dataset_artifacts(
        tmp_path,
        dataset="holdout",
        races=[race],
        answers={"race-mismatch": [1, 2, 3]},
    )

    manifest_path = tmp_path / "holdout_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["races"][0]["entry_finalized_at"] = "2025-01-01T10:40:00+09:00"
    manifest["races"][0]["snapshot_ready_at"] = "2025-01-01T10:40:00+09:00"
    manifest["audit"] = {
        "passed": True,
        "violations": [],
        "violation_counts": {},
        "checked_races": 1,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    with pytest.raises(
        ValueError, match="snapshot_meta does not match manifest timing record"
    ):
        resolve_offline_evaluation_dataset_artifacts(
            "holdout",
            artifact_root=tmp_path,
        )
