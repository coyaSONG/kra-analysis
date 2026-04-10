"""중간 prerace 스냅샷을 표준 대체랭킹 입력 스키마로 적재하는 공통 계층."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from feature_engineering import compute_race_features

from shared.data_adapter import convert_snapshot_to_enriched_format
from shared.prerace_prediction_payload import (
    HorseFeatureBuilder,
    HorseListPreprocessor,
    build_prerace_race_payload_from_enriched,
)
from shared.read_contract import RaceSnapshot, RaceSourceLookup


class StandardizedRaceQueryPort(Protocol):
    """표준 prerace 적재가 필요로 하는 최소 조회 포트."""

    def load_race_basic_data(
        self,
        race_id: str,
        *,
        lookup: RaceSourceLookup,
    ) -> dict[str, Any] | None: ...


@dataclass(frozen=True, slots=True)
class StandardizedPreracePayload:
    """중간 스키마 검증과 표준 스키마 적재 결과를 함께 담는 DTO."""

    race_id: str
    race_date: str
    meet: str | int | None
    lookup: RaceSourceLookup | None
    basic_data: dict[str, Any]
    enriched_data: dict[str, Any]
    standard_payload: dict[str, Any]
    candidate_filter: dict[str, Any]
    field_policy: dict[str, Any]
    removed_post_race_paths: tuple[str, ...]
    entry_resolution_audit: dict[str, Any] | None


def resolve_race_record_reference(
    race_record: RaceSnapshot | Mapping[str, Any],
) -> tuple[dict[str, Any], RaceSourceLookup]:
    """RaceSnapshot 또는 lookup mapping에서 표준 race reference를 만든다."""

    if isinstance(race_record, RaceSnapshot):
        reference = {
            "race_id": race_record.race_id,
            "race_date": race_record.race_date,
            "race_no": str(race_record.race_number),
            "meet": race_record.key.meet_name,
        }
        return reference, RaceSourceLookup.from_snapshot(race_record)

    if not isinstance(race_record, Mapping):
        raise TypeError("race_record must be a RaceSnapshot or mapping")

    reference = {
        "race_id": str(race_record["race_id"]),
        "race_date": str(race_record["race_date"]),
        "race_no": str(
            race_record.get("race_no") or race_record.get("race_number") or ""
        ),
        "meet": race_record.get("meet"),
    }
    return reference, RaceSourceLookup.from_race_info(race_record)


def build_standardized_prerace_payload(
    basic_data: dict[str, Any] | RaceSnapshot,
    *,
    race_id: str,
    race_date: str,
    meet: str | int | None = None,
    lookup: RaceSourceLookup | None = None,
    cancelled_horses: list[dict[str, Any]] | None = None,
    include_resolution_audit: bool = False,
    horse_preprocessor: HorseListPreprocessor | None = None,
    feature_builder: HorseFeatureBuilder | None = None,
) -> StandardizedPreracePayload:
    """저장 중간 스키마를 검증·정제해 표준 prerace payload로 적재한다."""

    raw_basic_data = (
        basic_data.basic_data if isinstance(basic_data, RaceSnapshot) else basic_data
    )
    if not raw_basic_data:
        raise ValueError(f"race {race_id} is missing basic_data")

    enriched = convert_snapshot_to_enriched_format(
        raw_basic_data,
        include_resolution_audit=include_resolution_audit,
    )
    if not enriched:
        raise ValueError(
            f"race {race_id} could not be converted from intermediate basic_data"
        )

    removed_paths: list[str] = []
    normalized_cancelled_horses = (
        cancelled_horses
        if cancelled_horses is not None
        else raw_basic_data.get("cancelled_horses")
    )
    standard_payload, candidate_filter, field_policy = (
        build_prerace_race_payload_from_enriched(
            enriched,
            race_id=race_id,
            race_date=race_date,
            meet=meet,
            cancelled_horses=normalized_cancelled_horses,
            removed_paths=removed_paths,
            horse_preprocessor=horse_preprocessor,
            feature_builder=feature_builder or compute_race_features,
        )
    )

    resolution_audit = (
        enriched.get("response", {}).get("body", {}).get("entryResolutionAudit")
    )

    return StandardizedPreracePayload(
        race_id=race_id,
        race_date=race_date,
        meet=meet,
        lookup=lookup,
        basic_data=raw_basic_data,
        enriched_data=enriched,
        standard_payload=standard_payload,
        candidate_filter=candidate_filter,
        field_policy=field_policy,
        removed_post_race_paths=tuple(sorted(set(removed_paths))),
        entry_resolution_audit=(
            resolution_audit if isinstance(resolution_audit, dict) else None
        ),
    )


def load_standardized_prerace_payload(
    race_record: RaceSnapshot | Mapping[str, Any],
    *,
    query_port: StandardizedRaceQueryPort,
    include_resolution_audit: bool = False,
    horse_preprocessor: HorseListPreprocessor | None = None,
    feature_builder: HorseFeatureBuilder | None = None,
) -> StandardizedPreracePayload:
    """조회 포트를 통해 intermediate snapshot을 다시 읽어 표준 payload를 만든다."""

    reference, lookup = resolve_race_record_reference(race_record)
    basic_data = query_port.load_race_basic_data(reference["race_id"], lookup=lookup)
    if not basic_data:
        raise ValueError(
            f"snapshot lookup returned no basic_data for race {reference['race_id']}"
        )

    return build_standardized_prerace_payload(
        basic_data,
        race_id=reference["race_id"],
        race_date=reference["race_date"],
        meet=reference.get("meet"),
        lookup=lookup,
        include_resolution_audit=include_resolution_audit,
        horse_preprocessor=horse_preprocessor,
        feature_builder=feature_builder,
    )
