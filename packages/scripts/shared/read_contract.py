"""
Shared read contract for scripts.

This module defines the stable DTOs used by sync DB readers and downstream
data adapters without forcing callers to depend on raw row dictionaries.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

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
class RaceSnapshot:
    """Canonical read DTO for a race row."""

    key: RaceKey
    collection_status: str | None = None
    result_status: str | None = None
    basic_data: dict[str, Any] | None = None
    result_data: Any | None = None

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
            result_data=_decode_json_if_needed(row.get("result_data")),
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
