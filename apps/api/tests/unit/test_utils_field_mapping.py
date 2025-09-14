"""
Unit tests for utils.field_mapping helpers.
"""

import pytest

from utils.field_mapping import (
    camel_to_snake, snake_to_camel,
    convert_api_to_internal, convert_internal_to_api,
    extract_race_horses,
)


@pytest.mark.unit
def test_camel_snake_conversion_roundtrip():
    assert camel_to_snake("hrNo") == "hr_no"
    assert snake_to_camel("hr_no") == "hrNo"
    assert camel_to_snake("WinRateY") == "win_rate_y"


@pytest.mark.unit
def test_convert_api_to_internal_nested():
    data = {
        "hrNo": "001",
        "jkInfo": {"jkNo": "J001"},
        "arr": [{"trNo": "T001"}],
    }
    converted = convert_api_to_internal(data)
    assert converted["hr_no"] == "001"
    assert converted["jk_info"]["jk_no"] == "J001"
    assert converted["arr"][0]["tr_no"] == "T001"


@pytest.mark.unit
def test_convert_internal_to_api_nested():
    data = {
        "hr_no": "001",
        "jk_info": {"jk_no": "J001"},
        "arr": [{"tr_no": "T001"}],
    }
    converted = convert_internal_to_api(data)
    assert converted["hrNo"] == "001"
    assert converted["jkInfo"]["jkNo"] == "J001"
    assert converted["arr"][0]["trNo"] == "T001"


@pytest.mark.unit
def test_extract_race_horses_list_and_single_item():
    resp_list = {"response": {"body": {"items": {"item": [{"hrNo": "001"}, {"hrNo": "002"}]}}}}
    horses = extract_race_horses(resp_list)
    assert [h["hr_no"] for h in horses] == ["001", "002"]

    resp_single = {"response": {"body": {"items": {"item": {"hrNo": "003"}}}}}
    horses2 = extract_race_horses(resp_single)
    assert [h["hr_no"] for h in horses2] == ["003"]

