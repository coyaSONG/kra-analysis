"""Offline evaluation dataset artifact resolution helpers."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evaluation.leakage_checks import check_detailed_results_for_leakage
from shared.prerace_field_policy import (
    filter_prerace_payload,
    validate_operational_dataset_payload,
)

from autoresearch.holdout_dataset import (
    audit_candidate_selection_traces,
    audit_snapshot_manifest_races,
)

_DATASET_NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")
_TEMPORAL_VIOLATION_PREVIEW_LIMIT = 5
_LEGACY_BOOTSTRAP_REPLAY_STATUS = "legacy_snapshot_without_manifest"
_LEGACY_BOOTSTRAP_SOURCE = "offline_evaluation_snapshot_legacy_bootstrap"
_LEGACY_BOOTSTRAP_CREATED_AT = "1970-01-01T00:00:00+00:00"


@dataclass(frozen=True, slots=True)
class OfflineEvaluationDatasetArtifacts:
    """Separated artifact bundle used by offline evaluation only."""

    dataset: str
    artifact_root: Path
    dataset_path: Path
    answer_key_path: Path
    manifest_path: Path


def _build_legacy_bootstrap_manifest(
    *,
    dataset: str,
    races: list[dict[str, Any]],
) -> dict[str, Any]:
    race_rows: list[dict[str, Any]] = []
    race_ids: list[str] = []
    seen_race_ids: set[str] = set()

    for index, race in enumerate(races):
        if not isinstance(race, dict):
            raise ValueError(
                "offline dataset artifact entries must be JSON objects when bootstrapping a manifest: "
                f"dataset={dataset}, index={index}"
            )
        race_id = _normalize_race_id(race.get("race_id"))
        if not race_id:
            raise ValueError(
                "offline dataset artifact entries require race_id when bootstrapping a manifest: "
                f"dataset={dataset}, index={index}"
            )
        if race_id in seen_race_ids:
            raise ValueError(
                f"offline dataset artifact contains duplicate race_id while bootstrapping manifest: {race_id}"
            )
        seen_race_ids.add(race_id)
        race_ids.append(race_id)
        race_rows.append(
            {
                "race_id": race_id,
                "replay_status": _LEGACY_BOOTSTRAP_REPLAY_STATUS,
                "include_in_strict_dataset": True,
            }
        )

    return {
        "format_version": "holdout-dataset-manifest-v1",
        "dataset": dataset,
        "created_at": _LEGACY_BOOTSTRAP_CREATED_AT,
        "race_count": len(race_rows),
        "strict_race_count": len(race_rows),
        "dataset_metadata": {
            "source": _LEGACY_BOOTSTRAP_SOURCE,
            "dataset_name": dataset,
            "requested_limit": None,
            "race_ids": race_ids,
        },
        "filter_policy": {
            "source_filter_basis": "entry_finalized_at",
            "required_pre_cutoff": True,
            "hard_required_sources": [
                "API214_1",
                "API72_2",
                "API189_1",
                "API9_1",
            ],
            "payload_shape": "legacy-race-array",
            "bootstrap_note": (
                "generated from legacy checked-in snapshot because dataset-side manifest was missing"
            ),
        },
        "replay_status_counts": {
            _LEGACY_BOOTSTRAP_REPLAY_STATUS: len(race_rows),
        },
        "audit": {
            "legacy_bootstrap": True,
            "warning": (
                "checked-in snapshot lacked per-race snapshot_meta; regenerate snapshots for full timing audit coverage"
            ),
        },
        "candidate_selection_audit": {
            "legacy_bootstrap": True,
        },
        "races": race_rows,
    }


def _maybe_materialize_legacy_bootstrap_manifest(
    bundle: OfflineEvaluationDatasetArtifacts,
) -> None:
    if bundle.manifest_path.exists():
        return
    if not bundle.dataset_path.exists() or not bundle.answer_key_path.exists():
        return

    dataset_payload = json.loads(bundle.dataset_path.read_text(encoding="utf-8"))
    if not isinstance(dataset_payload, list):
        raise ValueError(
            f"offline dataset artifact must be a JSON array: {bundle.dataset_path}"
        )

    manifest_payload = _build_legacy_bootstrap_manifest(
        dataset=bundle.dataset,
        races=dataset_payload,
    )
    bundle.manifest_path.write_text(
        json.dumps(manifest_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _is_legacy_bootstrap_manifest(manifest_payload: dict[str, Any]) -> bool:
    audit = manifest_payload.get("audit")
    if isinstance(audit, dict) and audit.get("legacy_bootstrap") is True:
        return True

    candidate_selection_audit = manifest_payload.get("candidate_selection_audit")
    if (
        isinstance(candidate_selection_audit, dict)
        and candidate_selection_audit.get("legacy_bootstrap") is True
    ):
        return True

    filter_policy = manifest_payload.get("filter_policy")
    if (
        isinstance(filter_policy, dict)
        and str(filter_policy.get("payload_shape") or "").strip() == "legacy-race-array"
    ):
        return True

    return False


def _preview(
    items: list[str], *, limit: int = _TEMPORAL_VIOLATION_PREVIEW_LIMIT
) -> str:
    if not items:
        return "[]"
    preview = items[:limit]
    remainder = len(items) - len(preview)
    suffix = "" if remainder <= 0 else f" ... (+{remainder} more)"
    return f"{preview}{suffix}"


def _normalize_race_id(value: Any) -> str:
    return str(value or "").strip()


def _validate_manifest_temporal_integrity(
    *,
    dataset: str,
    manifest_payload: dict[str, Any],
    legacy_bootstrap: bool = False,
) -> dict[str, dict[str, Any]]:
    manifest_races = manifest_payload.get("races")
    if not isinstance(manifest_races, list):
        raise ValueError(
            "offline evaluation dataset manifest must include per-race timing records in manifest.races"
        )

    race_index: dict[str, dict[str, Any]] = {}
    duplicate_race_ids: list[str] = []
    for row in manifest_races:
        if not isinstance(row, dict):
            raise ValueError(
                "offline evaluation dataset manifest.races entries must be JSON objects"
            )
        race_id = _normalize_race_id(row.get("race_id"))
        if not race_id:
            raise ValueError(
                "offline evaluation dataset manifest.races entries require race_id"
            )
        if race_id in race_index:
            duplicate_race_ids.append(race_id)
            continue
        race_index[race_id] = row

    if duplicate_race_ids:
        raise ValueError(
            "offline evaluation dataset manifest contains duplicate race_ids: "
            f"{sorted(set(duplicate_race_ids))}"
        )

    if legacy_bootstrap:
        return race_index

    audit_report = audit_snapshot_manifest_races(list(race_index.values()))
    if not audit_report["passed"]:
        violations = [
            f"{item['race_id']}:{item['code']}" for item in audit_report["violations"]
        ]
        raise ValueError(
            f"offline evaluation dataset manifest timing audit failed for {dataset}: "
            f"{_preview(violations)}"
        )

    return race_index


def _validate_dataset_temporal_integrity(
    *,
    dataset: str,
    races: list[dict[str, Any]],
    answers: dict[str, Any],
    manifest_race_index: dict[str, dict[str, Any]],
    legacy_bootstrap: bool = False,
) -> None:
    dataset_race_ids: list[str] = []
    duplicate_race_ids: list[str] = []
    missing_answer_keys: list[str] = []
    timing_rows: list[dict[str, Any]] = []

    for race in races:
        if not isinstance(race, dict):
            raise ValueError("offline dataset artifact entries must be JSON objects")

        race_id = _normalize_race_id(race.get("race_id"))
        if not race_id:
            raise ValueError("offline dataset artifact entries require race_id")
        if race_id in dataset_race_ids:
            duplicate_race_ids.append(race_id)
        dataset_race_ids.append(race_id)

        if race_id not in answers:
            missing_answer_keys.append(race_id)

        manifest_row = manifest_race_index.get(race_id)
        if manifest_row is None:
            raise ValueError(
                f"offline dataset race {race_id} is missing from manifest.races timing records"
            )

        if not legacy_bootstrap:
            snapshot_meta = race.get("snapshot_meta")
            if not isinstance(snapshot_meta, dict):
                raise ValueError(
                    f"offline dataset race {race_id} is missing snapshot_meta required for temporal audit"
                )

            if snapshot_meta != manifest_row:
                raise ValueError(
                    f"offline dataset race {race_id} snapshot_meta does not match manifest timing record"
                )

            source_lookup = snapshot_meta.get("source_lookup")
            entry_finalized_at = snapshot_meta.get("entry_finalized_at")
            if (
                not isinstance(source_lookup, dict)
                or str(source_lookup.get("entry_snapshot_at") or "").strip()
                != str(entry_finalized_at or "").strip()
            ):
                raise ValueError(
                    f"offline dataset race {race_id} source_lookup.entry_snapshot_at must match entry_finalized_at"
                )

            timing_rows.append(snapshot_meta)

        sanitized_race = (
            filter_prerace_payload(race)[0] if legacy_bootstrap else deepcopy(race)
        )
        sanitized_race.pop("snapshot_meta", None)
        sanitized_race.pop("input_schema", None)

        leakage_report = check_detailed_results_for_leakage(
            [{"race_id": race_id, "race_data": sanitized_race}]
        )
        if not leakage_report["passed"]:
            raise ValueError(
                f"offline dataset race {race_id} contains post-race leakage fields: "
                f"{_preview(leakage_report['issues'])}"
            )

        schema_report = validate_operational_dataset_payload(sanitized_race)
        if not schema_report["passed"]:
            raise ValueError(
                f"offline dataset race {race_id} violates prerace field policy: "
                f"{_preview(schema_report['violating_paths'])}"
            )

    if duplicate_race_ids:
        raise ValueError(
            "offline dataset artifact contains duplicate race_ids: "
            f"{sorted(set(duplicate_race_ids))}"
        )

    if missing_answer_keys:
        raise ValueError(
            "offline dataset artifact is missing answer keys for races: "
            f"{_preview(sorted(set(missing_answer_keys)))}"
        )

    manifest_race_ids = sorted(manifest_race_index)
    dataset_race_id_set = sorted(set(dataset_race_ids))
    if dataset_race_id_set != manifest_race_ids:
        missing_from_dataset = sorted(set(manifest_race_ids) - set(dataset_race_id_set))
        extra_in_dataset = sorted(set(dataset_race_id_set) - set(manifest_race_ids))
        raise ValueError(
            "offline dataset artifact race_id set does not match manifest.races: "
            f"missing_from_dataset={missing_from_dataset}, extra_in_dataset={extra_in_dataset}"
        )

    if legacy_bootstrap:
        return

    candidate_audit = audit_candidate_selection_traces(races)
    if not candidate_audit["passed"]:
        violations = [
            f"{item['race_id']}:{item['code']}"
            for item in candidate_audit["violations"]
        ]
        raise ValueError(
            f"offline dataset candidate trace audit failed for {dataset}: "
            f"{_preview(violations)}"
        )

    timing_audit = audit_snapshot_manifest_races(timing_rows)
    if not timing_audit["passed"]:
        violations = [
            f"{item['race_id']}:{item['code']}" for item in timing_audit["violations"]
        ]
        raise ValueError(
            f"offline dataset timing audit failed for {dataset}: {_preview(violations)}"
        )


def _validate_dataset_name(dataset: str) -> str:
    normalized = str(dataset).strip()
    if not normalized:
        raise ValueError("dataset name is required")
    if not _DATASET_NAME_RE.fullmatch(normalized):
        raise ValueError(
            "dataset name must contain only ASCII letters, digits, and underscores"
        )
    return normalized


def resolve_offline_evaluation_dataset_artifacts(
    dataset: str,
    *,
    artifact_root: Path,
) -> OfflineEvaluationDatasetArtifacts:
    """Resolve and validate the only allowed offline evaluation input artifacts."""

    normalized_dataset = _validate_dataset_name(dataset)
    root = artifact_root.resolve()
    bundle = OfflineEvaluationDatasetArtifacts(
        dataset=normalized_dataset,
        artifact_root=root,
        dataset_path=root / f"{normalized_dataset}.json",
        answer_key_path=root / f"{normalized_dataset}_answer_key.json",
        manifest_path=root / f"{normalized_dataset}_manifest.json",
    )
    _maybe_materialize_legacy_bootstrap_manifest(bundle)
    missing = [
        str(path)
        for path in (
            bundle.dataset_path,
            bundle.answer_key_path,
            bundle.manifest_path,
        )
        if not path.exists()
    ]
    if missing:
        raise FileNotFoundError(
            "offline evaluation requires separated dataset artifacts only; "
            f"missing={missing}"
        )

    dataset_payload = json.loads(bundle.dataset_path.read_text(encoding="utf-8"))
    answer_key_payload = json.loads(bundle.answer_key_path.read_text(encoding="utf-8"))
    manifest_payload = json.loads(bundle.manifest_path.read_text(encoding="utf-8"))
    manifest_dataset = str(manifest_payload.get("dataset") or "").strip()
    if manifest_dataset != normalized_dataset:
        raise ValueError(
            "dataset manifest does not match requested dataset: "
            f"requested={normalized_dataset!r} manifest={manifest_dataset!r}"
        )

    if not isinstance(dataset_payload, list):
        raise ValueError(
            f"offline dataset artifact must be a JSON array: {bundle.dataset_path}"
        )
    if not isinstance(answer_key_payload, dict):
        raise ValueError(
            f"offline answer key artifact must be a JSON object: {bundle.answer_key_path}"
        )

    legacy_bootstrap = _is_legacy_bootstrap_manifest(manifest_payload)
    manifest_race_index = _validate_manifest_temporal_integrity(
        dataset=normalized_dataset,
        manifest_payload=manifest_payload,
        legacy_bootstrap=legacy_bootstrap,
    )
    _validate_dataset_temporal_integrity(
        dataset=normalized_dataset,
        races=dataset_payload,
        answers=answer_key_payload,
        manifest_race_index=manifest_race_index,
        legacy_bootstrap=legacy_bootstrap,
    )

    return bundle


def load_offline_evaluation_dataset(
    artifacts: OfflineEvaluationDatasetArtifacts,
) -> tuple[list[dict[str, Any]], dict[str, list[int]]]:
    """Load only the separated dataset+answer_key artifacts for offline evaluation."""

    races = json.loads(artifacts.dataset_path.read_text(encoding="utf-8"))
    answers = json.loads(artifacts.answer_key_path.read_text(encoding="utf-8"))
    if not isinstance(races, list):
        raise ValueError(
            f"offline dataset artifact must be a JSON array: {artifacts.dataset_path}"
        )
    if not isinstance(answers, dict):
        raise ValueError(
            f"offline answer key artifact must be a JSON object: {artifacts.answer_key_path}"
        )
    manifest_payload = json.loads(artifacts.manifest_path.read_text(encoding="utf-8"))
    if _is_legacy_bootstrap_manifest(manifest_payload):
        races = [filter_prerace_payload(race)[0] for race in races]
    return races, answers
