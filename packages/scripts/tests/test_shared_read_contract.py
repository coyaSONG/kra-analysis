from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.data_adapter import (
    convert_basic_data_to_enriched_format,
    convert_snapshot_to_enriched_format,
)
from shared.db_client import RaceDBClient
from shared.read_contract import (
    RaceKey,
    RaceSnapshot,
    RaceSourceLookup,
    normalize_result_data,
)


def _strict_snapshot_meta(
    *,
    entry_finalized_at: str = "2025-07-19T10:35:00+09:00",
) -> dict[str, object]:
    return {
        "format_version": "holdout-snapshot-v1",
        "rule_version": "holdout-entry-finalization-rule-v1",
        "source_filter_basis": "entry_finalized_at",
        "scheduled_start_at": "2025-07-19T11:00:00+09:00",
        "operational_cutoff_at": "2025-07-19T10:50:00+09:00",
        "snapshot_ready_at": entry_finalized_at,
        "entry_finalized_at": entry_finalized_at,
        "selected_timestamp_field": "entry_finalized_at_override",
        "selected_timestamp_value": entry_finalized_at,
        "timestamp_source": "source_revision",
        "timestamp_confidence": "high",
        "revision_id": None,
        "late_reissue_after_cutoff": False,
        "cutoff_unbounded": False,
        "replay_status": "strict",
        "include_in_strict_dataset": True,
        "hard_required_sources_present": True,
        "hard_required_source_status": {
            "API214_1": "present",
            "API72_2": "present",
            "API189_1": "present",
            "API9_1": "present",
        },
    }


def test_normalize_result_data_supports_list_dict_and_string():
    assert normalize_result_data([1, 2, 3]) == [1, 2, 3]
    assert normalize_result_data({"top3": [4, 5, 6]}) == [4, 5, 6]
    assert normalize_result_data("[7, 8, 9]") == [7, 8, 9]


def test_race_source_lookup_requires_entry_snapshot_at():
    lookup = RaceSourceLookup.from_race_info(
        {
            "race_id": "race-1",
            "race_date": "20250719",
            "entry_snapshot_at": "2025-07-19T10:00:00+09:00",
        }
    )

    assert lookup.to_dict() == {
        "race_id": "race-1",
        "race_date": "20250719",
        "entry_snapshot_at": "2025-07-19T10:00:00+09:00",
    }


def test_race_source_lookup_from_snapshot_uses_entry_snapshot_metadata():
    snapshot = RaceSnapshot(
        key=RaceKey(race_id="race-9", race_date="20250719", meet=1, race_number=9),
        basic_data={
            "collected_at": "2025-07-19T10:35:00+09:00",
            "race_info": {"response": {"body": {"items": {"item": []}}}},
            "race_plan": {"sch_st_time": "1100"},
            "track": {"weather": "맑음"},
            "cancelled_horses": [],
        },
        raw_data={"snapshot_meta": _strict_snapshot_meta()},
        collected_at="2025-07-19T10:35:00+09:00",
        updated_at="2025-07-19T10:36:00+09:00",
    )

    lookup = RaceSourceLookup.from_snapshot(snapshot)

    assert lookup.to_dict() == {
        "race_id": "race-9",
        "race_date": "20250719",
        "entry_snapshot_at": "2025-07-19T10:35:00+09:00",
    }


def test_load_race_snapshot_returns_canonical_dto():
    with patch.object(RaceDBClient, "__init__", lambda self, **kw: None):
        client = RaceDBClient()

    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {
        "race_id": "race-1",
        "date": "20250719",
        "meet": 1,
        "race_number": 3,
        "collection_status": "collected",
        "result_status": "collected",
        "basic_data": {"race_info": {"response": {"body": {"items": {"item": []}}}}},
        "raw_data": {"snapshot_meta": {"replay_status": "strict"}},
        "result_data": {"top3": [1, 2, 3]},
    }
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value = mock_cursor
    client._conn = mock_conn

    snapshot = client.load_race_snapshot("race-1")

    assert snapshot is not None
    assert isinstance(snapshot.key, RaceKey)
    assert snapshot.race_id == "race-1"
    assert snapshot.race_date == "20250719"
    assert snapshot.raw_data == {"snapshot_meta": {"replay_status": "strict"}}
    assert snapshot.result_top3() == [1, 2, 3]
    assert snapshot.to_legacy_dict()["meet"] == "서울"


def test_load_race_basic_data_requires_matching_snapshot_lookup():
    with patch.object(RaceDBClient, "load_race_snapshot") as load_snapshot:
        client = RaceDBClient.__new__(RaceDBClient)
        load_snapshot.return_value = RaceSnapshot(
            key=RaceKey(race_id="race-1", race_date="20250719", meet=1, race_number=3),
            basic_data={
                "collected_at": "2025-07-19T10:35:00+09:00",
                "race_info": {"response": {"body": {"items": {"item": []}}}},
            },
            raw_data={"snapshot_meta": _strict_snapshot_meta()},
        )

        lookup = RaceSourceLookup(
            race_id="race-1",
            race_date="20250719",
            entry_snapshot_at="2025-07-19T10:35:00+09:00",
        )
        data = client.load_race_basic_data("race-1", lookup=lookup)

    assert data == {
        "collected_at": "2025-07-19T10:35:00+09:00",
        "race_info": {"response": {"body": {"items": {"item": []}}}},
    }


def test_convert_snapshot_to_enriched_format_accepts_race_snapshot():
    snapshot = RaceSnapshot(
        key=RaceKey(race_id="race-2", race_date="20250719", meet=1, race_number=1),
        basic_data={
            "race_info": {
                "response": {
                    "body": {"items": {"item": [{"chulNo": 1, "hrName": "Horse"}]}}
                }
            },
            "horses": [{"chul_no": 1, "hrDetail": {"win_rate": 12, "age": 4}}],
        },
    )

    enriched = convert_snapshot_to_enriched_format(snapshot)
    legacy = convert_basic_data_to_enriched_format(snapshot.basic_data or {})

    assert enriched == legacy
    assert enriched["response"]["body"]["items"]["item"][0]["hrDetail"]["winRate"] == 12
    assert enriched["response"]["body"]["items"]["item"][0]["hrDetail"]["age"] == 4


def test_load_race_basic_data_rejects_rows_collected_after_lookup_snapshot():
    with patch.object(RaceDBClient, "load_race_snapshot") as load_snapshot:
        client = RaceDBClient.__new__(RaceDBClient)
        load_snapshot.return_value = RaceSnapshot(
            key=RaceKey(race_id="race-1", race_date="20250719", meet=1, race_number=3),
            basic_data={
                "collected_at": "2025-07-19T10:40:00+09:00",
                "race_info": {"response": {"body": {"items": {"item": []}}}},
            },
            raw_data={"snapshot_meta": _strict_snapshot_meta()},
        )

        lookup = RaceSourceLookup(
            race_id="race-1",
            race_date="20250719",
            entry_snapshot_at="2025-07-19T10:35:00+09:00",
        )

        try:
            client.load_race_basic_data("race-1", lookup=lookup)
        except ValueError as exc:
            assert "basic_data was collected after lookup.entry_snapshot_at" in str(exc)
        else:
            raise AssertionError("expected cutoff visibility validation to fail")


def test_load_race_basic_data_rejects_rows_created_after_lookup_snapshot():
    with patch.object(RaceDBClient, "load_race_snapshot") as load_snapshot:
        client = RaceDBClient.__new__(RaceDBClient)
        load_snapshot.return_value = RaceSnapshot(
            key=RaceKey(race_id="race-1", race_date="20250719", meet=1, race_number=3),
            basic_data={
                "collected_at": "2025-07-19T10:35:00+09:00",
                "race_info": {"response": {"body": {"items": {"item": []}}}},
            },
            raw_data={"snapshot_meta": _strict_snapshot_meta()},
            created_at="2025-07-19T10:36:00+09:00",
        )

        lookup = RaceSourceLookup(
            race_id="race-1",
            race_date="20250719",
            entry_snapshot_at="2025-07-19T10:35:00+09:00",
        )

        try:
            client.load_race_basic_data("race-1", lookup=lookup)
        except ValueError as exc:
            assert "stored race row was created after lookup.entry_snapshot_at" in str(
                exc
            )
        else:
            raise AssertionError(
                "expected created_at cutoff visibility validation to fail"
            )


def test_load_race_basic_data_rejects_prerace_updates_after_lookup_snapshot():
    with patch.object(RaceDBClient, "load_race_snapshot") as load_snapshot:
        client = RaceDBClient.__new__(RaceDBClient)
        load_snapshot.return_value = RaceSnapshot(
            key=RaceKey(race_id="race-1", race_date="20250719", meet=1, race_number=3),
            basic_data={
                "collected_at": "2025-07-19T10:35:00+09:00",
                "race_info": {"response": {"body": {"items": {"item": []}}}},
            },
            raw_data={"snapshot_meta": _strict_snapshot_meta()},
            result_status="pending",
            updated_at="2025-07-19T10:36:00+09:00",
        )

        lookup = RaceSourceLookup(
            race_id="race-1",
            race_date="20250719",
            entry_snapshot_at="2025-07-19T10:35:00+09:00",
        )

        try:
            client.load_race_basic_data("race-1", lookup=lookup)
        except ValueError as exc:
            assert "stored race row was updated after lookup.entry_snapshot_at" in str(
                exc
            )
        else:
            raise AssertionError(
                "expected updated_at cutoff visibility validation to fail"
            )


def test_load_race_basic_data_allows_post_snapshot_result_updates():
    with patch.object(RaceDBClient, "load_race_snapshot") as load_snapshot:
        client = RaceDBClient.__new__(RaceDBClient)
        load_snapshot.return_value = RaceSnapshot(
            key=RaceKey(race_id="race-1", race_date="20250719", meet=1, race_number=3),
            basic_data={
                "collected_at": "2025-07-19T10:35:00+09:00",
                "race_info": {"response": {"body": {"items": {"item": []}}}},
            },
            raw_data={"snapshot_meta": _strict_snapshot_meta()},
            result_status="collected",
            result_data={"top3": [1, 2, 3]},
            updated_at="2025-07-19T11:10:00+09:00",
        )

        lookup = RaceSourceLookup(
            race_id="race-1",
            race_date="20250719",
            entry_snapshot_at="2025-07-19T10:35:00+09:00",
        )
        data = client.load_race_basic_data("race-1", lookup=lookup)

    assert data == {
        "collected_at": "2025-07-19T10:35:00+09:00",
        "race_info": {"response": {"body": {"items": {"item": []}}}},
    }


def test_convert_snapshot_to_enriched_format_resolves_duplicate_entries_with_priority_rule():
    snapshot = RaceSnapshot(
        key=RaceKey(race_id="race-3", race_date="20250719", meet=1, race_number=1),
        basic_data={
            "race_info": {
                "response": {
                    "body": {
                        "items": {
                            "item": [
                                {
                                    "chulNo": 1,
                                    "hrNo": "OLD001",
                                    "hrName": "기존말",
                                    "jkNo": "J001",
                                },
                                {
                                    "chulNo": 1,
                                    "hrNo": "001",
                                    "hrName": "확정말",
                                    "jkNo": "J001",
                                    "jkName": "기수1",
                                    "trNo": "T001",
                                    "trName": "조교사1",
                                    "owNo": "O001",
                                    "owName": "마주1",
                                    "age": 4,
                                    "sex": "수",
                                    "name": "한",
                                    "rank": "국6",
                                    "wgBudam": 54.5,
                                    "winOdds": 3.4,
                                },
                            ]
                        }
                    }
                }
            },
            "horses": [
                {"chul_no": 1, "hr_no": "BAD999", "hrDetail": {"win_rate": 99}},
                {"chul_no": 1, "hr_no": "001", "hrDetail": {"win_rate": 12, "age": 4}},
            ],
        },
    )

    enriched = convert_snapshot_to_enriched_format(
        snapshot,
        include_resolution_audit=True,
    )

    item = enriched["response"]["body"]["items"]["item"][0]
    audit = enriched["response"]["body"]["entryResolutionAudit"]

    assert len(enriched["response"]["body"]["items"]["item"]) == 1
    assert item["hrNo"] == "001"
    assert item["hrName"] == "확정말"
    assert item["hrDetail"]["winRate"] == 12
    assert audit["duplicate_chul_no_group_count"] == 2
    assert audit["identifier_inconsistency_count"] >= 2
    assert {entry["source"] for entry in audit["duplicate_chul_no_records"]} == {
        "race_info_items",
        "basic_data.horses",
    }
