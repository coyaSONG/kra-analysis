import pytest

from utils.field_mapping import (
    camel_to_snake,
    convert_api_to_internal,
    convert_internal_to_api,
    extract_race_horses,
    snake_to_camel,
)


@pytest.mark.unit
def test_camel_snake_roundtrip():
    assert camel_to_snake("rcDate") == "rc_date"
    assert snake_to_camel("rc_date") == "rcDate"


@pytest.mark.unit
def test_convert_api_to_internal_basic():
    api = {"rcDate": "20240719", "hrNo": "001", "jkName": "홍길동"}
    conv = convert_api_to_internal(api)
    assert conv["race_date"] == "20240719"
    assert conv["hr_no"] == "001"
    assert conv["jk_name"] == "홍길동"


@pytest.mark.unit
def test_convert_internal_to_api_basic():
    internal = {"race_date": "20240719", "hr_no": "001", "jk_name": "홍길동"}
    conv = convert_internal_to_api(internal)
    assert conv["rcDate"] == "20240719"
    assert conv["hrNo"] == "001"
    assert conv["jkName"] == "홍길동"


@pytest.mark.unit
def test_extract_race_horses_list_and_single():
    # List case
    api_list = {
        "response": {"body": {"items": {"item": [{"hrNo": "001"}, {"hrNo": "002"}]}}}
    }
    horses = extract_race_horses(api_list)
    assert len(horses) == 2 and horses[0]["hr_no"] == "001"

    # Single case
    api_single = {"response": {"body": {"items": {"item": {"hrNo": "003"}}}}}
    horses2 = extract_race_horses(api_single)
    assert len(horses2) == 1 and horses2[0]["hr_no"] == "003"


@pytest.mark.unit
def test_convert_functions_non_dict_passthrough():
    # Non-dict should return as-is
    assert convert_api_to_internal(["x"]) == ["x"]
    assert convert_internal_to_api(["y"]) == ["y"]
