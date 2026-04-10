"""
Shared read contract for scripts.

This module defines the stable DTOs used by sync DB readers and downstream
data adapters without forcing callers to depend on raw row dictionaries.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from shared.entry_snapshot_metadata import derive_or_restore_entry_snapshot_metadata
from shared.snapshot_query_schema import normalize_snapshot_lookup_payload

MEET_NAME_MAP = {1: "서울", 2: "제주", 3: "부산경남"}


def normalize_result_data(result_data: Any | None) -> list[int]:
    """Normalize `races.result_data` into a top3 list."""
    if not result_data:
        return []

    if isinstance(result_data, str):
        import json

        result_data = json.loads(result_data)

    if isinstance(result_data, list):
        return [int(item) for item in result_data]

    if isinstance(result_data, dict):
        top3 = result_data.get("top3", [])
        if isinstance(top3, list):
            return [int(item) for item in top3]

    return []


def _decode_json_if_needed(value: Any) -> Any:
    if isinstance(value, str):
        import json

        return json.loads(value)
    return value


@dataclass(frozen=True, slots=True)
class RaceKey:
    """Stable identity for a race row."""

    race_id: str
    race_date: str
    meet: int
    race_number: int

    @property
    def race_no(self) -> str:
        return str(self.race_number)

    @property
    def meet_name(self) -> str:
        return MEET_NAME_MAP.get(self.meet, "서울")

    def to_legacy_dict(self) -> dict[str, Any]:
        return {
            "race_id": self.race_id,
            "race_date": self.race_date,
            "race_no": self.race_no,
            "meet": self.meet_name,
        }


@dataclass(frozen=True, slots=True)
class RaceSourceLookup:
    """Per-race source lookup contract anchored to the entry snapshot time."""

    race_id: str
    race_date: str
    entry_snapshot_at: str

    @classmethod
    def from_race_info(cls, race_info: Mapping[str, Any]) -> "RaceSourceLookup":
        normalized = normalize_snapshot_lookup_payload(race_info)

        return cls(
            race_id=normalized["race_id"],
            race_date=normalized["race_date"],
            entry_snapshot_at=normalized["entry_snapshot_at"],
        )

    @classmethod
    def from_snapshot(cls, snapshot: "RaceSnapshot") -> "RaceSourceLookup":
        timing = derive_or_restore_entry_snapshot_metadata(
            race_date=snapshot.race_date,
            basic_data=snapshot.basic_data,
            raw_data=snapshot.raw_data,
            row_collected_at=snapshot.collected_at,
            row_updated_at=snapshot.updated_at,
        )
        if not timing.entry_finalized_at:
            raise ValueError(
                f"race {snapshot.race_id} is missing entry_finalized_at for snapshot lookup"
            )
        return cls(
            race_id=snapshot.race_id,
            race_date=snapshot.race_date,
            entry_snapshot_at=timing.entry_finalized_at,
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "race_id": self.race_id,
            "race_date": self.race_date,
            "entry_snapshot_at": self.entry_snapshot_at,
        }


@dataclass(frozen=True, slots=True)
class RaceSnapshot:
    """Canonical read DTO for a race row."""

    key: RaceKey
    collection_status: str | None = None
    result_status: str | None = None
    basic_data: dict[str, Any] | None = None
    raw_data: dict[str, Any] | None = None
    result_data: Any | None = None
    collected_at: datetime | str | None = None
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "RaceSnapshot":
        key = RaceKey(
            race_id=str(row["race_id"]),
            race_date=str(row["date"]),
            meet=int(row["meet"]),
            race_number=int(row["race_number"]),
        )
        return cls(
            key=key,
            collection_status=row.get("collection_status"),
            result_status=row.get("result_status"),
            basic_data=_decode_json_if_needed(row.get("basic_data")),
            raw_data=_decode_json_if_needed(row.get("raw_data")),
            result_data=_decode_json_if_needed(row.get("result_data")),
            collected_at=row.get("collected_at"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    @property
    def race_id(self) -> str:
        return self.key.race_id

    @property
    def race_date(self) -> str:
        return self.key.race_date

    @property
    def meet(self) -> int:
        return self.key.meet

    @property
    def race_number(self) -> int:
        return self.key.race_number

    def to_legacy_dict(self) -> dict[str, Any]:
        data = self.key.to_legacy_dict()
        data.update(
            {
                "collection_status": self.collection_status,
                "result_status": self.result_status,
            }
        )
        return data

    def result_top3(self) -> list[int]:
        return normalize_result_data(self.result_data)
