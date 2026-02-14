#!/usr/bin/env python3
"""
경마 예측을 위한 Feature Engineering 모듈

enriched 경주 데이터에서 파생 피처를 계산합니다.
- 말/기수/조교사 승률 및 입상률
- 부담중량 비율
- 휴양 리스크
- 배당률/레이팅 순위
"""
from __future__ import annotations

from typing import Any


def _safe_get(d: dict | None, key: str, default: Any = None) -> Any:
    """dict에서 안전하게 값을 가져오기. None이나 dict가 아닌 경우 default 반환."""
    if not isinstance(d, dict):
        return default
    return d.get(key, default)


def _safe_div(numerator: float | int | None, denominator: float | int | None) -> float | None:
    """안전한 나눗셈. None이거나 0으로 나누면 None 반환."""
    if numerator is None or denominator is None:
        return None
    try:
        numerator = float(numerator)
        denominator = float(denominator)
    except (TypeError, ValueError):
        return None
    if denominator == 0:
        return None
    return numerator / denominator


def compute_features(horse: dict) -> dict:
    """
    단일 출주마 dict에서 파생 피처를 계산합니다.

    Args:
        horse: enriched 경주 데이터의 개별 말 dict.
               필드: chulNo, winOdds, plcOdds, wgBudam, wgHr, age, sex,
                     rating, rcDist, ilsu, hrDetail, jkDetail, trDetail

    Returns:
        계산된 피처 dict. 계산 불가능한 피처는 None.
    """
    features: dict[str, Any] = {}

    # --- 1. burden_ratio: 부담중량 / 마체중 ---
    wg_budam = horse.get("wgBudam")
    wg_hr = horse.get("wgHr")
    features["burden_ratio"] = _safe_div(wg_budam, wg_hr)

    # --- 2-3. 기수 승률 / 입상률 ---
    jk = horse.get("jkDetail")
    jk_rc = _safe_get(jk, "rcCntT")
    jk_ord1 = _safe_get(jk, "ord1CntT")
    jk_ord2 = _safe_get(jk, "ord2CntT")
    jk_ord3 = _safe_get(jk, "ord3CntT")

    jk_win = _safe_div(jk_ord1, jk_rc)
    features["jockey_win_rate"] = round(jk_win * 100, 2) if jk_win is not None else None

    if jk_rc is not None and jk_ord1 is not None and jk_ord2 is not None and jk_ord3 is not None:
        try:
            jk_place_sum = float(jk_ord1) + float(jk_ord2) + float(jk_ord3)
            jk_place = _safe_div(jk_place_sum, jk_rc)
            features["jockey_place_rate"] = round(jk_place * 100, 2) if jk_place is not None else None
        except (TypeError, ValueError):
            features["jockey_place_rate"] = None
    else:
        features["jockey_place_rate"] = None

    # --- 기수 최근 폼 (winRateY / winRateT) ---
    jk_win_rate_y = _safe_get(jk, "winRateY")
    jk_win_rate_t = _safe_get(jk, "winRateT")
    features["jockey_form"] = _safe_div(jk_win_rate_y, jk_win_rate_t)

    # --- 기수 최근 승률 (ord1CntY / rcCntY) ---
    jk_rc_y = _safe_get(jk, "rcCntY")
    jk_ord1_y = _safe_get(jk, "ord1CntY")
    jk_recent_win = _safe_div(jk_ord1_y, jk_rc_y)
    features["jockey_recent_win_rate"] = round(jk_recent_win * 100, 2) if jk_recent_win is not None else None

    # --- 4-5. 말 승률 / 입상률 ---
    hr = horse.get("hrDetail")
    hr_rc = _safe_get(hr, "rcCntT")
    hr_ord1 = _safe_get(hr, "ord1CntT")
    hr_ord2 = _safe_get(hr, "ord2CntT")
    hr_ord3 = _safe_get(hr, "ord3CntT")

    hr_win = _safe_div(hr_ord1, hr_rc)
    features["horse_win_rate"] = round(hr_win * 100, 2) if hr_win is not None else None

    if hr_rc is not None and hr_ord1 is not None and hr_ord2 is not None and hr_ord3 is not None:
        try:
            hr_place_sum = float(hr_ord1) + float(hr_ord2) + float(hr_ord3)
            hr_place = _safe_div(hr_place_sum, hr_rc)
            features["horse_place_rate"] = round(hr_place * 100, 2) if hr_place is not None else None
        except (TypeError, ValueError):
            features["horse_place_rate"] = None
    else:
        features["horse_place_rate"] = None

    # --- 평균 상금 (totalPrize / rcCntT) ---
    hr_total_prize = _safe_get(hr, "totalPrize")
    features["horse_avg_prize"] = _safe_div(hr_total_prize, hr_rc)

    # --- 6. horse_consistency: 최근 착순의 표준편차 ---
    # hrDetail에 개별 착순 기록이 없으므로, 통산 기록 기반으로
    # 분포를 추정할 수 없는 경우 None 반환
    # (개별 경주 결과 리스트가 있으면 활용 가능)
    features["horse_consistency"] = None

    # --- 7-8. 조교사 승률 / 입상률 ---
    tr = horse.get("trDetail")
    tr_rc = _safe_get(tr, "rcCntT")
    tr_ord1 = _safe_get(tr, "ord1CntT")
    tr_ord2 = _safe_get(tr, "ord2CntT")
    tr_ord3 = _safe_get(tr, "ord3CntT")

    tr_win = _safe_div(tr_ord1, tr_rc)
    features["trainer_win_rate"] = round(tr_win * 100, 2) if tr_win is not None else None

    if tr_rc is not None and tr_ord1 is not None and tr_ord2 is not None and tr_ord3 is not None:
        try:
            tr_place_sum = float(tr_ord1) + float(tr_ord2) + float(tr_ord3)
            tr_place = _safe_div(tr_place_sum, tr_rc)
            features["trainer_place_rate"] = round(tr_place * 100, 2) if tr_place is not None else None
        except (TypeError, ValueError):
            features["trainer_place_rate"] = None
    else:
        features["trainer_place_rate"] = None

    # --- 9-10. 휴양일수 및 리스크 ---
    ilsu = horse.get("ilsu")
    features["rest_days"] = ilsu

    if ilsu is not None:
        try:
            ilsu_val = int(ilsu)
            if ilsu_val > 180:
                features["rest_risk"] = "high"
            elif ilsu_val > 90:
                features["rest_risk"] = "medium"
            else:
                features["rest_risk"] = "low"
        except (TypeError, ValueError):
            features["rest_risk"] = None
    else:
        features["rest_risk"] = None

    # --- 11. age_prime: 전성기 나이 (4~6세) ---
    age = horse.get("age")
    if age is not None:
        try:
            age_val = int(age)
            features["age_prime"] = 4 <= age_val <= 6
        except (TypeError, ValueError):
            features["age_prime"] = None
    else:
        features["age_prime"] = None

    return features


def compute_race_features(horses: list[dict]) -> list[dict]:
    """
    경주 전체 출주마 리스트에 대해 피처를 계산하고 순위 정보를 추가합니다.

    Args:
        horses: 출주마 dict 리스트 (enriched 데이터에서 파싱된 형태)

    Returns:
        각 말에 'computed_features' dict가 추가된 리스트.
        computed_features에는 compute_features 결과 + odds_rank, rating_rank 포함.
    """
    if not horses:
        return horses

    # 1단계: 각 말의 기본 피처 계산
    for horse in horses:
        horse["computed_features"] = compute_features(horse)

    # 2단계: odds_rank 계산 (winOdds 오름차순, 낮을수록 인기)
    # winOdds가 None인 경우 큰 값으로 처리
    odds_sorted = sorted(
        range(len(horses)),
        key=lambda i: float(horses[i].get("winOdds") or 9999),
    )
    for rank, idx in enumerate(odds_sorted, start=1):
        horses[idx]["computed_features"]["odds_rank"] = rank

    # 3단계: rating_rank 계산 (rating 내림차순, 높을수록 좋음)
    # rating이 None인 경우 작은 값으로 처리
    rating_sorted = sorted(
        range(len(horses)),
        key=lambda i: float(horses[i].get("rating") or 0),
        reverse=True,
    )
    for rank, idx in enumerate(rating_sorted, start=1):
        horses[idx]["computed_features"]["rating_rank"] = rank

    return horses
