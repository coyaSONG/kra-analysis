"""출전표 확정 시점 스냅샷 메타데이터 계약과 공통 산출 규칙."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from shared.prerace_source_schema import HARD_REQUIRED_SOURCE_APIS

KST = ZoneInfo("Asia/Seoul")
SNAPSHOT_META_VERSION = "holdout-snapshot-v1"
ENTRY_FINALIZATION_RULE_VERSION = "holdout-entry-finalization-rule-v1"
SOURCE_FILTER_BASIS = "entry_finalized_at"
DEFAULT_OPERATIONAL_BUFFER_MINUTES = 10

TIMESTAMP_SOURCES: tuple[str, ...] = (
    "source_revision",
    "snapshot_collected_at",
    "derived_from_schedule",
    "fallback_collected_only",
)
TIMESTAMP_CONFIDENCES: tuple[str, ...] = ("high", "medium", "low")
REPLAY_STATUSES: tuple[str, ...] = (
    "strict",
    "degraded",
    "partial_snapshot",
    "late_snapshot_unusable",
    "missing_timestamp",
    "unrecoverable_post_cutoff_reissue",
)
HARD_REQUIRED_SOURCE_STATUSES: tuple[str, ...] = ("present", "missing")

_HARD_REQUIRED_SOURCE_PATHS: dict[str, str] = {
    "API214_1": "race_info",
    "API72_2": "race_plan",
    "API189_1": "track",
    "API9_1": "cancelled_horses",
}


def parse_snapshot_datetime(value: datetime | str | None) -> datetime | None:
    if value in ("", None):
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(KST)


def format_snapshot_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def extract_sch_st_time(basic_data: dict[str, Any] | None) -> str | None:
    if not isinstance(basic_data, dict):
        return None

    race_plan = basic_data.get("race_plan") or {}
    candidates = [
        race_plan.get("sch_st_time"),
        race_plan.get("schStTime"),
    ]
    try:
        items = basic_data["race_info"]["response"]["body"]["items"]["item"]
        if not isinstance(items, list):
            items = [items]
        if items:
            candidates.append(items[0].get("schStTime"))
    except (KeyError, TypeError):
        pass

    for raw in candidates:
        if raw in ("", None):
            continue
        digits = "".join(ch for ch in str(raw).strip() if ch.isdigit())
        if len(digits) == 3:
            digits = f"0{digits}"
        if len(digits) == 4:
            return digits
    return None


def derive_scheduled_start_at(
    race_date: str | None,
    basic_data: dict[str, Any] | None,
) -> datetime | None:
    if not race_date:
        return None

    sch_st_time = extract_sch_st_time(basic_data)
    if sch_st_time is None:
        return None

    try:
        return datetime.strptime(f"{race_date}{sch_st_time}", "%Y%m%d%H%M").replace(
            tzinfo=KST
        )
    except ValueError:
        return None


def build_hard_required_source_status(
    basic_data: dict[str, Any] | None,
) -> dict[str, str]:
    if not isinstance(basic_data, dict):
        return dict.fromkeys(HARD_REQUIRED_SOURCE_APIS, "missing")

    return {
        source_api: (
            "present"
            if (
                path in basic_data
                and (path == "cancelled_horses" or bool(basic_data.get(path)))
            )
            else "missing"
        )
        for source_api, path in _HARD_REQUIRED_SOURCE_PATHS.items()
    }


@dataclass(frozen=True, slots=True)
class EntrySnapshotMetadata:
    format_version: str
    rule_version: str
    source_filter_basis: str
    scheduled_start_at: str | None
    operational_cutoff_at: str | None
    snapshot_ready_at: str | None
    entry_finalized_at: str | None
    selected_timestamp_field: str
    selected_timestamp_value: str | None
    timestamp_source: str
    timestamp_confidence: str
    revision_id: str | None
    late_reissue_after_cutoff: bool
    cutoff_unbounded: bool
    replay_status: str
    include_in_strict_dataset: bool
    hard_required_sources_present: bool
    hard_required_source_status: dict[str, str]

    def __post_init__(self) -> None:
        if self.format_version != SNAPSHOT_META_VERSION:
            raise ValueError(
                f"unsupported snapshot meta version: {self.format_version}"
            )
        if self.rule_version != ENTRY_FINALIZATION_RULE_VERSION:
            raise ValueError(f"unsupported rule version: {self.rule_version}")
        if self.source_filter_basis != SOURCE_FILTER_BASIS:
            raise ValueError(
                f"source_filter_basis must be {SOURCE_FILTER_BASIS!r}: {self.source_filter_basis!r}"
            )
        if self.timestamp_source not in TIMESTAMP_SOURCES:
            raise ValueError(f"unsupported timestamp_source: {self.timestamp_source}")
        if self.timestamp_confidence not in TIMESTAMP_CONFIDENCES:
            raise ValueError(
                f"unsupported timestamp_confidence: {self.timestamp_confidence}"
            )
        if self.replay_status not in REPLAY_STATUSES:
            raise ValueError(f"unsupported replay_status: {self.replay_status}")
        for source_api in HARD_REQUIRED_SOURCE_APIS:
            status = self.hard_required_source_status.get(source_api)
            if status not in HARD_REQUIRED_SOURCE_STATUSES:
                raise ValueError(
                    f"unsupported hard_required_source_status for {source_api}: {status!r}"
                )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def snapshot_meta_dict(meta: EntrySnapshotMetadata) -> dict[str, Any]:
    return meta.to_dict()


def build_entry_snapshot_metadata(
    *,
    race_date: str | None,
    basic_data: dict[str, Any] | None,
    row_collected_at: datetime | str | None = None,
    row_updated_at: datetime | str | None = None,
    entry_finalized_at_override: datetime | str | None = None,
    revision_id: str | None = None,
) -> EntrySnapshotMetadata:
    scheduled_start_at = derive_scheduled_start_at(race_date, basic_data)
    operational_cutoff_at = (
        scheduled_start_at - timedelta(minutes=DEFAULT_OPERATIONAL_BUFFER_MINUTES)
        if scheduled_start_at is not None
        else None
    )

    source_status = build_hard_required_source_status(basic_data)
    hard_required_sources_present = all(
        status == "present" for status in source_status.values()
    )

    basic_collected_at = parse_snapshot_datetime(
        (basic_data or {}).get("collected_at") if isinstance(basic_data, dict) else None
    )
    row_collected_dt = parse_snapshot_datetime(row_collected_at)
    row_updated_dt = parse_snapshot_datetime(row_updated_at)
    override_dt = parse_snapshot_datetime(entry_finalized_at_override)

    snapshot_ready_at: datetime | None = None
    entry_finalized_at: datetime | None = None
    selected_timestamp_field = "missing_timestamp"
    selected_timestamp_value: datetime | None = None
    timestamp_source = "fallback_collected_only"
    timestamp_confidence = "low"

    if override_dt is not None:
        snapshot_ready_at = override_dt
        entry_finalized_at = override_dt
        selected_timestamp_field = "entry_finalized_at_override"
        selected_timestamp_value = override_dt
        timestamp_source = "source_revision"
        timestamp_confidence = "high"
    elif basic_collected_at is not None:
        snapshot_ready_at = basic_collected_at
        entry_finalized_at = basic_collected_at
        selected_timestamp_field = "basic_data.collected_at"
        selected_timestamp_value = basic_collected_at
        timestamp_source = "snapshot_collected_at"
        timestamp_confidence = "medium"
    elif row_collected_dt is not None:
        snapshot_ready_at = row_collected_dt
        entry_finalized_at = row_collected_dt
        selected_timestamp_field = "races.collected_at"
        selected_timestamp_value = row_collected_dt
        timestamp_source = "snapshot_collected_at"
        timestamp_confidence = "medium"
    elif operational_cutoff_at is not None:
        entry_finalized_at = operational_cutoff_at
        selected_timestamp_field = "race_plan.sch_st_time_minus_10m"
        selected_timestamp_value = operational_cutoff_at
        timestamp_source = "derived_from_schedule"
        timestamp_confidence = "low"
    elif row_updated_dt is not None:
        entry_finalized_at = row_updated_dt
        selected_timestamp_field = "races.updated_at"
        selected_timestamp_value = row_updated_dt
        timestamp_source = "fallback_collected_only"
        timestamp_confidence = "low"

    cutoff_unbounded = operational_cutoff_at is None
    if entry_finalized_at is None:
        replay_status = "missing_timestamp"
        include_in_strict_dataset = False
    elif not hard_required_sources_present:
        replay_status = "partial_snapshot"
        include_in_strict_dataset = False
    elif (
        operational_cutoff_at is not None and entry_finalized_at > operational_cutoff_at
    ):
        replay_status = "late_snapshot_unusable"
        include_in_strict_dataset = False
    elif timestamp_source in {"source_revision", "snapshot_collected_at"}:
        replay_status = "strict"
        include_in_strict_dataset = True
    else:
        replay_status = "degraded"
        include_in_strict_dataset = True

    return EntrySnapshotMetadata(
        format_version=SNAPSHOT_META_VERSION,
        rule_version=ENTRY_FINALIZATION_RULE_VERSION,
        source_filter_basis=SOURCE_FILTER_BASIS,
        scheduled_start_at=format_snapshot_datetime(scheduled_start_at),
        operational_cutoff_at=format_snapshot_datetime(operational_cutoff_at),
        snapshot_ready_at=format_snapshot_datetime(snapshot_ready_at),
        entry_finalized_at=format_snapshot_datetime(entry_finalized_at),
        selected_timestamp_field=selected_timestamp_field,
        selected_timestamp_value=format_snapshot_datetime(selected_timestamp_value),
        timestamp_source=timestamp_source,
        timestamp_confidence=timestamp_confidence,
        revision_id=revision_id,
        late_reissue_after_cutoff=False,
        cutoff_unbounded=cutoff_unbounded,
        replay_status=replay_status,
        include_in_strict_dataset=include_in_strict_dataset,
        hard_required_sources_present=hard_required_sources_present,
        hard_required_source_status=source_status,
    )


def restore_entry_snapshot_metadata(
    stored_meta: dict[str, Any] | None,
) -> EntrySnapshotMetadata | None:
    if not isinstance(stored_meta, dict):
        return None

    format_version = str(stored_meta.get("format_version") or "").strip()
    if format_version != SNAPSHOT_META_VERSION:
        return None

    hard_required_source_status = stored_meta.get("hard_required_source_status")
    if not isinstance(hard_required_source_status, dict):
        hard_required_source_status = dict.fromkeys(
            HARD_REQUIRED_SOURCE_APIS, "missing"
        )

    return EntrySnapshotMetadata(
        format_version=format_version,
        rule_version=str(
            stored_meta.get("rule_version") or ENTRY_FINALIZATION_RULE_VERSION
        ),
        source_filter_basis=str(
            stored_meta.get("source_filter_basis") or SOURCE_FILTER_BASIS
        ),
        scheduled_start_at=_optional_str(stored_meta.get("scheduled_start_at")),
        operational_cutoff_at=_optional_str(stored_meta.get("operational_cutoff_at")),
        snapshot_ready_at=_optional_str(stored_meta.get("snapshot_ready_at")),
        entry_finalized_at=_optional_str(stored_meta.get("entry_finalized_at")),
        selected_timestamp_field=str(
            stored_meta.get("selected_timestamp_field") or "unknown"
        ),
        selected_timestamp_value=_optional_str(
            stored_meta.get("selected_timestamp_value")
        ),
        timestamp_source=str(stored_meta.get("timestamp_source") or ""),
        timestamp_confidence=str(stored_meta.get("timestamp_confidence") or ""),
        revision_id=_optional_str(stored_meta.get("revision_id")),
        late_reissue_after_cutoff=bool(
            stored_meta.get("late_reissue_after_cutoff", False)
        ),
        cutoff_unbounded=bool(stored_meta.get("cutoff_unbounded", False)),
        replay_status=str(stored_meta.get("replay_status") or ""),
        include_in_strict_dataset=bool(
            stored_meta.get("include_in_strict_dataset", False)
        ),
        hard_required_sources_present=bool(
            stored_meta.get("hard_required_sources_present", False)
        ),
        hard_required_source_status={
            str(source_api): str(status)
            for source_api, status in hard_required_source_status.items()
        },
    )


def derive_or_restore_entry_snapshot_metadata(
    *,
    race_date: str | None,
    basic_data: dict[str, Any] | None,
    raw_data: dict[str, Any] | None,
    row_collected_at: datetime | str | None = None,
    row_updated_at: datetime | str | None = None,
) -> EntrySnapshotMetadata:
    stored_meta = None
    if isinstance(raw_data, dict):
        stored_meta = raw_data.get("snapshot_meta")
    if stored_meta is None and isinstance(basic_data, dict):
        stored_meta = basic_data.get("snapshot_meta")

    restored = restore_entry_snapshot_metadata(stored_meta)
    if restored is not None:
        return restored

    return build_entry_snapshot_metadata(
        race_date=race_date,
        basic_data=basic_data,
        row_collected_at=row_collected_at,
        row_updated_at=row_updated_at,
    )


def _optional_str(value: Any) -> str | None:
    if value in ("", None):
        return None
    return str(value)
