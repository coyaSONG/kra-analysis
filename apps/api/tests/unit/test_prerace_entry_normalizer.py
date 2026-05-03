from __future__ import annotations

import csv
from pathlib import Path

import pytest

from utils.prerace_entry_normalizer import (
    RULE_TABLE_FIELD_PATHS,
    normalize_prerace_horse_entry,
)

pytestmark = pytest.mark.unit


def test_rule_table_field_paths_match_normalizer_coverage():
    csv_path = (
        Path(__file__).resolve().parents[4]
        / "data"
        / "contracts"
        / "prerace_entry_preprocessing_rules_v1.csv"
    )

    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert {row["field_path"] for row in rows} == RULE_TABLE_FIELD_PATHS


def test_normalize_prerace_horse_entry_applies_rule_table_value_system():
    normalized = normalize_prerace_horse_entry(
        {
            "chulNo": "7",
            "hrNo": "001.0",
            "hrName": "테스트말",
            "jkNo": "080565.0",
            "jkName": "기수",
            "trNo": "070180.0",
            "trName": "조교사",
            "owNo": 65126,
            "owName": "마주",
            "age": "4",
            "gender": "M",
            "country": "한",
            "class_rank": "국6등급",
            "rating": "0",
            "burden_weight": "53.5",
            "wgBudamBigo": "-",
            "wgHr": "-",
            "winOdds": "0",
            "plcOdds": "abc",
            "ilsu": "x",
            "hrTool": "  ",
            "jkDetail": {"birthday": "1982-02-12", "sp_date": "-"},
            "trDetail": {"age": "-", "birthday": "-"},
            "jkStats": {"qnl_rate_y": "12.5", "rc_cnt_y": "10"},
            "owDetail": {"ow_no": "065126.0"},
            "training": {"train_state": " 양호 "},
        }
    )

    assert normalized["hr_no"] == "001"
    assert normalized["jk_no"] == "080565"
    assert normalized["tr_no"] == "070180"
    assert normalized["sex"] == "수"
    assert normalized["name"] == "한"
    assert normalized["country"] == "한"
    assert normalized["rating"] == 0
    assert normalized["wg_budam"] == 53.5
    assert normalized["wg_budam_bigo"] is None
    assert normalized["wg_hr"] is None
    assert normalized["weight"] is None
    assert normalized["weight_delta"] is None
    assert normalized["win_odds"] is None
    assert normalized["plc_odds"] is None
    assert "ilsu" not in normalized
    assert "hr_tool" not in normalized
    assert normalized["jkDetail"]["birthday"] == "19820212"
    assert normalized["jkDetail"]["sp_date"] is None
    assert normalized["trDetail"]["age"] is None
    assert normalized["trDetail"]["birthday"] is None
    assert normalized["jkStats"]["qnl_rate_y"] == 12.5
    assert normalized["jkStats"]["rc_cnt_y"] == 10
    assert normalized["owDetail"]["ow_no"] == "065126"
    assert normalized["training"]["train_state"] == "양호"
    assert {
        "id_normalized",
        "sex_bucketed",
        "rating_known_false",
        "budam_note_missing",
        "market_signal_missing",
        "odds_parse_failed",
        "ilsu_parse_failed",
        "hr_tool_missing",
        "weight_missing",
        "weight_delta_missing",
        "popularity_unusable",
    } <= set(normalized["normalization_flags"])


def test_normalize_prerace_horse_entry_nulls_numeric_outliers_but_keeps_entry():
    normalized = normalize_prerace_horse_entry(
        {
            "chulNo": "5",
            "hrNo": "005",
            "hrName": "이상치말",
            "jkNo": "080100",
            "jkName": "기수",
            "trNo": "070100",
            "trName": "조교사",
            "owNo": "110100",
            "owName": "마주",
            "age": "4",
            "sex": "암",
            "name": "한",
            "rank": "국4등급",
            "rating": "181",
            "burden_weight": "70",
            "wgHr": "700(+55)",
            "winOdds": "350",
            "plcOdds": "120",
        }
    )

    assert normalized["rating"] is None
    assert normalized["wg_budam"] is None
    assert normalized["weight"] is None
    assert normalized["weight_delta"] is None
    assert normalized["win_odds"] is None
    assert normalized["plc_odds"] is None
    assert {
        "core_missing",
        "rating_outlier",
        "wg_budam_outlier",
        "weight_outlier",
        "weight_delta_outlier",
        "win_odds_outlier",
        "plc_odds_outlier",
        "market_signal_missing",
        "popularity_unusable",
    } <= set(normalized["normalization_flags"])
