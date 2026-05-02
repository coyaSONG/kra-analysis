"""Integration tests for the predict router."""

from __future__ import annotations

from typing import Any

import pytest

from routers import predict as predict_router
from services.prediction_service import ModelNotLoadedError


@pytest.fixture
def stub_predict(monkeypatch):
    """Replace prediction_service.predict / model_info with deterministic stubs."""

    def _apply(
        predict_result: dict[str, Any] | Exception,
        info_result: dict[str, Any] | Exception | None = None,
    ):
        def _predict(race):
            if isinstance(predict_result, Exception):
                raise predict_result
            return predict_result

        def _info():
            if info_result is None:
                return {
                    "feature_names": ["rating"],
                    "model_kind": "logreg",
                    "model_params": {"max_iter": 200},
                    "positive_class_weight": 1.0,
                    "imputer_strategy": "median",
                    "split": {"train_end": "20251115"},
                    "dataset_name": "test_dataset",
                    "trained_at_utc": "2026-05-02T00:00:00+00:00",
                    "git_commit": "deadbeef",
                    "n_train_rows": 20,
                    "n_train_positive": 7,
                    "n_train_races": 5,
                    "config_path": "/tmp/test_config.json",
                    "schema_version": "champion-clean-bundle-v1",
                }
            if isinstance(info_result, Exception):
                raise info_result
            return info_result

        monkeypatch.setattr(predict_router.prediction_service, "predict", _predict)
        monkeypatch.setattr(predict_router.prediction_service, "model_info", _info)

    return _apply


@pytest.mark.asyncio
@pytest.mark.unit
async def test_predict_returns_200_with_valid_bundle(
    authenticated_client, stub_predict
):
    stub_predict(
        predict_result={
            "race_id": "20251210_1_5",
            "predicted": ["7", "3", "11"],
            "scores": {"7": 0.71, "3": 0.66, "11": 0.62, "1": 0.30},
            "confidence": 0.71,
            "reasoning": "stub",
            "model_version": {
                "trained_at_utc": "2026-05-02T00:00:00+00:00",
                "git_commit": "deadbeef",
                "model_kind": "logreg",
                "schema_version": "champion-clean-bundle-v1",
                "dataset_name": "test_dataset",
                "n_train_rows": 20,
                "n_train_races": 5,
            },
        }
    )

    response = await authenticated_client.post(
        "/api/v2/predict/",
        json={"race": {"race_id": "20251210_1_5", "horses": [{"chulNo": 1}]}},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["race_id"] == "20251210_1_5"
    assert body["predicted"] == ["7", "3", "11"]
    assert pytest.approx(body["confidence"], rel=1e-6) == 0.71
    assert body["model_version"]["schema_version"] == "champion-clean-bundle-v1"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_predict_returns_503_when_model_missing(
    authenticated_client, stub_predict
):
    stub_predict(predict_result=ModelNotLoadedError("not found"))

    response = await authenticated_client.post(
        "/api/v2/predict/",
        json={"race": {"race_id": "20251210_1_5", "horses": [{"chulNo": 1}]}},
    )
    assert response.status_code == 503
    assert "not found" in response.json()["detail"]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_predict_returns_400_on_invalid_payload(
    authenticated_client, stub_predict
):
    stub_predict(predict_result=ValueError("missing required field 'horses'"))

    response = await authenticated_client.post(
        "/api/v2/predict/",
        json={"race": {"race_id": "x"}},
    )
    assert response.status_code == 400
    assert "Invalid race payload" in response.json()["detail"]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_model_info_returns_metadata(authenticated_client, stub_predict):
    stub_predict(predict_result={})  # not used; info_result default applies
    response = await authenticated_client.get("/api/v2/predict/model-info")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["dataset_name"] == "test_dataset"
    assert body["schema_version"] == "champion-clean-bundle-v1"
    assert body["feature_names"] == ["rating"]
