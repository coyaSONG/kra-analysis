from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.operational_cutoff import (  # noqa: E402
    INVALID_SCHEDULED_START,
    MISSING_SCHEDULED_START,
    MISSING_SOURCE_SNAPSHOT,
    PASS,
    SOURCE_AFTER_CUTOFF,
    classify_source_snapshot_for_t30,
    derive_scheduled_start_at_from_fields,
    normalize_scheduled_start_time,
)


def test_normalize_scheduled_start_time_accepts_kra_variants() -> None:
    assert normalize_scheduled_start_time(930) == "0930"
    assert normalize_scheduled_start_time("09:30") == "0930"
    assert normalize_scheduled_start_time("1100") == "1100"
    assert normalize_scheduled_start_time("2460") is None
    assert normalize_scheduled_start_time("abc") is None


def test_derive_scheduled_start_at_from_fields_returns_kst() -> None:
    scheduled = derive_scheduled_start_at_from_fields("20250101", "1100")

    assert scheduled is not None
    assert scheduled.isoformat() == "2025-01-01T11:00:00+09:00"


def test_classify_source_snapshot_for_t30_passes_at_or_before_cutoff() -> None:
    status = classify_source_snapshot_for_t30(
        race_date="20250101",
        scheduled_start_time="1100",
        source_snapshot_at="2025-01-01T10:30:00+09:00",
    )

    assert status.passed is True
    assert status.reason == PASS
    assert status.operational_cutoff_at == "2025-01-01T10:30:00+09:00"


def test_classify_source_snapshot_for_t30_converts_utc_to_kst() -> None:
    status = classify_source_snapshot_for_t30(
        race_date="20250101",
        scheduled_start_time="1100",
        source_snapshot_at="2025-01-01T01:29:00Z",
    )

    assert status.passed is True
    assert status.source_snapshot_at == "2025-01-01T10:29:00+09:00"


def test_classify_source_snapshot_for_t30_rejects_after_cutoff() -> None:
    status = classify_source_snapshot_for_t30(
        race_date="20250101",
        scheduled_start_time="1100",
        source_snapshot_at="2025-01-01T10:31:00+09:00",
    )

    assert status.passed is False
    assert status.reason == SOURCE_AFTER_CUTOFF


def test_classify_source_snapshot_for_t30_requires_schedule_and_snapshot() -> None:
    missing_schedule = classify_source_snapshot_for_t30(
        race_date="20250101",
        scheduled_start_time=None,
        source_snapshot_at="2025-01-01T10:00:00+09:00",
    )
    invalid_schedule = classify_source_snapshot_for_t30(
        race_date="20250101",
        scheduled_start_time="2500",
        source_snapshot_at="2025-01-01T10:00:00+09:00",
    )
    missing_snapshot = classify_source_snapshot_for_t30(
        race_date="20250101",
        scheduled_start_time="1100",
        source_snapshot_at=None,
    )

    assert missing_schedule.reason == MISSING_SCHEDULED_START
    assert invalid_schedule.reason == INVALID_SCHEDULED_START
    assert missing_snapshot.reason == MISSING_SOURCE_SNAPSHOT
