"""Predict 라우터의 요청/응답 DTO."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    """단일 경주 예측 요청.

    `race` 필드는 prerace-canonical-v2 race payload (race_id, race_date, meet,
    race_info, horses[]). 내부적으로 alternative-ranking 입력 스키마로 검증된다.
    """

    race: dict[str, Any] = Field(
        ...,
        description="prerace-canonical-v2 형식의 단일 경주 payload",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "race": {
                    "race_id": "20251210_1_5",
                    "race_date": "20251210",
                    "meet": 1,
                    "race_info": {"distance": 1400, "track": "맑음"},
                    "horses": [
                        {"chulNo": 1, "rating": 80, "wgBudam": 56},
                    ],
                }
            }
        }
    }


class ModelVersionInfo(BaseModel):
    trained_at_utc: str | None = None
    git_commit: str | None = None
    model_kind: str | None = None
    schema_version: str | None = None
    dataset_name: str | None = None
    n_train_rows: int | None = None
    n_train_races: int | None = None


class PredictResponse(BaseModel):
    race_id: str = Field(..., description="입력 race_id")
    predicted: list[str] = Field(
        ..., description="추정된 top-3 chulNo (score 내림차순)"
    )
    scores: dict[str, float] = Field(..., description="모든 후보 chulNo의 score map")
    confidence: float = Field(..., description="top-1 score (0~1)", ge=0.0, le=1.0)
    reasoning: str = Field(..., description="간단한 설명 문자열")
    model_version: ModelVersionInfo

    model_config = {
        "json_schema_extra": {
            "example": {
                "race_id": "20251210_1_5",
                "predicted": ["7", "3", "11"],
                "scores": {"7": 0.71, "3": 0.66, "11": 0.62},
                "confidence": 0.71,
                "reasoning": "top3 by leakage-free LogReg champion ...",
                "model_version": {
                    "trained_at_utc": "2026-05-02T14:23:42+00:00",
                    "git_commit": "e357434...",
                    "model_kind": "logreg",
                    "schema_version": "champion-clean-bundle-v1",
                    "dataset_name": "full_year_2025_prerace_canonical_v2",
                    "n_train_rows": 16146,
                    "n_train_races": 1520,
                },
            }
        }
    }


class ModelInfoResponse(BaseModel):
    """현재 로드된 챔피언 번들 메타데이터."""

    feature_names: list[str]
    model_kind: str
    model_params: dict[str, Any]
    positive_class_weight: float
    imputer_strategy: str
    split: dict[str, Any]
    dataset_name: str
    trained_at_utc: str | None = None
    git_commit: str | None = None
    n_train_rows: int
    n_train_positive: int
    n_train_races: int
    config_path: str | None = None
    schema_version: str
