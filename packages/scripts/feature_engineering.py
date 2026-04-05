#!/usr/bin/env python3
"""
경마 예측을 위한 Feature Engineering 모듈

enriched 경주 데이터에서 파생 피처를 계산합니다.
- 말/기수/조교사 승률 및 입상률
- 부담중량 비율
- 휴양 리스크
- 배당률/레이팅 순위
- (v2) 신뢰도 가중 blend, jkStats, training, owner, race-relative
"""

from __future__ import annotations

from typing import Any


def _safe_get(d: dict | None, key: str, default: Any = None) -> Any:
    """dict에서 안전하게 값을 가져오기. None이나 dict가 아닌 경우 default 반환."""
    if not isinstance(d, dict):
        return default
    return d.get(key, default)


def _safe_div(
    numerator: float | int | None, denominator: float | int | None
) -> float | None:
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


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _blend(
    rate_y: float | None, n_y: int | None, rate_t: float | None, k: int
) -> float | None:
    """연도/통산 성적 신뢰도 가중 블렌딩.

    표본이 적을수록 통산(rate_t)에 가까워지고,
    표본이 많을수록 올해(rate_y)를 더 믿는다.
    """
    if rate_t is None:
        return rate_y
    if rate_y is None:
        return rate_t
    if n_y is None or n_y < 0:
        return rate_t
    w = n_y / (n_y + k)
    return w * rate_y + (1 - w) * rate_t


def _place_rate(ord1: Any, ord2: Any, ord3: Any, rc: Any) -> float | None:
    """입상률(1~3위 비율) 계산."""
    if rc is None or ord1 is None or ord2 is None or ord3 is None:
        return None
    try:
        total = float(ord1) + float(ord2) + float(ord3)
        starts = float(rc)
    except (TypeError, ValueError):
        return None
    if starts == 0:
        return None
    return total / starts


def compute_features(horse: dict) -> dict:
    """
    단일 출주마 dict에서 파생 피처를 계산합니다.

    Args:
        horse: enriched 경주 데이터의 개별 말 dict.
               필드: chulNo, winOdds, plcOdds, wgBudam, wgHr, age, sex,
                     rating, rcDist, ilsu, hrDetail, jkDetail, trDetail,
                     jkStats, owDetail, training (optional, from new APIs)

    Returns:
        계산된 피처 dict. 계산 불가능한 피처는 None.
    """
    features: dict[str, Any] = {}

    # --- 1. burden_ratio: 부담중량 / 마체중 ---
    wg_budam = horse.get("wgBudam")
    wg_hr = horse.get("wgHr")
    features["burden_ratio"] = _safe_div(wg_budam, wg_hr)

    # --- 2-3. 기수 승률 / 입상률 (jkDetail) ---
    jk = horse.get("jkDetail")
    jk_rc = _safe_get(jk, "rcCntT")
    jk_ord1 = _safe_get(jk, "ord1CntT")
    jk_ord2 = _safe_get(jk, "ord2CntT")
    jk_ord3 = _safe_get(jk, "ord3CntT")

    jk_win = _safe_div(jk_ord1, jk_rc)
    features["jockey_win_rate"] = round(jk_win * 100, 2) if jk_win is not None else None

    jk_place = _place_rate(jk_ord1, jk_ord2, jk_ord3, jk_rc)
    features["jockey_place_rate"] = (
        round(jk_place * 100, 2) if jk_place is not None else None
    )

    # --- 기수 최근 폼 (winRateY / winRateT) ---
    jk_win_rate_y = _safe_get(jk, "winRateY")
    jk_win_rate_t = _safe_get(jk, "winRateT")
    features["jockey_form"] = _safe_div(jk_win_rate_y, jk_win_rate_t)

    # --- 기수 최근 승률 (ord1CntY / rcCntY) ---
    jk_rc_y = _safe_get(jk, "rcCntY")
    jk_ord1_y = _safe_get(jk, "ord1CntY")
    jk_recent_win = _safe_div(jk_ord1_y, jk_rc_y)
    features["jockey_recent_win_rate"] = (
        round(jk_recent_win * 100, 2) if jk_recent_win is not None else None
    )

    # --- 4-5. 말 승률 / 입상률 ---
    hr = horse.get("hrDetail")
    hr_rc = _safe_get(hr, "rcCntT")
    hr_ord1 = _safe_get(hr, "ord1CntT")
    hr_ord2 = _safe_get(hr, "ord2CntT")
    hr_ord3 = _safe_get(hr, "ord3CntT")

    hr_win = _safe_div(hr_ord1, hr_rc)
    features["horse_win_rate"] = round(hr_win * 100, 2) if hr_win is not None else None

    hr_place = _place_rate(hr_ord1, hr_ord2, hr_ord3, hr_rc)
    features["horse_place_rate"] = (
        round(hr_place * 100, 2) if hr_place is not None else None
    )

    # --- 평균 상금 (totalPrize / rcCntT) ---
    hr_total_prize = _safe_get(hr, "totalPrize")
    features["horse_avg_prize"] = _safe_div(hr_total_prize, hr_rc)

    # --- 6. horse_consistency: (개별 착순 기록 없어 None) ---
    features["horse_consistency"] = None

    # --- 최근 top3 통계 (past_stats에서 주입) ---
    past = horse.get("past_stats")
    if past and isinstance(past, dict):
        features["recent_top3_rate"] = past.get("recent_top3_rate")
        features["recent_win_rate"] = past.get("recent_win_rate")
        features["recent_race_count"] = past.get("recent_race_count")
    else:
        features["recent_top3_rate"] = None
        features["recent_win_rate"] = None
        features["recent_race_count"] = None

    # --- 7-8. 조교사 승률 / 입상률 ---
    tr = horse.get("trDetail")
    tr_rc = _safe_get(tr, "rcCntT")
    tr_ord1 = _safe_get(tr, "ord1CntT")
    tr_ord2 = _safe_get(tr, "ord2CntT")
    tr_ord3 = _safe_get(tr, "ord3CntT")

    tr_win = _safe_div(tr_ord1, tr_rc)
    features["trainer_win_rate"] = (
        round(tr_win * 100, 2) if tr_win is not None else None
    )

    tr_place = _place_rate(tr_ord1, tr_ord2, tr_ord3, tr_rc)
    features["trainer_place_rate"] = (
        round(tr_place * 100, 2) if tr_place is not None else None
    )

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

    # ================================================================
    # v2 피처: 신규 API 데이터 (없으면 None으로 graceful degradation)
    # ================================================================

    # --- 12. 신뢰도 가중 blend: 말 top3 스킬 ---
    hr_rc_y = _safe_get(hr, "rcCntY")
    hr_ord1_y = _safe_get(hr, "ord1CntY")
    hr_ord2_y = _safe_get(hr, "ord2CntY")
    hr_ord3_y = _safe_get(hr, "ord3CntY")

    hr_place_t = _place_rate(hr_ord1, hr_ord2, hr_ord3, hr_rc)
    hr_place_y = _place_rate(hr_ord1_y, hr_ord2_y, hr_ord3_y, hr_rc_y)

    features["horse_top3_skill"] = _blend(
        hr_place_y, _safe_int(hr_rc_y, 0), hr_place_t, k=3
    )
    features["horse_starts_y"] = _safe_int(hr_rc_y, 0) if hr_rc_y is not None else None
    features["horse_low_sample"] = (
        _safe_int(hr_rc_y, 0) < 3 if hr_rc_y is not None else True
    )

    # --- 13. jkStats 기반 기수 스킬 (API11_1, jkDetail과 별도) ---
    jks = horse.get("jkStats")
    if jks and isinstance(jks, dict):
        jks_qnl_y = _safe_get(jks, "qnlRateY")
        jks_qnl_t = _safe_get(jks, "qnlRateT")
        jks_rc_y = _safe_get(jks, "rcCntY")
        features["jk_qnl_rate_y"] = (
            _safe_float(jks_qnl_y) if jks_qnl_y is not None else None
        )
        features["jk_qnl_rate_t"] = (
            _safe_float(jks_qnl_t) if jks_qnl_t is not None else None
        )
        features["jk_skill"] = _blend(
            _safe_float(jks_qnl_y, 0.0) / 100 if jks_qnl_y is not None else None,
            _safe_int(jks_rc_y, 0),
            _safe_float(jks_qnl_t, 0.0) / 100 if jks_qnl_t is not None else None,
            k=15,
        )
    else:
        features["jk_qnl_rate_y"] = None
        features["jk_qnl_rate_t"] = None
        # jkDetail 기반 폴백
        jk_place_t = _place_rate(jk_ord1, jk_ord2, jk_ord3, jk_rc)
        jk_ord1_y_val = _safe_get(jk, "ord1CntY")
        jk_ord2_y_val = _safe_get(jk, "ord2CntY")
        jk_ord3_y_val = _safe_get(jk, "ord3CntY")
        jk_place_y = _place_rate(jk_ord1_y_val, jk_ord2_y_val, jk_ord3_y_val, jk_rc_y)
        features["jk_skill"] = _blend(
            jk_place_y, _safe_int(jk_rc_y, 0), jk_place_t, k=15
        )

    # --- 14. 조교사 blend 스킬 ---
    tr_rc_y = _safe_get(tr, "rcCntY")
    tr_ord1_y = _safe_get(tr, "ord1CntY")
    tr_ord2_y = _safe_get(tr, "ord2CntY")
    tr_ord3_y = _safe_get(tr, "ord3CntY")

    tr_place_t = _place_rate(tr_ord1, tr_ord2, tr_ord3, tr_rc)
    tr_place_y = _place_rate(tr_ord1_y, tr_ord2_y, tr_ord3_y, tr_rc_y)

    features["tr_skill"] = _blend(tr_place_y, _safe_int(tr_rc_y, 0), tr_place_t, k=20)

    # --- 15. Training 피처 (API329) ---
    training = horse.get("training")
    if training and isinstance(training, dict):
        remk = _safe_get(training, "remkTxt", "")
        score_map = {"양호": 1, "보통": 0, "불량": -1}
        features["training_score"] = score_map.get(str(remk).strip(), None)
        features["training_missing"] = False

        trng_dt = _safe_get(training, "trngDt")
        race_date = horse.get("rcDate")
        if trng_dt and race_date:
            try:
                from datetime import datetime

                td = datetime.strptime(str(trng_dt)[:8], "%Y%m%d")
                rd = datetime.strptime(str(race_date)[:8], "%Y%m%d")
                days = (rd - td).days
                features["days_since_training"] = max(0, days)
                features["recent_training"] = days <= 3
            except (ValueError, TypeError):
                features["days_since_training"] = None
                features["recent_training"] = None
        else:
            features["days_since_training"] = None
            features["recent_training"] = None
    else:
        features["training_score"] = None
        features["training_missing"] = True
        features["days_since_training"] = None
        features["recent_training"] = None

    # --- 16. Owner 피처 (API14_1) ---
    ow = horse.get("owDetail")
    if ow and isinstance(ow, dict):
        ow_rc_t = _safe_get(ow, "rcCntT")
        ow_ord1_t = _safe_get(ow, "ord1CntT")
        ow_rc_y = _safe_get(ow, "rcCntY")
        ow_ord1_y = _safe_get(ow, "ord1CntY")

        ow_win_t = _safe_div(ow_ord1_t, ow_rc_t)
        ow_win_y = _safe_div(ow_ord1_y, ow_rc_y)
        features["owner_win_rate"] = (
            round(ow_win_t * 100, 2) if ow_win_t is not None else None
        )
        features["owner_skill"] = _blend(
            ow_win_y, _safe_int(ow_rc_y, 0), ow_win_t, k=30
        )
    else:
        features["owner_win_rate"] = None
        features["owner_skill"] = None

    return features


def compute_race_features(horses: list[dict]) -> list[dict]:
    """
    경주 전체 출주마 리스트에 대해 피처를 계산하고 순위 정보를 추가합니다.

    Args:
        horses: 출주마 dict 리스트 (enriched 데이터에서 파싱된 형태)

    Returns:
        각 말에 'computed_features' dict가 추가된 리스트.
        computed_features에는 compute_features 결과 + race-relative 피처 포함.
    """
    if not horses:
        return horses

    n = len(horses)

    # 1단계: 각 말의 기본 피처 계산
    for horse in horses:
        horse["computed_features"] = compute_features(horse)

    # 2단계: race-relative rankings
    def _rank_by(key_fn, reverse=False):
        """경주 내 순위 계산. 값이 None이면 최하위."""
        indexed = []
        for i, h in enumerate(horses):
            val = key_fn(h)
            indexed.append((i, val))
        default = float("-inf") if reverse else float("inf")
        indexed.sort(
            key=lambda x: x[1] if x[1] is not None else default, reverse=reverse
        )
        ranks = [0] * n
        for rank, (idx, _) in enumerate(indexed, start=1):
            ranks[idx] = rank
        return ranks

    # odds_rank (winOdds 오름차순, 낮을수록 인기)
    odds_ranks = _rank_by(lambda h: _safe_float(h.get("winOdds"), 9999))
    # rating_rank (rating 내림차순, 높을수록 좋음)
    rating_ranks = _rank_by(lambda h: _safe_float(h.get("rating"), 0), reverse=True)
    # horse_top3_skill_rank (내림차순)
    skill_ranks = _rank_by(
        lambda h: h["computed_features"].get("horse_top3_skill"), reverse=True
    )
    # jk_skill_rank (내림차순)
    jk_ranks = _rank_by(lambda h: h["computed_features"].get("jk_skill"), reverse=True)
    # tr_skill_rank (내림차순)
    tr_ranks = _rank_by(lambda h: h["computed_features"].get("tr_skill"), reverse=True)
    # wg_budam_rank (부담중량 오름차순, 낮을수록 유리)
    budam_ranks = _rank_by(lambda h: _safe_float(h.get("wgBudam"), 999))

    for i, horse in enumerate(horses):
        cf = horse["computed_features"]
        cf["odds_rank"] = odds_ranks[i]
        cf["rating_rank"] = rating_ranks[i]
        cf["horse_skill_rank"] = skill_ranks[i]
        cf["jk_skill_rank"] = jk_ranks[i]
        cf["tr_skill_rank"] = tr_ranks[i]
        cf["wg_budam_rank"] = budam_ranks[i]

    # 3단계: gap features (상위 3위와 4위 사이 격차)
    skills = []
    for h in horses:
        s = h["computed_features"].get("horse_top3_skill")
        skills.append(s if s is not None else 0.0)
    skills_sorted = sorted(skills, reverse=True)
    gap_3rd_4th = skills_sorted[2] - skills_sorted[3] if n >= 4 else None

    for horse in horses:
        horse["computed_features"]["gap_3rd_4th"] = gap_3rd_4th

    # 4단계: race context features
    field_size = n

    # wet track: 주로상태에서 추론 (첫 번째 말의 track 필드)
    track_val = horses[0].get("track", "") if horses else ""
    wet_track = track_val in ("불량", "습", "다습") if track_val else False

    # cancelled horses count (cancelledHorses 필드가 있으면)
    cancelled = horses[0].get("cancelledHorses")
    if cancelled and isinstance(cancelled, list):
        cancelled_count = len(cancelled)
    else:
        cancelled_count = 0

    for horse in horses:
        cf = horse["computed_features"]
        cf["field_size"] = field_size
        cf["field_size_live"] = field_size - cancelled_count
        cf["wet_track"] = wet_track
        cf["cancelled_count"] = cancelled_count

    return horses
