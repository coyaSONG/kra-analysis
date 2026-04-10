from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from feature_engineering import (  # noqa: E402
    FeatureAvailabilityValidationError,
    compute_features,
    compute_race_features,
)


def _race_horses() -> list[dict]:
    return [
        {
            "chulNo": 1,
            "hrNo": "001",
            "hrName": "테스트1",
            "rating": 90,
            "winOdds": 2.4,
            "wgBudam": 55,
            "wgHr": "490(+1)",
        },
        {
            "chulNo": 2,
            "hrNo": "002",
            "hrName": "테스트2",
            "rating": 85,
            "winOdds": 4.1,
            "wgBudam": 54,
            "wgHr": "480(+0)",
        },
        {
            "chulNo": 3,
            "hrNo": "003",
            "hrName": "테스트3",
            "rating": 80,
            "winOdds": 7.8,
            "wgBudam": 53,
            "wgHr": "470(-1)",
        },
    ]


def test_compute_race_features_excludes_hold_dependent_rank_by_default() -> None:
    horses = compute_race_features(_race_horses())

    assert [horse["computed_features"]["odds_rank"] for horse in horses] == [
        None,
        None,
        None,
    ]
    assert [horse["computed_features"]["rating_rank"] for horse in horses] == [1, 2, 3]


def test_compute_race_features_raise_mode_fails_on_non_operational_input() -> None:
    with pytest.raises(FeatureAvailabilityValidationError) as exc_info:
        compute_race_features(_race_horses(), validation_mode="raise")

    message = str(exc_info.value)
    assert "odds_rank" in message
    assert "horses[].win_odds=HOLD" in message


def test_compute_features_keeps_allowed_snapshot_and_stored_only_sources() -> None:
    horse = {
        "chulNo": 1,
        "rcDate": "20250101",
        "age": 4,
        "ilsu": 12,
        "wgBudam": 55,
        "wgHr": "490(+1)",
        "hrDetail": {
            "rcCntT": 10,
            "ord1CntT": 2,
            "ord2CntT": 1,
            "ord3CntT": 1,
            "rcCntY": 4,
            "ord1CntY": 1,
            "ord2CntY": 1,
            "ord3CntY": 0,
            "totalPrize": 1000000,
        },
        "training": {
            "remkTxt": "양호",
            "trngDt": "20241230",
        },
    }

    features = compute_features(horse)

    assert features["horse_win_rate"] == 20.0
    assert features["horse_top3_skill"] is not None
    assert features["training_score"] == 1
    assert features["training_missing"] is False
    assert features["days_since_training"] == 2


def test_compute_features_preserves_missing_flag_when_training_source_is_allowed() -> (
    None
):
    features = compute_features({"chulNo": 1, "rcDate": "20250101"})

    assert features["training_score"] is None
    assert features["training_missing"] is True
