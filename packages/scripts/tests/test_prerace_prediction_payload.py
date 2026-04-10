from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.prerace_prediction_payload import (
    build_prerace_race_payload_from_enriched,
    strip_forbidden_fields,
)


def test_strip_forbidden_fields_renames_rank_and_removes_postrace_keys():
    cleaned = strip_forbidden_fields(
        {
            "chulNo": 1,
            "rank": "국6",
            "ordBigo": "-",
            "nested": {"rcTime": "1:12.3"},
        }
    )

    assert cleaned["class_rank"] == "국6"
    assert "rank" not in cleaned
    assert "ordBigo" not in cleaned
    assert "rcTime" not in cleaned["nested"]


def test_build_prerace_race_payload_from_enriched_uses_common_schema_contract():
    removed_paths: list[str] = []
    payload, candidate_filter, _field_policy = build_prerace_race_payload_from_enriched(
        {
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
                                "hrDetail": {
                                    "rcCntT": 5,
                                    "ord1CntT": 1,
                                    "ord2CntT": 1,
                                    "ord3CntT": 1,
                                },
                                "jkDetail": {
                                    "rcCntT": 10,
                                    "ord1CntT": 2,
                                    "ord2CntT": 1,
                                    "ord3CntT": 1,
                                },
                                "trDetail": {
                                    "rcCntT": 8,
                                    "ord1CntT": 1,
                                    "ord2CntT": 1,
                                    "ord3CntT": 1,
                                },
                            },
                            {
                                "rcDate": "20250719",
                                "rcNo": 3,
                                "rcDist": 1200,
                                "track": "건조",
                                "weather": "맑음",
                                "meet": "서울",
                                "chulNo": 2,
                                "hrName": "브라보",
                                "hrNo": "002",
                                "jkName": "기수2",
                                "jkNo": "J2",
                                "trName": "조교사2",
                                "trNo": "T2",
                                "owName": "마주2",
                                "owNo": "O2",
                                "winOdds": 0,
                                "plcOdds": 0,
                                "rating": 71,
                                "rank": "국6",
                                "age": 3,
                                "sex": "암",
                                "name": "한국",
                                "wgBudam": 53,
                                "wgBudamBigo": "-",
                                "wgHr": "460(+1)",
                                "ilsu": 15,
                            },
                        ]
                    }
                }
            }
        },
        race_id="20250719_1_3",
        race_date="20250719",
        meet="서울",
        removed_paths=removed_paths,
    )

    assert payload["race_id"] == "20250719_1_3"
    assert payload["input_schema"]["schema_version"] == "alternative-ranking-input-v1"
    assert payload["horses"][0]["class_rank"] == "국6"
    assert "winOdds" not in payload["horses"][0]
    assert "ordBigo" not in removed_paths
    assert "horses[0].ordBigo" in removed_paths
    assert candidate_filter["status_counts"]["normal"] == 1
    assert candidate_filter["status_counts"]["scratched"] == 1
