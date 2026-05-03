"""Operational prediction cutoff helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

from shared.entry_snapshot_metadata import KST, parse_snapshot_datetime

OPERATIONAL_CUTOFF_VERSION = "operational-cutoff-v1"
DEFAULT_T30_CUTOFF_MINUTES = 30

PASS = "pass"
MISSING_SCHEDULED_START = "missing_scheduled_start"
INVALID_SCHEDULED_START = "invalid_scheduled_start"
MISSING_SOURCE_SNAPSHOT = "missing_source_snapshot_at"
SOURCE_AFTER_CUTOFF = "source_after_cutoff"

OPERATIONAL_CUTOFF_REASONS = frozenset(
    {
        PASS,
        MISSING_SCHEDULED_START,
        INVALID_SCHEDULED_START,
        MISSING_SOURCE_SNAPSHOT,
        SOURCE_AFTER_CUTOFF,
    }
)


@dataclass(frozen=True, slots=True)
class OperationalCutoffStatus:
    version: str
    race_date: str | None
    scheduled_start_at: str | None
    operational_cutoff_at: str | None
    source_snapshot_at: str | None
    cutoff_minutes: int
    passed: bool
    reason: str

    def __post_init__(self) -> None:
        if self.version != OPERATIONAL_CUTOFF_VERSION:
            raise ValueError(f"unsupported operational cutoff version: {self.version}")
        if self.cutoff_minutes <= 0:
            raise ValueError("cutoff_minutes must be positive")
        if self.reason not in OPERATIONAL_CUTOFF_REASONS:
            raise ValueError(f"unsupported operational cutoff reason: {self.reason}")
        if self.passed != (self.reason == PASS):
            raise ValueError("passed must be true if and only if reason is 'pass'")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_scheduled_start_time(value: int | str | None) -> str | None:
    """Normalize KRA `schStTime`-style values to HHMM."""

    if value in ("", None):
        return None
    digits = "".join(ch for ch in str(value).strip() if ch.isdigit())
    if len(digits) == 3:
        digits = f"0{digits}"
    if len(digits) != 4:
        return None
    hour = int(digits[:2])
    minute = int(digits[2:])
    if hour > 23 or minute > 59:
        return None
    return digits


def derive_scheduled_start_at_from_fields(
    race_date: str | None,
    scheduled_start_time: int | str | None,
) -> datetime | None:
    """Build a KST scheduled start timestamp from race date and start time."""

    if not race_date:
        return None
    normalized_time = normalize_scheduled_start_time(scheduled_start_time)
    if normalized_time is None:
        return None
    try:
        return datetime.strptime(f"{race_date}{normalized_time}", "%Y%m%d%H%M").replace(
            tzinfo=KST
        )
    except ValueError:
        return None


def classify_source_snapshot_for_t30(
    *,
    race_date: str | None,
    scheduled_start_time: int | str | None,
    source_snapshot_at: datetime | str | None,
    cutoff_minutes: int = DEFAULT_T30_CUTOFF_MINUTES,
) -> OperationalCutoffStatus:
    """Classify whether a source snapshot is usable under the T-30 rule."""

    scheduled_start_at = derive_scheduled_start_at_from_fields(
        race_date,
        scheduled_start_time,
    )
    if scheduled_start_at is None:
        reason = (
            MISSING_SCHEDULED_START
            if scheduled_start_time in ("", None)
            else INVALID_SCHEDULED_START
        )
        return OperationalCutoffStatus(
            version=OPERATIONAL_CUTOFF_VERSION,
            race_date=race_date,
            scheduled_start_at=None,
            operational_cutoff_at=None,
            source_snapshot_at=None,
            cutoff_minutes=cutoff_minutes,
            passed=False,
            reason=reason,
        )

    operational_cutoff_at = scheduled_start_at - timedelta(minutes=cutoff_minutes)
    snapshot_at = parse_snapshot_datetime(source_snapshot_at)
    if snapshot_at is None:
        return OperationalCutoffStatus(
            version=OPERATIONAL_CUTOFF_VERSION,
            race_date=race_date,
            scheduled_start_at=scheduled_start_at.isoformat(),
            operational_cutoff_at=operational_cutoff_at.isoformat(),
            source_snapshot_at=None,
            cutoff_minutes=cutoff_minutes,
            passed=False,
            reason=MISSING_SOURCE_SNAPSHOT,
        )

    if snapshot_at > operational_cutoff_at:
        return OperationalCutoffStatus(
            version=OPERATIONAL_CUTOFF_VERSION,
            race_date=race_date,
            scheduled_start_at=scheduled_start_at.isoformat(),
            operational_cutoff_at=operational_cutoff_at.isoformat(),
            source_snapshot_at=snapshot_at.isoformat(),
            cutoff_minutes=cutoff_minutes,
            passed=False,
            reason=SOURCE_AFTER_CUTOFF,
        )

    return OperationalCutoffStatus(
        version=OPERATIONAL_CUTOFF_VERSION,
        race_date=race_date,
        scheduled_start_at=scheduled_start_at.isoformat(),
        operational_cutoff_at=operational_cutoff_at.isoformat(),
        source_snapshot_at=snapshot_at.isoformat(),
        cutoff_minutes=cutoff_minutes,
        passed=True,
        reason=PASS,
    )
