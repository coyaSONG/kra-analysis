"""Export checksum-pinned feature archives, never prediction-rate evidence."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any
from uuid import uuid4

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.kra_race_card_pdf import NUMERIC_FIELDS, validate_identity

from autoresearch.kra_race_card_pdf_replay import (
    MAX_MANIFEST_BYTES,
    ReplayError,
    archive_path,
    checked_digest,
    parse_json,
    read_bytes,
    replay_race_card_snapshot,
    sha256,
)

PLAN_VERSION = "kra-race-card-pdf-bundle-plan-v1"
BUNDLE_VERSION = "kra-race-card-pdf-feature-bundle-v1"
SCOPE_BASIS = "capture_inventory_not_evaluation_universe"
DEFAULT_OUTPUT_DIR = Path(".cache/autoresearch/race_card_pdf_bundles")
IMPLEMENTATION_FILES = (
    "shared/kra_race_card_pdf.py",
    "shared/kra_race_card_pdf_audit.py",
    "shared/kra_entry_sheet.py",
    "shared/operational_cutoff.py",
    "shared/entry_snapshot_metadata.py",
    "autoresearch/kra_entry_sheet_snapshot.py",
    "autoresearch/kra_race_card_pdf_snapshot.py",
    "autoresearch/kra_race_card_pdf_replay.py",
    "autoresearch/kra_race_card_pdf_bundle.py",
)
RACE_KEYS = {
    "meet",
    "race_date",
    "race_no",
    "race_id",
    "manifest_path",
    "manifest_sha256",
    "pdf_sha256",
    "entry_manifest_sha256",
}


def implementation_fingerprint() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    dependencies = {}
    for name in ("pdfplumber", "pdfminer.six", "pypdfium2"):
        try:
            dependencies[name] = version(name)
        except PackageNotFoundError:
            dependencies[name] = "not_installed"
    return {
        "source_sha256": {
            name: sha256((root / name).read_bytes()) for name in IMPLEMENTATION_FILES
        },
        "dependency_versions": dependencies,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
    }


def _identity(race_id: Any) -> dict[str, Any]:
    if not isinstance(race_id, str):
        raise ReplayError("invalid_planned_race_id")
    try:
        date, meeting, number = race_id.split("_")
        identity = {"meet": int(meeting), "race_date": date, "race_no": int(number)}
        validate_identity(**identity)
    except (ValueError, TypeError) as exc:
        raise ReplayError("invalid_planned_race_id") from exc
    if race_id != f"{date}_{identity['meet']}_{identity['race_no']}":
        raise ReplayError("noncanonical_planned_race_id")
    return identity


def plan_from_cohort(cohort_path: Path, *, archive_root: Path) -> dict[str, Any]:
    """Pin current manifest bytes, without pretending this is acquisition time."""
    content = read_bytes(cohort_path, limit=MAX_MANIFEST_BYTES)
    cohort = parse_json(content)
    observations = cohort.get("observations")
    groups = cohort.get("planned_meet_dates")
    if not isinstance(observations, list) or not isinstance(groups, list):
        raise ReplayError("invalid_capture_inventory")
    requested = set()
    for group in groups:
        if not isinstance(group, list) or len(group) != 2:
            raise ReplayError("invalid_planned_meeting_date")
        validate_identity(group[0], group[1], 1)
        requested.add(tuple(group))
    if len(requested) != len(groups) or not requested:
        raise ReplayError("invalid_planned_meeting_date")
    races = []
    observed_groups = set()
    unknown_groups = set()
    for observation in observations:
        if not isinstance(observation, dict):
            raise ReplayError("invalid_capture_observation")
        if "race_id" not in observation:
            group = (observation.get("meet"), observation.get("date"))
            if group not in requested:
                raise ReplayError("observation_outside_planned_scope")
            unknown_groups.add(group)
            continue
        identity = _identity(observation["race_id"])
        group = (identity["meet"], identity["race_date"])
        if group not in requested:
            raise ReplayError("observation_outside_planned_scope")
        observed_groups.add(group)
        record = {
            **identity,
            "race_id": observation["race_id"],
            "manifest_path": observation.get("manifest_path"),
            "manifest_sha256": None,
            "pdf_sha256": observation.get("sha256"),
            "entry_manifest_sha256": None,
        }
        try:
            path = archive_path(record["manifest_path"], archive_root=archive_root)
            if (
                path.name != "snapshot.json"
                or path.parent.parent.name != record["race_id"]
            ):
                raise ReplayError("pdf_manifest_path_contract_mismatch")
            manifest_content = read_bytes(path, limit=MAX_MANIFEST_BYTES)
            record["manifest_sha256"] = sha256(manifest_content)
            manifest = parse_json(manifest_content)
            embedded = manifest.get("entry_snapshot")
            if isinstance(embedded, dict) and embedded.get("source_manifest_path"):
                entry_path = archive_path(
                    embedded["source_manifest_path"], archive_root=archive_root
                )
                if (
                    entry_path.name != "entry_capture.json"
                    or entry_path.parent.parent.parent != path.parent.parent.parent
                ):
                    raise ReplayError("entry_manifest_not_same_capture_archive")
                record["entry_manifest_sha256"] = sha256(
                    read_bytes(entry_path, limit=MAX_MANIFEST_BYTES)
                )
        except ReplayError:
            # Retain absent or damaged sources in the declared inventory.
            pass
        races.append(record)
    unknown_groups.update(requested - observed_groups)
    return {
        "format_version": PLAN_VERSION,
        "scope_basis": SCOPE_BASIS,
        "pinned_at": datetime.now(UTC).isoformat(),
        "cohort_sha256": sha256(content),
        "implementation": implementation_fingerprint(),
        "races": races,
        "unresolved_scope": [
            {"meet": meet, "race_date": date, "reason": "race_universe_unknown"}
            for meet, date in sorted(unknown_groups)
        ],
    }


def _validate_plan(plan: dict[str, Any]) -> datetime:
    if set(plan) != {
        "format_version",
        "scope_basis",
        "pinned_at",
        "cohort_sha256",
        "implementation",
        "races",
        "unresolved_scope",
    }:
        raise ReplayError("unexpected_plan_fields")
    if plan["format_version"] != PLAN_VERSION or plan["scope_basis"] != SCOPE_BASIS:
        raise ReplayError("unsupported_plan_contract")
    if plan["implementation"] != implementation_fingerprint():
        raise ReplayError("plan_implementation_changed")
    try:
        pinned = datetime.fromisoformat(plan["pinned_at"])
    except (ValueError, TypeError) as exc:
        raise ReplayError("invalid_plan_pin_timestamp") from exc
    if pinned.tzinfo is None or pinned.utcoffset() is None:
        raise ReplayError("invalid_plan_pin_timestamp")
    if pinned > datetime.now(UTC):
        raise ReplayError("plan_pin_timestamp_in_future")
    if plan["cohort_sha256"] is not None:
        checked_digest(plan["cohort_sha256"])
    races, unknown = plan["races"], plan["unresolved_scope"]
    if (
        not isinstance(races, list)
        or not isinstance(unknown, list)
        or not 1 <= len(races) + len(unknown) <= 10_000
    ):
        raise ReplayError("invalid_plan_inventory")
    seen = set()
    for race in races:
        if not isinstance(race, dict) or set(race) != RACE_KEYS:
            raise ReplayError("unexpected_planned_race_fields")
        identity = _identity(race["race_id"])
        if any(
            type(race[key]) is not type(value) or race[key] != value
            for key, value in identity.items()
        ):
            raise ReplayError("planned_race_identity_mismatch")
        if race["race_id"] in seen:
            raise ReplayError("duplicate_planned_race")
        seen.add(race["race_id"])
        for key in ("manifest_sha256", "pdf_sha256", "entry_manifest_sha256"):
            if race[key] is not None:
                checked_digest(race[key])
        if race["manifest_path"] is not None and not isinstance(
            race["manifest_path"], str
        ):
            raise ReplayError("invalid_planned_manifest_path")
    seen_groups = set()
    for group in unknown:
        if not isinstance(group, dict) or set(group) != {"meet", "race_date", "reason"}:
            raise ReplayError("invalid_unresolved_scope")
        validate_identity(group["meet"], group["race_date"], 1)
        key = (group["meet"], group["race_date"])
        if group["reason"] != "race_universe_unknown" or key in seen_groups:
            raise ReplayError("invalid_unresolved_scope")
        seen_groups.add(key)
    return pinned


def _feature_projection(row: dict[str, Any], replay: dict[str, Any]) -> dict[str, Any]:
    features = {}
    for field in NUMERIC_FIELDS:
        value = row[field]
        if value is not None and (
            type(value) not in (int, float)
            or not math.isfinite(value)
            or value < 0
            or (field == "trainer_win_rate" and value > 100)
        ):
            raise ReplayError("invalid_numeric_pdf_feature")
        features[field] = value
        features[f"{field}_missing"] = value is None
    features["training_summary_truncated"] = row["training_summary_truncated"]
    return {
        "race_id": replay["race_id"],
        "chulNo": row["chulNo"],
        "hrNo": row["hrNo"],
        "hrName": row["hrName"],
        "features_available_at": replay["features_available_at"],
        "features": features,
    }


def build_bundle(plan: dict[str, Any], *, archive_root: Path) -> dict[str, Any]:
    pinned = _validate_plan(plan)
    races = []
    feature_rows = []
    for record in plan["races"]:
        identity = {key: record[key] for key in ("meet", "race_date", "race_no")}
        if not record["manifest_path"] or not record["manifest_sha256"]:
            replay = {
                "eligible_for_prerace_features": False,
                "reasons": ["snapshot_not_available_in_plan"],
                "feature_rows": [],
                "evidence": {},
            }
        elif not record["entry_manifest_sha256"]:
            replay = {
                "eligible_for_prerace_features": False,
                "reasons": ["entry_manifest_not_pinned"],
                "feature_rows": [],
                "evidence": {},
            }
        else:
            replay = replay_race_card_snapshot(
                record["manifest_path"],
                archive_root=archive_root,
                expected_sha256=record["manifest_sha256"],
                expected_identity=identity,
                expected_pdf_sha256=record["pdf_sha256"],
                expected_entry_manifest_sha256=record["entry_manifest_sha256"],
            )
        if (
            replay["eligible_for_prerace_features"]
            and datetime.fromisoformat(replay["features_available_at"]) > pinned
        ):
            replay.update(
                eligible_for_prerace_features=False,
                reasons=["source_after_plan_pin"],
                feature_rows=[],
            )
        try:
            projected = [
                _feature_projection(row, replay) for row in replay["feature_rows"]
            ]
        except ReplayError as exc:
            replay.update(eligible_for_prerace_features=False, reasons=[str(exc)])
            projected = []
        feature_rows.extend(projected)
        races.append(
            {
                **identity,
                "race_id": record["race_id"],
                "eligible_for_prerace_features": replay[
                    "eligible_for_prerace_features"
                ],
                "fallback_required": not replay["eligible_for_prerace_features"],
                "reasons": replay["reasons"],
                "entry_horse_count": replay.get("entry_horse_count"),
                "feature_row_count": len(projected),
                "evidence": replay["evidence"],
            }
        )
    eligible = sum(race["eligible_for_prerace_features"] for race in races)
    complete = eligible == len(races) and not plan["unresolved_scope"]
    return {
        "format_version": BUNDLE_VERSION,
        "scope_basis": SCOPE_BASIS,
        "status": "verified_feature_archive" if complete else "partial_feature_archive",
        "all_declared_sources_eligible": complete,
        "implementation": plan["implementation"],
        "numeric_feature_columns": list(NUMERIC_FIELDS),
        "race_count": len(races),
        "eligible_race_count": eligible,
        "blocked_race_count": len(races) - eligible,
        "feature_row_count": len(feature_rows),
        "races": races,
        "feature_rows": feature_rows,
        "unresolved_scope": plan["unresolved_scope"],
        "counts_as_70_percent_evidence": False,
        "model_promoted": False,
        "prediction_accuracy_evaluated": False,
        "timing_evidence": "local_capture_completion_not_third_party_attestation",
    }


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False
        )
        + "\n"
    ).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--cohort", type=Path)
    inputs.add_argument("--plan", type=Path)
    parser.add_argument("--archive-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    try:
        plan = (
            plan_from_cohort(args.cohort, archive_root=args.archive_root)
            if args.cohort
            else parse_json(read_bytes(args.plan, limit=MAX_MANIFEST_BYTES))
        )
        bundle = build_bundle(plan, archive_root=args.archive_root)
        exported = datetime.now(UTC)
        directory = args.output_dir / (
            exported.strftime("%Y%m%dT%H%M%S.%fZ") + "_" + uuid4().hex[:12]
        )
        directory.mkdir(parents=True, exist_ok=False)
        plan_content = _json_bytes(plan)
        bundle.update(
            exported_at=exported.isoformat(), input_plan_sha256=sha256(plan_content)
        )
        bundle_content = _json_bytes(bundle)
        for name, content in (
            ("input_plan.json", plan_content),
            ("feature_bundle.json", bundle_content),
        ):
            with (directory / name).open("xb") as stream:
                stream.write(content)
        summary = {
            "manifest_path": str(directory / "feature_bundle.json"),
            "input_plan_path": str(directory / "input_plan.json"),
            "bundle_sha256": sha256(bundle_content),
            **{
                key: bundle[key]
                for key in (
                    "status",
                    "race_count",
                    "eligible_race_count",
                    "blocked_race_count",
                    "feature_row_count",
                    "unresolved_scope",
                )
            },
            "blocked_races": [
                {"race_id": race["race_id"], "reasons": race["reasons"]}
                for race in bundle["races"]
                if race["fallback_required"]
            ],
        }
        with (directory / "export_summary.json").open("xb") as stream:
            stream.write(_json_bytes(summary))
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return (
            2
            if args.require_complete and not bundle["all_declared_sources_eligible"]
            else 0
        )
    except (ReplayError, ValueError, TypeError, OSError) as exc:
        print(
            json.dumps(
                {
                    "status": "invalid_bundle_input",
                    "reason": str(exc)
                    if isinstance(exc, ReplayError)
                    else "invalid_plan_or_output",
                    "error_type": type(exc).__name__,
                },
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
