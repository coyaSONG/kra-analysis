"""Autoresearch 평가 결과용 재현성 매니페스트 helpers."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from shared.execution_matrix import validate_evaluation_seeds
from shared.reproducibility_manifest_schema import (
    ArtifactHashRecord,
    ReproducibilityManifest,
    RunConfiguration,
    SeedEnvelope,
    SourceDataVersion,
    SplitManifestReference,
    validate_reproducibility_manifest,
)

from autoresearch.dataset_artifacts import (
    OfflineEvaluationDatasetArtifacts,
)

DEFAULT_DATASET_SPLIT_FILENAMES = {
    "holdout": "holdout_split_manifest.json",
    "mini_val": "mini_val_split_manifest.json",
}
PREDICTION_ARTIFACT_SUFFIX = "_predictions.json"
METRICS_ARTIFACT_SUFFIX = "_metrics.json"
REPRODUCIBILITY_ARTIFACTS_KEY = "_reproducibility_artifacts"
REPRODUCIBILITY_CHECK_REPORT_VERSION = "research-evaluation-reproducibility-report-v1"
REPRODUCIBILITY_CHECK_REPORT_JSON_FILENAME = (
    "research_evaluation_reproducibility_report.json"
)
REPRODUCIBILITY_CHECK_REPORT_MARKDOWN_FILENAME = (
    "research_evaluation_reproducibility_report.md"
)
MODEL_RANDOM_STATE_BY_KIND = {
    "hgb": 42,
    "rf": 42,
    "et": 42,
}


def _normalize_datetime(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.now(UTC).astimezone()
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone()


def _sha256_bytes(content: bytes) -> str:
    return sha256(content).hexdigest()


def _artifact_record(
    *,
    artifact_id: str,
    role: str,
    path: Path,
    content: bytes,
    generated_at: datetime | None = None,
) -> ArtifactHashRecord:
    return ArtifactHashRecord(
        artifact_id=artifact_id,
        role=role,
        path=str(path),
        sha256=_sha256_bytes(content),
        byte_size=len(content),
        generated_at=generated_at,
    )


def _dataset_input_records(
    *,
    artifacts: OfflineEvaluationDatasetArtifacts,
) -> list[ArtifactHashRecord]:
    required_paths = [
        ("dataset_snapshot", "input_dataset", artifacts.dataset_path),
        ("dataset_answer_key", "input_answer_key", artifacts.answer_key_path),
        ("dataset_manifest", "input_dataset_manifest", artifacts.manifest_path),
    ]

    records: list[ArtifactHashRecord] = []
    for artifact_id, role, path in required_paths:
        if not path.exists():
            raise FileNotFoundError(f"필수 입력 아티팩트를 찾을 수 없습니다: {path}")
        content = path.read_bytes()
        records.append(
            _artifact_record(
                artifact_id=artifact_id,
                role=role,
                path=path,
                content=content,
            )
        )
    return records


def _stable_json_payload(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def _stable_json_digest(payload: Any) -> str:
    return _sha256_bytes(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def _load_json_path(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _default_prediction_artifact_payload(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "format_version": "research-evaluation-prediction-rows-v1",
        "dataset": (result.get("config") or {}).get("dataset"),
        "run_id": None,
        "seed_index": None,
        "model_random_state": (result.get("runtime_params") or {}).get(
            "model_random_state"
        ),
        "windows": [],
    }


def _default_metrics_artifact_payload(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "format_version": "research-evaluation-metrics-v1",
        "dataset": (result.get("config") or {}).get("dataset"),
        "run_id": None,
        "seed_index": None,
        "model_random_state": (result.get("runtime_params") or {}).get(
            "model_random_state"
        ),
        "feature_count": result.get("feature_count"),
        "market_feature_count": result.get("market_feature_count"),
        "integrity": dict(result.get("integrity") or {}),
        "summary": dict(result.get("summary") or {}),
        "dev": dict(result.get("dev") or {}),
        "test": dict(result.get("test") or {}),
        "rolling": list(result.get("rolling") or []),
    }


def _normalize_result_payloads(
    result: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    output_payload = {
        key: value
        for key, value in result.items()
        if key != REPRODUCIBILITY_ARTIFACTS_KEY
    }
    artifact_payloads = result.get(REPRODUCIBILITY_ARTIFACTS_KEY)
    if not isinstance(artifact_payloads, dict):
        return (
            output_payload,
            _default_prediction_artifact_payload(output_payload),
            _default_metrics_artifact_payload(output_payload),
        )

    raw_predictions = artifact_payloads.get("prediction_rows")
    raw_metrics = artifact_payloads.get("metrics_summary")
    prediction_payload = (
        raw_predictions
        if isinstance(raw_predictions, dict)
        else _default_prediction_artifact_payload(output_payload)
    )
    metrics_payload = (
        raw_metrics
        if isinstance(raw_metrics, dict)
        else _default_metrics_artifact_payload(output_payload)
    )
    return output_payload, prediction_payload, metrics_payload


def _split_seed_envelope(dataset: str, output_dir: Path) -> SeedEnvelope:
    split_filename = DEFAULT_DATASET_SPLIT_FILENAMES.get(dataset)
    if not split_filename:
        return SeedEnvelope(
            model_random_state=None,
            selection_seed=None,
            selection_seed_invariant=None,
            evaluation_seeds=(),
        )

    split_path = output_dir / split_filename
    if not split_path.exists():
        return SeedEnvelope(
            model_random_state=None,
            selection_seed=None,
            selection_seed_invariant=None,
            evaluation_seeds=(),
        )

    payload = json.loads(split_path.read_text(encoding="utf-8"))
    seed_block = (payload.get("metadata") or {}).get("seed") or {}
    evaluation_seeds = validate_evaluation_seeds(
        tuple(seed_block.get("evaluation_seeds") or ()),
        allow_empty=True,
    )
    return SeedEnvelope(
        model_random_state=None,
        selection_seed=seed_block.get("selection_seed"),
        selection_seed_invariant=seed_block.get("selection_seed_invariant"),
        evaluation_seeds=evaluation_seeds,
    )


def _build_split_reference(
    *,
    dataset: str,
    output_dir: Path,
) -> tuple[ArtifactHashRecord | None, SplitManifestReference | None]:
    split_filename = DEFAULT_DATASET_SPLIT_FILENAMES.get(dataset)
    if not split_filename:
        return None, None

    split_path = output_dir / split_filename
    if not split_path.exists():
        return None, None

    content = split_path.read_bytes()
    payload = json.loads(content.decode("utf-8"))
    seed_block = (payload.get("metadata") or {}).get("seed") or {}
    included_race_ids = tuple(payload.get("included_race_ids") or ())
    record = _artifact_record(
        artifact_id="dataset_split_manifest",
        role="input_split_manifest",
        path=split_path,
        content=content,
    )
    split_reference = SplitManifestReference(
        artifact_id=record.artifact_id,
        manifest_path=str(split_path),
        manifest_sha256=record.sha256,
        included_race_count=len(included_race_ids) or None,
        included_race_ids_sha256=(
            _sha256_bytes(
                json.dumps(
                    list(included_race_ids),
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            )
            if included_race_ids
            else None
        ),
        selection_seed=seed_block.get("selection_seed"),
        selection_seed_invariant=seed_block.get("selection_seed_invariant"),
        evaluation_seeds=validate_evaluation_seeds(
            tuple(seed_block.get("evaluation_seeds") or ()),
            allow_empty=True,
        ),
    )
    return record, split_reference


def model_random_state_for_config(config: dict[str, Any]) -> int | None:
    """현재 모델 설정에서 실효 random_state를 반환한다."""

    model = config.get("model") or {}
    return MODEL_RANDOM_STATE_BY_KIND.get(model.get("kind"))


def serialize_reproducibility_manifest(manifest: ReproducibilityManifest) -> str:
    """재현성 매니페스트를 canonical JSON 문자열로 직렬화한다."""

    return json.dumps(
        manifest.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def _attach_manifest_sha(manifest: ReproducibilityManifest) -> ReproducibilityManifest:
    payload = manifest.model_dump(mode="json")
    payload_without_sha = {**payload, "manifest_sha256": None}
    digest = _sha256_bytes(
        json.dumps(payload_without_sha, ensure_ascii=False, sort_keys=True).encode(
            "utf-8"
        )
    )
    return manifest.model_copy(update={"manifest_sha256": digest})


def build_research_evaluation_manifest(
    *,
    config_path: Path,
    config: dict[str, Any],
    output_path: Path,
    output_payload: str,
    created_at: datetime | str | None,
    dataset_artifacts: OfflineEvaluationDatasetArtifacts,
    runtime_params_path: Path | None = None,
    runtime_params: dict[str, Any] | None = None,
    prediction_artifact_path: Path | None = None,
    prediction_artifact_payload: str | None = None,
    metrics_artifact_path: Path | None = None,
    metrics_artifact_payload: str | None = None,
) -> ReproducibilityManifest:
    """평가 출력과 입력 스냅샷 기준으로 재현성 매니페스트를 구성한다."""

    normalized_created_at = _normalize_datetime(created_at)
    dataset = dataset_artifacts.dataset
    config_content = config_path.read_bytes()
    output_bytes = output_payload.encode("utf-8")

    input_records = _dataset_input_records(artifacts=dataset_artifacts)
    split_record, split_reference = _build_split_reference(
        dataset=dataset,
        output_dir=output_path.parent,
    )
    config_record = _artifact_record(
        artifact_id="evaluation_config",
        role="input_config",
        path=config_path,
        content=config_content,
    )
    runtime_records: list[ArtifactHashRecord] = []
    if runtime_params_path:
        runtime_content = runtime_params_path.read_bytes()
        runtime_records.append(
            _artifact_record(
                artifact_id="evaluation_runtime_params",
                role="input_runtime_params",
                path=runtime_params_path,
                content=runtime_content,
            )
        )
    output_auxiliary_records: list[ArtifactHashRecord] = []
    if prediction_artifact_path is not None and prediction_artifact_payload is not None:
        output_auxiliary_records.append(
            _artifact_record(
                artifact_id="evaluation_prediction_rows",
                role="output_prediction_rows",
                path=prediction_artifact_path,
                content=prediction_artifact_payload.encode("utf-8"),
                generated_at=normalized_created_at,
            )
        )
    if metrics_artifact_path is not None and metrics_artifact_payload is not None:
        output_auxiliary_records.append(
            _artifact_record(
                artifact_id="evaluation_metrics_summary",
                role="output_metrics_summary",
                path=metrics_artifact_path,
                content=metrics_artifact_payload.encode("utf-8"),
                generated_at=normalized_created_at,
            )
        )
    output_record = _artifact_record(
        artifact_id="evaluation_result",
        role="output_result",
        path=output_path,
        content=output_bytes,
        generated_at=normalized_created_at,
    )
    artifact_records = (
        config_record,
        *runtime_records,
        *input_records,
        *([split_record] if split_record is not None else []),
        *output_auxiliary_records,
        output_record,
    )

    source_version_payload = {
        "dataset": dataset,
        "artifacts": [
            {
                "artifact_id": record.artifact_id,
                "sha256": record.sha256,
            }
            for record in artifact_records
            if record.role in {"input_dataset", "input_answer_key"}
        ],
    }
    source_version = (
        "dataset-source-v1:"
        + _sha256_bytes(
            json.dumps(
                source_version_payload, ensure_ascii=False, sort_keys=True
            ).encode("utf-8")
        )[:16]
    )

    split_seed_envelope = _split_seed_envelope(dataset, output_path.parent)
    manifest = ReproducibilityManifest(
        run_type="research_evaluation",
        run_created_at=normalized_created_at,
        source_data=SourceDataVersion(
            dataset=dataset,
            version_id=source_version,
            artifact_ids=tuple(
                record.artifact_id
                for record in artifact_records
                if record.role in {"input_dataset", "input_answer_key"}
            ),
        ),
        configuration=RunConfiguration(
            config_path=str(config_path),
            config_sha256=_sha256_bytes(config_content),
            settings=config,
        ),
        seeds=split_seed_envelope.model_copy(
            update={
                "model_random_state": (runtime_params or {}).get(
                    "model_random_state", model_random_state_for_config(config)
                )
            }
        ),
        split=split_reference,
        artifacts=artifact_records,
    )
    return _attach_manifest_sha(manifest)


def manifest_path_for_output(output_path: Path) -> Path:
    """결과 JSON 옆에 companion manifest 저장 경로를 계산한다."""

    return output_path.with_name(f"{output_path.stem}_manifest.json")


def prediction_artifact_path_for_output(output_path: Path) -> Path:
    """평가별 예측 상세 산출물 저장 경로를 계산한다."""

    return output_path.with_name(f"{output_path.stem}{PREDICTION_ARTIFACT_SUFFIX}")


def metrics_artifact_path_for_output(output_path: Path) -> Path:
    """평가별 지표 요약 산출물 저장 경로를 계산한다."""

    return output_path.with_name(f"{output_path.stem}{METRICS_ARTIFACT_SUFFIX}")


def _build_artifact_index(
    manifest_payload: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    records = manifest_payload.get("artifacts") or []
    index: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        artifact_id = record.get("artifact_id")
        if isinstance(artifact_id, str) and artifact_id:
            index[artifact_id] = record
    return index


def _first_difference(
    reference: Any,
    regenerated: Any,
    *,
    path: str = "$",
) -> dict[str, Any] | None:
    if reference == regenerated:
        return None

    if type(reference) is not type(regenerated):
        return {
            "path": path,
            "difference_type": "type_mismatch",
            "reference_value": reference,
            "regenerated_value": regenerated,
        }

    if isinstance(reference, dict):
        keys = sorted(set(reference.keys()) | set(regenerated.keys()))
        for key in keys:
            next_path = f"{path}.{key}"
            if key not in reference:
                return {
                    "path": next_path,
                    "difference_type": "missing_from_reference",
                    "reference_value": None,
                    "regenerated_value": regenerated.get(key),
                }
            if key not in regenerated:
                return {
                    "path": next_path,
                    "difference_type": "missing_from_regenerated",
                    "reference_value": reference.get(key),
                    "regenerated_value": None,
                }
            difference = _first_difference(
                reference[key],
                regenerated[key],
                path=next_path,
            )
            if difference is not None:
                return difference
        return None

    if isinstance(reference, list):
        shared_length = min(len(reference), len(regenerated))
        for index in range(shared_length):
            difference = _first_difference(
                reference[index],
                regenerated[index],
                path=f"{path}[{index}]",
            )
            if difference is not None:
                return difference
        if len(reference) != len(regenerated):
            mismatch_index = shared_length
            return {
                "path": f"{path}[{mismatch_index}]",
                "difference_type": "length_mismatch",
                "reference_value": (
                    reference[mismatch_index]
                    if mismatch_index < len(reference)
                    else None
                ),
                "regenerated_value": (
                    regenerated[mismatch_index]
                    if mismatch_index < len(regenerated)
                    else None
                ),
            }
        return None

    return {
        "path": path,
        "difference_type": "value_mismatch",
        "reference_value": reference,
        "regenerated_value": regenerated,
    }


def _format_difference_summary(
    *,
    matched: bool,
    difference: dict[str, Any] | None,
    basis: str,
) -> str:
    if matched:
        return f"{basis} 일치"
    if difference is None:
        return f"{basis} 불일치"
    return (
        f"{basis} 불일치: {difference['path']} "
        f"({difference['reference_value']!r} != {difference['regenerated_value']!r})"
    )


def _build_value_check(
    *,
    label: str,
    category: str,
    reference_value: Any,
    regenerated_value: Any,
    required_for_pass: bool,
    reference_path: str | None = None,
    regenerated_path: str | None = None,
) -> dict[str, Any]:
    matched = reference_value == regenerated_value
    difference = _first_difference(reference_value, regenerated_value)
    return {
        "label": label,
        "category": category,
        "comparison_basis": "canonical_json_digest",
        "required_for_pass": required_for_pass,
        "matched": matched,
        "reference_sha256": _stable_json_digest(reference_value),
        "regenerated_sha256": _stable_json_digest(regenerated_value),
        "reference_byte_size": None,
        "regenerated_byte_size": None,
        "reference_path": reference_path,
        "regenerated_path": regenerated_path,
        "reference_value": reference_value,
        "regenerated_value": regenerated_value,
        "difference": difference,
        "difference_summary": _format_difference_summary(
            matched=matched,
            difference=difference,
            basis=label,
        ),
    }


def _build_artifact_check(
    *,
    label: str,
    category: str,
    reference_record: dict[str, Any] | None,
    regenerated_record: dict[str, Any] | None,
    required_for_pass: bool,
) -> dict[str, Any]:
    reference_sha = (
        str(reference_record.get("sha256"))
        if isinstance(reference_record, dict) and reference_record.get("sha256")
        else None
    )
    regenerated_sha = (
        str(regenerated_record.get("sha256"))
        if isinstance(regenerated_record, dict) and regenerated_record.get("sha256")
        else None
    )
    reference_size = (
        int(reference_record["byte_size"])
        if isinstance(reference_record, dict)
        and reference_record.get("byte_size") is not None
        else None
    )
    regenerated_size = (
        int(regenerated_record["byte_size"])
        if isinstance(regenerated_record, dict)
        and regenerated_record.get("byte_size") is not None
        else None
    )
    matched = (
        reference_sha is not None
        and regenerated_sha is not None
        and reference_sha == regenerated_sha
        and reference_size == regenerated_size
    )

    difference: dict[str, Any] | None = None
    if reference_record is None or regenerated_record is None:
        difference = {
            "path": label,
            "difference_type": "missing_artifact",
            "reference_value": None
            if reference_record is None
            else reference_record.get("path"),
            "regenerated_value": (
                None if regenerated_record is None else regenerated_record.get("path")
            ),
        }
    elif not matched:
        difference = {
            "path": label,
            "difference_type": "artifact_hash_mismatch",
            "reference_value": {
                "sha256": reference_sha,
                "byte_size": reference_size,
            },
            "regenerated_value": {
                "sha256": regenerated_sha,
                "byte_size": regenerated_size,
            },
        }

    return {
        "label": label,
        "category": category,
        "comparison_basis": "artifact_sha256_and_byte_size",
        "required_for_pass": required_for_pass,
        "matched": matched,
        "reference_sha256": reference_sha,
        "regenerated_sha256": regenerated_sha,
        "reference_byte_size": reference_size,
        "regenerated_byte_size": regenerated_size,
        "reference_path": (
            str(reference_record.get("path"))
            if isinstance(reference_record, dict) and reference_record.get("path")
            else None
        ),
        "regenerated_path": (
            str(regenerated_record.get("path"))
            if isinstance(regenerated_record, dict) and regenerated_record.get("path")
            else None
        ),
        "reference_value": None,
        "regenerated_value": None,
        "difference": difference,
        "difference_summary": (
            f"{label} artifact 일치"
            if matched
            else (
                f"{label} artifact 누락"
                if difference is not None
                and difference["difference_type"] == "missing_artifact"
                else (
                    f"{label} artifact 해시 불일치 "
                    f"({reference_sha} != {regenerated_sha})"
                )
            )
        ),
    }


def build_research_evaluation_reproducibility_report(
    *,
    reference_output_path: Path,
    regenerated_output_path: Path,
    generated_at: datetime | str | None = None,
) -> dict[str, Any]:
    """두 번 실행한 평가 산출물을 비교해 사람이 검수할 수 있는 리포트를 만든다."""

    normalized_generated_at = _normalize_datetime(generated_at)
    reference_manifest_path = manifest_path_for_output(reference_output_path)
    regenerated_manifest_path = manifest_path_for_output(regenerated_output_path)

    reference_output_payload = _load_json_path(reference_output_path)
    regenerated_output_payload = _load_json_path(regenerated_output_path)
    reference_manifest_payload = _load_json_path(reference_manifest_path)
    regenerated_manifest_payload = _load_json_path(regenerated_manifest_path)

    reference_manifest_ok, reference_manifest_errors = (
        validate_reproducibility_manifest(reference_manifest_payload)
    )
    regenerated_manifest_ok, regenerated_manifest_errors = (
        validate_reproducibility_manifest(regenerated_manifest_payload)
    )

    reference_artifacts = _build_artifact_index(reference_manifest_payload)
    regenerated_artifacts = _build_artifact_index(regenerated_manifest_payload)
    artifact_order = list(reference_artifacts)
    for artifact_id in regenerated_artifacts:
        if artifact_id not in reference_artifacts:
            artifact_order.append(artifact_id)

    required_checks: list[dict[str, Any]] = []
    informational_checks: list[dict[str, Any]] = []

    required_checks.append(
        _build_value_check(
            label="evaluation_result_payload",
            category="output_payload",
            reference_value=reference_output_payload,
            regenerated_value=regenerated_output_payload,
            required_for_pass=True,
            reference_path=str(reference_output_path),
            regenerated_path=str(regenerated_output_path),
        )
    )

    for artifact_id in artifact_order:
        reference_record = reference_artifacts.get(artifact_id)
        regenerated_record = regenerated_artifacts.get(artifact_id)
        role = None
        if reference_record is not None:
            role = reference_record.get("role")
        elif regenerated_record is not None:
            role = regenerated_record.get("role")
        category = (
            "output_artifact"
            if isinstance(role, str) and role.startswith("output_")
            else "input_artifact"
        )
        target = (
            required_checks
            if category != "output_artifact" or artifact_id != "evaluation_result"
            else informational_checks
        )
        if artifact_id == "evaluation_result":
            # output JSON 본문 비교가 이미 있으므로 manifest의 output artifact 레코드는 참고용으로만 남긴다.
            target = informational_checks
        target.append(
            _build_artifact_check(
                label=artifact_id,
                category=category,
                reference_record=reference_record,
                regenerated_record=regenerated_record,
                required_for_pass=artifact_id != "evaluation_result",
            )
        )

    required_checks.extend(
        [
            _build_value_check(
                label="source_data.version_id",
                category="manifest_invariant",
                reference_value=reference_manifest_payload["source_data"]["version_id"],
                regenerated_value=regenerated_manifest_payload["source_data"][
                    "version_id"
                ],
                required_for_pass=True,
            ),
            _build_value_check(
                label="configuration.config_sha256",
                category="manifest_invariant",
                reference_value=reference_manifest_payload["configuration"][
                    "config_sha256"
                ],
                regenerated_value=regenerated_manifest_payload["configuration"][
                    "config_sha256"
                ],
                required_for_pass=True,
            ),
            _build_value_check(
                label="configuration.settings",
                category="manifest_invariant",
                reference_value=reference_manifest_payload["configuration"]["settings"],
                regenerated_value=regenerated_manifest_payload["configuration"][
                    "settings"
                ],
                required_for_pass=True,
            ),
            _build_value_check(
                label="seeds",
                category="manifest_invariant",
                reference_value=reference_manifest_payload["seeds"],
                regenerated_value=regenerated_manifest_payload["seeds"],
                required_for_pass=True,
            ),
            _build_value_check(
                label="split",
                category="manifest_invariant",
                reference_value=reference_manifest_payload.get("split"),
                regenerated_value=regenerated_manifest_payload.get("split"),
                required_for_pass=True,
            ),
        ]
    )

    informational_checks.extend(
        [
            _build_value_check(
                label="run_created_at",
                category="manifest_file",
                reference_value=reference_manifest_payload.get("run_created_at"),
                regenerated_value=regenerated_manifest_payload.get("run_created_at"),
                required_for_pass=False,
                reference_path=str(reference_manifest_path),
                regenerated_path=str(regenerated_manifest_path),
            ),
        ]
    )

    manifest_validation = {
        "reference_ok": reference_manifest_ok,
        "reference_errors": reference_manifest_errors,
        "regenerated_ok": regenerated_manifest_ok,
        "regenerated_errors": regenerated_manifest_errors,
    }

    mismatched_required = [
        row["label"]
        for row in required_checks
        if row["matched"] is False and row["required_for_pass"]
    ]
    mismatched_informational = [
        row["label"] for row in informational_checks if row["matched"] is False
    ]
    difference_summary = [
        {
            "label": row["label"],
            "category": row["category"],
            "required_for_pass": row["required_for_pass"],
            "summary": row["difference_summary"],
        }
        for row in [*required_checks, *informational_checks]
        if row["matched"] is False
    ]

    passed = (
        reference_manifest_ok and regenerated_manifest_ok and not mismatched_required
    )

    return {
        "format_version": REPRODUCIBILITY_CHECK_REPORT_VERSION,
        "generated_at": normalized_generated_at.isoformat(),
        "reference_output_path": str(reference_output_path),
        "regenerated_output_path": str(regenerated_output_path),
        "reference_manifest_path": str(reference_manifest_path),
        "regenerated_manifest_path": str(regenerated_manifest_path),
        "passed": passed,
        "manifest_validation": manifest_validation,
        "result_snapshots": {
            "reference": {
                "summary": reference_output_payload.get("summary"),
                "integrity": reference_output_payload.get("integrity"),
                "source_version_id": reference_manifest_payload["source_data"][
                    "version_id"
                ],
            },
            "regenerated": {
                "summary": regenerated_output_payload.get("summary"),
                "integrity": regenerated_output_payload.get("integrity"),
                "source_version_id": regenerated_manifest_payload["source_data"][
                    "version_id"
                ],
            },
        },
        "required_checks": required_checks,
        "informational_checks": informational_checks,
        "matched_items": [
            row["label"]
            for row in [*required_checks, *informational_checks]
            if row["matched"] is True
        ],
        "mismatched_items": {
            "required": mismatched_required,
            "informational": mismatched_informational,
        },
        "difference_summary": difference_summary,
    }


def render_research_evaluation_reproducibility_markdown(
    report: dict[str, Any],
) -> str:
    """재현성 비교 리포트를 사람이 읽기 쉬운 markdown으로 렌더링한다."""

    validation = report["manifest_validation"]
    lines = [
        "# Research Evaluation Reproducibility Report",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- status: `{'PASS' if report['passed'] else 'FAIL'}`",
        f"- reference_output: `{report['reference_output_path']}`",
        f"- regenerated_output: `{report['regenerated_output_path']}`",
        f"- reference_manifest: `{report['reference_manifest_path']}`",
        f"- regenerated_manifest: `{report['regenerated_manifest_path']}`",
        "",
        "## Manifest Validation",
        "",
        (
            f"- reference: `{'PASS' if validation['reference_ok'] else 'FAIL'}` / "
            f"{', '.join(validation['reference_errors']) or '-'}"
        ),
        (
            f"- regenerated: `{'PASS' if validation['regenerated_ok'] else 'FAIL'}` / "
            f"{', '.join(validation['regenerated_errors']) or '-'}"
        ),
        "",
        "## Required Checks",
        "",
        "| item | status | reference_sha256 | regenerated_sha256 | summary |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in report["required_checks"]:
        lines.append(
            f"| {row['label']} | {'PASS' if row['matched'] else 'FAIL'} | "
            f"{row['reference_sha256'] or '-'} | {row['regenerated_sha256'] or '-'} | "
            f"{row['difference_summary']} |"
        )

    lines.extend(
        [
            "",
            "## Informational Checks",
            "",
            "| item | status | reference_sha256 | regenerated_sha256 | summary |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in report["informational_checks"]:
        lines.append(
            f"| {row['label']} | {'PASS' if row['matched'] else 'INFO-MISMATCH'} | "
            f"{row['reference_sha256'] or '-'} | {row['regenerated_sha256'] or '-'} | "
            f"{row['difference_summary']} |"
        )

    lines.extend(["", "## Difference Summary", ""])
    if not report["difference_summary"]:
        lines.append("- required/informational 차이가 없습니다.")
    else:
        for item in report["difference_summary"]:
            prefix = "required" if item["required_for_pass"] else "info"
            lines.append(f"- [{prefix}] `{item['label']}`: {item['summary']}")

    result_snapshots = report["result_snapshots"]
    lines.extend(
        [
            "",
            "## Result Snapshots",
            "",
            f"- reference summary: `{json.dumps(result_snapshots['reference']['summary'], ensure_ascii=False, sort_keys=True)}`",
            f"- regenerated summary: `{json.dumps(result_snapshots['regenerated']['summary'], ensure_ascii=False, sort_keys=True)}`",
            f"- reference integrity: `{json.dumps(result_snapshots['reference']['integrity'], ensure_ascii=False, sort_keys=True)}`",
            f"- regenerated integrity: `{json.dumps(result_snapshots['regenerated']['integrity'], ensure_ascii=False, sort_keys=True)}`",
            "",
        ]
    )
    return "\n".join(lines)


def sync_research_evaluation_reproducibility_report(
    *,
    reference_output_path: Path,
    regenerated_output_path: Path,
    report_dir: Path | None = None,
    generated_at: datetime | str | None = None,
) -> dict[str, Any]:
    """재현성 비교 JSON/Markdown 리포트를 디스크에 저장한다."""

    resolved_report_dir = report_dir or Path(
        os.path.commonpath(
            [
                str(reference_output_path.parent.resolve()),
                str(regenerated_output_path.parent.resolve()),
            ]
        )
    )
    report = build_research_evaluation_reproducibility_report(
        reference_output_path=reference_output_path,
        regenerated_output_path=regenerated_output_path,
        generated_at=generated_at,
    )
    resolved_report_dir.mkdir(parents=True, exist_ok=True)
    json_path = resolved_report_dir / REPRODUCIBILITY_CHECK_REPORT_JSON_FILENAME
    markdown_path = resolved_report_dir / REPRODUCIBILITY_CHECK_REPORT_MARKDOWN_FILENAME
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    markdown_path.write_text(
        render_research_evaluation_reproducibility_markdown(report),
        encoding="utf-8",
    )
    return {
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
        "passed": report["passed"],
        "mismatched_items": report["mismatched_items"],
    }


def write_research_evaluation_bundle(
    *,
    result: dict[str, Any],
    config_path: Path,
    output_path: Path,
    created_at: datetime | str | None,
    dataset_artifacts: OfflineEvaluationDatasetArtifacts,
    runtime_params_path: Path | None = None,
    runtime_params: dict[str, Any] | None = None,
) -> tuple[Path, Path]:
    """평가 결과 JSON과 companion 재현성 매니페스트를 함께 저장한다."""

    normalized_result, prediction_payload_obj, metrics_payload_obj = (
        _normalize_result_payloads(result)
    )
    output_payload = _stable_json_payload(normalized_result)
    prediction_artifact_payload = _stable_json_payload(prediction_payload_obj)
    metrics_artifact_payload = _stable_json_payload(metrics_payload_obj)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output_payload, encoding="utf-8")
    prediction_artifact_path = prediction_artifact_path_for_output(output_path)
    prediction_artifact_path.write_text(
        prediction_artifact_payload,
        encoding="utf-8",
    )
    metrics_artifact_path = metrics_artifact_path_for_output(output_path)
    metrics_artifact_path.write_text(
        metrics_artifact_payload,
        encoding="utf-8",
    )

    config = json.loads(config_path.read_text(encoding="utf-8"))
    manifest = build_research_evaluation_manifest(
        config_path=config_path,
        config=config,
        output_path=output_path,
        output_payload=output_payload,
        created_at=created_at,
        dataset_artifacts=dataset_artifacts,
        runtime_params_path=runtime_params_path,
        runtime_params=runtime_params,
        prediction_artifact_path=prediction_artifact_path,
        prediction_artifact_payload=prediction_artifact_payload,
        metrics_artifact_path=metrics_artifact_path,
        metrics_artifact_payload=metrics_artifact_payload,
    )
    manifest_path = manifest_path_for_output(output_path)
    manifest_path.write_text(
        serialize_reproducibility_manifest(manifest),
        encoding="utf-8",
    )
    return output_path, manifest_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "research_clean 2회 실행 산출물을 비교해 재현성 검사용 JSON/Markdown 리포트를 저장한다."
        )
    )
    parser.add_argument(
        "--reference-output",
        required=True,
        help="기준 research_clean.json 경로",
    )
    parser.add_argument(
        "--regenerated-output",
        required=True,
        help="재실행 research_clean.json 경로",
    )
    parser.add_argument(
        "--report-dir",
        help="리포트 저장 디렉터리. 생략 시 두 실행 디렉터리의 공통 상위 디렉터리 사용",
    )
    parser.add_argument(
        "--generated-at",
        help="리포트 생성 시각 override (ISO-8601)",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    result = sync_research_evaluation_reproducibility_report(
        reference_output_path=Path(args.reference_output),
        regenerated_output_path=Path(args.regenerated_output),
        report_dir=Path(args.report_dir) if args.report_dir else None,
        generated_at=args.generated_at,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["passed"] is False:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
