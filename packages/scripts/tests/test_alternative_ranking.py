from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.alternative_ranking import (  # noqa: E402
    ALTERNATIVE_RANKING_PRIORITY_RULES,
    rank_race_entries,
)
from shared.prediction_input_schema import (  # noqa: E402
    ALTERNATIVE_RANKING_ALLOWED_FEATURES,  # noqa: E402
)


def _horse(
    chul_no: int,
    *,
    hr_name: str | None = None,
    rating: int | None = None,
    wg_budam: float | None = None,
    horse_top3_skill: float | None = None,
    jk_skill: float | None = None,
    tr_skill: float | None = None,
    training_score: float | None = None,
    recent_training: bool | None = None,
    age_prime: bool | None = None,
    rest_days: float | None = None,
    year_starts: int | None = None,
    year_places: int | None = None,
    total_starts: int | None = None,
    total_places: int | None = None,
    wg_budam_bigo: str | None = None,
    extra_fields: dict | None = None,
    computed_feature_overrides: dict | None = None,
) -> dict:
    hr_detail = {}
    if year_starts is not None:
        hr_detail["rcCntY"] = year_starts
        hr_detail["ord1CntY"] = year_places or 0
        hr_detail["ord2CntY"] = 0
        hr_detail["ord3CntY"] = 0
    if total_starts is not None:
        hr_detail["rcCntT"] = total_starts
        hr_detail["ord1CntT"] = total_places or 0
        hr_detail["ord2CntT"] = 0
        hr_detail["ord3CntT"] = 0

    horse = {
        "chulNo": chul_no,
        "hrNo": f"{chul_no:03d}",
        "hrName": hr_name or f"테스트{chul_no}",
        "rating": rating,
        "wgBudam": wg_budam,
        "wgBudamBigo": wg_budam_bigo,
        "hrDetail": hr_detail,
        "computed_features": {
            "horse_top3_skill": horse_top3_skill,
            "jk_skill": jk_skill,
            "tr_skill": tr_skill,
            "training_score": training_score,
            "recent_training": recent_training,
            "age_prime": age_prime,
            "rest_days": rest_days,
        },
    }
    if computed_feature_overrides:
        horse["computed_features"].update(computed_feature_overrides)
    if extra_fields:
        horse.update(extra_fields)
    return horse


def _top3(
    horses: list[dict], *, model_scores: dict[int, object] | None = None
) -> list[int]:
    ranked = rank_race_entries(horses, model_scores=model_scores)
    return [entry.chul_no for entry in ranked[:3] if entry.chul_no is not None]


@pytest.fixture
def tied_race_fixture() -> list[dict]:
    return [
        _horse(
            7,
            extra_fields={
                "winOdds": 1.1,
                "plcOdds": 1.0,
                "odds_rank": 1,
                "postrace_rank": 1,
            },
        ),
        _horse(
            2,
            extra_fields={
                "winOdds": 99.9,
                "plcOdds": 50.0,
                "winOdds_rr": 0.01,
            },
        ),
        _horse(
            4,
            extra_fields={
                "plcOdds_rr": 0.02,
                "result_sectional_rank": 99,
            },
        ),
        _horse(
            1,
            extra_fields={
                "odds_rank": 99,
                "resultFinalOrd": 12,
            },
        ),
    ]


def test_rank_race_entries_prioritizes_model_score_when_present() -> None:
    horses = [
        _horse(1, horse_top3_skill=0.1, year_starts=10, year_places=1, rating=70),
        _horse(2, horse_top3_skill=0.9, year_starts=10, year_places=5, rating=90),
        _horse(3, horse_top3_skill=0.4, year_starts=10, year_places=3, rating=80),
    ]

    ranked = rank_race_entries(horses, model_scores={1: 0.95, 2: 0.10})

    assert [entry.chul_no for entry in ranked[:3]] == [1, 2, 3]
    assert ranked[0].model_score == 0.95
    assert ranked[1].model_score == 0.10


def test_rank_race_entries_uses_priority_rules_before_rating() -> None:
    horses = [
        _horse(1, horse_top3_skill=0.20, year_starts=12, year_places=2, rating=98),
        _horse(2, horse_top3_skill=0.20, year_starts=12, year_places=6, rating=70),
        _horse(3, horse_top3_skill=0.10, year_starts=12, year_places=1, rating=99),
    ]

    ranked = rank_race_entries(horses)

    assert [entry.chul_no for entry in ranked[:3]] == [2, 1, 3]
    assert (
        ranked[0].rule_values["year_place_rate"]
        > ranked[1].rule_values["year_place_rate"]
    )


def test_rank_race_entries_falls_back_to_deterministic_chulno_order() -> None:
    horses = [_horse(7), _horse(2), _horse(4)]

    ranked = rank_race_entries(horses)

    assert [entry.chul_no for entry in ranked] == [2, 4, 7]


def test_alternative_ranking_priority_rules_use_operational_features_only() -> None:
    rule_features = {
        rule.name
        for rule in ALTERNATIVE_RANKING_PRIORITY_RULES
        if rule.name != "model_score"
    }

    assert rule_features <= set(ALTERNATIVE_RANKING_ALLOWED_FEATURES)
    assert rule_features.isdisjoint(
        {"winOdds", "plcOdds", "odds_rank", "winOdds_rr", "plcOdds_rr"}
    )


def test_rank_race_entries_returns_deterministic_top3_when_scores_missing(
    tied_race_fixture: list[dict],
) -> None:
    invalid_model_scores = {
        7: "nan",
        2: None,
        4: float("inf"),
        1: "not-a-number",
    }

    assert _top3(tied_race_fixture) == [1, 2, 4]
    assert _top3(tied_race_fixture, model_scores=invalid_model_scores) == [1, 2, 4]


def test_rank_race_entries_handles_partial_missing_input_features_with_residual_signals() -> (
    None
):
    horses = [
        _horse(
            1,
            horse_top3_skill=0.45,
            year_starts=10,
            year_places=4,
            rating=88,
            wg_budam=55,
        ),
        _horse(
            2,
            horse_top3_skill=None,
            year_starts=8,
            year_places=4,
            rating=None,
            wg_budam=54,
            computed_feature_overrides={
                "jk_skill": None,
                "tr_skill": None,
                "training_score": None,
                "rest_days": None,
            },
        ),
        _horse(
            3,
            horse_top3_skill=None,
            year_starts=None,
            total_starts=20,
            total_places=6,
            rating=79,
            wg_budam=None,
            computed_feature_overrides={
                "jk_skill": 0.62,
                "tr_skill": 0.41,
                "training_score": None,
                "rest_days": 18,
            },
        ),
        _horse(
            4,
            horse_top3_skill=None,
            year_starts=None,
            total_starts=12,
            total_places=1,
            rating=67,
            wg_budam=57,
            computed_feature_overrides={
                "jk_skill": 0.12,
                "tr_skill": 0.09,
                "training_score": None,
                "rest_days": 45,
            },
        ),
    ]

    assert _top3(horses) == [1, 2, 3]


def test_rank_race_entries_returns_deterministic_top3_when_race_level_features_are_all_missing() -> (
    None
):
    horses = [
        _horse(
            4,
            rating=None,
            wg_budam=None,
            horse_top3_skill=None,
            jk_skill=None,
            tr_skill=None,
            training_score=None,
            recent_training=None,
            age_prime=None,
            rest_days=None,
            year_starts=None,
            total_starts=None,
            extra_fields={"wgBudamBigo": None},
        ),
        _horse(
            1,
            rating=None,
            wg_budam=None,
            horse_top3_skill=None,
            jk_skill=None,
            tr_skill=None,
            training_score=None,
            recent_training=None,
            age_prime=None,
            rest_days=None,
            year_starts=None,
            total_starts=None,
            extra_fields={"wgBudamBigo": None},
        ),
        _horse(
            7,
            rating=None,
            wg_budam=None,
            horse_top3_skill=None,
            jk_skill=None,
            tr_skill=None,
            training_score=None,
            recent_training=None,
            age_prime=None,
            rest_days=None,
            year_starts=None,
            total_starts=None,
            extra_fields={"wgBudamBigo": None},
        ),
        _horse(
            2,
            rating=None,
            wg_budam=None,
            horse_top3_skill=None,
            jk_skill=None,
            tr_skill=None,
            training_score=None,
            recent_training=None,
            age_prime=None,
            rest_days=None,
            year_starts=None,
            total_starts=None,
            extra_fields={"wgBudamBigo": None},
        ),
    ]

    assert _top3(horses) == [1, 2, 4]
    assert _top3(
        horses,
        model_scores={
            4: None,
            1: float("nan"),
            7: float("inf"),
            2: "not-a-number",
        },
    ) == [1, 2, 4]


def test_rank_race_entries_ignores_disallowed_fields_and_keeps_top3_stable(
    tied_race_fixture: list[dict],
) -> None:
    permutations = [
        tied_race_fixture,
        list(reversed(tied_race_fixture)),
        [
            tied_race_fixture[2],
            tied_race_fixture[0],
            tied_race_fixture[3],
            tied_race_fixture[1],
        ],
    ]

    for horses in permutations:
        assert _top3(horses) == [1, 2, 4]
