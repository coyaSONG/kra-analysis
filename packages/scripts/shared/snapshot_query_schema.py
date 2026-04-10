"""출전표 확정 시점 기준 스냅샷 조회 공통 계약."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

SNAPSHOT_QUERY_SCHEMA_VERSION = "entry-snapshot-query-v1"
SNAPSHOT_QUERY_TIME_BASIS = "entry_finalized_at"
SNAPSHOT_QUERY_TIME_FIELD = "entry_snapshot_at"
SNAPSHOT_QUERY_TIME_FIELD_ALIASES: tuple[str, ...] = (
    "entry_snapshot_at",
    "entry_finalized_at",
)
SNAPSHOT_QUERY_VALUE_TYPES: tuple[str, ...] = ("string", "integer", "iso-datetime")


@dataclass(frozen=True, slots=True)
class SnapshotQueryParamSpec:
    name: str
    required: bool
    value_type: str
    description: str
    aliases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.value_type not in SNAPSHOT_QUERY_VALUE_TYPES:
            raise ValueError(
                f"unsupported snapshot query value_type: {self.value_type}"
            )

    def candidate_names(self) -> tuple[str, ...]:
        return (self.name, *self.aliases)


@dataclass(frozen=True, slots=True)
class SnapshotInputFieldSpec:
    field_path: str
    param_name: str
    required: bool
    description: str
    aliases: tuple[str, ...] = ()

    def candidate_names(self) -> tuple[str, ...]:
        return (self.param_name, *self.aliases)


LOOKUP_PARAM_SPECS: tuple[SnapshotQueryParamSpec, ...] = (
    SnapshotQueryParamSpec(
        name="race_id",
        required=True,
        value_type="string",
        description="조회 대상 경주의 안정 식별자.",
    ),
    SnapshotQueryParamSpec(
        name="race_date",
        required=True,
        value_type="string",
        description="조회 대상 경주의 일자(YYYYMMDD).",
        aliases=("date", "rcDate"),
    ),
    SnapshotQueryParamSpec(
        name=SNAPSHOT_QUERY_TIME_FIELD,
        required=True,
        value_type="iso-datetime",
        description="출전표 확정 시점 기준 재조회 시각.",
        aliases=("entry_finalized_at",),
    ),
)

LIST_QUERY_PARAM_SPECS: tuple[SnapshotQueryParamSpec, ...] = (
    SnapshotQueryParamSpec(
        name="date_filter",
        required=False,
        value_type="string",
        description="특정 일자(YYYYMMDD)만 조회할 때 사용하는 선택 파라미터.",
    ),
    SnapshotQueryParamSpec(
        name="limit",
        required=False,
        value_type="integer",
        description="반환할 최대 경주 수.",
    ),
)

INPUT_FIELD_SPECS: tuple[SnapshotInputFieldSpec, ...] = (
    SnapshotInputFieldSpec(
        field_path="race_info.race_id",
        param_name="race_id",
        required=True,
        description="경주 단위 source lookup 식별자.",
        aliases=("race_id",),
    ),
    SnapshotInputFieldSpec(
        field_path="race_info.race_date",
        param_name="race_date",
        required=True,
        description="경주일. legacy payload의 date/rcDate 별칭을 허용한다.",
        aliases=("race_date", "date", "rcDate"),
    ),
    SnapshotInputFieldSpec(
        field_path=f"race_info.{SNAPSHOT_QUERY_TIME_FIELD}",
        param_name=SNAPSHOT_QUERY_TIME_FIELD,
        required=True,
        description="출전표 확정 시점 조회 anchor. entry_finalized_at 별칭을 허용한다.",
        aliases=SNAPSHOT_QUERY_TIME_FIELD_ALIASES,
    ),
)

LOOKUP_REQUIRED_FIELDS: tuple[str, ...] = tuple(
    spec.name for spec in LOOKUP_PARAM_SPECS if spec.required
)
LOOKUP_OPTIONAL_FIELDS: tuple[str, ...] = tuple(
    spec.name for spec in LOOKUP_PARAM_SPECS if not spec.required
)
LIST_QUERY_PARAM_NAMES: tuple[str, ...] = tuple(
    spec.name for spec in LIST_QUERY_PARAM_SPECS
)
INPUT_REQUIRED_FIELD_PATHS: tuple[str, ...] = tuple(
    spec.field_path for spec in INPUT_FIELD_SPECS if spec.required
)


def _first_present_value(
    payload: Mapping[str, Any],
    *,
    names: tuple[str, ...],
) -> Any | None:
    for name in names:
        if name in payload:
            value = payload[name]
            if isinstance(value, str):
                value = value.strip()
            if value not in ("", None):
                return value
    return None


def normalize_snapshot_lookup_payload(payload: Mapping[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for spec in LOOKUP_PARAM_SPECS:
        value = _first_present_value(payload, names=spec.candidate_names())
        if value is None:
            if spec.required:
                raise ValueError(f"snapshot lookup requires {spec.name}")
            continue
        normalized[spec.name] = str(value).strip()
    normalized["source_filter_basis"] = SNAPSHOT_QUERY_TIME_BASIS
    normalized["schema_version"] = SNAPSHOT_QUERY_SCHEMA_VERSION
    return normalized


def normalize_snapshot_list_query_params(
    *,
    date_filter: str | None = None,
    limit: int | str | None = None,
) -> dict[str, int | str]:
    normalized: dict[str, int | str] = {}
    if date_filter is not None:
        date_filter = str(date_filter).strip()
        if date_filter:
            normalized["date_filter"] = date_filter
    if limit is not None:
        try:
            parsed_limit = int(limit)
        except (TypeError, ValueError) as exc:
            raise ValueError("snapshot list query limit must be an integer") from exc
        if parsed_limit <= 0:
            raise ValueError("snapshot list query limit must be positive")
        normalized["limit"] = parsed_limit
    return normalized
