from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.prerace_field_policy import filter_prerace_payload


def _sha256_path(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _safe_int(value: Any, default: int = 999999) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _canonical_horse_order(horses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        horses,
        key=lambda horse: (
            _safe_int(horse.get("chulNo")),
            str(horse.get("hrNo") or ""),
        ),
    )


def _strip_computed_features(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {
            key: _strip_computed_features(value)
            for key, value in payload.items()
            if key != "computed_features"
        }
    if isinstance(payload, list):
        return [_strip_computed_features(item) for item in payload]
    return deepcopy(payload)


def canonicalize_race_payload(race: dict[str, Any]) -> dict[str, Any]:
    filtered_race, _policy = filter_prerace_payload(deepcopy(race))
    filtered_race = _strip_computed_features(filtered_race)
    horses = filtered_race.get("horses")
    if isinstance(horses, list):
        filtered_race["horses"] = _canonical_horse_order(
            [horse for horse in horses if isinstance(horse, dict)]
        )
    return filtered_race


def _rewrite_manifest(
    *,
    manifest: dict[str, Any],
    source_dataset: str,
    output_dataset: str,
    source_hashes: dict[str, str],
    race_ids: list[str],
) -> dict[str, Any]:
    rewritten = deepcopy(manifest)
    rewritten["dataset"] = output_dataset
    rewritten["created_at"] = datetime.now(UTC).isoformat()
    rewritten["race_count"] = len(race_ids)
    rewritten["strict_race_count"] = len(race_ids)

    metadata = rewritten.setdefault("dataset_metadata", {})
    if isinstance(metadata, dict):
        metadata["dataset_name"] = output_dataset
        metadata["source_dataset_name"] = source_dataset
        metadata["race_ids"] = race_ids

    audit = rewritten.setdefault("audit", {})
    if isinstance(audit, dict):
        audit["legacy_bootstrap"] = True
        audit["canonicalized_prerace_v2"] = True
        audit["source_dataset"] = source_dataset
        audit["source_hashes"] = source_hashes
        audit["transform"] = {
            "policy": "filter_prerace_payload + strip computed_features + sort horses by chulNo/hrNo",
            "uses_answer_key_for_features": False,
        }

    candidate_audit = rewritten.setdefault("candidate_selection_audit", {})
    if isinstance(candidate_audit, dict):
        candidate_audit["legacy_bootstrap"] = True
        candidate_audit["canonicalized_prerace_v2"] = True

    rewritten["races"] = [
        {
            "race_id": race_id,
            "replay_status": "canonicalized_legacy_prerace_v2",
            "include_in_strict_dataset": True,
        }
        for race_id in race_ids
    ]
    rewritten["replay_status_counts"] = {
        "canonicalized_legacy_prerace_v2": len(race_ids),
    }
    return rewritten


def materialize_clean_dataset(
    *,
    artifact_root: Path,
    source_dataset: str,
    output_dataset: str,
) -> dict[str, Any]:
    source_dataset_path = artifact_root / f"{source_dataset}.json"
    source_answer_path = artifact_root / f"{source_dataset}_answer_key.json"
    source_manifest_path = artifact_root / f"{source_dataset}_manifest.json"

    races = json.loads(source_dataset_path.read_text(encoding="utf-8"))
    answers = json.loads(source_answer_path.read_text(encoding="utf-8"))
    manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    if not isinstance(races, list):
        raise ValueError("source dataset must be a JSON array")
    if not isinstance(answers, dict):
        raise ValueError("source answer key must be a JSON object")
    if not isinstance(manifest, dict):
        raise ValueError("source manifest must be a JSON object")

    clean_races = [canonicalize_race_payload(race) for race in races]
    race_ids = [str(race.get("race_id") or "") for race in clean_races]
    if any(not race_id for race_id in race_ids):
        raise ValueError("canonicalized dataset contains blank race_id")
    if len(race_ids) != len(set(race_ids)):
        raise ValueError("canonicalized dataset contains duplicate race_id")

    source_hashes = {
        "dataset_sha256": _sha256_path(source_dataset_path),
        "answer_key_sha256": _sha256_path(source_answer_path),
        "manifest_sha256": _sha256_path(source_manifest_path),
    }
    clean_manifest = _rewrite_manifest(
        manifest=manifest,
        source_dataset=source_dataset,
        output_dataset=output_dataset,
        source_hashes=source_hashes,
        race_ids=race_ids,
    )

    output_dataset_path = artifact_root / f"{output_dataset}.json"
    output_answer_path = artifact_root / f"{output_dataset}_answer_key.json"
    output_manifest_path = artifact_root / f"{output_dataset}_manifest.json"

    output_dataset_path.write_text(
        json.dumps(clean_races, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    output_answer_path.write_text(
        json.dumps(answers, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    output_manifest_path.write_text(
        json.dumps(clean_manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "source_dataset": source_dataset,
        "output_dataset": output_dataset,
        "race_count": len(clean_races),
        "output_paths": {
            "dataset": str(output_dataset_path),
            "answer_key": str(output_answer_path),
            "manifest": str(output_manifest_path),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--source-dataset", default="full_year_2025")
    parser.add_argument(
        "--output-dataset",
        default="full_year_2025_prerace_canonical_v2",
    )
    args = parser.parse_args()

    summary = materialize_clean_dataset(
        artifact_root=args.artifact_root,
        source_dataset=args.source_dataset,
        output_dataset=args.output_dataset,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
