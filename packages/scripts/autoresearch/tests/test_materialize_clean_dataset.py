from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from autoresearch.dataset_artifacts import (  # noqa: E402
    resolve_offline_evaluation_dataset_artifacts,
)
from autoresearch.materialize_clean_dataset import (
    materialize_clean_dataset,  # noqa: E402
)


def _write_source_artifacts(tmp_path: Path) -> None:
    races = [
        {
            "race_id": "race-clean-v2",
            "race_date": "20250101",
            "meet": "서울",
            "race_info": {
                "rcDate": "20250101",
                "rcNo": "1",
                "rcDist": 1200,
                "computed_features": {"race_level": 99},
            },
            "horses": [
                {
                    "chulNo": 3,
                    "hrNo": "h3",
                    "hrName": "테스트마3",
                    "rating": 0,
                    "ord": 1,
                    "rcTime": "1:12.3",
                    "winOdds": 1.1,
                    "plcOdds": 1.0,
                    "buG1fOrd": 1,
                    "computed_features": {
                        "rating_rank": 1,
                        "raw_array_position": 0,
                    },
                },
                {
                    "chulNo": 1,
                    "hrNo": "h1",
                    "hrName": "테스트마1",
                    "rating": 0,
                    "ord": 2,
                    "rcTime": "1:12.4",
                    "winOdds": 2.2,
                    "plcOdds": 1.1,
                    "buG1fOrd": 2,
                    "computed_features": {"rating_rank": 2},
                },
                {
                    "chulNo": 2,
                    "hrNo": "h2",
                    "hrName": "테스트마2",
                    "rating": 0,
                    "ord": 3,
                    "rcTime": "1:12.5",
                    "winOdds": 3.3,
                    "plcOdds": 1.2,
                    "buG1fOrd": 3,
                    "computed_features": {"rating_rank": 3},
                },
            ],
        }
    ]
    answers = {"race-clean-v2": [3, 1, 2]}
    manifest = {
        "format_version": "holdout-dataset-manifest-v1",
        "dataset": "full_year_2025",
        "created_at": "2026-04-01T00:00:00+00:00",
        "race_count": 1,
        "strict_race_count": 1,
        "dataset_metadata": {
            "source": "test",
            "dataset_name": "full_year_2025",
            "race_ids": ["race-clean-v2"],
        },
        "filter_policy": {"payload_shape": "legacy-race-array"},
        "audit": {"legacy_bootstrap": True},
        "candidate_selection_audit": {"legacy_bootstrap": True},
        "races": [
            {
                "race_id": "race-clean-v2",
                "replay_status": "legacy_snapshot_without_manifest",
                "include_in_strict_dataset": True,
            }
        ],
    }

    (tmp_path / "full_year_2025.json").write_text(
        json.dumps(races, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (tmp_path / "full_year_2025_answer_key.json").write_text(
        json.dumps(answers, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (tmp_path / "full_year_2025_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _contains_key(payload: object, target_key: str) -> bool:
    if isinstance(payload, dict):
        return target_key in payload or any(
            _contains_key(value, target_key) for value in payload.values()
        )
    if isinstance(payload, list):
        return any(_contains_key(item, target_key) for item in payload)
    return False


def test_materialize_clean_dataset_strips_leakage_and_canonicalizes_order(
    tmp_path: Path,
) -> None:
    _write_source_artifacts(tmp_path)

    summary = materialize_clean_dataset(
        artifact_root=tmp_path,
        source_dataset="full_year_2025",
        output_dataset="full_year_2025_prerace_canonical_v2",
    )

    assert summary["race_count"] == 1
    clean_races = json.loads(
        (tmp_path / "full_year_2025_prerace_canonical_v2.json").read_text(
            encoding="utf-8"
        )
    )
    clean_answers = json.loads(
        (tmp_path / "full_year_2025_prerace_canonical_v2_answer_key.json").read_text(
            encoding="utf-8"
        )
    )
    clean_manifest = json.loads(
        (tmp_path / "full_year_2025_prerace_canonical_v2_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert [horse["chulNo"] for horse in clean_races[0]["horses"]] == [1, 2, 3]
    assert clean_answers == {"race-clean-v2": [3, 1, 2]}
    assert clean_manifest["dataset"] == "full_year_2025_prerace_canonical_v2"
    assert clean_manifest["audit"]["canonicalized_prerace_v2"] is True
    assert clean_manifest["audit"]["transform"]["uses_answer_key_for_features"] is False

    for blocked_key in (
        "computed_features",
        "ord",
        "rcTime",
        "winOdds",
        "plcOdds",
        "buG1fOrd",
    ):
        assert not _contains_key(clean_races, blocked_key)

    resolve_offline_evaluation_dataset_artifacts(
        "full_year_2025_prerace_canonical_v2",
        artifact_root=tmp_path,
    )
