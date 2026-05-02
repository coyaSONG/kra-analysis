"""Unit tests for prediction_service."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pytest

# Ensure packages/scripts is importable for the service module
_SCRIPTS_DIR = Path(__file__).resolve().parents[4] / "packages" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from services.prediction_service import (  # noqa: E402
    ModelNotLoadedError,
    PredictionService,
)


def _make_test_bundle(feature_names: list[str]) -> dict[str, Any]:
    """Tiny fitted LogReg pipeline with the bundle schema."""
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    pipeline = Pipeline(
        [
            ("imp", SimpleImputer(strategy="median")),
            ("clf", LogisticRegression(max_iter=200)),
        ]
    )
    rng = np.random.default_rng(0)
    X = rng.normal(size=(20, len(feature_names)))
    y = (rng.uniform(size=20) > 0.5).astype(int)
    if y.sum() == 0:
        y[0] = 1
    pipeline.fit(X, y)
    return {
        "pipeline": pipeline,
        "feature_names": feature_names,
        "model_kind": "logreg",
        "model_params": {"max_iter": 200, "C": 1.0},
        "positive_class_weight": 1.0,
        "imputer_strategy": "median",
        "split": {"train_end": "20251115"},
        "dataset_name": "test_dataset",
        "trained_at_utc": "2026-05-02T00:00:00+00:00",
        "git_commit": "deadbeef",
        "n_train_rows": 20,
        "n_train_positive": int(y.sum()),
        "n_train_races": 5,
        "config_path": "/tmp/test_config.json",
        "schema_version": "champion-clean-bundle-v1",
    }


@pytest.mark.unit
def test_load_raises_when_path_missing(tmp_path: Path):
    service = PredictionService(bundle_path=tmp_path / "nope.joblib")
    with pytest.raises(ModelNotLoadedError):
        service.load()


@pytest.mark.unit
def test_load_caches_bundle(tmp_path: Path):
    bundle = _make_test_bundle(["rating", "wgBudam"])
    bundle_path = tmp_path / "test.joblib"
    joblib.dump(bundle, bundle_path)

    service = PredictionService(bundle_path=bundle_path)
    first = service.load()
    second = service.load()
    assert first is second
    assert first["schema_version"] == "champion-clean-bundle-v1"


@pytest.mark.unit
def test_model_info_excludes_pipeline(tmp_path: Path):
    bundle = _make_test_bundle(["rating", "wgBudam"])
    bundle_path = tmp_path / "test.joblib"
    joblib.dump(bundle, bundle_path)

    service = PredictionService(bundle_path=bundle_path)
    info = service.model_info()
    assert "pipeline" not in info
    assert info["feature_names"] == ["rating", "wgBudam"]
    assert info["dataset_name"] == "test_dataset"


@pytest.mark.unit
def test_load_rejects_unknown_schema_version(tmp_path: Path):
    bundle = _make_test_bundle(["rating"])
    bundle["schema_version"] = "champion-clean-bundle-v999"
    bundle_path = tmp_path / "test.joblib"
    joblib.dump(bundle, bundle_path)

    service = PredictionService(bundle_path=bundle_path)
    with pytest.raises(ValueError, match="schema_version"):
        service.load()
