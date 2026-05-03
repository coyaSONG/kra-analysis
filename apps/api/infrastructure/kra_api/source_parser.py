"""KRA source response parser and source-to-schema mapping helpers."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from adapters.kra_response_adapter import KRAResponseAdapter
from utils.field_mapping import convert_api_to_internal

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_SCRIPTS_ROOT = _PROJECT_ROOT / "packages" / "scripts"
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

from shared.prerace_source_schema import (  # noqa: E402
    SOURCE_FIELD_MAPPINGS,
    FieldMappingSpec,
)

INTERMEDIATE_SCHEMA_VERSION = "kra-source-intermediate-v1"


@dataclass(frozen=True, slots=True)
class SourceMappedRecord:
    source_api: str
    source_field: str
    schema_path: str
    value: Any
    required: bool
    join_key: str | None = None
    join_value: str | int | None = None


@dataclass(frozen=True, slots=True)
class ParsedSourceDocument:
    schema_version: str
    source_api: str
    source_format: str
    race_metadata: dict[str, Any]
    fragment: dict[str, Any]
    records: tuple[SourceMappedRecord, ...]


def parse_kra_response_payload(
    payload: dict[str, Any] | str | bytes,
) -> tuple[dict[str, Any], str]:
    """Parse raw JSON/XML response bodies into a dict payload."""

    if isinstance(payload, dict):
        return payload, "dict"

    if isinstance(payload, bytes):
        text = _decode_bytes(payload)
    elif isinstance(payload, str):
        text = payload
    else:  # pragma: no cover - defensive guard
        raise TypeError(f"Unsupported payload type: {type(payload)!r}")

    stripped = text.strip()
    if not stripped:
        return {}, "empty"

    if stripped.startswith("<"):
        return _parse_xml_payload(stripped), "xml"

    return json.loads(stripped), "json"


def build_source_document(
    source_api: str,
    payload: dict[str, Any] | str | bytes,
    *,
    race_no: int | None = None,
    race_date: str | None = None,
    meet: int | str | None = None,
) -> ParsedSourceDocument:
    """Convert one source response into a canonical intermediate document."""

    parsed_payload, source_format = parse_kra_response_payload(payload)
    builder = _SOURCE_BUILDERS.get(source_api)
    if builder is None:
        raise ValueError(f"Unsupported source_api: {source_api}")

    fragment, records = builder(
        parsed_payload,
        race_no=race_no,
        race_date=race_date,
        meet=meet,
    )
    race_metadata = _merge_race_metadata(
        KRAResponseAdapter.extract_race_metadata(parsed_payload),
        race_no=race_no,
        race_date=race_date,
        meet=meet,
    )
    return ParsedSourceDocument(
        schema_version=INTERMEDIATE_SCHEMA_VERSION,
        source_api=source_api,
        source_format=source_format,
        race_metadata=race_metadata,
        fragment=fragment,
        records=tuple(records),
    )


def _build_api214_document(
    payload: dict[str, Any],
    *,
    race_no: int | None = None,
    race_date: str | None = None,
    meet: int | str | None = None,
) -> tuple[dict[str, Any], list[SourceMappedRecord]]:
    del race_no, race_date, meet
    records: list[SourceMappedRecord] = []
    items = KRAResponseAdapter.extract_items(payload)
    metadata = KRAResponseAdapter.extract_race_metadata(payload)
    fragment = {
        "race_date": metadata.get("race_date"),
        "race_no": metadata.get("race_no"),
        "meet": metadata.get("meet"),
        "race_info": {"response": {"body": {"items": {"item": items}}}},
        "horses": KRAResponseAdapter.extract_race_entries(payload),
    }

    for spec in _specs_for("API214_1"):
        if spec.schema_path == "race_info.response.body.items.item[]":
            records.append(_record(spec, items))
            continue
        if spec.schema_path in {"race_date", "race_no", "meet"}:
            value = fragment.get(spec.schema_path)
            if value is not None:
                records.append(_record(spec, value))
            continue
        if not spec.schema_path.startswith("horses[]."):
            continue
        field_name = spec.schema_path.removeprefix("horses[].")
        for horse in fragment["horses"]:
            value = horse.get(field_name)
            if value is None and not spec.required:
                continue
            records.append(
                _record(
                    spec,
                    value,
                    join_value=horse.get("chul_no"),
                )
            )
    return fragment, records


def _build_race_level_document(
    source_api: str,
    payload: dict[str, Any],
    *,
    race_no: int | None = None,
    race_date: str | None = None,
    meet: int | str | None = None,
) -> tuple[dict[str, Any], list[SourceMappedRecord]]:
    selected = _select_target_item(
        payload,
        race_no=race_no,
        race_date=race_date,
        meet=meet,
    )
    section = "race_plan" if source_api == "API72_2" else "track"
    fragment: dict[str, Any] = {section: {}}
    records: list[SourceMappedRecord] = []
    if not selected:
        return fragment, records

    normalized_row = convert_api_to_internal(selected)
    for spec in _specs_for(source_api):
        field_name = spec.schema_path.removeprefix(f"{section}.")
        value = normalized_row.get(field_name)
        if value is None and spec.source_field not in {"*", ""}:
            value = selected.get(spec.source_field)
        if value is None and not spec.required:
            continue
        fragment[section][field_name] = value
        records.append(_record(spec, value))
    return fragment, records


def _build_cancelled_document(
    payload: dict[str, Any],
    *,
    race_no: int | None = None,
    race_date: str | None = None,
    meet: int | str | None = None,
) -> tuple[dict[str, Any], list[SourceMappedRecord]]:
    rows = KRAResponseAdapter.select_matching_race_items(
        payload,
        race_no=race_no or 0,
        race_date=race_date,
        meet=meet,
    )
    if race_no is None:
        rows = KRAResponseAdapter.extract_items(payload)

    converted_rows = [convert_api_to_internal(row) for row in rows]
    spec = _specs_for("API9_1")[0]
    return {
        "cancelled_horses": converted_rows,
    }, [_record(spec, converted_rows)]


def _build_detail_document(
    source_api: str,
    payload: dict[str, Any],
    *,
    race_no: int | None = None,
    race_date: str | None = None,
    meet: int | str | None = None,
) -> tuple[dict[str, Any], list[SourceMappedRecord]]:
    del race_no, race_date, meet
    spec = _specs_for(source_api)[0]
    items = KRAResponseAdapter.extract_items(payload)
    if not items:
        single = KRAResponseAdapter.extract_single_item(payload)
        items = [single] if isinstance(single, dict) else []

    join_rows: list[dict[str, Any]] = []
    records: list[SourceMappedRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        value = convert_api_to_internal(item)
        join_value = _extract_join_value(item, spec.join_key)
        row = {
            "join_key": spec.join_key,
            "join_value": join_value,
            "schema_path": spec.schema_path,
            "value": value,
        }
        join_rows.append(row)
        records.append(_record(spec, value, join_value=join_value))
    return {"join_rows": join_rows}, records


def _specs_for(source_api: str) -> tuple[FieldMappingSpec, ...]:
    return tuple(
        spec for spec in SOURCE_FIELD_MAPPINGS if spec.source_api == source_api
    )


def _record(
    spec: FieldMappingSpec,
    value: Any,
    *,
    join_value: str | int | None = None,
) -> SourceMappedRecord:
    return SourceMappedRecord(
        source_api=spec.source_api,
        source_field=spec.source_field,
        schema_path=spec.schema_path,
        value=value,
        required=spec.required,
        join_key=spec.join_key,
        join_value=join_value,
    )


def _select_target_item(
    payload: dict[str, Any],
    *,
    race_no: int | None,
    race_date: str | None,
    meet: int | str | None,
) -> dict[str, Any] | None:
    if race_no is not None:
        selected = KRAResponseAdapter.select_matching_race_item(
            payload,
            race_no=race_no,
            race_date=race_date,
            meet=meet,
        )
        if selected is not None:
            return selected
    return KRAResponseAdapter.extract_single_item(payload)


def _merge_race_metadata(
    parsed: dict[str, Any],
    *,
    race_no: int | None,
    race_date: str | None,
    meet: int | str | None,
) -> dict[str, Any]:
    metadata = dict(parsed)
    if metadata.get("race_no") is None and race_no is not None:
        metadata["race_no"] = KRAResponseAdapter._safe_int_or_none(race_no)
    if metadata.get("race_date") is None and race_date is not None:
        metadata["race_date"] = KRAResponseAdapter._normalize_race_date(race_date)
    if metadata.get("meet") is None and meet is not None:
        metadata["meet"] = KRAResponseAdapter._normalize_meet(meet)
    return {key: value for key, value in metadata.items() if value is not None}


def _extract_join_value(item: dict[str, Any], join_key: str | None) -> str | int | None:
    if join_key == "hrName":
        value = (
            item.get("hrName")
            or item.get("hrnm")
            or item.get("hr_name")
            or item.get("hr_nm")
        )
        return KRAResponseAdapter._normalize_string(value)
    if join_key == "chulNo":
        value = item.get("chulNo") or item.get("chul_no")
        return KRAResponseAdapter._safe_int_or_none(value)
    if join_key == "rcNo":
        value = item.get("rcNo") or item.get("race_no")
        return KRAResponseAdapter._safe_int_or_none(value)
    if join_key in {"hrNo", "jkNo", "trNo", "owNo"}:
        snake_key = join_key[:-2].lower() + "_no"
        value = item.get(join_key) or item.get(snake_key)
        return KRAResponseAdapter._normalize_identifier(value)
    return None


def _decode_bytes(payload: bytes) -> str:
    for encoding in ("utf-8", "euc-kr"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    return payload.decode("utf-8", errors="replace")


def _parse_xml_payload(text: str) -> dict[str, Any]:
    root = ET.fromstring(text)
    return {root.tag: _xml_element_to_value(root)}


def _xml_element_to_value(element: ET.Element) -> Any:
    children = list(element)
    if not children:
        return _coerce_xml_scalar(element.text)

    grouped: dict[str, Any] = {}
    for child in children:
        value = _xml_element_to_value(child)
        if child.tag in grouped:
            existing = grouped[child.tag]
            if not isinstance(existing, list):
                grouped[child.tag] = [existing, value]
            else:
                existing.append(value)
        else:
            grouped[child.tag] = value
    return grouped


def _coerce_xml_scalar(value: str | None) -> Any:
    if value is None:
        return None
    stripped = value.strip()
    if stripped == "":
        return None
    if len(stripped) > 1 and stripped.startswith("0") and stripped.isdigit():
        return stripped
    if stripped.isdigit() or (stripped.startswith("-") and stripped[1:].isdigit()):
        try:
            return int(stripped)
        except ValueError:  # pragma: no cover - defensive guard
            return stripped
    try:
        if "." in stripped:
            return float(stripped)
    except ValueError:
        return stripped
    return stripped


SourceBuilder = Callable[..., tuple[dict[str, Any], list[SourceMappedRecord]]]


_SOURCE_BUILDERS: dict[str, SourceBuilder] = {
    "API214_1": _build_api214_document,
    "API72_2": lambda payload, **kwargs: _build_race_level_document(
        "API72_2", payload, **kwargs
    ),
    "API189_1": lambda payload, **kwargs: _build_race_level_document(
        "API189_1", payload, **kwargs
    ),
    "API9_1": _build_cancelled_document,
    "API8_2": lambda payload, **kwargs: _build_detail_document(
        "API8_2", payload, **kwargs
    ),
    "API12_1": lambda payload, **kwargs: _build_detail_document(
        "API12_1", payload, **kwargs
    ),
    "API19_1": lambda payload, **kwargs: _build_detail_document(
        "API19_1", payload, **kwargs
    ),
    "API11_1": lambda payload, **kwargs: _build_detail_document(
        "API11_1", payload, **kwargs
    ),
    "API14_1": lambda payload, **kwargs: _build_detail_document(
        "API14_1", payload, **kwargs
    ),
    "API329": lambda payload, **kwargs: _build_detail_document(
        "API329", payload, **kwargs
    ),
}
