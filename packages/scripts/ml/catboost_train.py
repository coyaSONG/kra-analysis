#!/usr/bin/env python3
"""
CatBoost 기반 경마 Top-3 예측 모델 학습 파이프라인

GPT-5.4 Pro + Codex 컨설팅 기반 설계:
- Walk-forward temporal split (날짜 기준, 같은 경주 train/val 혼재 방지)
- CatBoost classifier (범주형 + missing 기본 지원)
- set_match, top3_recall, top6_recall 평가
- 확장된 피처셋 (blend, jkStats, training, race-relative)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

# feature_engineering 모듈 임포트를 위한 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))
from feature_engineering import compute_race_features

# ---------------------------------------------------------------------------
# Feature columns — v2 확장 피처셋
# ---------------------------------------------------------------------------

# 숫자형 피처
NUMERIC_FEATURES = [
    # 기존 피처
    "burden_ratio",
    "jockey_win_rate",
    "jockey_place_rate",
    "horse_win_rate",
    "horse_place_rate",
    "trainer_win_rate",
    "win_odds",
    "plc_odds",
    "rest_days",
    # v2: blend 스킬
    "horse_top3_skill",
    "jk_skill",
    "tr_skill",
    "owner_skill",
    # v2: jkStats
    "jk_qnl_rate_y",
    "jk_qnl_rate_t",
    # v2: training
    "training_score",
    "days_since_training",
    # v2: race-relative ranks
    "odds_rank",
    "rating_rank",
    "horse_skill_rank",
    "jk_skill_rank",
    "tr_skill_rank",
    "wg_budam_rank",
    # v2: gap / context
    "gap_3rd_4th",
    "field_size",
    "field_size_live",
    "cancelled_count",
    # horse metadata
    "horse_starts_y",
]

# 범주형 피처 (CatBoost에 직접 전달)
CATEGORICAL_FEATURES = [
    "rest_risk",
    "age_prime",
    "horse_low_sample",
    "wet_track",
    "training_missing",
    "recent_training",
]

ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


# ---------------------------------------------------------------------------
# Data loading: autoresearch snapshots 활용
# ---------------------------------------------------------------------------


def _horse_to_row(horse: dict, race_id: str, race_date: str) -> dict[str, Any]:
    """단일 출주마 → flat feature row 변환."""
    cf = horse.get("computed_features", {})
    row: dict[str, Any] = {
        "race_id": race_id,
        "race_date": race_date,
        "chul_no": int(horse.get("chulNo", 0)),
    }

    # 숫자형 피처
    for feat in NUMERIC_FEATURES:
        val = cf.get(feat)
        if val is None:
            # computed_features에 없으면 horse 원본에서 시도
            if feat == "win_odds":
                val = horse.get("winOdds")
            elif feat == "plc_odds":
                val = horse.get("plcOdds")
            elif feat == "rest_days":
                val = horse.get("ilsu")
        if val is not None:
            try:
                row[feat] = float(val)
            except (TypeError, ValueError):
                row[feat] = None
        else:
            row[feat] = None

    # 범주형 피처
    for feat in CATEGORICAL_FEATURES:
        val = cf.get(feat)
        if val is not None:
            if isinstance(val, bool):
                row[feat] = int(val)
            else:
                row[feat] = str(val)
        else:
            row[feat] = None

    return row


def load_snapshot_dataset(
    snapshot_path: Path,
    answer_key_path: Path,
    mode: str = "holdout",
) -> tuple[list[dict], list[int], list[str], list[int]]:
    """autoresearch snapshot에서 데이터셋 로드.

    Returns:
        rows: feature row list
        labels: is_top3 label list
        race_ids: race_id per row
        group_ids: integer group id per row
    """
    with open(snapshot_path) as f:
        races = json.load(f)
    with open(answer_key_path) as f:
        answer_key = json.load(f).get(mode, {})

    rows: list[dict] = []
    labels: list[int] = []
    race_ids: list[str] = []
    group_ids: list[int] = []

    for group_idx, race in enumerate(races):
        race_id = race.get("race_id", "")
        race_date = race.get("race_date", "")
        actual_top3 = answer_key.get(race_id)
        if not actual_top3 or len(actual_top3) < 3:
            continue

        horse_list = race.get("horses", [])
        if len(horse_list) < 3:
            continue

        # 피처 재계산 (snapshot이 v1이면 새 피처 추가됨)
        horse_list = compute_race_features(horse_list)

        actual_set = {int(x) for x in actual_top3}
        for horse in horse_list:
            chul_no = int(horse.get("chulNo", 0))
            row = _horse_to_row(horse, race_id, race_date)
            is_top3 = 1 if chul_no in actual_set else 0

            rows.append(row)
            labels.append(is_top3)
            race_ids.append(race_id)
            group_ids.append(group_idx)

    return rows, labels, race_ids, group_ids


# ---------------------------------------------------------------------------
# Walk-forward temporal split
# ---------------------------------------------------------------------------


def walk_forward_split(
    rows: list[dict],
    labels: list[int],  # noqa: ARG001
    group_ids: list[int],
    n_folds: int = 5,
    min_train_ratio: float = 0.4,
) -> list[tuple[list[int], list[int]]]:
    """날짜 기준 walk-forward split.

    같은 경주의 말이 train/val에 섞이지 않도록 group 단위로 분할.
    """
    # group별 첫 등장 날짜
    group_dates: dict[int, str] = {}
    for i, gid in enumerate(group_ids):
        if gid not in group_dates:
            group_dates[gid] = rows[i].get("race_date", "")

    # 날짜순 정렬된 고유 그룹
    sorted_groups = sorted(group_dates.keys(), key=lambda g: group_dates[g])
    n_groups = len(sorted_groups)

    if n_groups < n_folds + 1:
        # 데이터가 너무 적으면 단일 split
        cut = int(n_groups * 0.7)
        train_groups = set(sorted_groups[:cut])
        val_groups = set(sorted_groups[cut:])
        train_idx = [i for i, g in enumerate(group_ids) if g in train_groups]
        val_idx = [i for i, g in enumerate(group_ids) if g in val_groups]
        return [(train_idx, val_idx)]

    folds = []
    min_train = max(int(n_groups * min_train_ratio), 1)

    for fold in range(n_folds):
        # 점진적으로 train 범위 확대
        val_size = n_groups // (n_folds + 1)
        train_end = min_train + fold * val_size
        val_end = min(train_end + val_size, n_groups)

        if train_end >= n_groups or val_end <= train_end:
            break

        train_groups = set(sorted_groups[:train_end])
        val_groups = set(sorted_groups[train_end:val_end])

        train_idx = [i for i, g in enumerate(group_ids) if g in train_groups]
        val_idx = [i for i, g in enumerate(group_ids) if g in val_groups]

        if train_idx and val_idx:
            folds.append((train_idx, val_idx))

    return folds


# ---------------------------------------------------------------------------
# Evaluation metrics
# ---------------------------------------------------------------------------


def evaluate_set_match(
    y_prob: np.ndarray,
    y_true: np.ndarray,
    groups: np.ndarray,
) -> dict[str, float]:
    """경주별 set_match + top-k recall 계산."""
    unique_groups = np.unique(groups)
    set_matches: list[float] = []
    top3_recalls: list[float] = []
    top6_recalls: list[float] = []
    exact_count = 0

    for g in unique_groups:
        mask = groups == g
        probs = y_prob[mask]
        actual = y_true[mask]

        if len(probs) < 3:
            continue

        actual_top3 = set(np.where(actual == 1)[0])
        if not actual_top3:
            continue

        # top-3 예측
        top3_idx = set(np.argsort(probs)[-3:])
        correct_3 = len(top3_idx & actual_top3)
        sm = correct_3 / 3
        set_matches.append(sm)
        top3_recalls.append(correct_3 / len(actual_top3))

        if correct_3 == 3:
            exact_count += 1

        # top-6 recall (triplet re-ranker 전제조건 검증)
        if len(probs) >= 6:
            top6_idx = set(np.argsort(probs)[-6:])
            correct_6 = len(top6_idx & actual_top3)
            top6_recalls.append(correct_6 / len(actual_top3))
        else:
            top6_recalls.append(1.0)  # 6마리 미만이면 전부 포함

    n = len(set_matches)
    return {
        "set_match": np.mean(set_matches) if n > 0 else 0.0,
        "top3_recall": np.mean(top3_recalls) if n > 0 else 0.0,
        "top6_recall": np.mean(top6_recalls) if n > 0 else 0.0,
        "exact_match_rate": exact_count / n * 100 if n > 0 else 0.0,
        "avg_correct": np.mean([sm * 3 for sm in set_matches]) if n > 0 else 0.0,
        "n_races": n,
    }


# ---------------------------------------------------------------------------
# Training pipeline
# ---------------------------------------------------------------------------


def _rows_to_arrays(
    rows: list[dict],
    labels: list[int],
) -> tuple[np.ndarray, np.ndarray, list[int]]:
    """feature rows → numpy arrays. CatBoost용 categorical index도 반환."""
    n = len(rows)
    f = len(ALL_FEATURES)
    X = np.empty((n, f), dtype=object)

    for i, row in enumerate(rows):
        for j, feat in enumerate(ALL_FEATURES):
            X[i, j] = row.get(feat)

    # categorical feature indices
    cat_indices = [ALL_FEATURES.index(c) for c in CATEGORICAL_FEATURES]

    y = np.array(labels, dtype=np.int32)
    return X, y, cat_indices


def train(
    snapshot_dir: Path,
    mode: str = "holdout",
    n_folds: int = 5,
    output_dir: Path | None = None,
) -> dict:
    """CatBoost 학습 파이프라인."""
    try:
        from catboost import CatBoostClassifier
    except ImportError:
        print("[ERROR] catboost가 설치되지 않았습니다: uv add catboost")
        sys.exit(1)

    print("=" * 60)
    print("CatBoost Top-3 예측 모델 학습")
    print("=" * 60)

    # 1. 데이터 로드
    snapshot_path = snapshot_dir / f"{mode}.json"
    answer_key_path = snapshot_dir / "answer_key.json"

    if not snapshot_path.exists():
        print(f"[ERROR] Snapshot not found: {snapshot_path}")
        sys.exit(1)

    print(f"\n[1/4] 데이터 로드: {snapshot_path}")
    rows, labels, race_ids, group_ids = load_snapshot_dataset(
        snapshot_path, answer_key_path, mode
    )

    if not rows:
        print("[ERROR] 데이터가 없습니다.")
        sys.exit(1)

    n_samples = len(rows)
    n_positive = sum(labels)
    n_races = len(set(group_ids))
    print(
        f"  샘플: {n_samples} ({n_positive} positive, {n_samples - n_positive} negative)"
    )
    print(f"  경주: {n_races}")
    print(
        f"  피처: {len(ALL_FEATURES)} ({len(NUMERIC_FEATURES)} numeric + {len(CATEGORICAL_FEATURES)} categorical)"
    )

    # 2. Walk-forward CV
    print(f"\n[2/4] Walk-forward {n_folds}-fold 교차 검증...")
    X, y, cat_indices = _rows_to_arrays(rows, labels)
    groups_arr = np.array(group_ids)

    folds = walk_forward_split(rows, labels, group_ids, n_folds=n_folds)
    if not folds:
        print("[ERROR] fold 생성 실패 (데이터 부족)")
        sys.exit(1)

    fold_metrics: list[dict] = []
    oof_probs = np.full(n_samples, np.nan)

    catboost_params = {
        "iterations": 300,
        "depth": 6,
        "learning_rate": 0.05,
        "l2_leaf_reg": 3,
        "random_seed": 42,
        "verbose": 0,
        "auto_class_weights": "Balanced",
    }

    for fold_idx, (train_idx, val_idx) in enumerate(folds):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]
        groups_val = groups_arr[val_idx]

        model = CatBoostClassifier(**catboost_params, cat_features=cat_indices)
        model.fit(X_train, y_train, eval_set=(X_val, y_val), early_stopping_rounds=30)

        y_val_prob = model.predict_proba(X_val)[:, 1]
        oof_probs[val_idx] = y_val_prob

        metrics = evaluate_set_match(y_val_prob, y_val, groups_val)
        fold_metrics.append(metrics)

        print(
            f"  Fold {fold_idx + 1}: set_match={metrics['set_match']:.3f} | "
            f"top3_recall={metrics['top3_recall']:.3f} | "
            f"top6_recall={metrics['top6_recall']:.3f} | "
            f"exact={metrics['exact_match_rate']:.1f}% | "
            f"races={metrics['n_races']}"
        )

    # CV 요약
    mean_sm = np.mean([m["set_match"] for m in fold_metrics])
    mean_t3r = np.mean([m["top3_recall"] for m in fold_metrics])
    mean_t6r = np.mean([m["top6_recall"] for m in fold_metrics])
    mean_exact = np.mean([m["exact_match_rate"] for m in fold_metrics])
    mean_correct = np.mean([m["avg_correct"] for m in fold_metrics])

    print(f"\n  CV 평균 set_match: {mean_sm:.3f}")
    print(f"  CV 평균 top3_recall: {mean_t3r:.3f}")
    print(f"  CV 평균 top6_recall: {mean_t6r:.3f}")
    print(f"  CV 평균 exact_match: {mean_exact:.1f}%")
    print(f"  CV 평균 적중수: {mean_correct:.2f}/3")

    # 3. Feature importance
    print("\n[3/4] Feature Importance...")
    final_model = CatBoostClassifier(**catboost_params, cat_features=cat_indices)
    final_model.fit(X, y)

    importances = final_model.get_feature_importance()
    importance_pairs = sorted(
        zip(ALL_FEATURES, importances, strict=False),
        key=lambda x: x[1],
        reverse=True,
    )

    max_imp = max(importances) if max(importances) > 0 else 1
    print(f"  {'Feature':<25} {'Importance':>10}")
    print(f"  {'-' * 25} {'-' * 10}")
    for feat, imp in importance_pairs[:15]:
        bar = "#" * int(imp / max_imp * 20)
        print(f"  {feat:<25} {imp:>10.1f}  {bar}")

    # 4. 모델 저장
    if output_dir:
        print(f"\n[4/4] 모델 저장: {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)
        model_path = output_dir / "catboost_v1.cbm"
        final_model.save_model(str(model_path))

        meta = {
            "created_at": datetime.now().isoformat(),
            "features": ALL_FEATURES,
            "cat_features": CATEGORICAL_FEATURES,
            "params": catboost_params,
            "cv_results": {
                "mean_set_match": float(mean_sm),
                "mean_top3_recall": float(mean_t3r),
                "mean_top6_recall": float(mean_t6r),
                "mean_exact_match_rate": float(mean_exact),
                "fold_metrics": [
                    {
                        k: float(v) if isinstance(v, (float, np.floating)) else v
                        for k, v in m.items()
                    }
                    for m in fold_metrics
                ],
            },
            "n_samples": n_samples,
            "n_races": n_races,
            "feature_importances": {k: float(v) for k, v in importance_pairs},
        }
        with open(output_dir / "catboost_v1_meta.json", "w") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        print(f"  모델: {model_path}")
        print(f"  메타: {output_dir / 'catboost_v1_meta.json'}")

    # 최종 요약
    print("\n" + "=" * 60)
    print("학습 완료!")
    print(f"  set_match: {mean_sm:.3f}")
    print(f"  top3_recall: {mean_t3r:.3f}")
    print(f"  top6_recall: {mean_t6r:.3f} (triplet re-ranker 전제조건)")
    print(f"  exact_match: {mean_exact:.1f}%")
    print(f"  avg_correct: {mean_correct:.2f}/3")
    print("=" * 60)

    return {
        "set_match": float(mean_sm),
        "top3_recall": float(mean_t3r),
        "top6_recall": float(mean_t6r),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="CatBoost Top-3 예측 모델 학습")
    parser.add_argument(
        "--snapshot-dir",
        type=Path,
        default=Path(__file__).parent.parent / "autoresearch" / "snapshots",
        help="autoresearch snapshot 디렉토리",
    )
    parser.add_argument(
        "--mode",
        choices=["mini_val", "holdout"],
        default="mini_val",
        help="평가 데이터셋 (default: mini_val)",
    )
    parser.add_argument(
        "--folds",
        type=int,
        default=5,
        help="Walk-forward fold 수 (default: 5)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="모델 저장 디렉토리 (미지정 시 저장 안함)",
    )
    args = parser.parse_args()
    train(args.snapshot_dir, args.mode, args.folds, args.output_dir)


if __name__ == "__main__":
    main()
