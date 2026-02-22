"""MLflow experiment tracking for prompt evaluation."""

import json
import os
from pathlib import Path
from typing import Any

try:
    import mlflow

    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False


class ExperimentTracker:
    """Tracks prompt evaluation experiments with MLflow."""

    def __init__(self, experiment_name: str = "kra-prompt-evaluation"):
        self.enabled = (
            MLFLOW_AVAILABLE and os.getenv("MLFLOW_TRACKING_URI", "") != "disabled"
        )
        if not self.enabled:
            return

        # Set tracking URI (default: local ./mlruns directory)
        tracking_uri = os.getenv(
            "MLFLOW_TRACKING_URI", f"file://{Path.cwd() / 'mlruns'}"
        )
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)

    def start_run(
        self, run_name: str | None = None, tags: dict[str, str] | None = None
    ):
        """Start a new MLflow run."""
        if not self.enabled:
            return self
        mlflow.start_run(run_name=run_name, tags=tags or {})
        return self

    def log_params(self, params: dict[str, Any]):
        """Log parameters."""
        if not self.enabled:
            return
        for key, value in params.items():
            mlflow.log_param(key, value)

    def log_metrics(self, metrics: dict[str, float], step: int | None = None):
        """Log metrics."""
        if not self.enabled:
            return
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                mlflow.log_metric(key, value, step=step)

    def log_artifact(self, file_path: str):
        """Log a file as artifact."""
        if not self.enabled:
            return
        if Path(file_path).exists():
            mlflow.log_artifact(file_path)

    def log_text(self, text: str, artifact_name: str):
        """Log text content as artifact."""
        if not self.enabled:
            return
        mlflow.log_text(text, artifact_name)

    def log_run_metadata(
        self,
        run_metadata: dict[str, Any],
        artifact_name: str = "run_metadata.json",
        local_output_dir: str | Path | None = None,
    ) -> str | None:
        """Log standardized run metadata to MLflow and/or local artifacts."""
        from evaluation.run_metadata import (
            validate_run_metadata,
            write_run_metadata_artifact,
        )

        ok, errors = validate_run_metadata(run_metadata)
        if not ok:
            raise ValueError(f"invalid_run_metadata: {errors}")

        local_path: Path | None = None
        if local_output_dir is not None:
            local_path = write_run_metadata_artifact(
                run_metadata,
                output_dir=local_output_dir,
                filename=artifact_name,
            )

        if self.enabled:
            mlflow.log_text(
                json.dumps(run_metadata, ensure_ascii=False, indent=2),
                artifact_name,
            )

        return str(local_path) if local_path else None

    def end_run(self):
        """End the current run."""
        if not self.enabled:
            return
        mlflow.end_run()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_run()
        return False
