from __future__ import annotations

import json
from pathlib import Path

import pytest

from infrastructure.kra_api.source_parser import (
    INTERMEDIATE_SCHEMA_VERSION,
    build_source_document,
    parse_kra_response_payload,
)


def _example_path(name: str) -> Path:
    return Path(__file__).resolve().parents[4] / "examples" / name


@pytest.mark.unit
def test_parse_kra_response_payload_normalizes_json_and_xml_examples():
    json_payload = json.loads(_example_path("api214_response.json").read_text())
    xml_payload = _example_path("api214_response.xml").read_bytes()

    parsed_json, json_format = parse_kra_response_payload(json_payload)
    parsed_xml, xml_format = parse_kra_response_payload(xml_payload)

    assert json_format == "dict"
    assert xml_format == "xml"
    assert parsed_json["response"]["header"]["resultCode"] == "00"
    assert parsed_xml["response"]["header"]["resultCode"] == "00"
    assert len(parsed_json["response"]["body"]["items"]["item"]) == len(
        parsed_xml["response"]["body"]["items"]["item"]
    )


@pytest.mark.unit
def test_build_source_document_maps_api214_xml_into_canonical_fragment():
    xml_payload = _example_path("api214_response.xml").read_bytes()

    document = build_source_document("API214_1", xml_payload)

    assert document.schema_version == INTERMEDIATE_SCHEMA_VERSION
    assert document.race_metadata == {
        "race_date": "20250523",
        "race_no": 1,
        "meet": 3,
    }
    assert document.fragment["race_date"] == "20250523"
    assert document.fragment["race_no"] == 1
    assert document.fragment["meet"] == 3
    assert document.fragment["horses"][0]["chul_no"] == 1
    assert document.fragment["horses"][-1]["chul_no"] == 11
    assert any(
        record.schema_path == "race_info.response.body.items.item[]"
        for record in document.records
    )
    assert any(
        record.schema_path == "horses[].wg_hr" and record.join_value == 1
        for record in document.records
    )


@pytest.mark.unit
def test_build_source_document_filters_race_level_rows_and_absorbs_alias_types():
    payload = {
        "response": {
            "body": {
                "items": {
                    "item": [
                        {
                            "rcDate": 20260405,
                            "rcNo": "2",
                            "meet": "서울",
                            "rank": "국5",
                            "budam": "별정A",
                            "rcDist": "1000",
                            "ageCond": "2세",
                        },
                        {
                            "rcDate": "20260405",
                            "rcNo": 3,
                            "meet": "1",
                            "rank": "국6",
                            "budam": "핸디캡",
                            "rcDist": 1200,
                            "ageCond": "연령오픈",
                            "sexCond": "암",
                            "schStTime": "1430",
                        },
                    ]
                }
            }
        }
    }

    document = build_source_document(
        "API72_2",
        payload,
        race_date="20260405",
        race_no=3,
        meet=1,
    )

    assert document.fragment == {
        "race_plan": {
            "rank": "국6",
            "budam": "핸디캡",
            "rc_dist": 1200,
            "age_cond": "연령오픈",
            "sex_cond": "암",
            "sch_st_time": "1430",
        }
    }
    assert {record.schema_path for record in document.records} >= {
        "race_plan.rank",
        "race_plan.budam",
        "race_plan.rc_dist",
        "race_plan.age_cond",
    }


@pytest.mark.unit
def test_build_source_document_emits_join_rows_for_detail_sources():
    payload = json.loads(_example_path("api8_2_response.json").read_text())

    document = build_source_document("API8_2", payload)

    assert document.fragment["join_rows"][0]["join_key"] == "hrNo"
    assert document.fragment["join_rows"][0]["join_value"] == "0051228"
    assert document.fragment["join_rows"][0]["schema_path"] == "horses[].hrDetail"
    assert document.fragment["join_rows"][0]["value"]["hr_no"] == "0051228"
    assert document.fragment["join_rows"][0]["value"]["ow_no"] == 118011


@pytest.mark.unit
def test_build_source_document_uses_hrnm_alias_for_training_rows():
    payload = {
        "response": {
            "body": {
                "items": {
                    "item": [
                        {"hrnm": "천년의질주", "trngDt": 20260410, "remkTxt": "양호"},
                        {"hrName": "강철마", "trngDt": 20260410, "remkTxt": "보통"},
                    ]
                }
            }
        }
    }

    document = build_source_document("API329", payload)

    assert [row["join_value"] for row in document.fragment["join_rows"]] == [
        "천년의질주",
        "강철마",
    ]
    assert document.fragment["join_rows"][0]["value"]["hrnm"] == "천년의질주"
