#!/usr/bin/env python3
"""Leakage-free 챔피언 모델로 단일 경주의 삼복연승 top-3을 예측한다.

train_clean.py가 산출한 joblib 번들을 로드해 prerace-canonical-v2 입력
스키마(odds·결과 필드 미사용)에 따라 추론을 수행한다.

Usage (CLI):
    uv run python3 packages/scripts/ml/predict_clean.py race.json
    uv run python3 packages/scripts/ml/predict_clean.py race.json --model models/champion_clean.joblib

Library:
    from ml.predict_clean import load_bundle, predict_race
    bundle = load_bundle("models/champion_clean.joblib")
    result = predict_race(race_payload, bundle)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import joblib
import numpy as np

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from shared.prediction_input_schema import (  # noqa: E402
    build_alternative_ranking_rows_for_race,
)

DEFAULT_MODEL_PATH = "models/champion_clean.joblib"
BUNDLE_SCHEMA_VERSION = "champion-clean-bundle-v1"


def load_bundle(path: str | Path) -> dict[str, Any]:
    """joblib 번들 로드 + 스키마 검증."""
    bundle = joblib.load(path)
    if bundle.get("schema_version") != BUNDLE_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported bundle schema_version: {bundle.get('schema_version')!r}; "
            f"expected {BUNDLE_SCHEMA_VERSION!r}"
        )
    if "pipeline" not in bundle or "feature_names" not in bundle:
        raise ValueError("Bundle missing required keys: pipeline, feature_names")
    return bundle


def predict_race(
    race: Mapping[str, Any],
    bundle: Mapping[str, Any],
) -> dict[str, Any]:
    """단일 경주의 top-3 chulNo와 모든 후보의 score를 반환한다."""
    rows = build_alternative_ranking_rows_for_race(race)
    if not rows:
        return {
            "race_id": str(race.get("race_id", "")),
            "predicted": [],
            "scores": {},
            "confidence": 0.0,
            "model_version": _model_version(bundle),
            "reasoning": "no_active_runners",
        }

    feature_names: list[str] = list(bundle["feature_names"])
    pipeline = bundle["pipeline"]
    X = np.array(
        [[row.get(name, np.nan) for name in feature_names] for row in rows],
        dtype=float,
    )
    probs = pipeline.predict_proba(X)[:, 1]

    chuls = [row["chulNo"] for row in rows]
    scored = sorted(zip(chuls, probs), key=lambda pair: -pair[1])
    top3 = [str(chul) for chul, _ in scored[:3]]
    scores = {str(chul): float(prob) for chul, prob in scored}
    confidence = float(scored[0][1]) if scored else 0.0

    return {
        "race_id": str(race.get("race_id", "")),
        "predicted": top3,
        "scores": scores,
        "confidence": confidence,
        "model_version": _model_version(bundle),
        "reasoning": (
            "top3 by leakage-free LogReg champion (prerace-canonical-v2 inputs only); "
            f"top-1 prob={confidence:.4f}"
        ),
    }


def _model_version(bundle: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "trained_at_utc": bundle.get("trained_at_utc"),
        "git_commit": bundle.get("git_commit"),
        "model_kind": bundle.get("model_kind"),
        "schema_version": bundle.get("schema_version"),
        "dataset_name": bundle.get("dataset_name"),
        "n_train_rows": bundle.get("n_train_rows"),
        "n_train_races": bundle.get("n_train_races"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "race_path",
        help="Race payload JSON 파일 경로 (prerace-canonical-v2 형식)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_PATH,
        help="joblib 번들 경로 (기본: models/champion_clean.joblib)",
    )
    args = parser.parse_args()

    bundle = load_bundle(args.model)
    race = json.loads(Path(args.race_path).read_text(encoding="utf-8"))
    result = predict_race(race, bundle)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
