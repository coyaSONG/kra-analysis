from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.prediction_input_schema import (
    ALTERNATIVE_RANKING_ALLOWED_FEATURES,  # noqa: E402
)

from autoresearch.dataset_artifacts import (
    OfflineEvaluationDatasetArtifacts,  # noqa: E402
)
from autoresearch.research_clean import (  # noqa: E402
    PredictionCoverageError,
    _build_feature_rows,
    _evaluate_window_with_details,
    _normalize_dataset_before_split,
    _normalize_feature_rows_before_split,
    _predict_top3_for_race,
    _predict_top3_per_race,
    _summarize,
    _validate_features,
    evaluate,
)


def _base_training_race() -> dict[str, object]:
    return {
        "race_id": "20250101_1_1",
        "race_date": "20250101",
        "race_info": {
            "rcDate": "20250101",
            "rcNo": 1,
            "rcDist": 1200,
            "weather": "맑음",
            "track": "건조 (5%)",
            "budam": "별정A",
        },
        "horses": [
            {
                "chulNo": 1,
                "hrNo": "001",
                "hrName": "테스트1",
                "age": 4,
                "sex": "수",
                "rating": 82,
                "wgBudam": 55,
                "wgHr": "490(+1)",
                "computed_features": {
                    "horse_win_rate": 22.0,
                    "horse_place_rate": 44.0,
                },
            },
            {
                "chulNo": 2,
                "hrNo": "002",
                "hrName": "테스트2",
                "age": 4,
                "sex": "암",
                "rating": 79,
                "wgBudam": 54,
                "wgHr": "480(+0)",
                "computed_features": {
                    "horse_win_rate": 18.0,
                    "horse_place_rate": 38.0,
                },
            },
            {
                "chulNo": 3,
                "hrNo": "003",
                "hrName": "테스트3",
                "age": 3,
                "sex": "수",
                "rating": 76,
                "wgBudam": 53,
                "wgHr": "470(-1)",
                "computed_features": {
                    "horse_win_rate": 12.0,
                    "horse_place_rate": 29.0,
                },
            },
        ],
    }


def test_validate_features_rejects_non_operational_inputs() -> None:
    try:
        _validate_features(["rating", "winOdds"])
    except ValueError as exc:
        assert "Non-operational features requested" in str(exc)
        assert "winOdds" in str(exc)
    else:
        raise AssertionError("hold feature must be rejected before model input build")


def test_build_feature_rows_filters_forbidden_source_columns_before_model_input() -> (
    None
):
    race = _base_training_race()
    race["snapshot_meta"] = {"replay_status": "strict"}
    race["horses"][0]["winOdds"] = 2.8
    race["horses"][0]["plcOdds"] = 1.4
    race["horses"][0]["result"] = "1"
    race["horses"][0]["computed_features"]["odds_rank"] = 1
    race["horses"][1]["winOdds"] = 4.1
    race["horses"][1]["plcOdds"] = 1.8
    race["horses"][1]["actual_result"] = [1, 2, 3]
    race["horses"][1]["computed_features"]["odds_rank"] = 2
    race["horses"][2]["winOdds"] = 6.8
    race["horses"][2]["plcOdds"] = 2.6
    race["horses"][2]["computed_features"]["odds_rank"] = 3
    races = [race]

    rows = _build_feature_rows(races, {"20250101_1_1": [1, 2, 3]})

    assert len(rows) == 3
    first = rows[0]
    assert "winOdds" not in first
    assert "plcOdds" not in first
    assert "odds_rank" not in first
    assert first["horse_win_rate"] == 22.0
    assert first["target"] == 1
    assert set(first) == {
        "race_id",
        "race_date",
        "chulNo",
        "target",
        *ALTERNATIVE_RANKING_ALLOWED_FEATURES,
    }


def test_build_feature_rows_fails_fast_when_leakage_survives_sanitization(
    monkeypatch,
) -> None:
    from autoresearch import research_clean

    monkeypatch.setattr(
        research_clean, "_sanitize_training_race_payload", lambda race: deepcopy(race)
    )
    race = _base_training_race()
    race["horses"][0]["actual_result"] = [1, 2, 3]

    with pytest.raises(ValueError) as exc_info:
        _build_feature_rows([race], {"20250101_1_1": [1, 2, 3]})

    message = str(exc_info.value)
    assert "training input leakage check failed" in message
    assert "actual_result" in message


def test_build_feature_rows_fails_fast_when_schema_violation_survives_sanitization(
    monkeypatch,
) -> None:
    from autoresearch import research_clean

    monkeypatch.setattr(
        research_clean, "_sanitize_training_race_payload", lambda race: deepcopy(race)
    )
    race = _base_training_race()
    race["snapshot_meta"] = {"replay_status": "strict"}

    with pytest.raises(ValueError) as exc_info:
        _build_feature_rows([race], {"20250101_1_1": [1, 2, 3]})

    message = str(exc_info.value)
    assert "operational schema validation failed" in message
    assert "snapshot_meta" in message


def test_normalize_dataset_before_split_is_input_order_invariant() -> None:
    late_race = _base_training_race()
    late_race["race_id"] = "20250102_1_2"
    late_race["race_date"] = "20250102"
    late_race["race_info"]["rcDate"] = "20250102"
    late_race["horses"] = [
        {
            "chulNo": 2,
            "hrNo": "002",
            "hrName": "중복-희소",
            "computed_features": {},
        },
        {
            "chulNo": 2,
            "hrNo": "002",
            "hrName": "중복-풍부",
            "age": 4,
            "sex": "암",
            "rating": 79,
            "wgBudam": 54,
            "wgHr": "480(+0)",
            "computed_features": {"horse_win_rate": 18.0},
        },
        {
            "chulNo": 1,
            "hrNo": "001",
            "hrName": "정상1",
            "age": 4,
            "sex": "수",
            "rating": 82,
            "wgBudam": 55,
            "wgHr": "490(+1)",
            "computed_features": {"horse_win_rate": 22.0},
        },
        {
            "hrNo": "MISSING",
            "hrName": "번호없음",
        },
    ]

    early_sparse = _base_training_race()
    early_sparse["horses"][0]["computed_features"] = {}
    early_sparse["horses"][1]["computed_features"] = {}
    early_sparse["horses"][2]["computed_features"] = {}

    early_rich = _base_training_race()
    early_rich["race_date"] = ""
    early_rich["race_info"]["rcDate"] = "20250101"

    races = [late_race, early_sparse, early_rich]
    answers = {
        "20250102_1_2": ["2", 1, 3, 3],
        "20250101_1_1": [1, 2, 3],
    }

    normalized_a = _normalize_dataset_before_split(races, answers)
    normalized_b = _normalize_dataset_before_split(list(reversed(races)), answers)

    races_a, answers_a, summary_a = normalized_a
    races_b, answers_b, summary_b = normalized_b

    assert [race["race_id"] for race in races_a] == ["20250101_1_1", "20250102_1_2"]
    assert [race["race_id"] for race in races_b] == ["20250101_1_1", "20250102_1_2"]
    assert races_a == races_b
    assert answers_a == answers_b
    assert summary_a == summary_b
    assert summary_a["duplicate_race_group_count"] == 1
    assert summary_a["duplicate_horse_group_count"] == 1
    assert summary_a["dropped_horse_without_chul_count"] == 1
    assert [horse["chulNo"] for horse in races_a[1]["horses"]] == [1, 2]
    assert races_a[1]["horses"][1]["hrName"] == "중복-풍부"
    assert answers_a["20250102_1_2"] == [2, 1, 3]


def test_normalize_feature_rows_before_split_sorts_and_dedupes_rows() -> None:
    rows = [
        {
            "race_id": "20250102_1_2",
            "race_date": "20250102",
            "chulNo": 2,
            "target": 1,
            "rating": "",
            "age": 4,
        },
        {
            "race_id": "20250101_1_1",
            "race_date": "20250101",
            "chulNo": 3,
            "target": 0,
            "rating": 77,
            "age": 3,
        },
        {
            "race_id": "20250102_1_2",
            "race_date": "20250102",
            "chulNo": 2,
            "target": 1,
            "rating": 79,
            "age": 4,
        },
    ]

    normalized_rows, summary = _normalize_feature_rows_before_split(rows)

    assert [(row["race_id"], row["chulNo"]) for row in normalized_rows] == [
        ("20250101_1_1", 3),
        ("20250102_1_2", 2),
    ]
    assert normalized_rows[1]["rating"] == 79.0
    assert np.isnan(normalized_rows[0]["wgBudam"])
    assert summary["duplicate_row_group_count"] == 1
    assert summary["duplicate_row_count"] == 1
    assert summary["normalized_row_count"] == 2


def test_predict_top3_for_race_uses_alternative_ranking_when_scores_are_all_invalid() -> (
    None
):
    race_horses = [
        {
            "chulNo": 1,
            "hrNo": "001",
            "hrName": "저입상",
            "rating": 92,
            "wgBudam": 56,
            "hrDetail": {"rcCntY": 10, "ord1CntY": 1, "ord2CntY": 0, "ord3CntY": 0},
            "computed_features": {"horse_top3_skill": 0.20},
        },
        {
            "chulNo": 2,
            "hrNo": "002",
            "hrName": "안정형",
            "rating": 78,
            "wgBudam": 54,
            "hrDetail": {"rcCntY": 10, "ord1CntY": 4, "ord2CntY": 1, "ord3CntY": 1},
            "computed_features": {"horse_top3_skill": 0.20},
        },
        {
            "chulNo": 3,
            "hrNo": "003",
            "hrName": "보통형",
            "rating": 80,
            "wgBudam": 55,
            "hrDetail": {"rcCntY": 10, "ord1CntY": 2, "ord2CntY": 1, "ord3CntY": 1},
            "computed_features": {"horse_top3_skill": 0.10},
        },
    ]

    predicted = _predict_top3_for_race(
        race_horses,
        [(np.nan, 1), (np.inf, 2), (-np.inf, 3)],
    )

    assert predicted == [2, 1, 3]


def test_predict_top3_for_race_merges_partial_model_scores_with_partial_input_fallback() -> (
    None
):
    race_horses = [
        {
            "chulNo": 1,
            "hrNo": "001",
            "hrName": "모델선두",
            "rating": 82,
            "wgBudam": 55,
            "hrDetail": {"rcCntY": 8, "ord1CntY": 2, "ord2CntY": 1, "ord3CntY": 1},
            "computed_features": {
                "horse_top3_skill": 0.28,
                "jk_skill": 0.31,
                "rest_days": 14,
            },
        },
        {
            "chulNo": 2,
            "hrNo": "002",
            "hrName": "연간입상형",
            "rating": None,
            "wgBudam": 54,
            "hrDetail": {"rcCntY": 6, "ord1CntY": 2, "ord2CntY": 1, "ord3CntY": 1},
            "computed_features": {
                "horse_top3_skill": None,
                "jk_skill": None,
                "tr_skill": None,
                "rest_days": None,
            },
        },
        {
            "chulNo": 3,
            "hrNo": "003",
            "hrName": "잔존신호형",
            "rating": 79,
            "wgBudam": None,
            "hrDetail": {"rcCntT": 18, "ord1CntT": 3, "ord2CntT": 2, "ord3CntT": 1},
            "computed_features": {
                "horse_top3_skill": None,
                "jk_skill": 0.57,
                "tr_skill": 0.38,
                "rest_days": 12,
            },
        },
        {
            "chulNo": 4,
            "hrNo": "004",
            "hrName": "후순위",
            "rating": 65,
            "wgBudam": 57,
            "hrDetail": {"rcCntT": 10, "ord1CntT": 0, "ord2CntT": 1, "ord3CntT": 0},
            "computed_features": {
                "horse_top3_skill": None,
                "jk_skill": 0.11,
                "tr_skill": 0.09,
                "rest_days": 44,
            },
        },
    ]

    predicted = _predict_top3_for_race(
        race_horses,
        [(0.91, 1), (np.nan, 2), (np.inf, 3), (-np.inf, 4)],
    )

    assert predicted == [1, 2, 3]


def test_summarize_keeps_exact_rate_when_partial_model_scores_are_invalid() -> None:
    race_lookup = {
        "20250101_1_1": [
            {
                "chulNo": 1,
                "hrNo": "001",
                "hrName": "저입상",
                "rating": 92,
                "wgBudam": 56,
                "hrDetail": {"rcCntY": 10, "ord1CntY": 1, "ord2CntY": 0, "ord3CntY": 0},
                "computed_features": {"horse_top3_skill": 0.20},
            },
            {
                "chulNo": 2,
                "hrNo": "002",
                "hrName": "모델선두",
                "rating": 78,
                "wgBudam": 54,
                "hrDetail": {"rcCntY": 10, "ord1CntY": 4, "ord2CntY": 1, "ord3CntY": 1},
                "computed_features": {"horse_top3_skill": 0.20},
            },
            {
                "chulNo": 3,
                "hrNo": "003",
                "hrName": "대체2위",
                "rating": 80,
                "wgBudam": 55,
                "hrDetail": {"rcCntY": 10, "ord1CntY": 2, "ord2CntY": 1, "ord3CntY": 1},
                "computed_features": {"horse_top3_skill": 0.10},
            },
            {
                "chulNo": 4,
                "hrNo": "004",
                "hrName": "후순위",
                "rating": 74,
                "wgBudam": 57,
                "hrDetail": {"rcCntY": 10, "ord1CntY": 0, "ord2CntY": 0, "ord3CntY": 1},
                "computed_features": {"horse_top3_skill": 0.05},
            },
        ]
    }

    summary = _summarize(
        groups=np.array(
            ["20250101_1_1", "20250101_1_1", "20250101_1_1", "20250101_1_1"]
        ),
        chuls=[1, 2, 3, 4],
        probs=np.array([np.nan, 0.91, np.nan, np.nan]),
        answers={"20250101_1_1": [2, 1, 3]},
        race_lookup=race_lookup,
    )

    assert summary["races"] == 1
    assert summary["exact_3of3"] == 1
    assert summary["exact_3of3_rate"] == 1.0


def test_predict_top3_per_race_keeps_top3_contract_across_mixed_fallback_branches() -> (
    None
):
    race_lookup = {
        "20250101_1_1": [
            {
                "chulNo": 1,
                "hrNo": "001",
                "hrName": "모델선두",
                "rating": 71,
                "wgBudam": 56,
                "hrDetail": {"rcCntY": 10, "ord1CntY": 1, "ord2CntY": 1, "ord3CntY": 1},
                "computed_features": {"horse_top3_skill": 0.10},
            },
            {
                "chulNo": 2,
                "hrNo": "002",
                "hrName": "대체2위",
                "rating": 84,
                "wgBudam": 54,
                "hrDetail": {"rcCntY": 10, "ord1CntY": 4, "ord2CntY": 1, "ord3CntY": 1},
                "computed_features": {"horse_top3_skill": 0.30},
            },
            {
                "chulNo": 3,
                "hrNo": "003",
                "hrName": "모델2위",
                "rating": 73,
                "wgBudam": 55,
                "hrDetail": {"rcCntY": 10, "ord1CntY": 2, "ord2CntY": 1, "ord3CntY": 1},
                "computed_features": {"horse_top3_skill": 0.15},
            },
            {
                "chulNo": 4,
                "hrNo": "004",
                "hrName": "후순위",
                "rating": 66,
                "wgBudam": 57,
                "hrDetail": {"rcCntY": 10, "ord1CntY": 0, "ord2CntY": 0, "ord3CntY": 1},
                "computed_features": {"horse_top3_skill": 0.05},
            },
        ],
        "20250101_1_2": [
            {
                "chulNo": 1,
                "hrNo": "101",
                "hrName": "부분모델선두",
                "rating": 82,
                "wgBudam": 55,
                "hrDetail": {"rcCntY": 8, "ord1CntY": 2, "ord2CntY": 1, "ord3CntY": 1},
                "computed_features": {
                    "horse_top3_skill": 0.28,
                    "jk_skill": 0.31,
                    "rest_days": 14,
                },
            },
            {
                "chulNo": 2,
                "hrNo": "102",
                "hrName": "연간입상형",
                "rating": None,
                "wgBudam": 54,
                "hrDetail": {"rcCntY": 6, "ord1CntY": 2, "ord2CntY": 1, "ord3CntY": 1},
                "computed_features": {
                    "horse_top3_skill": None,
                    "jk_skill": None,
                    "tr_skill": None,
                    "rest_days": None,
                },
            },
            {
                "chulNo": 3,
                "hrNo": "103",
                "hrName": "잔존신호형",
                "rating": 79,
                "wgBudam": None,
                "hrDetail": {"rcCntT": 18, "ord1CntT": 3, "ord2CntT": 2, "ord3CntT": 1},
                "computed_features": {
                    "horse_top3_skill": None,
                    "jk_skill": 0.57,
                    "tr_skill": 0.38,
                    "rest_days": 12,
                },
            },
            {
                "chulNo": 4,
                "hrNo": "104",
                "hrName": "후순위",
                "rating": 65,
                "wgBudam": 57,
                "hrDetail": {"rcCntT": 10, "ord1CntT": 0, "ord2CntT": 1, "ord3CntT": 0},
                "computed_features": {
                    "horse_top3_skill": None,
                    "jk_skill": 0.11,
                    "tr_skill": 0.09,
                    "rest_days": 44,
                },
            },
        ],
        "20250101_1_3": [
            {
                "chulNo": 1,
                "hrNo": "201",
                "hrName": "저입상",
                "rating": 92,
                "wgBudam": 56,
                "hrDetail": {"rcCntY": 10, "ord1CntY": 1, "ord2CntY": 0, "ord3CntY": 0},
                "computed_features": {"horse_top3_skill": 0.20},
            },
            {
                "chulNo": 2,
                "hrNo": "202",
                "hrName": "안정형",
                "rating": 78,
                "wgBudam": 54,
                "hrDetail": {"rcCntY": 10, "ord1CntY": 4, "ord2CntY": 1, "ord3CntY": 1},
                "computed_features": {"horse_top3_skill": 0.20},
            },
            {
                "chulNo": 3,
                "hrNo": "203",
                "hrName": "보통형",
                "rating": 80,
                "wgBudam": 55,
                "hrDetail": {"rcCntY": 10, "ord1CntY": 2, "ord2CntY": 1, "ord3CntY": 1},
                "computed_features": {"horse_top3_skill": 0.10},
            },
            {
                "chulNo": 4,
                "hrNo": "204",
                "hrName": "후순위",
                "rating": 74,
                "wgBudam": 57,
                "hrDetail": {"rcCntY": 10, "ord1CntY": 0, "ord2CntY": 0, "ord3CntY": 1},
                "computed_features": {"horse_top3_skill": 0.05},
            },
        ],
    }
    groups = np.array(
        [
            "20250101_1_1",
            "20250101_1_1",
            "20250101_1_1",
            "20250101_1_1",
            "20250101_1_2",
            "20250101_1_2",
            "20250101_1_2",
            "20250101_1_2",
            "20250101_1_3",
            "20250101_1_3",
            "20250101_1_3",
            "20250101_1_3",
            "20250101_1_4",
            "20250101_1_4",
            "20250101_1_4",
            "20250101_1_4",
        ]
    )
    chuls = [1, 2, 3, 4, 1, 2, 3, 4, 1, 2, 3, 4, 5, 4, 9, 2]
    probs = np.array(
        [
            0.95,
            0.52,
            0.88,
            0.10,
            0.91,
            np.nan,
            np.inf,
            -np.inf,
            np.nan,
            np.inf,
            -np.inf,
            "nan",
            0.80,
            np.nan,
            0.60,
            None,
        ],
        dtype=float,
    )

    predicted_by_race = _predict_top3_per_race(
        groups,
        chuls,
        probs,
        race_lookup=race_lookup,
    )

    assert predicted_by_race == {
        "20250101_1_1": [1, 3, 2],
        "20250101_1_2": [1, 2, 3],
        "20250101_1_3": [2, 1, 3],
        "20250101_1_4": [5, 9, 2],
    }
    for predicted in predicted_by_race.values():
        assert len(predicted) == 3
        assert len(set(predicted)) == 3
        assert all(isinstance(chul_no, int) for chul_no in predicted)


def test_evaluate_window_with_details_raises_when_prediction_coverage_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from autoresearch import research_clean

    class DummyModel:
        def fit(self, X, y, **kwargs):
            return self

        def predict_proba(self, X):
            return np.array(
                [
                    [0.1, 0.9],
                    [0.2, 0.8],
                ]
            )

    monkeypatch.setattr(
        research_clean, "_make_model", lambda model_parameters: DummyModel()
    )
    monkeypatch.setattr(
        research_clean,
        "_predict_top3_per_race",
        lambda groups, chuls, probs, race_lookup=None: {"20250101_1_1": [1, 2, 3]},
    )

    with pytest.raises(PredictionCoverageError, match="20250101_1_2"):
        _evaluate_window_with_details(
            X=np.zeros((4, 1), dtype=float),
            y=np.array([1, 0, 1, 0]),
            groups=np.array(
                ["20241231_1_1", "20241231_1_1", "20250101_1_1", "20250101_1_2"]
            ),
            dates=np.array(["20241231", "20241231", "20250101", "20250101"]),
            chuls=[1, 2, 1, 2],
            answers={
                "20250101_1_1": [1, 2, 3],
                "20250101_1_2": [1, 2, 3],
            },
            race_lookup={},
            model_parameters=SimpleNamespace(positive_class_weight=1.0),
            train_end="20241231",
            eval_start="20250101",
            eval_end=None,
        )


def test_summarize_aggregates_multi_race_batch_with_mixed_fallback_branches() -> None:
    race_lookup = {
        "20250101_1_1": [
            {
                "chulNo": 1,
                "hrNo": "001",
                "hrName": "모델선두",
                "rating": 71,
                "wgBudam": 56,
                "hrDetail": {"rcCntY": 10, "ord1CntY": 1, "ord2CntY": 1, "ord3CntY": 1},
                "computed_features": {"horse_top3_skill": 0.10},
            },
            {
                "chulNo": 2,
                "hrNo": "002",
                "hrName": "대체2위",
                "rating": 84,
                "wgBudam": 54,
                "hrDetail": {"rcCntY": 10, "ord1CntY": 4, "ord2CntY": 1, "ord3CntY": 1},
                "computed_features": {"horse_top3_skill": 0.30},
            },
            {
                "chulNo": 3,
                "hrNo": "003",
                "hrName": "모델2위",
                "rating": 73,
                "wgBudam": 55,
                "hrDetail": {"rcCntY": 10, "ord1CntY": 2, "ord2CntY": 1, "ord3CntY": 1},
                "computed_features": {"horse_top3_skill": 0.15},
            },
            {
                "chulNo": 4,
                "hrNo": "004",
                "hrName": "후순위",
                "rating": 66,
                "wgBudam": 57,
                "hrDetail": {"rcCntY": 10, "ord1CntY": 0, "ord2CntY": 0, "ord3CntY": 1},
                "computed_features": {"horse_top3_skill": 0.05},
            },
        ],
        "20250101_1_2": [
            {
                "chulNo": 1,
                "hrNo": "101",
                "hrName": "부분모델선두",
                "rating": 82,
                "wgBudam": 55,
                "hrDetail": {"rcCntY": 8, "ord1CntY": 2, "ord2CntY": 1, "ord3CntY": 1},
                "computed_features": {
                    "horse_top3_skill": 0.28,
                    "jk_skill": 0.31,
                    "rest_days": 14,
                },
            },
            {
                "chulNo": 2,
                "hrNo": "102",
                "hrName": "연간입상형",
                "rating": None,
                "wgBudam": 54,
                "hrDetail": {"rcCntY": 6, "ord1CntY": 2, "ord2CntY": 1, "ord3CntY": 1},
                "computed_features": {
                    "horse_top3_skill": None,
                    "jk_skill": None,
                    "tr_skill": None,
                    "rest_days": None,
                },
            },
            {
                "chulNo": 3,
                "hrNo": "103",
                "hrName": "잔존신호형",
                "rating": 79,
                "wgBudam": None,
                "hrDetail": {"rcCntT": 18, "ord1CntT": 3, "ord2CntT": 2, "ord3CntT": 1},
                "computed_features": {
                    "horse_top3_skill": None,
                    "jk_skill": 0.57,
                    "tr_skill": 0.38,
                    "rest_days": 12,
                },
            },
            {
                "chulNo": 4,
                "hrNo": "104",
                "hrName": "후순위",
                "rating": 65,
                "wgBudam": 57,
                "hrDetail": {"rcCntT": 10, "ord1CntT": 0, "ord2CntT": 1, "ord3CntT": 0},
                "computed_features": {
                    "horse_top3_skill": None,
                    "jk_skill": 0.11,
                    "tr_skill": 0.09,
                    "rest_days": 44,
                },
            },
        ],
        "20250101_1_3": [
            {
                "chulNo": 1,
                "hrNo": "201",
                "hrName": "저입상",
                "rating": 92,
                "wgBudam": 56,
                "hrDetail": {"rcCntY": 10, "ord1CntY": 1, "ord2CntY": 0, "ord3CntY": 0},
                "computed_features": {"horse_top3_skill": 0.20},
            },
            {
                "chulNo": 2,
                "hrNo": "202",
                "hrName": "안정형",
                "rating": 78,
                "wgBudam": 54,
                "hrDetail": {"rcCntY": 10, "ord1CntY": 4, "ord2CntY": 1, "ord3CntY": 1},
                "computed_features": {"horse_top3_skill": 0.20},
            },
            {
                "chulNo": 3,
                "hrNo": "203",
                "hrName": "보통형",
                "rating": 80,
                "wgBudam": 55,
                "hrDetail": {"rcCntY": 10, "ord1CntY": 2, "ord2CntY": 1, "ord3CntY": 1},
                "computed_features": {"horse_top3_skill": 0.10},
            },
            {
                "chulNo": 4,
                "hrNo": "204",
                "hrName": "후순위",
                "rating": 74,
                "wgBudam": 57,
                "hrDetail": {"rcCntY": 10, "ord1CntY": 0, "ord2CntY": 0, "ord3CntY": 1},
                "computed_features": {"horse_top3_skill": 0.05},
            },
        ],
    }

    summary = _summarize(
        groups=np.array(
            [
                "20250101_1_1",
                "20250101_1_1",
                "20250101_1_1",
                "20250101_1_1",
                "20250101_1_2",
                "20250101_1_2",
                "20250101_1_2",
                "20250101_1_2",
                "20250101_1_3",
                "20250101_1_3",
                "20250101_1_3",
                "20250101_1_3",
                "20250101_1_4",
                "20250101_1_4",
                "20250101_1_4",
                "20250101_1_4",
            ]
        ),
        chuls=[1, 2, 3, 4, 1, 2, 3, 4, 1, 2, 3, 4, 5, 4, 9, 2],
        probs=np.array(
            [
                0.95,
                0.52,
                0.88,
                0.10,
                0.91,
                np.nan,
                np.inf,
                -np.inf,
                np.nan,
                np.inf,
                -np.inf,
                "nan",
                0.80,
                np.nan,
                0.60,
                None,
            ],
            dtype=float,
        ),
        answers={
            "20250101_1_1": [1, 3, 2],
            "20250101_1_2": [1, 2, 3],
            "20250101_1_3": [2, 1, 3],
            "20250101_1_4": [5, 2, 7],
        },
        race_lookup=race_lookup,
    )

    assert summary == {
        "races": 4,
        "exact_3of3": 3,
        "exact_3of3_rate": 0.75,
        "hit_2of3": 1,
        "hit_1of3": 0,
        "miss_0of3": 0,
        "avg_set_match": 0.916667,
    }


def test_evaluate_includes_dataset_selection_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from autoresearch import research_clean

    manifest_path = tmp_path / "holdout_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "races": [
                    {"race_id": "race-2"},
                    {"race_id": "race-1"},
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    artifacts = OfflineEvaluationDatasetArtifacts(
        dataset="holdout",
        artifact_root=tmp_path,
        dataset_path=tmp_path / "holdout.json",
        answer_key_path=tmp_path / "holdout_answer_key.json",
        manifest_path=manifest_path,
    )

    monkeypatch.setattr(
        research_clean,
        "resolve_offline_evaluation_dataset_artifacts",
        lambda dataset, artifact_root: artifacts,
    )
    monkeypatch.setattr(
        research_clean, "_load_dataset", lambda dataset_artifacts: ([], {})
    )
    monkeypatch.setattr(
        research_clean,
        "_normalize_dataset_before_split",
        lambda races, answers: (races, answers, {}),
    )
    monkeypatch.setattr(
        research_clean,
        "_build_feature_rows",
        lambda races, answers: [
            {
                "race_id": "race-1",
                "race_date": "20250101",
                "chulNo": 1,
                "target": 1,
                "rating": 82.0,
            }
        ],
    )
    monkeypatch.setattr(
        research_clean,
        "_normalize_feature_rows_before_split",
        lambda rows: (rows, {}),
    )
    monkeypatch.setattr(
        research_clean,
        "_build_arrays",
        lambda rows, features: (
            np.zeros((1, len(features)), dtype=float),
            np.array([1]),
            np.array(["race-1"]),
            np.array(["20250101"]),
            [1],
        ),
    )

    class DummySplitPlan:
        primary_split = SimpleNamespace(
            train_end="20241231",
            dev_end="20250101",
            test_start="20250101",
        )
        rolling_windows: tuple[object, ...] = ()

    monkeypatch.setattr(
        research_clean,
        "build_temporal_split_plan",
        lambda dates, config: DummySplitPlan(),
    )
    monkeypatch.setattr(
        research_clean,
        "_evaluate_window_with_details",
        lambda **kwargs: {
            "summary": {
                "exact_3of3_rate": 0.75,
                "avg_set_match": 0.75,
                "races": 1,
            },
            "prediction_rows": [
                {
                    "race_id": "race-1",
                    "predicted_top3_unordered": [1, 2, 3],
                    "actual_top3_unordered": [1, 2, 3],
                    "hit_count": 3,
                    "exact_match": True,
                }
            ],
            "window": {
                "train_end": "20241231",
                "eval_start": "20250101",
                "eval_end": None,
            },
        },
    )

    class DummyContext:
        config_path = str(tmp_path / "config.json")
        config = {
            "dataset": "holdout",
            "features": ["rating"],
            "split": {
                "train_end": "20241231",
                "dev_end": "20250101",
                "test_start": "20250101",
            },
            "model": {"kind": "hgb", "params": {"max_depth": 6}},
        }
        model_parameters = SimpleNamespace(
            model_dump=lambda mode="json": {
                "kind": "hgb",
                "params": {"max_depth": 6},
                "random_state": 11,
            }
        )
        input_contract = None

        def runtime_params_dict(self) -> dict[str, int]:
            return {"model_random_state": 11}

        def model_dump(self, mode: str = "json") -> dict[str, object]:
            return {
                "config_path": self.config_path,
                "runtime_params": {"model_random_state": 11},
            }

    result = evaluate(
        Path(DummyContext.config_path),
        evaluation_context=DummyContext(),
    )

    assert result["dataset_selection"]["expected_race_count"] == 2
    assert result["dataset_selection"]["final_race_ids"] == ["race-2", "race-1"]
    assert len(result["dataset_selection"]["source_artifact_sha256"]) == 64
    assert result["_reproducibility_artifacts"]["prediction_rows"]["dataset_selection"][
        "final_race_ids"
    ] == ["race-2", "race-1"]
    assert (
        result["_reproducibility_artifacts"]["metrics_summary"]["dataset_selection"][
            "expected_race_count"
        ]
        == 2
    )
