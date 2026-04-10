from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.prerace_standard_loader import (
    build_standardized_prerace_payload,
    load_standardized_prerace_payload,
    resolve_race_record_reference,
)
from shared.read_contract import RaceKey, RaceSnapshot


def _basic_data() -> dict:
    return {
        "collected_at": "2025-07-19T10:35:00+09:00",
        "race_info": {
            "response": {
                "body": {
                    "items": {
                        "item": [
                            {
                                "rcDate": "20250719",
                                "rcNo": 3,
                                "rcName": "일반",
                                "rcDist": 1200,
                                "track": "건조",
                                "weather": "맑음",
                                "meet": "서울",
                                "budam": "별정A",
                                "ageCond": "3세",
                                "chulNo": 1,
                                "hrName": "알파",
                                "hrNo": "001",
                                "jkName": "기수1",
                                "jkNo": "J1",
                                "trName": "조교사1",
                                "trNo": "T1",
                                "owName": "마주1",
                                "owNo": "O1",
                                "winOdds": 2.5,
                                "plcOdds": 1.4,
                                "rating": 75,
                                "rank": "국6",
                                "age": 3,
                                "sex": "수",
                                "name": "한국",
                                "wgBudam": 54,
                                "wgBudamBigo": "-",
                                "wgHr": "470(+3)",
                                "ilsu": 21,
                                "ordBigo": "-",
                            }
                        ]
                    }
                }
            }
        },
        "race_plan": {"sch_st_time": "1450"},
        "track": {"weather": "맑음", "track": "건조", "water_percent": 4},
        "cancelled_horses": [],
        "horses": [
            {
                "chul_no": 1,
                "hr_no": "001",
                "hrDetail": {
                    "rc_cnt_t": 5,
                    "ord1_cnt_t": 1,
                    "ord2_cnt_t": 1,
                    "ord3_cnt_t": 1,
                },
                "jkDetail": {
                    "rc_cnt_t": 10,
                    "ord1_cnt_t": 2,
                    "ord2_cnt_t": 1,
                    "ord3_cnt_t": 1,
                },
                "trDetail": {
                    "rc_cnt_t": 8,
                    "ord1_cnt_t": 1,
                    "ord2_cnt_t": 1,
                    "ord3_cnt_t": 1,
                },
            }
        ],
    }


def _snapshot() -> RaceSnapshot:
    return RaceSnapshot(
        key=RaceKey(
            race_id="20250719_1_3", race_date="20250719", meet=1, race_number=3
        ),
        basic_data=_basic_data(),
        raw_data={
            "snapshot_meta": {
                "entry_finalized_at": "2025-07-19T10:35:00+09:00",
                "replay_status": "strict",
                "include_in_strict_dataset": True,
                "hard_required_sources_present": True,
                "source_filter_basis": "entry_finalized_at",
            }
        },
        collected_at="2025-07-19T10:35:00+09:00",
        updated_at="2025-07-19T10:36:00+09:00",
    )


class _FakeQueryPort:
    def __init__(self, basic_data: dict) -> None:
        self.basic_data = basic_data
        self.lookups: list[dict[str, str]] = []

    def load_race_basic_data(self, race_id: str, *, lookup):
        self.lookups.append(lookup.to_dict())
        assert race_id == "20250719_1_3"
        return self.basic_data


def test_resolve_race_record_reference_supports_snapshot_and_mapping() -> None:
    reference, lookup = resolve_race_record_reference(_snapshot())

    assert reference == {
        "race_id": "20250719_1_3",
        "race_date": "20250719",
        "race_no": "3",
        "meet": "서울",
    }
    assert lookup.entry_snapshot_at == "2025-07-19T10:35:00+09:00"

    mapping_reference, mapping_lookup = resolve_race_record_reference(
        {
            "race_id": "20250719_1_3",
            "race_date": "20250719",
            "entry_finalized_at": "2025-07-19T10:35:00+09:00",
            "meet": "서울",
        }
    )
    assert mapping_reference["race_id"] == "20250719_1_3"
    assert mapping_lookup.entry_snapshot_at == "2025-07-19T10:35:00+09:00"


def test_build_standardized_prerace_payload_normalizes_intermediate_snapshot() -> None:
    standardized = build_standardized_prerace_payload(
        _basic_data(),
        race_id="20250719_1_3",
        race_date="20250719",
        meet="서울",
        include_resolution_audit=True,
    )

    assert standardized.standard_payload["race_id"] == "20250719_1_3"
    assert standardized.standard_payload["input_schema"]["schema_version"] == (
        "alternative-ranking-input-v1"
    )
    assert standardized.standard_payload["horses"][0]["class_rank"] == "국6"
    assert "rank" not in standardized.standard_payload["horses"][0]
    assert "horses[0].ordBigo" in standardized.removed_post_race_paths
    assert standardized.entry_resolution_audit is not None
    assert standardized.entry_resolution_audit["audit_version"] == (
        "prerace-entry-resolution-v1"
    )


def test_load_standardized_prerace_payload_uses_query_port_lookup_contract() -> None:
    query_port = _FakeQueryPort(_basic_data())

    standardized = load_standardized_prerace_payload(
        {
            "race_id": "20250719_1_3",
            "race_date": "20250719",
            "entry_snapshot_at": "2025-07-19T10:35:00+09:00",
            "meet": "서울",
        },
        query_port=query_port,
    )

    assert query_port.lookups == [
        {
            "race_id": "20250719_1_3",
            "race_date": "20250719",
            "entry_snapshot_at": "2025-07-19T10:35:00+09:00",
        }
    ]
    assert standardized.lookup is not None
    assert standardized.lookup.entry_snapshot_at == "2025-07-19T10:35:00+09:00"
    assert standardized.standard_payload["horses"][0]["hrNo"] == "001"
