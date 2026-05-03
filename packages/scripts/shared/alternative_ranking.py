"""출전표 확정 시점 정보만으로 단일 경주를 결정론적으로 정렬하는 대체 랭킹 모듈."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RankingRule:
    name: str
    direction: str
    description: str


@dataclass(frozen=True, slots=True)
class RankedEntry:
    rank: int
    horse: dict[str, Any]
    chul_no: int | None
    hr_name: str
    model_score: float | None
    rule_values: dict[str, Any]


ALTERNATIVE_RANKING_PRIORITY_RULES: tuple[RankingRule, ...] = (
    RankingRule(
        name="model_score",
        direction="desc",
        description="모델 점수가 존재하면 최우선으로 사용하며, 값이 높을수록 앞선다.",
    ),
    RankingRule(
        name="horse_top3_skill",
        direction="desc",
        description="말 자체의 축소 추정 top3 스킬이 높을수록 앞선다.",
    ),
    RankingRule(
        name="year_place_rate",
        direction="desc",
        description="연간 입상률이 높을수록 앞선다.",
    ),
    RankingRule(
        name="total_place_rate",
        direction="desc",
        description="통산 입상률이 높을수록 앞선다.",
    ),
    RankingRule(
        name="jk_skill",
        direction="desc",
        description="기수 스킬이 높을수록 앞선다.",
    ),
    RankingRule(
        name="tr_skill",
        direction="desc",
        description="조교사 스킬이 높을수록 앞선다.",
    ),
    RankingRule(
        name="rating",
        direction="desc",
        description="사전 레이팅이 높을수록 앞선다.",
    ),
    RankingRule(
        name="training_score",
        direction="desc",
        description="직전 조교 상태 점수가 높을수록 앞선다.",
    ),
    RankingRule(
        name="recent_training",
        direction="desc",
        description="최근 조교 이력이 있으면 앞선다.",
    ),
    RankingRule(
        name="age_prime",
        direction="desc",
        description="전성기 연령대로 판단되면 앞선다.",
    ),
    RankingRule(
        name="allowance_flag",
        direction="desc",
        description="감량 표시가 있으면 앞선다.",
    ),
    RankingRule(
        name="wgBudam",
        direction="asc",
        description="부담중량이 낮을수록 앞선다.",
    ),
    RankingRule(
        name="rest_days",
        direction="asc",
        description="휴양일수가 짧을수록 앞선다.",
    ),
)

ALTERNATIVE_RANKING_TIEBREAK_RULES: tuple[RankingRule, ...] = (
    RankingRule(
        name="chulNo",
        direction="asc",
        description="최종 동률이면 출전번호가 낮을수록 앞선다.",
    ),
    RankingRule(
        name="hrNo",
        direction="asc",
        description="출전번호까지 같으면 마번 문자열 오름차순으로 고정한다.",
    ),
)


def _safe_float(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _safe_int(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _place_rate(
    ord1: object, ord2: object, ord3: object, total: object
) -> float | None:
    total_count = _safe_float(total)
    if total_count is None or total_count <= 0:
        return None
    ord1_value = _safe_float(ord1) or 0.0
    ord2_value = _safe_float(ord2) or 0.0
    ord3_value = _safe_float(ord3) or 0.0
    return (ord1_value + ord2_value + ord3_value) / total_count


def _year_place_rate(horse: Mapping[str, Any]) -> float | None:
    detail = horse.get("hrDetail") or {}
    starts_y = _safe_int(detail.get("rcCntY"))
    if starts_y is not None and starts_y > 0:
        places_y = (
            (_safe_int(detail.get("ord1CntY")) or 0)
            + (_safe_int(detail.get("ord2CntY")) or 0)
            + (_safe_int(detail.get("ord3CntY")) or 0)
        )
        return places_y / (starts_y + 2)
    return _total_place_rate(horse)


def _total_place_rate(horse: Mapping[str, Any]) -> float | None:
    detail = horse.get("hrDetail") or {}
    starts_t = _safe_int(detail.get("rcCntT"))
    if starts_t is None or starts_t < 0:
        return None
    places_t = (
        (_safe_int(detail.get("ord1CntT")) or 0)
        + (_safe_int(detail.get("ord2CntT")) or 0)
        + (_safe_int(detail.get("ord3CntT")) or 0)
    )
    return places_t / (starts_t + 15)


def _bool_score(value: object) -> float | None:
    if value is True:
        return 1.0
    if value is False:
        return 0.0
    return None


def _score_component_desc(value: object) -> tuple[int, float]:
    number = _safe_float(value)
    if number is None:
        return (1, 0.0)
    return (0, -number)


def _score_component_asc(value: object) -> tuple[int, float]:
    number = _safe_float(value)
    if number is None:
        return (1, 0.0)
    return (0, number)


def _extract_rule_values(
    horse: Mapping[str, Any],
    *,
    model_scores: Mapping[int, object] | None,
) -> dict[str, Any]:
    computed = horse.get("computed_features") or {}
    chul_no = _safe_int(horse.get("chulNo"))
    model_score = None
    if model_scores is not None and chul_no is not None and chul_no in model_scores:
        model_score = _safe_float(model_scores[chul_no])

    return {
        "model_score": model_score,
        "horse_top3_skill": _safe_float(computed.get("horse_top3_skill")),
        "year_place_rate": _year_place_rate(horse),
        "total_place_rate": _total_place_rate(horse),
        "jk_skill": _safe_float(computed.get("jk_skill")),
        "tr_skill": _safe_float(computed.get("tr_skill")),
        "rating": _safe_float(horse.get("rating")),
        "training_score": _safe_float(computed.get("training_score")),
        "recent_training": _bool_score(computed.get("recent_training")),
        "age_prime": _bool_score(computed.get("age_prime")),
        "allowance_flag": 1.0 if str(horse.get("wgBudamBigo") or "") == "*" else 0.0,
        "wgBudam": _safe_float(horse.get("wgBudam")),
        "rest_days": _safe_float(computed.get("rest_days")),
        "chulNo": chul_no,
        "hrNo": str(horse.get("hrNo") or ""),
    }


def _build_sort_key(rule_values: Mapping[str, Any]) -> tuple[Any, ...]:
    model_score = rule_values["model_score"]
    chul_no = rule_values["chulNo"]
    hr_no = rule_values["hrNo"]

    return (
        0 if model_score is not None else 1,
        -model_score if model_score is not None else 0.0,
        *_score_component_desc(rule_values["horse_top3_skill"]),
        *_score_component_desc(rule_values["year_place_rate"]),
        *_score_component_desc(rule_values["total_place_rate"]),
        *_score_component_desc(rule_values["jk_skill"]),
        *_score_component_desc(rule_values["tr_skill"]),
        *_score_component_desc(rule_values["rating"]),
        *_score_component_desc(rule_values["training_score"]),
        *_score_component_desc(rule_values["recent_training"]),
        *_score_component_desc(rule_values["age_prime"]),
        *_score_component_desc(rule_values["allowance_flag"]),
        *_score_component_asc(rule_values["wgBudam"]),
        *_score_component_asc(rule_values["rest_days"]),
        chul_no if chul_no is not None else 10**9,
        hr_no,
    )


def rank_race_entries(
    horses: Sequence[dict[str, Any]],
    *,
    model_scores: Mapping[int, object] | None = None,
) -> list[RankedEntry]:
    """단일 경주의 전체 출전마를 운영 규칙에 따라 결정론적으로 정렬한다."""

    prepared: list[tuple[tuple[Any, ...], dict[str, Any], dict[str, Any]]] = []
    for horse in horses:
        rule_values = _extract_rule_values(horse, model_scores=model_scores)
        prepared.append((_build_sort_key(rule_values), dict(horse), rule_values))

    prepared.sort(key=lambda item: item[0])

    ranked: list[RankedEntry] = []
    for index, (_sort_key, horse, rule_values) in enumerate(prepared, start=1):
        ranked.append(
            RankedEntry(
                rank=index,
                horse=horse,
                chul_no=rule_values["chulNo"],
                hr_name=str(horse.get("hrName") or ""),
                model_score=rule_values["model_score"],
                rule_values=rule_values,
            )
        )
    return ranked
