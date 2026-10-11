"""Minimum timing checks and repository-reviewed production training admission.

Timing metadata is not proof of historical source availability. Only exact recipes
reviewed into the canonical registry can cross the production admission boundary.
"""

from __future__ import annotations

import json
import platform
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from typing import Any

from shared.entry_snapshot_metadata import HARD_REQUIRED_SOURCE_APIS, KST
from shared.kra_race_identity import MEET_NAMES, validate_race_identity

from autoresearch.dataset_artifacts import (
    _is_legacy_bootstrap_manifest,
    _validate_dataset_name,
    _validate_dataset_temporal_integrity,
    _validate_manifest_temporal_integrity,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
APPROVAL_REGISTRY_PATH = (
    REPO_ROOT / "data/contracts/production_training_reviews_v1.json"
)
ADMISSION_VERSION = "production-training-admission-v1"
_RACE_ID = re.compile(r"^([0-9]{8})_([1-4])_([1-9]|1[0-9]|20)$")
_ROLES = ("config", "dataset", "answer_key", "manifest")
_IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[3]
_IMPLEMENTATION_FILES = (
    "packages/scripts/ml/train_clean.py",
    "packages/scripts/autoresearch/training_evidence.py",
    "packages/scripts/autoresearch/dataset_artifacts.py",
    "packages/scripts/autoresearch/holdout_dataset.py",
    "packages/scripts/autoresearch/research_clean.py",
    "packages/scripts/autoresearch/parameter_context.py",
    "packages/scripts/autoresearch/reproducibility.py",
    "packages/scripts/autoresearch/split_plan.py",
    "packages/scripts/feature_engineering.py",
    "packages/scripts/evaluation/leakage_checks.py",
    "packages/scripts/shared/prediction_input_schema.py",
    "packages/scripts/shared/prerace_field_policy.py",
    "packages/scripts/shared/prerace_field_metadata_schema.py",
    "packages/scripts/shared/feature_source_timing_contract.py",
    "packages/scripts/shared/entry_snapshot_metadata.py",
    "packages/scripts/shared/kra_race_identity.py",
    "packages/scripts/shared/autoresearch_config_schema.py",
    "packages/scripts/shared/execution_matrix.py",
    "data/contracts/prediction_input_field_registry_v1.csv",
    "data/contracts/feature_source_timing_contract_v1.csv",
    "uv.lock",
)


def _implementation_bytes() -> bytes:
    files = {}
    for relative in _IMPLEMENTATION_FILES:
        raw = (_IMPLEMENTATION_ROOT / relative).read_bytes()
        files[relative] = {"sha256": sha256(raw).hexdigest(), "byte_size": len(raw)}
    return json.dumps(
        {
            "files": files,
            "python": platform.python_version(),
            "packages": {
                name: version(name)
                for name in ("numpy", "scikit-learn", "joblib", "pydantic")
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


@dataclass(frozen=True, slots=True)
class FrozenTrainingInputs:
    """Validated immutable bytes, not paths to mutable input files."""

    dataset: str
    config_bytes: bytes
    dataset_bytes: bytes
    answer_key_bytes: bytes
    manifest_bytes: bytes
    implementation_bytes: bytes
    registry_bytes: bytes
    review_bytes: bytes
    review_id: str

    def load_dataset(self) -> tuple[list[dict], dict[str, list[int]]]:
        return json.loads(self.dataset_bytes), json.loads(self.answer_key_bytes)

    def receipt(self) -> dict[str, Any]:
        blobs = (
            self.config_bytes,
            self.dataset_bytes,
            self.answer_key_bytes,
            self.manifest_bytes,
            self.implementation_bytes,
            self.registry_bytes,
            self.review_bytes,
        )
        return {
            "admission_version": ADMISSION_VERSION,
            "source_review_id": self.review_id,
            "artifacts": {
                role: {"sha256": sha256(raw).hexdigest(), "byte_size": len(raw)}
                for role, raw in zip(
                    (*_ROLES, "implementation", "review_registry", "source_review"),
                    blobs,
                    strict=True,
                )
            },
            "minimum_timing_checks_passed": True,
            "admission_basis": "repository_review_of_exact_recipe",
            "model_promoted": False,
            "target_accuracy_verified": False,
            "implementation": json.loads(self.implementation_bytes),
        }

    def require_unchanged_implementation(self) -> None:
        if _implementation_bytes() != self.implementation_bytes:
            raise ValueError(
                "Training implementation or environment changed after admission"
            )


def _aware(value: Any, *, field: str, race_id: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{race_id}: missing aware timestamp {field}")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{race_id}: invalid timestamp {field}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{race_id}: timezone required for {field}")
    return parsed.astimezone(UTC)


def validate_minimum_training_timing(row: dict[str, Any]) -> None:
    """Necessary conditions only; this never authorizes unreviewed source lineage."""
    race_id = str(row.get("race_id", "unknown"))
    for name, expected in (
        ("include_in_strict_dataset", True),
        ("hard_required_sources_present", True),
        ("late_reissue_after_cutoff", False),
        ("cutoff_unbounded", False),
    ):
        if row.get(name) is not expected:
            raise ValueError(
                f"{race_id}: production training requires {name}={expected}"
            )
    if row.get("replay_status") != "strict":
        raise ValueError(
            f"{race_id}: production training requires strict replay_status"
        )
    source = row.get("timestamp_source")
    expected_confidence = {"source_revision": "high", "snapshot_collected_at": "medium"}
    if not isinstance(source, str) or source not in expected_confidence:
        raise ValueError(f"{race_id}: unverified timestamp_source {source!r}")
    if row.get("timestamp_confidence") != expected_confidence[source]:
        raise ValueError(f"{race_id}: invalid timestamp_confidence")
    if row.get("source_filter_basis") != "entry_finalized_at":
        raise ValueError(f"{race_id}: unsupported source_filter_basis")
    status = row.get("hard_required_source_status")
    if not isinstance(status, dict) or any(
        status.get(api) != "present" for api in HARD_REQUIRED_SOURCE_APIS
    ):
        raise ValueError(f"{race_id}: missing hard-required source status")

    start = _aware(
        row.get("scheduled_start_at"), field="scheduled_start_at", race_id=race_id
    )
    cutoff = _aware(
        row.get("operational_cutoff_at"), field="operational_cutoff_at", race_id=race_id
    )
    ready = _aware(
        row.get("snapshot_ready_at"), field="snapshot_ready_at", race_id=race_id
    )
    entry = _aware(
        row.get("entry_finalized_at"), field="entry_finalized_at", race_id=race_id
    )
    lookup = row.get("source_lookup")
    if not isinstance(lookup, dict):
        raise ValueError(f"{race_id}: missing source_lookup")
    captured = _aware(
        lookup.get("capture_completed_at"),
        field="source_lookup.capture_completed_at",
        race_id=race_id,
    )
    if not entry <= captured <= ready <= cutoff < start:
        raise ValueError(
            f"{race_id}: capture/ready/entry must precede bounded cutoff and start"
        )
    if source == "snapshot_collected_at" and entry != captured:
        raise ValueError(
            f"{race_id}: snapshot entry timestamp must match capture completion"
        )
    match = _RACE_ID.fullmatch(race_id)
    if match is None or start.astimezone(KST).strftime("%Y%m%d") != match[1]:
        raise ValueError(f"{race_id}: schedule does not match race identity")


def _validate_full_fields(races: list[dict], answers: dict[str, Any]) -> None:
    race_ids: set[str] = set()
    for race in races:
        if not isinstance(race, dict) or not isinstance(race.get("race_id"), str):
            raise ValueError("production training requires canonical race identities")
        race_id = race["race_id"]
        match = _RACE_ID.fullmatch(race_id)
        if match is None:
            raise ValueError(f"invalid production race identity: {race_id}")
        date, meet, number = match[1], int(match[2]), int(match[3])
        validate_race_identity(meet, date, number)
        if race_id in race_ids:
            raise ValueError(f"duplicate production race: {race_id}")
        race_ids.add(race_id)
        info = race.get("race_info")
        if (
            race.get("race_date") != date
            or not isinstance(info, dict)
            or info.get("rcDate") != date
            or type(info.get("meet")) not in (int, str)
            or info.get("meet")
            not in (
                meet,
                str(meet),
                *(name for name, code in MEET_NAMES.items() if code == meet),
            )
            or type(info.get("rcNo")) not in (int, str)
            or info.get("rcNo") not in (number, str(number))
            or isinstance(info.get("meet"), bool)
            or isinstance(info.get("rcNo"), bool)
        ):
            raise ValueError(f"{race_id}: inconsistent race identity")
        horses = race.get("horses")
        if (
            not isinstance(horses, list)
            or len(horses) < 3
            or type(info.get("dusu")) is not int
            or info["dusu"] != len(horses)
        ):
            raise ValueError(f"{race_id}: incomplete declared runner field")
        runners: set[int] = set()
        horse_ids: set[str] = set()
        for horse in horses:
            if not isinstance(horse, dict):
                raise ValueError(f"{race_id}: invalid runner")
            runner = horse.get("chulNo")
            horse_id = horse.get("hrNo")
            if (
                type(runner) is not int
                or not 1 <= runner <= 20
                or runner in runners
                or not isinstance(horse_id, str)
                or not horse_id.strip()
                or horse_id in horse_ids
            ):
                raise ValueError(
                    f"{race_id}: missing or duplicate runner/horse identity"
                )
            runners.add(runner)
            horse_ids.add(horse_id)
        target = answers.get(race_id)
        if (
            not isinstance(target, list)
            or len(target) != 3
            or any(type(item) is not int or item not in runners for item in target)
            or len(set(target)) != 3
        ):
            raise ValueError(f"{race_id}: invalid unordered three-horse target")
    if set(answers) != race_ids:
        raise ValueError(
            "production answer-key membership must match every dataset race"
        )


def _object(raw: bytes, *, role: str) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError(f"production {role} must be a JSON object")
    return payload


def _require_review(dataset: str, blobs: dict[str, bytes]) -> tuple[bytes, bytes, str]:
    registry_bytes = APPROVAL_REGISTRY_PATH.read_bytes()
    registry = _object(registry_bytes, role="review registry")
    if registry.get("format_version") != "production-training-reviews-v1":
        raise ValueError("unsupported production review registry")
    approvals = registry.get("approved_recipes")
    if not isinstance(approvals, list):
        raise ValueError("production review registry requires approved_recipes")
    actual_pins = {
        role: {"sha256": sha256(raw).hexdigest(), "byte_size": len(raw)}
        for role, raw in blobs.items()
    }
    matches = [
        item
        for item in approvals
        if isinstance(item, dict)
        and item.get("dataset") == dataset
        and item.get("artifacts") == actual_pins
    ]
    if len(matches) != 1:
        raise ValueError(
            "production training source lineage is unreviewed: no unique approved exact recipe; "
            "timing metadata alone is not pre-race proof (use offline diagnostics)"
        )
    approval = matches[0]
    review_id, relative_path = (
        approval.get("review_id"),
        approval.get("source_review_path"),
    )
    if (
        not isinstance(review_id, str)
        or not review_id.strip()
        or not isinstance(relative_path, str)
    ):
        raise ValueError("production approval requires a source review reference")
    review_path = (REPO_ROOT / relative_path).resolve()
    if not review_path.is_relative_to((REPO_ROOT / "docs/research").resolve()):
        raise ValueError("source review must remain inside docs/research")
    review_bytes = review_path.read_bytes()
    if not review_bytes or sha256(review_bytes).hexdigest() != approval.get(
        "source_review_sha256"
    ):
        raise ValueError("production source review content changed or is missing")
    return registry_bytes, review_bytes, review_id


def load_reviewed_training_inputs(
    *, config_path: Path, artifact_root: Path
) -> FrozenTrainingInputs:
    """Reject unsafe/unknown inputs before fit; never materialize compatibility data."""
    config_bytes = config_path.read_bytes()
    config = _object(config_bytes, role="config")
    if not isinstance(config.get("dataset"), str):
        raise ValueError("production config requires a string dataset name")
    dataset = _validate_dataset_name(config.get("dataset", ""))
    root = artifact_root.resolve()
    manifest_bytes = (root / f"{dataset}_manifest.json").read_bytes()
    manifest = _object(manifest_bytes, role="manifest")
    if _is_legacy_bootstrap_manifest(manifest):
        raise ValueError(
            "legacy bootstrap inputs are not eligible for production training"
        )
    if manifest.get("dataset") != dataset:
        raise ValueError("production dataset and manifest names differ")
    manifest_rows = manifest.get("races")
    if not isinstance(manifest_rows, list) or not manifest_rows:
        raise ValueError("production manifest requires a nonempty full race set")
    for row in manifest_rows:
        if not isinstance(row, dict):
            raise ValueError("production manifest race must be an object")
        validate_minimum_training_timing(row)

    dataset_bytes = (root / f"{dataset}.json").read_bytes()
    answer_key_bytes = (root / f"{dataset}_answer_key.json").read_bytes()
    races = json.loads(dataset_bytes)
    answers = _object(answer_key_bytes, role="answer key")
    if not isinstance(races, list) or not races:
        raise ValueError("production dataset requires a nonempty full race set")
    _validate_full_fields(races, answers)
    race_index = _validate_manifest_temporal_integrity(
        dataset=dataset, manifest_payload=manifest
    )
    _validate_dataset_temporal_integrity(
        dataset=dataset,
        races=races,
        answers=answers,
        manifest_race_index=race_index,
    )
    implementation_bytes = _implementation_bytes()
    blobs = dict(
        zip(
            _ROLES,
            (config_bytes, dataset_bytes, answer_key_bytes, manifest_bytes),
            strict=True,
        )
    )
    blobs["implementation"] = implementation_bytes
    registry_bytes, review_bytes, review_id = _require_review(dataset, blobs)
    return FrozenTrainingInputs(
        dataset=dataset,
        config_bytes=config_bytes,
        dataset_bytes=dataset_bytes,
        answer_key_bytes=answer_key_bytes,
        manifest_bytes=manifest_bytes,
        implementation_bytes=implementation_bytes,
        registry_bytes=registry_bytes,
        review_bytes=review_bytes,
        review_id=review_id,
    )
