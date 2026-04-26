from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from autoresearch.t30_release_evaluation import run_t30_release_evaluation


def _horse(chul_no: int, *, rating: float, weight_delta: float) -> dict[str, object]:
    recent_count = float(chul_no + 2)
    return {
        "chulNo": chul_no,
        "age": 3,
        "class_rank": "국6",
        "rating": rating,
        "sex": "수",
        "wgBudam": 55.0,
        "wgHr": f"450({weight_delta:+.0f})",
        "weight_delta": weight_delta,
        "hrDetail": {"rcCntT": 10, "rcCntY": 3},
        "jkDetail": {"ord1CntT": 1, "ord2CntT": 1, "ord3CntT": 1, "rcCntT": 10},
        "trDetail": {"ord1CntT": 1, "ord2CntT": 1, "ord3CntT": 1, "rcCntT": 10},
        "computed_features": {
            "cancelled_count": 0.0,
            "field_size_live": 4.0,
            "jk_skill": 99.0,
            "recent_race_count": recent_count,
            "recent_win_count": 1.0,
            "recent_win_rate": 1.0 / recent_count,
            "recent_top3_count": 2.0,
            "recent_top3_rate": 2.0 / recent_count,
        },
    }


def _race(
    race_id: str, race_date: str, ratings: tuple[float, float, float, float]
) -> dict[str, object]:
    return {
        "race_id": race_id,
        "race_date": race_date,
        "race_info": {
            "rcDate": race_date,
            "rcNo": 1,
            "rcDist": 1200,
            "track": "건조",
            "weather": "맑음",
            "meet": "서울",
            "budam": "별정A",
        },
        "horses": [
            _horse(chul_no, rating=rating, weight_delta=float(chul_no - 2))
            for chul_no, rating in enumerate(ratings, start=1)
        ],
        "snapshot_meta": {
            "operational_cutoff_status": {
                "passed": True,
                "reason": "ok",
                "scheduled_start_at": "2025-01-01T11:00:00+09:00",
                "operational_cutoff_at": "2025-01-01T10:30:00+09:00",
                "source_snapshot_at": "2025-01-01T10:00:00+09:00",
            },
            "entry_change_audit": {"source_present": False},
        },
    }


def test_run_t30_release_evaluation_removes_backfill_only_config_features(
    tmp_path: Path,
) -> None:
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    mini = [
        _race("20250101_1_1", "20250101", (90.0, 80.0, 70.0, 10.0)),
        _race("20250102_1_1", "20250102", (88.0, 82.0, 72.0, 20.0)),
    ]
    holdout = [
        _race("20250103_1_1", "20250103", (91.0, 81.0, 71.0, 11.0)),
        _race("20250104_1_1", "20250104", (89.0, 83.0, 73.0, 21.0)),
    ]
    answer_key = {
        "mini_val": {str(race["race_id"]): [1, 2, 3] for race in mini},
        "holdout": {str(race["race_id"]): [1, 2, 3] for race in holdout},
    }
    (snapshot_dir / "mini_val.json").write_text(
        json.dumps(mini, ensure_ascii=False),
        encoding="utf-8",
    )
    (snapshot_dir / "holdout.json").write_text(
        json.dumps(holdout, ensure_ascii=False),
        encoding="utf-8",
    )
    (snapshot_dir / "answer_key.json").write_text(
        json.dumps(answer_key, ensure_ascii=False),
        encoding="utf-8",
    )
    config_path = tmp_path / "clean_model_config.json"
    config_path.write_text(
        json.dumps({"features": ["rating", "jk_skill"]}),
        encoding="utf-8",
    )

    report = run_t30_release_evaluation(
        snapshot_dir=snapshot_dir,
        config_path=config_path,
    )

    assert report["removed_config_features"] == ["jk_skill"]
    assert report["baseline"]["features"] == ["rating"]
    assert "jk_skill" not in report["release"]["features"]
    assert "recent_top3_rate" in report["release"]["features"]
    assert "weight_delta" in report["release"]["features"]
    assert report["gate"]["passed"] is True
    assert report["release"]["test_race_count"] == 2
