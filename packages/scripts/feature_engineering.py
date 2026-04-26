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

from shared.prerace_field_policy import ALLOWED_FLAGS, resolve_train_inference_flag

FEATURE_TIMING_VALIDATION_MODES = frozenset({"exclude", "raise", "off"})

# 각 피처가 의존하는 canonical 입력 경로. 여러 튜플은 fallback 그룹을 의미한다.
_FEATURE_SOURCE_PATHS: dict[str, tuple[tuple[str, ...], ...]] = {
    "burden_ratio": (("horses[].wg_budam", "horses[].wg_hr"),),
    "jockey_win_rate": (("horses[].jkDetail",),),
    "jockey_place_rate": (("horses[].jkDetail",),),
    "jockey_form": (("horses[].jkDetail",),),
    "jockey_recent_win_rate": (("horses[].jkDetail",),),
    "horse_win_rate": (("horses[].hrDetail",),),
    "horse_place_rate": (("horses[].hrDetail",),),
    "horse_avg_prize": (("horses[].hrDetail",),),
    "recent_top3_rate": (("horses[].past_stats",),),
    "recent_win_rate": (("horses[].past_stats",),),
    "recent_race_count": (("horses[].past_stats",),),
    "trainer_win_rate": (("horses[].trDetail",),),
    "trainer_place_rate": (("horses[].trDetail",),),
    "rest_days": (("horses[].ilsu",),),
    "rest_risk": (("horses[].ilsu",),),
    "age_prime": (("horses[].age",),),
    "horse_top3_skill": (("horses[].hrDetail",),),
    "horse_starts_y": (("horses[].hrDetail",),),
    "horse_low_sample": (("horses[].hrDetail",),),
    "jk_qnl_rate_y": (("horses[].jkStats",),),
    "jk_qnl_rate_t": (("horses[].jkStats",),),
    "jk_skill": (("horses[].jkStats",), ("horses[].jkDetail",)),
    "tr_skill": (("horses[].trDetail",),),
    "training_score": (("horses[].training",),),
    "training_missing": (("horses[].training",),),
    "days_since_training": (("horses[].training",),),
    "recent_training": (("horses[].training",),),
    "owner_win_rate": (("horses[].owDetail",),),
    "owner_skill": (("horses[].owDetail",),),
}

_RACE_FEATURE_SOURCE_PATHS: dict[str, tuple[tuple[str, ...], ...]] = {
    "odds_rank": (("horses[].win_odds",),),
    "rating_rank": (("horses[].rating",),),
    "horse_skill_rank": (("horses[].hrDetail",),),
    "jk_skill_rank": (("horses[].jkStats",), ("horses[].jkDetail",)),
    "tr_skill_rank": (("horses[].trDetail",),),
    "wg_budam_rank": (("horses[].wg_budam",),),
    "gap_3rd_4th": (("horses[].hrDetail",),),
    "field_size": (("horses[].chul_no",),),
    "field_size_live": (("cancelled_horses",),),
    "wet_track": (("track.track",),),
    "cancelled_count": (("cancelled_horses",),),
}


class FeatureAvailabilityValidationError(ValueError):
    """출전표 확정 시점 이후/보류 입력 의존 피처가 계산될 때 발생."""


def _validate_validation_mode(mode: str) -> str:
    if mode not in FEATURE_TIMING_VALIDATION_MODES:
        raise ValueError(
            f"unsupported validation_mode: {mode}. "
            f"expected one of {sorted(FEATURE_TIMING_VALIDATION_MODES)}"
        )
    return mode


def _dependency_report(
    dependency_groups: tuple[tuple[str, ...], ...],
) -> list[dict[str, Any]]:
    report: list[dict[str, Any]] = []
    for group in dependency_groups:
        flags = {path: resolve_train_inference_flag(path) for path in group}
        blocked = {
            path: flag for path, flag in flags.items() if flag not in ALLOWED_FLAGS
        }
        report.append(
            {
                "paths": group,
                "flags": flags,
                "blocked": blocked,
                "allowed": not blocked,
            }
        )
    return report


def _feature_allowed(
    feature_name: str,
    *,
    validation_mode: str,
    source_paths: dict[str, tuple[tuple[str, ...], ...]],
) -> bool:
    if validation_mode == "off":
        return True

    dependency_groups = source_paths.get(feature_name, ())
    if not dependency_groups:
        return True

    report = _dependency_report(dependency_groups)
    if any(group["allowed"] for group in report):
        return True

    if validation_mode == "raise":
        detail = "; ".join(
            ", ".join(f"{path}={flag}" for path, flag in group["blocked"].items())
            for group in report
        )
        raise FeatureAvailabilityValidationError(
            f"feature '{feature_name}' depends on non-operational columns: {detail}"
        )

    return False


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


def compute_features(horse: dict, *, validation_mode: str = "exclude") -> dict:
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
    validation_mode = _validate_validation_mode(validation_mode)
    features: dict[str, Any] = {}

    # --- 1. burden_ratio: 부담중량 / 마체중 ---
    if _feature_allowed(
        "burden_ratio",
        validation_mode=validation_mode,
        source_paths=_FEATURE_SOURCE_PATHS,
    ):
        wg_budam = horse.get("wgBudam")
        wg_hr = horse.get("wgHr")
        features["burden_ratio"] = _safe_div(wg_budam, wg_hr)
    else:
        features["burden_ratio"] = None

    # --- 2-3. 기수 승률 / 입상률 (jkDetail) ---
    jk = horse.get("jkDetail")
    jk_rc = _safe_get(jk, "rcCntT")
    jk_ord1 = _safe_get(jk, "ord1CntT")
    jk_ord2 = _safe_get(jk, "ord2CntT")
    jk_ord3 = _safe_get(jk, "ord3CntT")

    jk_rc_y = _safe_get(jk, "rcCntY")
    if _feature_allowed(
        "jockey_win_rate",
        validation_mode=validation_mode,
        source_paths=_FEATURE_SOURCE_PATHS,
    ):
        jk_win = _safe_div(jk_ord1, jk_rc)
        features["jockey_win_rate"] = (
            round(jk_win * 100, 2) if jk_win is not None else None
        )

        jk_place = _place_rate(jk_ord1, jk_ord2, jk_ord3, jk_rc)
        features["jockey_place_rate"] = (
            round(jk_place * 100, 2) if jk_place is not None else None
        )

        # --- 기수 최근 폼 (winRateY / winRateT) ---
        jk_win_rate_y = _safe_get(jk, "winRateY")
        jk_win_rate_t = _safe_get(jk, "winRateT")
        features["jockey_form"] = _safe_div(jk_win_rate_y, jk_win_rate_t)

        # --- 기수 최근 승률 (ord1CntY / rcCntY) ---
        jk_ord1_y = _safe_get(jk, "ord1CntY")
        jk_recent_win = _safe_div(jk_ord1_y, jk_rc_y)
        features["jockey_recent_win_rate"] = (
            round(jk_recent_win * 100, 2) if jk_recent_win is not None else None
        )
    else:
        features["jockey_win_rate"] = None
        features["jockey_place_rate"] = None
        features["jockey_form"] = None
        features["jockey_recent_win_rate"] = None

    # --- 4-5. 말 승률 / 입상률 ---
    hr = horse.get("hrDetail")
    hr_rc = _safe_get(hr, "rcCntT")
    hr_ord1 = _safe_get(hr, "ord1CntT")
    hr_ord2 = _safe_get(hr, "ord2CntT")
    hr_ord3 = _safe_get(hr, "ord3CntT")

    if _feature_allowed(
        "horse_win_rate",
        validation_mode=validation_mode,
        source_paths=_FEATURE_SOURCE_PATHS,
    ):
        hr_win = _safe_div(hr_ord1, hr_rc)
        features["horse_win_rate"] = (
            round(hr_win * 100, 2) if hr_win is not None else None
        )

        hr_place = _place_rate(hr_ord1, hr_ord2, hr_ord3, hr_rc)
        features["horse_place_rate"] = (
            round(hr_place * 100, 2) if hr_place is not None else None
        )

        # --- 평균 상금 (totalPrize / rcCntT) ---
        hr_total_prize = _safe_get(hr, "totalPrize")
        features["horse_avg_prize"] = _safe_div(hr_total_prize, hr_rc)
    else:
        features["horse_win_rate"] = None
        features["horse_place_rate"] = None
        features["horse_avg_prize"] = None

    # --- 6. horse_consistency: (개별 착순 기록 없어 None) ---
    features["horse_consistency"] = None

    # --- 최근 top3 통계 (past_stats에서 주입) ---
    past = horse.get("past_stats")
    if (
        _feature_allowed(
            "recent_top3_rate",
            validation_mode=validation_mode,
            source_paths=_FEATURE_SOURCE_PATHS,
        )
        and past
        and isinstance(past, dict)
    ):
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

    if _feature_allowed(
        "trainer_win_rate",
        validation_mode=validation_mode,
        source_paths=_FEATURE_SOURCE_PATHS,
    ):
        tr_win = _safe_div(tr_ord1, tr_rc)
        features["trainer_win_rate"] = (
            round(tr_win * 100, 2) if tr_win is not None else None
        )

        tr_place = _place_rate(tr_ord1, tr_ord2, tr_ord3, tr_rc)
        features["trainer_place_rate"] = (
            round(tr_place * 100, 2) if tr_place is not None else None
        )
    else:
        features["trainer_win_rate"] = None
        features["trainer_place_rate"] = None

    # --- 9-10. 휴양일수 및 리스크 ---
    ilsu = horse.get("ilsu")
    if _feature_allowed(
        "rest_days",
        validation_mode=validation_mode,
        source_paths=_FEATURE_SOURCE_PATHS,
    ):
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
    else:
        features["rest_days"] = None
        features["rest_risk"] = None

    # --- 11. age_prime: 전성기 나이 (4~6세) ---
    age = horse.get("age")
    if (
        _feature_allowed(
            "age_prime",
            validation_mode=validation_mode,
            source_paths=_FEATURE_SOURCE_PATHS,
        )
        and age is not None
    ):
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

    if _feature_allowed(
        "horse_top3_skill",
        validation_mode=validation_mode,
        source_paths=_FEATURE_SOURCE_PATHS,
    ):
        hr_place_t = _place_rate(hr_ord1, hr_ord2, hr_ord3, hr_rc)
        hr_place_y = _place_rate(hr_ord1_y, hr_ord2_y, hr_ord3_y, hr_rc_y)

        features["horse_top3_skill"] = _blend(
            hr_place_y, _safe_int(hr_rc_y, 0), hr_place_t, k=3
        )
        features["horse_starts_y"] = (
            _safe_int(hr_rc_y, 0) if hr_rc_y is not None else None
        )
        features["horse_low_sample"] = (
            _safe_int(hr_rc_y, 0) < 3 if hr_rc_y is not None else True
        )
    else:
        features["horse_top3_skill"] = None
        features["horse_starts_y"] = None
        features["horse_low_sample"] = None

    # --- 13. jkStats 기반 기수 스킬 (API11_1, jkDetail과 별도) ---
    jks = horse.get("jkStats")
    if (
        _feature_allowed(
            "jk_skill",
            validation_mode=validation_mode,
            source_paths=_FEATURE_SOURCE_PATHS,
        )
        and jks
        and isinstance(jks, dict)
    ):
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
    elif _feature_allowed(
        "jk_skill",
        validation_mode=validation_mode,
        source_paths=_FEATURE_SOURCE_PATHS,
    ):
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
    else:
        features["jk_qnl_rate_y"] = None
        features["jk_qnl_rate_t"] = None
        features["jk_skill"] = None

    # --- 14. 조교사 blend 스킬 ---
    tr_rc_y = _safe_get(tr, "rcCntY")
    tr_ord1_y = _safe_get(tr, "ord1CntY")
    tr_ord2_y = _safe_get(tr, "ord2CntY")
    tr_ord3_y = _safe_get(tr, "ord3CntY")

    if _feature_allowed(
        "tr_skill",
        validation_mode=validation_mode,
        source_paths=_FEATURE_SOURCE_PATHS,
    ):
        tr_place_t = _place_rate(tr_ord1, tr_ord2, tr_ord3, tr_rc)
        tr_place_y = _place_rate(tr_ord1_y, tr_ord2_y, tr_ord3_y, tr_rc_y)

        features["tr_skill"] = _blend(
            tr_place_y, _safe_int(tr_rc_y, 0), tr_place_t, k=20
        )
    else:
        features["tr_skill"] = None

    # --- 15. Training 피처 (API329) ---
    training = horse.get("training")
    training_allowed = _feature_allowed(
        "training_score",
        validation_mode=validation_mode,
        source_paths=_FEATURE_SOURCE_PATHS,
    )
    if training_allowed and training and isinstance(training, dict):
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
    elif training_allowed:
        features["training_score"] = None
        features["training_missing"] = True
        features["days_since_training"] = None
        features["recent_training"] = None
    else:
        features["training_score"] = None
        features["training_missing"] = None
        features["days_since_training"] = None
        features["recent_training"] = None

    # --- 16. Owner 피처 (API14_1) ---
    ow = horse.get("owDetail")
    if (
        _feature_allowed(
            "owner_win_rate",
            validation_mode=validation_mode,
            source_paths=_FEATURE_SOURCE_PATHS,
        )
        and ow
        and isinstance(ow, dict)
    ):
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


def compute_race_features(
    horses: list[dict], *, validation_mode: str = "exclude"
) -> list[dict]:
    """
    경주 전체 출주마 리스트에 대해 피처를 계산하고 순위 정보를 추가합니다.

    Args:
        horses: 출주마 dict 리스트 (enriched 데이터에서 파싱된 형태)

    Returns:
        각 말에 'computed_features' dict가 추가된 리스트.
        computed_features에는 compute_features 결과 + race-relative 피처 포함.
    """
    validation_mode = _validate_validation_mode(validation_mode)
    if not horses:
        return horses

    n = len(horses)

    # 1단계: 각 말의 기본 피처 계산
    for horse in horses:
        horse["computed_features"] = compute_features(
            horse,
            validation_mode=validation_mode,
        )

    # 2단계: race-relative rankings
    def _rank_by(key_fn, reverse=False):
        """경주 내 dense rank. 동점은 같은 순위로 둔다."""
        default = float("-inf") if reverse else float("inf")
        values = []
        for horse in horses:
            value = key_fn(horse)
            values.append(value if value is not None else default)
        ordered_values = sorted(set(values), reverse=reverse)
        rank_by_value = {
            value: rank for rank, value in enumerate(ordered_values, start=1)
        }
        return [rank_by_value[value] for value in values]

    # odds_rank (winOdds 오름차순, 낮을수록 인기)
    odds_rank_allowed = _feature_allowed(
        "odds_rank",
        validation_mode=validation_mode,
        source_paths=_RACE_FEATURE_SOURCE_PATHS,
    )
    rating_rank_allowed = _feature_allowed(
        "rating_rank",
        validation_mode=validation_mode,
        source_paths=_RACE_FEATURE_SOURCE_PATHS,
    )
    horse_skill_rank_allowed = _feature_allowed(
        "horse_skill_rank",
        validation_mode=validation_mode,
        source_paths=_RACE_FEATURE_SOURCE_PATHS,
    )
    jk_skill_rank_allowed = _feature_allowed(
        "jk_skill_rank",
        validation_mode=validation_mode,
        source_paths=_RACE_FEATURE_SOURCE_PATHS,
    )
    tr_skill_rank_allowed = _feature_allowed(
        "tr_skill_rank",
        validation_mode=validation_mode,
        source_paths=_RACE_FEATURE_SOURCE_PATHS,
    )
    wg_budam_rank_allowed = _feature_allowed(
        "wg_budam_rank",
        validation_mode=validation_mode,
        source_paths=_RACE_FEATURE_SOURCE_PATHS,
    )
    gap_feature_allowed = _feature_allowed(
        "gap_3rd_4th",
        validation_mode=validation_mode,
        source_paths=_RACE_FEATURE_SOURCE_PATHS,
    )
    field_size_allowed = _feature_allowed(
        "field_size",
        validation_mode=validation_mode,
        source_paths=_RACE_FEATURE_SOURCE_PATHS,
    )
    field_size_live_allowed = _feature_allowed(
        "field_size_live",
        validation_mode=validation_mode,
        source_paths=_RACE_FEATURE_SOURCE_PATHS,
    )
    wet_track_allowed = _feature_allowed(
        "wet_track",
        validation_mode=validation_mode,
        source_paths=_RACE_FEATURE_SOURCE_PATHS,
    )
    cancelled_count_allowed = _feature_allowed(
        "cancelled_count",
        validation_mode=validation_mode,
        source_paths=_RACE_FEATURE_SOURCE_PATHS,
    )

    if odds_rank_allowed:
        odds_ranks = _rank_by(lambda h: _safe_float(h.get("winOdds"), 9999))
    else:
        odds_ranks = None
    # rating_rank (rating 내림차순, 높을수록 좋음)
    rating_ranks = (
        _rank_by(lambda h: _safe_float(h.get("rating"), 0), reverse=True)
        if rating_rank_allowed
        else None
    )
    # horse_top3_skill_rank (내림차순)
    skill_ranks = (
        _rank_by(lambda h: h["computed_features"].get("horse_top3_skill"), reverse=True)
        if horse_skill_rank_allowed
        else None
    )
    # jk_skill_rank (내림차순)
    jk_ranks = (
        _rank_by(lambda h: h["computed_features"].get("jk_skill"), reverse=True)
        if jk_skill_rank_allowed
        else None
    )
    # tr_skill_rank (내림차순)
    tr_ranks = (
        _rank_by(lambda h: h["computed_features"].get("tr_skill"), reverse=True)
        if tr_skill_rank_allowed
        else None
    )
    # wg_budam_rank (부담중량 오름차순, 낮을수록 유리)
    budam_ranks = (
        _rank_by(lambda h: _safe_float(h.get("wgBudam"), 999))
        if wg_budam_rank_allowed
        else None
    )

    for i, horse in enumerate(horses):
        cf = horse["computed_features"]
        cf["odds_rank"] = odds_ranks[i] if odds_ranks is not None else None
        cf["rating_rank"] = rating_ranks[i] if rating_ranks is not None else None
        cf["horse_skill_rank"] = skill_ranks[i] if skill_ranks is not None else None
        cf["jk_skill_rank"] = jk_ranks[i] if jk_ranks is not None else None
        cf["tr_skill_rank"] = tr_ranks[i] if tr_ranks is not None else None
        cf["wg_budam_rank"] = budam_ranks[i] if budam_ranks is not None else None

    # 3단계: gap features (상위 3위와 4위 사이 격차)
    if gap_feature_allowed:
        skills = []
        for h in horses:
            s = h["computed_features"].get("horse_top3_skill")
            skills.append(s if s is not None else 0.0)
        skills_sorted = sorted(skills, reverse=True)
        gap_3rd_4th = skills_sorted[2] - skills_sorted[3] if n >= 4 else None
    else:
        gap_3rd_4th = None

    for horse in horses:
        horse["computed_features"]["gap_3rd_4th"] = gap_3rd_4th

    # 4단계: race context features
    field_size = n if field_size_allowed else None

    # wet track: 주로상태에서 추론 (첫 번째 말의 track 필드)
    track_val = horses[0].get("track", "") if horses else ""
    wet_track = (
        track_val in ("불량", "습", "다습") if wet_track_allowed and track_val else None
    )

    # cancelled horses count (cancelledHorses 필드가 있으면)
    cancelled = horses[0].get("cancelledHorses")
    if cancelled_count_allowed and cancelled and isinstance(cancelled, list):
        cancelled_count = len(cancelled)
    elif cancelled_count_allowed:
        cancelled_count = 0
    else:
        cancelled_count = None

    for horse in horses:
        cf = horse["computed_features"]
        cf["field_size"] = field_size
        if (
            field_size_live_allowed
            and field_size is not None
            and cancelled_count is not None
        ):
            cf["field_size_live"] = field_size - cancelled_count
        else:
            cf["field_size_live"] = None
        cf["wet_track"] = wet_track
        cf["cancelled_count"] = cancelled_count

    return horses
