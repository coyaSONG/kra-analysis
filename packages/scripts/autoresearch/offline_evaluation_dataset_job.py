"""오프라인 평가용 데이터셋 생성 모듈/잡.

평가 입력은 반드시 ``RaceSourceLookup(entry_snapshot_at=entry_finalized_at)``
규약을 통해 다시 조회해 고정한다. 이렇게 해야 현재 DB row를 직접 읽는 대신
출전표 확정 시점 기준으로 재생 가능한 입력만 평가 팩에 포함된다.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.db_client import RaceDBClient
from shared.entry_change_snapshot_manifest import (
    select_entry_change_snapshot_for_replay,
)
from shared.prerace_standard_loader import build_standardized_prerace_payload
from shared.read_contract import RaceSnapshot, RaceSourceLookup
from shared.t30_release_gate import build_t30_release_gate_report

from autoresearch.holdout_dataset import (
    build_dataset_manifest,
    derive_snapshot_timing,
    select_allowed_basic_data,
    snapshot_meta_dict,
)
from autoresearch.holdout_split import (
    plan_recent_holdout_manifests,
    write_split_manifests,
)

SNAPSHOTS_DIR = Path(__file__).resolve().parent / "snapshots"
SNAPSHOT_DATASETS = ("mini_val", "holdout")


class OfflineEvaluationSnapshotQueryPort(Protocol):
    """오프라인 평가 입력을 기준시각으로 재조회하는 공통 포트."""

    def find_race_snapshots(
        self,
        date_filter: str | None = None,
        limit: int | None = None,
    ) -> list[RaceSnapshot]: ...

    def load_race_basic_data(
        self,
        race_id: str,
        *,
        lookup: RaceSourceLookup,
    ) -> dict[str, Any] | None: ...

    def get_past_top3_stats_for_race(
        self,
        hr_nos: list[str],
        *,
        lookup: RaceSourceLookup,
        lookback_days: int = 90,
    ) -> dict[str, dict[str, Any]]: ...

    def close(self) -> None: ...


def build_entry_snapshot_lookup(snapshot: RaceSnapshot) -> RaceSourceLookup:
    """경주별 평가 입력 조회는 entry_finalized_at 기준으로 고정한다."""
    return RaceSourceLookup.from_snapshot(snapshot)


def load_snapshot_basic_data_at_reference_time(
    snapshot: RaceSnapshot,
    *,
    query_port: OfflineEvaluationSnapshotQueryPort,
) -> RaceSnapshot:
    """공통 스냅샷 조회 규약으로 basic_data를 다시 읽어 평가 입력을 고정한다."""

    lookup = build_entry_snapshot_lookup(snapshot)
    basic_data = query_port.load_race_basic_data(snapshot.race_id, lookup=lookup)
    if not basic_data:
        raise ValueError(
            f"snapshot lookup returned no basic_data for race {snapshot.race_id} "
            f"at {lookup.entry_snapshot_at}"
        )
    return replace(snapshot, basic_data=basic_data)


def build_snapshot_race_data(
    snapshot: RaceSnapshot,
    *,
    query_port: OfflineEvaluationSnapshotQueryPort | None = None,
    with_past_stats: bool = False,
    entry_change_snapshot_dir: Path | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """경주 스냅샷을 평가용 strict payload와 timing 메타데이터로 변환한다."""

    timing = derive_snapshot_timing(snapshot)
    timing_meta = snapshot_meta_dict(timing)
    timing_meta["race_id"] = snapshot.race_id
    lookup = build_entry_snapshot_lookup(snapshot)

    if not timing.include_in_strict_dataset:
        return None, timing_meta

    filtered_basic_data = select_allowed_basic_data(snapshot.basic_data)
    entry_change_selection = None
    if entry_change_snapshot_dir is not None:
        entry_change_selection = select_entry_change_snapshot_for_replay(
            meet=snapshot.meet,
            cutoff_at=lookup.entry_snapshot_at,
            snapshot_dir=entry_change_snapshot_dir,
        )
        timing_meta["entry_change_source_lookup"] = entry_change_selection.to_dict()

    def _inject_past_stats(horses: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not with_past_stats:
            return horses
        if query_port is None:
            raise ValueError("with_past_stats requires query_port")
        hr_nos = [str(horse["hrNo"]) for horse in horses if horse.get("hrNo")]
        past_stats = query_port.get_past_top3_stats_for_race(
            hr_nos=hr_nos,
            lookup=lookup,
            lookback_days=90,
        )
        for horse in horses:
            hr_no = str(horse.get("hrNo") or "")
            if hr_no in past_stats:
                horse["past_stats"] = past_stats[hr_no]
        return horses

    try:
        standardized = build_standardized_prerace_payload(
            filtered_basic_data,
            race_id=snapshot.race_id,
            race_date=snapshot.race_date,
            meet=snapshot.key.meet_name,
            lookup=lookup,
            include_resolution_audit=True,
            entry_change_notices=(
                entry_change_selection.notices
                if entry_change_selection is not None
                and entry_change_selection.source_present
                else None
            ),
            horse_preprocessor=_inject_past_stats if with_past_stats else None,
        )
    except ValueError:
        timing_meta["include_in_strict_dataset"] = False
        timing_meta["replay_status"] = "payload_conversion_failed"
        return None, timing_meta
    if standardized.entry_resolution_audit is not None:
        timing_meta["entry_resolution_audit"] = standardized.entry_resolution_audit
    timing_meta["removed_post_race_fields"] = list(standardized.removed_post_race_paths)
    timing_meta["removed_post_race_field_count"] = len(
        standardized.removed_post_race_paths
    )
    timing_meta["field_policy"] = standardized.field_policy
    timing_meta["candidate_filter"] = standardized.candidate_filter
    timing_meta["operational_cutoff_status"] = standardized.operational_cutoff_status
    timing_meta["entry_change_audit"] = standardized.entry_change_audit
    timing_meta["source_lookup"] = lookup.to_dict()
    race_data = standardized.standard_payload
    race_data["snapshot_meta"] = timing_meta
    return race_data, timing_meta


def _normalize_snapshot_created_at(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.now().astimezone()
    if isinstance(value, datetime):
        return value.astimezone()
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone()


def _canonical_snapshot_json(payload: Any) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _collect_snapshot_paths(
    value: Any,
    *,
    path: str = "",
    paths: set[str] | None = None,
) -> set[str]:
    collected = paths if paths is not None else set()

    if isinstance(value, dict):
        if not value and path:
            collected.add(path)
            return collected
        for key in sorted(value):
            next_path = f"{path}.{key}" if path else key
            _collect_snapshot_paths(value[key], path=next_path, paths=collected)
        return collected

    if isinstance(value, list):
        list_path = f"{path}[]" if path else "[]"
        if not value:
            collected.add(list_path)
            return collected
        for item in value:
            _collect_snapshot_paths(item, path=list_path, paths=collected)
        return collected

    if path:
        collected.add(path)
    return collected


def _snapshot_column_signature(records: list[dict[str, Any]]) -> tuple[str, ...]:
    paths: set[str] = set()
    for record in records:
        _collect_snapshot_paths(record, paths=paths)
    return tuple(sorted(paths))


def _sequence_mismatch_details(
    reference: Sequence[Any],
    regenerated: Sequence[Any],
) -> dict[str, Any] | None:
    for index, (left, right) in enumerate(zip(reference, regenerated, strict=False)):
        if left != right:
            return {
                "first_mismatch_index": index,
                "reference_value": left,
                "regenerated_value": right,
            }

    if len(reference) != len(regenerated):
        return {
            "first_mismatch_index": min(len(reference), len(regenerated)),
            "reference_value": (
                None
                if len(reference) <= len(regenerated)
                else reference[len(regenerated)]
            ),
            "regenerated_value": (
                None
                if len(regenerated) <= len(reference)
                else regenerated[len(reference)]
            ),
        }

    return None


def build_snapshot_bundle(
    race_snapshots: list[RaceSnapshot],
    *,
    query_port: OfflineEvaluationSnapshotQueryPort,
    manifest_created_at: datetime | str | None = None,
    holdout_minimum_race_count: int = 50,
    mini_val_minimum_race_count: int = 20,
    with_past_stats: bool = False,
    entry_change_snapshot_dir: Path | None = None,
) -> dict[str, Any]:
    normalized_created_at = _normalize_snapshot_created_at(manifest_created_at)
    split_manifests = plan_recent_holdout_manifests(
        race_snapshots,
        manifest_created_at=normalized_created_at,
        holdout_minimum_race_count=holdout_minimum_race_count,
        mini_val_minimum_race_count=mini_val_minimum_race_count,
    )
    snapshot_by_id = {snapshot.race_id: snapshot for snapshot in race_snapshots}

    answer_key: dict[str, Any] = {"meta": {}, "mini_val": {}, "holdout": {}}
    snapshots: dict[str, list[dict[str, Any]]] = {"mini_val": [], "holdout": []}
    timing_manifests: dict[str, list[dict[str, Any]]] = {"mini_val": [], "holdout": []}

    for mode in SNAPSHOT_DATASETS:
        race_ids = split_manifests[mode].included_race_ids
        for race_id in race_ids:
            snapshot = snapshot_by_id.get(race_id)
            if not snapshot or not snapshot.basic_data:
                raise ValueError(
                    f"selected {mode} race is missing snapshot/basic_data: {race_id}"
                )

            frozen_snapshot = load_snapshot_basic_data_at_reference_time(
                snapshot,
                query_port=query_port,
            )
            race_data, timing_meta = build_snapshot_race_data(
                frozen_snapshot,
                query_port=query_port,
                with_past_stats=with_past_stats,
                entry_change_snapshot_dir=entry_change_snapshot_dir,
            )
            timing_manifests[mode].append(timing_meta)
            if not race_data:
                raise ValueError(
                    f"selected {mode} race cannot build strict payload: {race_id}"
                )

            snapshots[mode].append(race_data)

            result = frozen_snapshot.result_top3()
            if len(result) == 3:
                answer_key[mode][race_id] = result

    answer_key["meta"] = {
        "created_at": normalized_created_at.isoformat(),
        "snapshot_meta_version": "holdout-snapshot-v1",
        "dataset_manifest_version": "holdout-dataset-manifest-v1",
    }
    return {
        "created_at": normalized_created_at,
        "with_past_stats": with_past_stats,
        "entry_change_snapshot_dir": (
            str(entry_change_snapshot_dir) if entry_change_snapshot_dir else None
        ),
        "split_manifests": split_manifests,
        "snapshots": snapshots,
        "timing_manifests": timing_manifests,
        "answer_key": answer_key,
    }


def validate_snapshot_bundle_counts(bundle: dict[str, Any]) -> None:
    split_manifests = bundle["split_manifests"]
    snapshots = bundle["snapshots"]
    timing_manifests = bundle["timing_manifests"]

    for mode in SNAPSHOT_DATASETS:
        count = len(snapshots[mode])
        minimum = split_manifests[mode].parameters.minimum_race_count
        if count < minimum:
            raise ValueError(
                f"{mode} has only {count} races (need >= {minimum}). "
                "Check DB for missing basic_data or failed conversions."
            )
        for timing_meta in timing_manifests[mode]:
            candidate_filter = timing_meta.get("candidate_filter", {})
            validation = candidate_filter.get("final_candidate_validation", {})
            if validation.get("minimum_candidate_met") is False:
                race_id = timing_meta.get("race_id", "unknown")
                final_candidate_count = validation.get("final_candidate_count")
                raise ValueError(
                    f"{mode} race {race_id} has only {final_candidate_count} final candidates "
                    f"after supplement/fallback."
                )


def write_snapshot_bundle(
    bundle: dict[str, Any],
    *,
    snapshot_dir: Path = SNAPSHOTS_DIR,
) -> None:
    created_at = bundle["created_at"].isoformat()
    snapshots = bundle["snapshots"]
    answer_key = bundle["answer_key"]
    timing_manifests = bundle["timing_manifests"]

    snapshot_dir.mkdir(parents=True, exist_ok=True)
    write_split_manifests(bundle["split_manifests"])

    for mode in SNAPSHOT_DATASETS:
        content = json.dumps(snapshots[mode], ensure_ascii=False)
        sha = sha256(content.encode()).hexdigest()[:16]
        (snapshot_dir / f"{mode}.json").write_text(content, encoding="utf-8")
        (snapshot_dir / f"{mode}_answer_key.json").write_text(
            json.dumps(answer_key[mode], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        manifest = build_dataset_manifest(
            mode=mode,
            created_at=created_at,
            races=timing_manifests[mode],
        )
        (snapshot_dir / f"{mode}_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        gate_payloads = [
            {
                "race_id": record.get("race_id"),
                "standard_payload": record,
                "operational_cutoff_status": record.get("snapshot_meta", {}).get(
                    "operational_cutoff_status",
                    {},
                ),
                "entry_change_audit": record.get("snapshot_meta", {}).get(
                    "entry_change_audit",
                    {},
                ),
            }
            for record in snapshots[mode]
        ]
        (snapshot_dir / f"{mode}_t30_release_gate_report.json").write_text(
            json.dumps(
                build_t30_release_gate_report(gate_payloads),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"{mode}: {len(snapshots[mode])} races (sha256={sha})")

    (snapshot_dir / "answer_key.json").write_text(
        json.dumps(bundle["answer_key"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def check_snapshot_reproducibility(
    race_snapshots: list[RaceSnapshot],
    *,
    query_port: OfflineEvaluationSnapshotQueryPort,
    manifest_created_at: datetime | str | None = None,
    holdout_minimum_race_count: int = 50,
    mini_val_minimum_race_count: int = 20,
    reference_bundle: dict[str, Any] | None = None,
    with_past_stats: bool = False,
    entry_change_snapshot_dir: Path | None = None,
) -> dict[str, Any]:
    """입력 스냅샷을 동일 조건으로 두 번 생성해 byte/구조 단위 일치 여부를 검증한다."""

    reference = reference_bundle or build_snapshot_bundle(
        race_snapshots,
        query_port=query_port,
        manifest_created_at=manifest_created_at,
        holdout_minimum_race_count=holdout_minimum_race_count,
        mini_val_minimum_race_count=mini_val_minimum_race_count,
        with_past_stats=with_past_stats,
        entry_change_snapshot_dir=entry_change_snapshot_dir,
    )
    regenerated = build_snapshot_bundle(
        race_snapshots,
        query_port=query_port,
        manifest_created_at=reference["created_at"],
        holdout_minimum_race_count=holdout_minimum_race_count,
        mini_val_minimum_race_count=mini_val_minimum_race_count,
        with_past_stats=with_past_stats,
        entry_change_snapshot_dir=entry_change_snapshot_dir,
    )

    dataset_reports: dict[str, Any] = {}
    for mode in SNAPSHOT_DATASETS:
        reference_records = reference["snapshots"][mode]
        regenerated_records = regenerated["snapshots"][mode]

        reference_order = tuple(str(item.get("race_id")) for item in reference_records)
        regenerated_order = tuple(
            str(item.get("race_id")) for item in regenerated_records
        )
        reference_columns = _snapshot_column_signature(reference_records)
        regenerated_columns = _snapshot_column_signature(regenerated_records)
        reference_hash = sha256(
            _canonical_snapshot_json(reference_records).encode("utf-8")
        ).hexdigest()
        regenerated_hash = sha256(
            _canonical_snapshot_json(regenerated_records).encode("utf-8")
        ).hexdigest()

        record_count_match = len(reference_records) == len(regenerated_records)
        column_structure_match = reference_columns == regenerated_columns
        sort_order_match = reference_order == regenerated_order
        content_hash_match = reference_hash == regenerated_hash
        column_diff = None
        if not column_structure_match:
            column_diff = {
                "missing_from_regenerated": sorted(
                    set(reference_columns) - set(regenerated_columns)
                )[:20],
                "extra_in_regenerated": sorted(
                    set(regenerated_columns) - set(reference_columns)
                )[:20],
            }

        dataset_reports[mode] = {
            "passed": (
                record_count_match
                and column_structure_match
                and sort_order_match
                and content_hash_match
            ),
            "record_count_match": record_count_match,
            "column_structure_match": column_structure_match,
            "sort_order_match": sort_order_match,
            "content_hash_match": content_hash_match,
            "ordering_basis": "split_manifest.included_race_ids",
            "reference_record_count": len(reference_records),
            "regenerated_record_count": len(regenerated_records),
            "reference_column_count": len(reference_columns),
            "regenerated_column_count": len(regenerated_columns),
            "reference_content_sha256": reference_hash,
            "regenerated_content_sha256": regenerated_hash,
            "sort_order_mismatch": _sequence_mismatch_details(
                reference_order, regenerated_order
            ),
            "column_structure_diff": column_diff,
        }

    return {
        "passed": all(report["passed"] for report in dataset_reports.values()),
        "manifest_created_at": reference["created_at"].isoformat(),
        "datasets": dataset_reports,
    }


def create_offline_evaluation_dataset(
    *,
    force: bool = False,
    query_port: OfflineEvaluationSnapshotQueryPort | None = None,
    snapshot_dir: Path = SNAPSHOTS_DIR,
    manifest_created_at: datetime | str | None = None,
    with_past_stats: bool = False,
    entry_change_snapshot_dir: Path | None = None,
) -> None:
    """DB에서 경주 데이터를 읽어 오프라인 평가 snapshot 팩을 생성한다."""

    snapshot_dir.mkdir(parents=True, exist_ok=True)

    if (snapshot_dir / "mini_val.json").exists() and not force:
        print("Snapshot already exists. Use --force-recreate to regenerate.")
        return

    db = query_port or RaceDBClient()
    try:
        race_snapshots = db.find_race_snapshots()
        print(f"Found {len(race_snapshots)} collected races")

        created_at = _normalize_snapshot_created_at(manifest_created_at)
        bundle = build_snapshot_bundle(
            race_snapshots,
            query_port=db,
            manifest_created_at=created_at,
            with_past_stats=with_past_stats,
            entry_change_snapshot_dir=entry_change_snapshot_dir,
        )
        validate_snapshot_bundle_counts(bundle)

        reproducibility_report = check_snapshot_reproducibility(
            race_snapshots,
            query_port=db,
            manifest_created_at=created_at,
            reference_bundle=bundle,
            with_past_stats=with_past_stats,
            entry_change_snapshot_dir=entry_change_snapshot_dir,
        )
        if not reproducibility_report["passed"]:
            raise ValueError(
                "입력 스냅샷 재생성 검증에 실패했습니다. "
                f"details={json.dumps(reproducibility_report['datasets'], ensure_ascii=False, sort_keys=True)}"
            )

        write_snapshot_bundle(bundle, snapshot_dir=snapshot_dir)
        print("Snapshot reproducibility check passed")
        print(f"Snapshot created at {snapshot_dir}")
    except ValueError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1) from exc
    finally:
        if query_port is None:
            db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate offline evaluation datasets using entry-finalized snapshot lookups."
    )
    parser.add_argument("--force-recreate", action="store_true", help="snapshot 재생성")
    parser.add_argument(
        "--reference-time",
        help="dataset manifest created_at override (ISO-8601)",
    )
    parser.add_argument(
        "--with-past-stats",
        action="store_true",
        default=False,
        help="strict prior-date past_stats를 snapshot horse payload에 주입",
    )
    parser.add_argument(
        "--entry-change-snapshot-dir",
        type=Path,
        help="entry_change_bulletin raw/manifest snapshot directory",
    )
    args = parser.parse_args()

    create_offline_evaluation_dataset(
        force=args.force_recreate,
        manifest_created_at=args.reference_time,
        with_past_stats=args.with_past_stats,
        entry_change_snapshot_dir=args.entry_change_snapshot_dir,
    )


if __name__ == "__main__":
    main()
