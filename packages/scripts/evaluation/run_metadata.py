"""Run metadata schema and helpers for evaluation/improvement pipelines."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REQUIRED_RUN_METADATA_KEYS = (
    "commit_sha",
    "prompt_version",
    "data_snapshot_id",
    "seed",
    "mode",
)


def resolve_commit_sha() -> str:
    """Resolve commit SHA from CI env or local git repository."""
    for env_key in ("GITHUB_SHA", "CI_COMMIT_SHA", "COMMIT_SHA"):
        value = os.getenv(env_key, "").strip()
        if value:
            return value

    try:
        repo_root = Path(__file__).resolve().parents[3]
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def validate_run_metadata(metadata: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate required run metadata schema."""
    errors: list[str] = []
    for key in REQUIRED_RUN_METADATA_KEYS:
        if key not in metadata:
            errors.append(f"missing:{key}")
            continue
        value = metadata.get(key)
        if isinstance(value, str) and not value.strip():
            errors.append(f"empty:{key}")
        if value is None:
            errors.append(f"none:{key}")

    return len(errors) == 0, errors


def build_run_metadata(
    prompt_version: str,
    dataset_id: str,
    mode: str,
    seed: int = 42,
    commit_sha: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build standardized run metadata payload."""
    payload: dict[str, Any] = {
        "commit_sha": commit_sha or resolve_commit_sha(),
        "prompt_version": prompt_version,
        "data_snapshot_id": dataset_id,
        "seed": int(seed),
        "mode": mode,
        "created_at": datetime.now(UTC).isoformat(),
    }
    if extra:
        payload.update(extra)

    ok, errors = validate_run_metadata(payload)
    if not ok:
        raise ValueError(f"invalid_run_metadata: {errors}")

    return payload


def write_run_metadata_artifact(
    metadata: dict[str, Any],
    output_dir: Path | str,
    filename: str = "run_metadata.json",
) -> Path:
    """Write run metadata JSON artifact to local filesystem."""
    ok, errors = validate_run_metadata(metadata)
    if not ok:
        raise ValueError(f"invalid_run_metadata: {errors}")

    base = Path(output_dir)
    base.mkdir(parents=True, exist_ok=True)
    out_path = base / filename
    with out_path.open("w", encoding="utf-8") as fp:
        json.dump(metadata, fp, ensure_ascii=False, indent=2)
    return out_path
