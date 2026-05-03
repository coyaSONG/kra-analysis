import pytest

from services.collection_preprocessing import preprocess_data


@pytest.mark.unit
def test_preprocess_data_applies_rule_replacements_and_records_flags():
    result = preprocess_data(
        {
            "horses": [
                {
                    "chulNo": "1",
                    "hrNo": "001.0",
                    "hrName": "스타",
                    "jkNo": "J001.0",
                    "jkName": "기수",
                    "trNo": "T001.0",
                    "trName": "조교사",
                    "owNo": "O001.0",
                    "owName": "마주",
                    "age": "3",
                    "sex": "F",
                    "name": "한",
                    "rank": "국6",
                    "rating": "bad",
                    "wgBudam": "55.5",
                    "wgBudamBigo": "-",
                    "wgHr": "512(+2)",
                    "winOdds": "0",
                    "plcOdds": "bad",
                    "ilsu": "bad",
                    "hrTool": " ",
                    "hrDetail": None,
                }
            ]
        }
    )

    horse = result["horses"][0]
    assert horse["hr_no"] == "001"
    assert horse["jk_no"] == "J001"
    assert horse["sex"] == "암"
    assert horse["rating"] is None
    assert horse["wg_budam_bigo"] is None
    assert horse["weight"] == 512
    assert horse["weight_delta"] == 2
    assert horse["win_odds"] is None
    assert horse["plc_odds"] is None
    assert horse["hr_tool"] is None
    assert horse["hrDetail"] == {}
    assert "rating_parse_failed" in horse["preprocessing"]["flags"]
    assert "budam_note_missing" in horse["preprocessing"]["flags"]
    assert "market_signal_missing" in horse["preprocessing"]["flags"]
    assert "odds_parse_failed" in horse["preprocessing"]["flags"]
    assert "ilsu_parse_failed" in horse["preprocessing"]["flags"]
    assert "popularity_unusable" in horse["preprocessing"]["flags"]
    assert result["preprocessing_audit"]["rule_schema_version"].startswith(
        "prerace-entry-preprocessing-rules-v1"
    )


@pytest.mark.unit
def test_preprocess_data_records_exclusion_reasons_for_invalid_and_duplicate_entries():
    result = preprocess_data(
        {
            "horses": [
                {
                    "chulNo": "1",
                    "hrNo": "001",
                    "hrName": "정상마",
                    "jkNo": "J001",
                    "jkName": "기수1",
                    "trNo": "T001",
                    "trName": "조교사1",
                    "owNo": "O001",
                    "owName": "마주1",
                    "age": "3",
                    "sex": "M",
                    "name": "한",
                    "rank": "국6",
                    "wgBudam": "55.0",
                    "winOdds": "4.0",
                    "wgHr": "500",
                },
                {
                    "chulNo": "1",
                    "hrNo": "002",
                    "hrName": "중복마",
                    "jkNo": "J002",
                    "jkName": "기수2",
                    "trNo": "T002",
                    "trName": "조교사2",
                    "owNo": "O002",
                    "owName": "마주2",
                    "age": "4",
                    "sex": "F",
                    "name": "한",
                    "rank": "국5",
                    "wgBudam": "54.0",
                    "winOdds": "6.0",
                    "wgHr": "490",
                },
                {
                    "chulNo": "3",
                    "hrNo": "003",
                    "hrName": "연령오류",
                    "jkNo": "J003",
                    "jkName": "기수3",
                    "trNo": "T003",
                    "trName": "조교사3",
                    "owNo": "O003",
                    "owName": "마주3",
                    "age": "0",
                    "sex": "C",
                    "name": "한",
                    "rank": "국4",
                    "wgBudam": "53.0",
                    "winOdds": "8.0",
                    "wgHr": "480",
                },
            ]
        }
    )

    assert result["excluded_horses"] == 3
    assert result["horses"] == []
    excluded = result["preprocessing_audit"]["excluded_entries"]
    duplicate_reasons = [
        item["reasons"] for item in excluded if item["hr_no"] in {"001", "002"}
    ]
    assert all("chul_no_duplicate" in reasons for reasons in duplicate_reasons)
    age_reasons = next(item["reasons"] for item in excluded if item["hr_no"] == "003")
    assert "age_invalid" in age_reasons
    assert result["preprocessing_audit"]["reason_counts"]["chul_no_duplicate"] == 2


@pytest.mark.unit
def test_preprocess_data_nulls_soft_numeric_outliers_and_excludes_burden_weight_outlier():
    result = preprocess_data(
        {
            "horses": [
                {
                    "chulNo": "1",
                    "hrNo": "010",
                    "hrName": "소프트이상치",
                    "jkNo": "J010",
                    "jkName": "기수10",
                    "trNo": "T010",
                    "trName": "조교사10",
                    "owNo": "O010",
                    "owName": "마주10",
                    "age": "4",
                    "sex": "M",
                    "name": "한",
                    "rank": "국4",
                    "rating": "181",
                    "wgBudam": "55.0",
                    "winOdds": "350",
                    "plcOdds": "120",
                    "wgHr": "700(+55)",
                },
                {
                    "chulNo": "2",
                    "hrNo": "011",
                    "hrName": "부담중량이상치",
                    "jkNo": "J011",
                    "jkName": "기수11",
                    "trNo": "T011",
                    "trName": "조교사11",
                    "owNo": "O011",
                    "owName": "마주11",
                    "age": "4",
                    "sex": "F",
                    "name": "한",
                    "rank": "국4",
                    "wgBudam": "70.0",
                    "winOdds": "5.0",
                    "plcOdds": "2.0",
                    "wgHr": "470(+1)",
                },
            ]
        }
    )

    assert len(result["horses"]) == 1
    horse = result["horses"][0]
    assert horse["hr_no"] == "010"
    assert horse["rating"] is None
    assert horse["weight"] is None
    assert horse["weight_delta"] is None
    assert horse["win_odds"] is None
    assert horse["plc_odds"] is None
    assert {
        "rating_outlier",
        "weight_outlier",
        "weight_delta_outlier",
        "win_odds_outlier",
        "plc_odds_outlier",
        "market_signal_missing",
        "popularity_unusable",
    } <= set(horse["preprocessing"]["flags"])

    excluded = result["preprocessing_audit"]["excluded_entries"]
    excluded_row = next(item for item in excluded if item["hr_no"] == "011")
    assert "wg_budam_outlier" in excluded_row["reasons"]
