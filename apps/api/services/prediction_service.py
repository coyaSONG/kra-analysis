"""Leakage-free 챔피언 모델을 이용한 삼복연승 예측 서비스.

`packages/scripts/ml/predict_clean.py`의 추론 로직을 API 런타임에서 재사용한다.
번들은 프로세스당 1회 lazy-load 후 in-memory 캐시.
"""

from __future__ import annotations

import sys
import threading
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import structlog

# packages/scripts를 sys.path에 등록하여 ml.predict_clean 임포트 가능하게 함
_SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "packages" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from ml.predict_clean import load_bundle, predict_race  # noqa: E402

logger = structlog.get_logger()


class ModelNotLoadedError(RuntimeError):
    """챔피언 모델 번들이 로드되지 않았거나 경로가 잘못됨."""


class PredictionService:
    """챔피언 모델 번들을 캐싱하고 단건 예측을 수행한다."""

    def __init__(self, bundle_path: str | Path) -> None:
        self._bundle_path = Path(bundle_path)
        self._bundle: dict[str, Any] | None = None
        self._lock = threading.Lock()

    @property
    def bundle_path(self) -> Path:
        return self._bundle_path

    def load(self) -> dict[str, Any]:
        """번들을 로드한다 (이미 로드돼 있으면 캐시 반환)."""
        if self._bundle is not None:
            return self._bundle
        with self._lock:
            if self._bundle is not None:
                return self._bundle
            if not self._bundle_path.exists():
                raise ModelNotLoadedError(
                    f"Champion model bundle not found at {self._bundle_path}. "
                    "Run packages/scripts/ml/train_clean.py first."
                )
            logger.info(
                "Loading champion model bundle",
                path=str(self._bundle_path),
            )
            self._bundle = load_bundle(self._bundle_path)
            logger.info(
                "Champion model bundle loaded",
                schema_version=self._bundle.get("schema_version"),
                trained_at=self._bundle.get("trained_at_utc"),
                n_train_rows=self._bundle.get("n_train_rows"),
            )
            return self._bundle

    def model_info(self) -> dict[str, Any]:
        """번들 메타데이터(파이프라인 객체 제외)를 반환한다."""
        bundle = self.load()
        return {k: v for k, v in bundle.items() if k != "pipeline"}

    def predict(self, race: Mapping[str, Any]) -> dict[str, Any]:
        """단일 경주 payload에 대한 top-3 예측을 반환한다."""
        bundle = self.load()
        return predict_race(race, bundle)
