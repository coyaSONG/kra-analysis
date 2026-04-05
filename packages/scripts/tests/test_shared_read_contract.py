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
from shared.read_contract import RaceKey, RaceSnapshot, normalize_result_data


def test_normalize_result_data_supports_list_dict_and_string():
    assert normalize_result_data([1, 2, 3]) == [1, 2, 3]
    assert normalize_result_data({"top3": [4, 5, 6]}) == [4, 5, 6]
    assert normalize_result_data("[7, 8, 9]") == [7, 8, 9]


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
    assert snapshot.result_top3() == [1, 2, 3]
    assert snapshot.to_legacy_dict()["meet"] == "서울"


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
