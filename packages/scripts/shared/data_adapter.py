"""
DB 데이터 → 평가 스크립트 호환 포맷 변환 어댑터

DB basic_data 구조:
  race_info: {response: {body: {items: {item: [camelCase 기본 데이터]}}}}
  horses: [{chul_no, hr_name, ..., hrDetail: {snake_case}, jkDetail, trDetail}]

평가 스크립트 기대 포맷:
  {response: {body: {items: {item: [camelCase + hrDetail/jkDetail/trDetail(camelCase)]}}}}
"""

import re
from typing import Any

from shared.read_contract import RaceSnapshot

ENTRY_RESOLUTION_AUDIT_VERSION = "prerace-entry-resolution-v1"
_DETAIL_KEYS = (
    "hrDetail",
    "jkDetail",
    "trDetail",
    "jkStats",
    "owDetail",
    "training",
)
_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "chul_no": ("chulNo", "chul_no", "horse_no"),
    "hr_no": ("hrNo", "hr_no"),
    "hr_name": ("hrName", "hr_name", "horse_name"),
    "jk_no": ("jkNo", "jk_no"),
    "jk_name": ("jkName", "jk_name"),
    "tr_no": ("trNo", "tr_no"),
    "tr_name": ("trName", "tr_name"),
    "ow_no": ("owNo", "ow_no"),
    "ow_name": ("owName", "ow_name"),
    "age": ("age",),
    "sex": ("sex", "gender"),
    "name": ("name", "country"),
    "rank": ("rank", "class_rank"),
    "rating": ("rating",),
    "wg_budam": ("wgBudam", "wg_budam", "burden_weight"),
    "wg_budam_bigo": ("wgBudamBigo", "wg_budam_bigo"),
    "wg_hr": ("wgHr", "wg_hr"),
    "win_odds": ("winOdds", "win_odds"),
    "plc_odds": ("plcOdds", "plc_odds"),
    "ilsu": ("ilsu",),
    "hr_tool": ("hrTool", "hr_tool"),
}
_IDENTIFIER_FIELDS = ("hr_no", "jk_no", "tr_no", "ow_no")
_COMPLETENESS_FIELDS = (
    "hr_no",
    "hr_name",
    "jk_no",
    "jk_name",
    "tr_no",
    "tr_name",
    "ow_no",
    "ow_name",
    "age",
    "sex",
    "name",
    "rank",
    "rating",
    "wg_budam",
    "wg_budam_bigo",
    "wg_hr",
    "win_odds",
    "plc_odds",
    "ilsu",
    "hr_tool",
)


def _snake_to_camel(name: str) -> str:
    """snake_case → camelCase 변환"""
    components = name.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def _convert_dict_keys_to_camel(d: dict[str, Any]) -> dict[str, Any]:
    """dict의 모든 키를 snake_case → camelCase로 변환"""
    result = {}
    for key, value in d.items():
        camel_key = _snake_to_camel(key)
        if isinstance(value, dict):
            result[camel_key] = _convert_dict_keys_to_camel(value)
        elif isinstance(value, list):
            result[camel_key] = [
                _convert_dict_keys_to_camel(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[camel_key] = value
    return result


def _extract_basic_data(source: dict | RaceSnapshot | None) -> dict | None:
    if source is None:
        return None
    if isinstance(source, RaceSnapshot):
        return source.basic_data
    return source


def _normalize_identifier(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return re.sub(r"\.0+$", "", text)


def _normalize_chul_no(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _first_present_value(source: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    for alias in aliases:
        if alias in source:
            return source[alias]
    return None


def _canonical_value(source: dict[str, Any], field: str) -> Any:
    raw = _first_present_value(source, _FIELD_ALIASES[field])
    if field == "chul_no":
        return _normalize_chul_no(raw)
    if field in _IDENTIFIER_FIELDS:
        return _normalize_identifier(raw)
    if isinstance(raw, str):
        stripped = raw.strip()
        return stripped or None
    return raw


def _has_meaningful_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, dict):
        return bool(value)
    if isinstance(value, list):
        return bool(value)
    return True


def _entry_completeness_score(source: dict[str, Any]) -> int:
    score = sum(
        1
        for field in _COMPLETENESS_FIELDS
        if _has_meaningful_value(_canonical_value(source, field))
    )
    score += sum(
        1
        for detail_key in _DETAIL_KEYS
        if isinstance(source.get(detail_key), dict) and source.get(detail_key)
    )
    return score


def _count_identifier_matches(
    source: dict[str, Any], anchor_identifiers: dict[str, str | None]
) -> int:
    return sum(
        1
        for field, anchor in anchor_identifiers.items()
        if anchor is not None and _canonical_value(source, field) == anchor
    )


def _collect_identifier_variants(
    source_records: list[dict[str, Any]], *, source_label: str, chul_no: int
) -> list[dict[str, Any]]:
    inconsistencies: list[dict[str, Any]] = []
    for field in _IDENTIFIER_FIELDS:
        values = sorted(
            {
                value
                for record in source_records
                if (value := _canonical_value(record, field)) is not None
            }
        )
        if len(values) > 1:
            inconsistencies.append(
                {
                    "scope": "within_source",
                    "source": source_label,
                    "chul_no": chul_no,
                    "field": field,
                    "values": values,
                }
            )
    return inconsistencies


def _select_preferred_record(
    source_records: list[dict[str, Any]],
    *,
    anchor_identifiers: dict[str, str | None] | None = None,
) -> tuple[int, dict[str, Any]]:
    identifiers = anchor_identifiers or {}
    best_index = max(
        range(len(source_records)),
        key=lambda index: (
            _count_identifier_matches(source_records[index], identifiers),
            _entry_completeness_score(source_records[index]),
            -index,
        ),
    )
    return best_index, source_records[best_index]


def _detail_payload_from_horse_row(horse_row: dict[str, Any]) -> dict[str, Any]:
    details: dict[str, Any] = {}
    for detail_key in _DETAIL_KEYS:
        if detail_key in horse_row and horse_row[detail_key]:
            details[detail_key] = _convert_dict_keys_to_camel(horse_row[detail_key])
    return details


def _build_entry_resolution(
    items: list[dict[str, Any]], horses: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    items_by_chul_no: dict[int, list[dict[str, Any]]] = {}
    horses_by_chul_no: dict[int, list[dict[str, Any]]] = {}
    ordered_chul_nos: list[int] = []

    for item in items:
        chul_no = _canonical_value(item, "chul_no")
        if chul_no is None:
            continue
        if chul_no not in items_by_chul_no:
            items_by_chul_no[chul_no] = []
            ordered_chul_nos.append(chul_no)
        items_by_chul_no[chul_no].append(item)

    for horse in horses:
        chul_no = _canonical_value(horse, "chul_no")
        if chul_no is None:
            continue
        horses_by_chul_no.setdefault(chul_no, []).append(horse)

    selected_items: dict[int, dict[str, Any]] = {}
    audit: dict[str, Any] = {
        "audit_version": ENTRY_RESOLUTION_AUDIT_VERSION,
        "selected_record_rule": (
            "prefer identifier-consistent record, then more populated fields, "
            "then lower source index"
        ),
        "duplicate_chul_no_records": [],
        "identifier_inconsistencies": [],
        "orphan_horse_rows": [],
    }

    for chul_no in ordered_chul_nos:
        raw_candidates = items_by_chul_no[chul_no]
        horse_candidates = horses_by_chul_no.get(chul_no, [])

        selected_item_index, selected_item = _select_preferred_record(raw_candidates)
        selected_items[chul_no] = selected_item

        if len(raw_candidates) > 1:
            audit["duplicate_chul_no_records"].append(
                {
                    "source": "race_info_items",
                    "chul_no": chul_no,
                    "candidate_count": len(raw_candidates),
                    "selected_index": selected_item_index,
                    "selected_identifiers": {
                        field: _canonical_value(selected_item, field)
                        for field in _IDENTIFIER_FIELDS
                    },
                }
            )
            audit["identifier_inconsistencies"].extend(
                _collect_identifier_variants(
                    raw_candidates,
                    source_label="race_info_items",
                    chul_no=chul_no,
                )
            )

        if len(horse_candidates) > 1:
            selected_horse_index, selected_horse = _select_preferred_record(
                horse_candidates,
                anchor_identifiers={
                    field: _canonical_value(selected_item, field)
                    for field in _IDENTIFIER_FIELDS
                },
            )
            audit["duplicate_chul_no_records"].append(
                {
                    "source": "basic_data.horses",
                    "chul_no": chul_no,
                    "candidate_count": len(horse_candidates),
                    "selected_index": selected_horse_index,
                    "selected_identifiers": {
                        field: _canonical_value(selected_horse, field)
                        for field in _IDENTIFIER_FIELDS
                    },
                }
            )
            audit["identifier_inconsistencies"].extend(
                _collect_identifier_variants(
                    horse_candidates,
                    source_label="basic_data.horses",
                    chul_no=chul_no,
                )
            )
        elif len(horse_candidates) == 1:
            selected_horse = horse_candidates[0]
        else:
            selected_horse = None

        if selected_horse is not None:
            for field in _IDENTIFIER_FIELDS:
                item_value = _canonical_value(selected_item, field)
                horse_value = _canonical_value(selected_horse, field)
                if (
                    item_value is not None
                    and horse_value is not None
                    and item_value != horse_value
                ):
                    audit["identifier_inconsistencies"].append(
                        {
                            "scope": "between_sources",
                            "source": "race_info_items_vs_basic_data.horses",
                            "chul_no": chul_no,
                            "field": field,
                            "race_info_value": item_value,
                            "horse_row_value": horse_value,
                        }
                    )

    orphan_chul_nos = sorted(set(horses_by_chul_no) - set(items_by_chul_no))
    for chul_no in orphan_chul_nos:
        audit["orphan_horse_rows"].append(
            {
                "chul_no": chul_no,
                "candidate_count": len(horses_by_chul_no[chul_no]),
            }
        )

    resolved_items: list[dict[str, Any]] = []
    for item in items:
        chul_no = _canonical_value(item, "chul_no")
        if chul_no is None:
            resolved_items.append(item)
            continue

        selected_item = selected_items.get(chul_no)
        if selected_item is None or item is not selected_item:
            continue

        merged_item = dict(selected_item)
        horse_candidates = horses_by_chul_no.get(chul_no, [])
        if horse_candidates:
            _, selected_horse = _select_preferred_record(
                horse_candidates,
                anchor_identifiers={
                    field: _canonical_value(selected_item, field)
                    for field in _IDENTIFIER_FIELDS
                },
            )
            merged_item.update(_detail_payload_from_horse_row(selected_horse))
        resolved_items.append(merged_item)

    audit["duplicate_chul_no_group_count"] = len(audit["duplicate_chul_no_records"])
    audit["identifier_inconsistency_count"] = len(audit["identifier_inconsistencies"])
    audit["orphan_horse_row_count"] = len(audit["orphan_horse_rows"])
    return resolved_items, audit


def convert_snapshot_to_enriched_format(
    snapshot: dict | RaceSnapshot | None,
    *,
    include_resolution_audit: bool = False,
) -> dict | None:
    """공통 read DTO 또는 raw basic_data를 평가 스크립트 포맷으로 변환

    Args:
        snapshot: `RaceSnapshot` 또는 raw `basic_data` dict

    Returns:
        {response: {body: {items: {item: [...]}}}} 형태 또는 None
    """
    basic_data = _extract_basic_data(snapshot)
    if not basic_data:
        return None

    race_info = basic_data.get("race_info")
    horses = basic_data.get("horses", [])

    if not race_info:
        return None

    # race_info에서 원본 camelCase items 추출
    try:
        items = race_info["response"]["body"]["items"]["item"]
        if not isinstance(items, list):
            items = [items]
    except (KeyError, TypeError):
        return None

    if not items:
        return None

    resolved_items, resolution_audit = _build_entry_resolution(items, horses)

    # 경주 레벨 메타데이터 (신규 API)
    race_meta: dict[str, Any] = {}
    for meta_key in ("race_plan", "track", "cancelled_horses"):
        if meta_key in basic_data and basic_data[meta_key]:
            race_meta[_snake_to_camel(meta_key)] = basic_data[meta_key]

    # 각 camelCase item에 detail + race_meta 병합
    merged_items = []
    for item in resolved_items:
        merged = {**item, **race_meta}
        merged_items.append(merged)

    body: dict[str, Any] = {"items": {"item": merged_items}}
    if include_resolution_audit:
        body["entryResolutionAudit"] = resolution_audit

    return {"response": {"body": body}}


def convert_basic_data_to_enriched_format(
    basic_data: dict | RaceSnapshot,
    *,
    include_resolution_audit: bool = False,
) -> dict | None:
    """Backward-compatible wrapper for legacy callers."""
    return convert_snapshot_to_enriched_format(
        basic_data,
        include_resolution_audit=include_resolution_audit,
    )
