"""
Field name mapping utilities
Handles conversion between KRA API camelCase and internal snake_case
"""

import re
from typing import Any

from adapters.kra_response_adapter import KRAResponseAdapter


def camel_to_snake(name: str) -> str:
    """Convert camelCase to snake_case."""
    # Insert underscore before uppercase letters (except first)
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    # Insert underscore before uppercase letters followed by lowercase
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def snake_to_camel(name: str) -> str:
    """Convert snake_case to camelCase."""
    components = name.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


# KRA API field mappings (camelCase -> snake_case)
FIELD_MAPPINGS = {
    # Race fields
    "rcDate": "race_date",
    "rcNo": "race_no",
    "rcName": "race_name",
    "rcDist": "race_distance",
    "rcTime": "race_time",
    # Horse fields
    "hrNo": "hr_no",
    "hrName": "hr_name",
    "chulNo": "chul_no",
    "winOdds": "win_odds",
    "plcOdds": "plc_odds",
    "wgBudam": "weight",
    "rating": "rating",
    "ord": "ord",
    "rcCntT": "rc_cnt_t",
    "ord1CntT": "ord1_cnt_t",
    "ord2CntT": "ord2_cnt_t",
    "ord3CntT": "ord3_cnt_t",
    "rcCntY": "rc_cnt_y",
    "ord1CntY": "ord1_cnt_y",
    "winRateT": "win_rate_t",
    "plcRateT": "plc_rate_t",
    "winRateY": "win_rate_y",
    "chaksunT": "chaksun_t",
    "hrLastAmt": "hr_last_amt",
    # Jockey fields
    "jkNo": "jk_no",
    "jkName": "jk_name",
    # Trainer fields
    "trNo": "tr_no",
    "trName": "tr_name",
    # Parent horse fields
    "faHrNo": "fa_hr_no",
    "faHrName": "fa_hr_name",
    "moHrNo": "mo_hr_no",
    "moHrName": "mo_hr_name",
}

# Reverse mapping for converting back to API format
REVERSE_FIELD_MAPPINGS = {v: k for k, v in FIELD_MAPPINGS.items()}


def convert_api_to_internal(data: dict[str, Any]) -> dict[str, Any]:
    """
    Convert KRA API response fields from camelCase to snake_case.

    Args:
        data: API response data with camelCase fields

    Returns:
        Data with snake_case fields
    """
    if not isinstance(data, dict):
        return data

    converted = {}
    for key, value in data.items():
        # Use mapping if available, otherwise auto-convert
        new_key = FIELD_MAPPINGS.get(key, camel_to_snake(key))

        # Recursively convert nested dictionaries
        if isinstance(value, dict):
            converted[new_key] = convert_api_to_internal(value)
        # Recursively convert lists
        elif isinstance(value, list):
            converted[new_key] = [
                convert_api_to_internal(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            converted[new_key] = value

    return converted


def convert_internal_to_api(data: dict[str, Any]) -> dict[str, Any]:
    """
    Convert internal data from snake_case to camelCase for API.

    Args:
        data: Internal data with snake_case fields

    Returns:
        Data with camelCase fields
    """
    if not isinstance(data, dict):
        return data

    converted = {}
    for key, value in data.items():
        # Use mapping if available, otherwise auto-convert
        new_key = REVERSE_FIELD_MAPPINGS.get(key, snake_to_camel(key))

        # Recursively convert nested dictionaries
        if isinstance(value, dict):
            converted[new_key] = convert_internal_to_api(value)
        # Recursively convert lists
        elif isinstance(value, list):
            converted[new_key] = [
                convert_internal_to_api(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            converted[new_key] = value

    return converted


def extract_race_horses(api_response: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract horse data from KRA API response structure.

    Args:
        api_response: Raw API response

    Returns:
        List of horse dictionaries with snake_case fields
    """
    horses = []

    if "response" in api_response and "body" in api_response["response"]:
        items = api_response["response"]["body"].get("items", {})
        if items and "item" in items:
            raw_horses = items["item"]
            if not isinstance(raw_horses, list):
                raw_horses = [raw_horses]

            # Convert each horse's fields
            for horse in raw_horses:
                horses.append(convert_api_to_internal(horse))

    return horses
