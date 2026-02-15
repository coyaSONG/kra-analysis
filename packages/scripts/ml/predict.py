#!/usr/bin/env python3
"""
LightGBM 모델을 사용한 경마 Top-3 예측

학습된 모델을 로드하여 enriched 경주 데이터에 대해
각 출주마의 is_top3 확률을 예측하고 순위를 매깁니다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np

# feature_engineering 모듈 임포트를 위한 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))
from feature_engineering import compute_race_features

# ===================================================================
# Feature extraction (must match train_model.py)
# ===================================================================

FEATURE_COLUMNS = [
    "burden_ratio",
    "jockey_win_rate",
    "jockey_place_rate",
    "horse_win_rate",
    "horse_place_rate",
    "trainer_win_rate",
    "odds_rank",
    "rating_rank",
    "age_prime",
    "rest_days_risk",
    "horse_consistency",
    "win_odds",
    "plc_odds",
]


def _horse_to_feature_row(horse: dict) -> dict:
    """단일 출주마의 computed_features와 원시 값을 결합하여 피처 행을 만듭니다."""
    cf = horse.get("computed_features", {})
    row: dict = {}

    row["burden_ratio"] = cf.get("burden_ratio")
    row["jockey_win_rate"] = cf.get("jockey_win_rate")
    row["jockey_place_rate"] = cf.get("jockey_place_rate")
    row["horse_win_rate"] = cf.get("horse_win_rate")
    row["horse_place_rate"] = cf.get("horse_place_rate")
    row["trainer_win_rate"] = cf.get("trainer_win_rate")
    row["odds_rank"] = cf.get("odds_rank")
    row["rating_rank"] = cf.get("rating_rank")
    row["horse_consistency"] = cf.get("horse_consistency")

    # age_prime: bool -> int
    age_prime = cf.get("age_prime")
    row["age_prime"] = int(age_prime) if age_prime is not None else None

    # rest_days_risk: categorical -> numeric
    rest_risk = cf.get("rest_risk")
    risk_map = {"low": 0, "medium": 1, "high": 2}
    row["rest_days_risk"] = risk_map.get(rest_risk) if rest_risk else None

    # 원시 배당률
    try:
        row["win_odds"] = float(horse.get("winOdds", 0))
    except (TypeError, ValueError):
        row["win_odds"] = None
    try:
        row["plc_odds"] = float(horse.get("plcOdds", 0))
    except (TypeError, ValueError):
        row["plc_odds"] = None

    return row


# ===================================================================
# Prediction
# ===================================================================


def load_model(model_path: Path) -> dict:
    """학습된 모델 아티팩트를 로드합니다."""
    if not model_path.exists():
        print(f"[ERROR] 모델 파일을 찾을 수 없습니다: {model_path}")
        sys.exit(1)

    artifact = joblib.load(model_path)
    return artifact


def load_enriched_race(enriched_path: Path) -> tuple[list[dict], dict]:
    """enriched JSON 파일에서 출주마 리스트와 경주 정보를 로드합니다.

    Returns:
        (horses, race_info) 튜플
    """
    if not enriched_path.exists():
        print(f"[ERROR] enriched 파일을 찾을 수 없습니다: {enriched_path}")
        sys.exit(1)

    with open(enriched_path, encoding="utf-8") as f:
        data = json.load(f)

    if "response" not in data or "body" not in data["response"]:
        print("[ERROR] 잘못된 enriched 파일 형식입니다.")
        sys.exit(1)

    items = data["response"]["body"]["items"]["item"]
    if not isinstance(items, list):
        items = [items]

    # 기권/제외마 필터링 (winOdds == 0)
    horses = [h for h in items if h.get("winOdds", 0) != 0]

    if not horses:
        print("[ERROR] 유효한 출주마가 없습니다.")
        sys.exit(1)

    # 경주 정보 추출
    first = items[0]
    race_info = {
        "rcDate": first.get("rcDate", ""),
        "rcNo": first.get("rcNo", ""),
        "rcName": first.get("rcName", ""),
        "rcDist": first.get("rcDist", ""),
        "meet": first.get("meet", ""),
    }

    return horses, race_info


def predict_race(horses: list[dict], artifact: dict) -> list[dict]:
    """경주 출주마에 대해 is_top3 확률을 예측합니다.

    Returns:
        확률 내림차순으로 정렬된 예측 결과 리스트
    """
    model = artifact["model"]
    feature_columns = artifact.get("feature_columns", FEATURE_COLUMNS)

    # 피처 계산
    horses = compute_race_features(horses)

    results = []
    feature_rows = []

    for horse in horses:
        row = _horse_to_feature_row(horse)
        feature_vec = [row.get(col) for col in feature_columns]
        feature_rows.append(feature_vec)

        results.append(
            {
                "chul_no": int(horse.get("chulNo", 0)),
                "hr_name": horse.get("hrName", ""),
                "win_odds": horse.get("winOdds", 0),
            }
        )

    X = np.array(feature_rows, dtype=np.float64)

    # NaN 처리: -1로 대체
    nan_mask = np.isnan(X)
    if nan_mask.any():
        X[nan_mask] = -1

    # 확률 예측
    probabilities = model.predict_proba(X)[:, 1]

    for i, prob in enumerate(probabilities):
        results[i]["probability"] = float(prob)

    # 확률 내림차순 정렬
    results.sort(key=lambda x: x["probability"], reverse=True)

    # 순위 부여
    for rank, r in enumerate(results, start=1):
        r["rank"] = rank

    return results


def format_meet_name(meet_code) -> str:
    """경마장 코드를 이름으로 변환합니다."""
    meet_map = {
        1: "Seoul",
        2: "Jeju",
        3: "Busan",
        "1": "Seoul",
        "2": "Jeju",
        "3": "Busan",
    }
    return meet_map.get(meet_code, str(meet_code))


def print_predictions(results: list[dict], race_info: dict, enriched_path: str) -> None:
    """예측 결과를 보기 좋게 출력합니다."""
    # 경주 정보
    rc_date = race_info.get("rcDate", "")
    rc_no = race_info.get("rcNo", "")
    meet = format_meet_name(race_info.get("meet", ""))

    print()
    print("Horse Racing ML Prediction")
    print(f"Race: {rc_date} {meet} R{rc_no}")
    print("=" * 50)
    print(f"{'Rank':<6}{'Horse#':<8}{'Name':<18}{'Prob':<8}{'Odds'}")
    print("-" * 50)

    for r in results:
        prob_str = f"{r['probability']:.2f}"
        odds_str = f"{r['win_odds']}"
        name = r["hr_name"]
        # 이름이 너무 길면 자르기
        if len(name) > 16:
            name = name[:15] + "."

        marker = " *" if r["rank"] <= 3 else ""
        print(
            f"{r['rank']:<6}{r['chul_no']:<8}{name:<18}{prob_str:<8}{odds_str}{marker}"
        )

    print("-" * 50)
    print("* = ML Top-3 Pick")
    print()

    # top-3 요약
    top3 = [r for r in results if r["rank"] <= 3]
    print("Top-3 Picks:")
    for r in top3:
        print(
            f"  #{r['chul_no']} {r['hr_name']} (prob={r['probability']:.3f}, odds={r['win_odds']})"
        )
    print()


# ===================================================================
# CLI
# ===================================================================


def main():
    parser = argparse.ArgumentParser(
        description="LightGBM 모델을 사용한 경마 Top-3 예측",
    )
    parser.add_argument(
        "enriched_json",
        type=Path,
        help="enriched 경주 데이터 JSON 파일 경로",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=Path("data/models/lgbm_v1.pkl"),
        help="학습된 모델 파일 경로 (default: data/models/lgbm_v1.pkl)",
    )
    args = parser.parse_args()

    # 1. 모델 로드
    artifact = load_model(args.model)
    cv = artifact.get("cv_results", {})
    print(f"모델 로드 완료: {args.model}")
    if cv:
        print(
            f"  CV AUC: {cv.get('mean_auc', 0):.4f}, Top3 정확도: {cv.get('mean_exact_match_rate', 0):.1f}%"
        )

    # 2. 경주 데이터 로드
    horses, race_info = load_enriched_race(args.enriched_json)
    print(f"출주마: {len(horses)}마리")

    # 3. 예측
    results = predict_race(horses, artifact)

    # 4. 결과 출력
    print_predictions(results, race_info, str(args.enriched_json))


if __name__ == "__main__":
    main()
