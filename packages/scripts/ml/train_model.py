#!/usr/bin/env python3
"""
LightGBM 기반 경마 Top-3 예측 모델 학습 파이프라인

enriched 경주 데이터와 결과를 결합하여 이진 분류 모델(is_top3)을 학습합니다.
- GroupKFold 교차 검증 (경주 단위 그룹)
- Feature importance 분석
- Per-race top-3 정확도 평가
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import joblib
import numpy as np
from lightgbm import LGBMClassifier
from sklearn.metrics import precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupKFold

# feature_engineering 모듈 임포트를 위한 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))
from evaluation.mlflow_tracker import ExperimentTracker
from feature_engineering import compute_race_features

# ---------------------------------------------------------------------------
# Feature columns used by the model
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Default LightGBM hyperparameters
# ---------------------------------------------------------------------------
DEFAULT_PARAMS = {
    "n_estimators": 200,
    "max_depth": 6,
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_child_samples": 10,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
    "verbose": -1,
}


# ===================================================================
# Data loading helpers
# ===================================================================

def _parse_enriched_filename(filepath: str) -> dict | None:
    """enriched 파일 경로에서 날짜/경마장/경주번호 메타데이터를 추출합니다.

    파일명 형식: race_{meet}_{date}_{raceNo}_enriched.json
    디렉토리 구조: data/races/{year}/{month}/{date}/{venue}/
    """
    try:
        p = Path(filepath)
        filename = p.name  # race_1_20250608_1_enriched.json
        parts = filename.replace("_enriched.json", "").split("_")
        # parts: ['race', '1', '20250608', '1']
        if len(parts) < 4:
            return None

        meet_code = parts[1]
        rc_date = parts[2]
        rc_no = parts[3]

        venue = p.parent.name  # seoul / busan / jeju
        venue_map = {"seoul": "서울", "busan": "부산경남", "jeju": "제주"}
        meet_name = venue_map.get(venue, venue)

        return {
            "meet_code": meet_code,
            "rc_date": rc_date,
            "rc_no": rc_no,
            "venue": venue,
            "meet_name": meet_name,
            "filepath": str(filepath),
        }
    except Exception:
        return None


def _load_result(data_dir: Path, rc_date: str, meet_name: str, rc_no: str) -> list[int] | None:
    """캐시된 결과 파일(top3_{date}_{meet}_{raceNo}.json)을 로드합니다."""
    result_file = data_dir / "cache" / "results" / f"top3_{rc_date}_{meet_name}_{rc_no}.json"
    if not result_file.exists():
        return None
    try:
        with open(result_file, encoding="utf-8") as f:
            top3 = json.load(f)
        if isinstance(top3, list) and len(top3) == 3:
            return [int(x) for x in top3]
        return None
    except Exception:
        return None


def _extract_horses(enriched_path: str) -> list[dict] | None:
    """enriched JSON 파일에서 출주마 리스트를 추출합니다."""
    try:
        with open(enriched_path, encoding="utf-8") as f:
            data = json.load(f)

        if "response" not in data or "body" not in data["response"]:
            return None

        items = data["response"]["body"]["items"]["item"]
        if not isinstance(items, list):
            items = [items]

        # winOdds == 0 인 기권/제외마 필터링
        horses = [h for h in items if h.get("winOdds", 0) != 0]
        if not horses:
            return None

        return horses
    except Exception:
        return None


def _horse_to_feature_row(horse: dict, race_id: str) -> dict:
    """단일 출주마의 computed_features와 원시 값을 결합하여 피처 행을 만듭니다."""
    cf = horse.get("computed_features", {})

    row: dict = {"race_id": race_id, "chul_no": int(horse.get("chulNo", 0))}

    # computed features에서 가져오기
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
# Dataset building
# ===================================================================

def build_dataset(data_dir: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    """enriched 파일 + 결과 파일에서 (X, y, groups, race_ids) 데이터셋을 구축합니다.

    Returns:
        X: (N, F) 피처 행렬
        y: (N,) 레이블 (is_top3)
        groups: (N,) 경주 그룹 ID (정수)
        race_ids: 고유 경주 ID 문자열 목록
    """
    enriched_pattern = str(data_dir / "races" / "*" / "*" / "*" / "*" / "*_enriched.json")
    enriched_files = sorted(glob.glob(enriched_pattern))

    if not enriched_files:
        print(f"[WARN] enriched 파일을 찾을 수 없습니다: {enriched_pattern}")
        return np.array([]), np.array([]), np.array([]), []

    rows: list[dict] = []
    labels: list[int] = []
    group_ids: list[int] = []
    race_id_list: list[str] = []
    group_counter = 0
    matched = 0
    skipped_no_result = 0

    for ef in enriched_files:
        meta = _parse_enriched_filename(ef)
        if meta is None:
            continue

        # 결과 로드
        top3 = _load_result(data_dir, meta["rc_date"], meta["meet_name"], meta["rc_no"])
        if top3 is None:
            skipped_no_result += 1
            continue

        # 출주마 로드 및 피처 계산
        horses = _extract_horses(ef)
        if horses is None or len(horses) < 3:
            continue

        # compute_race_features로 파생 피처 계산 (odds_rank, rating_rank 포함)
        horses = compute_race_features(horses)

        race_id = f"{meta['meet_code']}_{meta['rc_date']}_{meta['rc_no']}"
        race_id_list.append(race_id)

        for horse in horses:
            chul_no = int(horse.get("chulNo", 0))
            row = _horse_to_feature_row(horse, race_id)
            is_top3 = 1 if chul_no in top3 else 0

            rows.append(row)
            labels.append(is_top3)
            group_ids.append(group_counter)

        group_counter += 1
        matched += 1

    print(f"데이터셋 구축 완료: {matched}개 경주, {len(rows)}개 샘플 (결과 없음: {skipped_no_result}개 스킵)")

    if not rows:
        return np.array([]), np.array([]), np.array([]), []

    # dict -> numpy 배열 변환
    X = np.array([[row.get(col) for col in FEATURE_COLUMNS] for row in rows], dtype=np.float64)

    # NaN 처리: 열별 중앙값으로 대체, 중앙값 없으면 -1
    for col_idx in range(X.shape[1]):
        col_data = X[:, col_idx]
        nan_mask = np.isnan(col_data)
        if nan_mask.all():
            X[:, col_idx] = -1
        elif nan_mask.any():
            median_val = np.nanmedian(col_data)
            col_data[nan_mask] = median_val
            X[:, col_idx] = col_data

    y = np.array(labels, dtype=np.int32)
    groups = np.array(group_ids, dtype=np.int32)

    return X, y, groups, race_id_list


# ===================================================================
# Evaluation helpers
# ===================================================================

def evaluate_per_race_top3(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    groups: np.ndarray,
) -> dict:
    """경주별 top-3 예측 정확도를 계산합니다.

    각 경주에서 확률 상위 3마리를 선택하고, 실제 top-3와 비교합니다.

    Returns:
        dict with keys: exact_match_rate, avg_correct_per_race, total_races
    """
    unique_groups = np.unique(groups)
    exact_matches = 0
    total_correct = 0

    for g in unique_groups:
        mask = groups == g
        probs = y_prob[mask]
        actual = y_true[mask]

        if len(probs) < 3:
            continue

        # 확률 상위 3개 인덱스
        top3_idx = np.argsort(probs)[-3:]
        predicted_top3 = set(top3_idx)

        # 실제 top3 인덱스
        actual_top3 = set(np.where(actual == 1)[0])

        correct = len(predicted_top3 & actual_top3)
        total_correct += correct
        if correct == 3:
            exact_matches += 1

    n_races = len(unique_groups)
    return {
        "exact_match_rate": exact_matches / n_races * 100 if n_races > 0 else 0,
        "avg_correct_per_race": total_correct / n_races if n_races > 0 else 0,
        "total_races": n_races,
    }


# ===================================================================
# Training pipeline
# ===================================================================

def train(data_dir: Path, output_dir: Path) -> None:
    """메인 학습 파이프라인을 실행합니다."""
    print("=" * 60)
    print("LightGBM Top-3 예측 모델 학습")
    print("=" * 60)

    # 1. 데이터셋 구축
    print("\n[1/4] 데이터셋 구축 중...")
    X, y, groups, race_ids = build_dataset(data_dir)

    if X.size == 0:
        print("[ERROR] 데이터가 없습니다. enriched 파일과 결과 파일을 확인하세요.")
        print(f"  - enriched 파일 경로: {data_dir / 'races' / '*' / '*' / '*' / '*' / '*_enriched.json'}")
        print(f"  - 결과 파일 경로: {data_dir / 'cache' / 'results' / 'top3_*.json'}")
        sys.exit(1)

    n_samples, n_features = X.shape
    n_positive = int(y.sum())
    n_races = len(np.unique(groups))
    print(f"  샘플 수: {n_samples} ({n_positive} positive, {n_samples - n_positive} negative)")
    print(f"  피처 수: {n_features}")
    print(f"  경주 수: {n_races}")
    print(f"  양성 비율: {n_positive / n_samples * 100:.1f}%")

    # 2. 교차 검증
    print("\n[2/4] 5-Fold GroupKFold 교차 검증...")
    n_splits = min(5, n_races)  # 경주 수가 5보다 적으면 조정
    gkf = GroupKFold(n_splits=n_splits)

    fold_aucs: list[float] = []
    fold_precisions: list[float] = []
    fold_recalls: list[float] = []
    fold_race_metrics: list[dict] = []
    oof_probs = np.zeros(n_samples)

    for fold_idx, (train_idx, val_idx) in enumerate(gkf.split(X, y, groups)):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]
        groups_val = groups[val_idx]

        model = LGBMClassifier(**DEFAULT_PARAMS)
        model.fit(X_train, y_train)

        y_val_prob = model.predict_proba(X_val)[:, 1]
        y_val_pred = (y_val_prob >= 0.5).astype(int)
        oof_probs[val_idx] = y_val_prob

        # AUC-ROC
        if len(np.unique(y_val)) > 1:
            auc = roc_auc_score(y_val, y_val_prob)
        else:
            auc = 0.0
        fold_aucs.append(auc)

        # Precision & Recall
        prec = float(precision_score(y_val, y_val_pred, zero_division=0))
        rec = float(recall_score(y_val, y_val_pred, zero_division=0))
        fold_precisions.append(prec)
        fold_recalls.append(rec)

        # Per-race top-3 accuracy
        race_metrics = evaluate_per_race_top3(y_val, y_val_prob, groups_val)
        fold_race_metrics.append(race_metrics)

        print(
            f"  Fold {fold_idx + 1}: AUC={auc:.4f} | "
            f"Prec={prec:.3f} | Rec={rec:.3f} | "
            f"Top3 정확도={race_metrics['exact_match_rate']:.1f}% | "
            f"평균 적중={race_metrics['avg_correct_per_race']:.2f}/3 | "
            f"경주 {race_metrics['total_races']}개"
        )

    # 교차 검증 요약
    mean_auc = np.mean(fold_aucs)
    std_auc = np.std(fold_aucs)
    mean_precision = np.mean(fold_precisions)
    mean_recall = np.mean(fold_recalls)
    mean_exact = np.mean([m["exact_match_rate"] for m in fold_race_metrics])
    mean_correct = np.mean([m["avg_correct_per_race"] for m in fold_race_metrics])

    print(f"\n  CV 평균 AUC: {mean_auc:.4f} (+/- {std_auc:.4f})")
    print(f"  CV 평균 Precision: {mean_precision:.4f}")
    print(f"  CV 평균 Recall: {mean_recall:.4f}")
    print(f"  CV 평균 Top3 정확도: {mean_exact:.1f}%")
    print(f"  CV 평균 적중 수: {mean_correct:.2f}/3")

    # 3. Feature importance
    print("\n[3/4] Feature Importance 분석...")

    # 전체 데이터로 최종 모델 학습
    final_model = LGBMClassifier(**DEFAULT_PARAMS)
    final_model.fit(X, y)

    importances = final_model.feature_importances_
    importance_pairs = sorted(
        zip(FEATURE_COLUMNS, importances, strict=False), key=lambda x: x[1], reverse=True
    )

    print(f"  {'Feature':<25} {'Importance':>10}")
    print(f"  {'-' * 25} {'-' * 10}")
    for feat, imp in importance_pairs:
        bar = "#" * int(imp / max(importances) * 20)
        print(f"  {feat:<25} {imp:>10.0f}  {bar}")

    # 4. 모델 저장
    print("\n[4/4] 모델 저장...")
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "lgbm_v1.pkl"

    cv_results = {
        "mean_auc": float(mean_auc),
        "std_auc": float(std_auc),
        "fold_aucs": [float(a) for a in fold_aucs],
        "mean_precision": float(mean_precision),
        "mean_recall": float(mean_recall),
        "mean_exact_match_rate": float(mean_exact),
        "mean_correct_per_race": float(mean_correct),
    }

    artifact = {
        "model": final_model,
        "feature_columns": FEATURE_COLUMNS,
        "params": DEFAULT_PARAMS,
        "cv_results": cv_results,
        "feature_importances": {k: float(v) for k, v in importance_pairs},
        "n_samples": n_samples,
        "n_races": n_races,
    }

    joblib.dump(artifact, model_path)
    print(f"  모델 저장 완료: {model_path}")

    # 5. MLflow 로깅
    tracker = ExperimentTracker(experiment_name="kra-lgbm-training")
    if tracker.enabled:
        print("\n[5/5] MLflow 로깅...")
        tracker.start_run(run_name=f"lgbm_v1_n{n_races}")
        tracker.log_params(DEFAULT_PARAMS)
        tracker.log_params({"n_samples": n_samples, "n_races": n_races, "n_features": n_features})
        tracker.log_metrics({
            "cv_mean_auc": float(mean_auc),
            "cv_std_auc": float(std_auc),
            "cv_mean_precision": float(mean_precision),
            "cv_mean_recall": float(mean_recall),
            "cv_top3_exact_match_rate": float(mean_exact),
            "cv_avg_correct_per_race": float(mean_correct),
        })
        tracker.log_artifact(str(model_path))
        tracker.end_run()
        print("  MLflow 로깅 완료")

    # 최종 요약
    print("\n" + "=" * 60)
    print("학습 완료!")
    print(f"  CV AUC: {mean_auc:.4f} (+/- {std_auc:.4f})")
    print(f"  Precision: {mean_precision:.4f} | Recall: {mean_recall:.4f}")
    print(f"  Top3 정확도: {mean_exact:.1f}%")
    print(f"  평균 적중: {mean_correct:.2f}/3")
    print(f"  모델 경로: {model_path}")
    print("=" * 60)


# ===================================================================
# CLI
# ===================================================================

def main():
    parser = argparse.ArgumentParser(
        description="LightGBM 기반 경마 Top-3 예측 모델 학습",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="데이터 루트 디렉토리 (default: data)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/models"),
        help="모델 저장 디렉토리 (default: data/models)",
    )
    args = parser.parse_args()

    train(args.data_dir, args.output_dir)


if __name__ == "__main__":
    main()
