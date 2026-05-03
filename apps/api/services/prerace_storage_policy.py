"""Storage policy helpers for prereace payload persistence."""

from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS_ROOT = _PROJECT_ROOT / "packages" / "scripts"
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

from shared.prerace_field_metadata_schema import (  # noqa: E402
    METADATA_SCHEMA_VERSION,
    FieldMetadataRule,
    match_field_metadata_rule,
    normalize_field_path,
)
from shared.prerace_field_policy import BLOCK, LABEL_ONLY, META_ONLY  # noqa: E402

from services.prerace_field_tagging import build_source_field_tags  # noqa: E402

STORAGE_POLICY_VERSION = "prerace-storage-policy-v1"

_KEEP = "keep"
_KEEP_AND_SHADOW = "keep_and_shadow"
_SHADOW_ONLY = "shadow_only"

_TAG_ACTIONS: dict[str, str] = {
    "pre_entry_allowed": _KEEP,
    "snapshot_only": _KEEP,
    "stored_only": _KEEP,
    "hold": _KEEP_AND_SHADOW,
    "post_entry_only": _SHADOW_ONLY,
    "metadata_only": _SHADOW_ONLY,
}
_BLOCKED_STORAGE_FLAGS = frozenset({BLOCK, LABEL_ONLY, META_ONLY})
_REQUIRED_RULE_METADATA_ATTRS: tuple[str, ...] = (
    "field_path",
    "field_role",
    "source_api",
    "source_field",
    "availability_stage",
    "publication_basis",
    "publication_basis_refs",
    "exception_rule",
    "validation_status",
    "validation_evidence",
    "operational_status",
    "train_inference_flag",
)
_SKIP_DIRECT_CHILD_AUDIT_TOP_LEVEL_FIELDS = frozenset(
    {"race_info", "race_plan", "track", "horses", "cancelled_horses", "failed_horses"}
)


def split_prerace_payload_for_storage(
    payload: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Split a normalized prereace payload into basic_data and shadow raw_data."""

    if not payload:
        return {}, None

    working = deepcopy(payload)
    source_field_tags = working.get("source_field_tags")
    if not isinstance(source_field_tags, dict):
        source_field_tags = build_source_field_tags(working)

    basic_payload = deepcopy(working)
    basic_payload.pop("source_field_tags", None)
    join_timing_audit = basic_payload.pop("join_timing_audit", None)
    snapshot_meta = basic_payload.pop("snapshot_meta", None)

    shadow_sections: dict[str, Any] = {}
    blocked_from_basic_count = 1 if "source_field_tags" in working else 0
    copied_to_shadow_count = 0

    blocked_race_info, copied_race_info = _filter_race_info_items(
        basic_payload,
        source_field_tags,
        shadow_sections,
    )
    blocked_from_basic_count += blocked_race_info
    copied_to_shadow_count += copied_race_info

    for section_name in ("race_plan", "track"):
        blocked, copied = _filter_dict_section(
            basic_payload,
            source_field_tags,
            shadow_sections,
            section_name=section_name,
        )
        blocked_from_basic_count += blocked
        copied_to_shadow_count += copied

    blocked_horses, copied_horses = _filter_horse_rows(
        basic_payload,
        source_field_tags,
        shadow_sections,
    )
    blocked_from_basic_count += blocked_horses
    copied_to_shadow_count += copied_horses

    blocked_cancelled, copied_cancelled = _filter_cancelled_rows(
        basic_payload,
        source_field_tags,
        shadow_sections,
    )
    blocked_from_basic_count += blocked_cancelled
    copied_to_shadow_count += copied_cancelled

    raw_data = {
        "storage_policy_version": STORAGE_POLICY_VERSION,
        "source_field_tags": source_field_tags,
        "storage_summary": {
            "blocked_from_basic_count": blocked_from_basic_count,
            "copied_to_shadow_count": copied_to_shadow_count,
        },
    }
    if shadow_sections:
        raw_data["tagged_field_shadow"] = shadow_sections
    if isinstance(join_timing_audit, dict):
        raw_data["join_timing_audit"] = join_timing_audit
    if isinstance(snapshot_meta, dict):
        raw_data["snapshot_meta"] = snapshot_meta

    validate_prerace_storage_result(basic_payload, raw_data)
    return basic_payload, raw_data


def validate_prerace_storage_result(
    basic_payload: dict[str, Any],
    raw_data: dict[str, Any] | None,
) -> None:
    """Raise when the persisted prereace payload violates storage audit rules."""

    issues = audit_prerace_storage_result(basic_payload, raw_data)
    if issues:
        raise ValueError("Invalid prereace storage result: " + "; ".join(issues))


def audit_prerace_storage_result(
    basic_payload: dict[str, Any],
    raw_data: dict[str, Any] | None,
) -> list[str]:
    """Inspect persisted prereace payload for metadata coverage and blocked-field leaks."""

    issues: list[str] = []

    if not isinstance(raw_data, dict):
        return ["raw_data must be an object for prereace storage audit"]

    source_field_tags = raw_data.get("source_field_tags")
    if not isinstance(source_field_tags, dict):
        return ["raw_data.source_field_tags must be an object"]

    if source_field_tags.get("metadata_schema_version") != METADATA_SCHEMA_VERSION:
        issues.append(
            "raw_data.source_field_tags.metadata_schema_version must match prerace metadata schema"
        )

    if not isinstance(source_field_tags.get("records"), dict):
        issues.append("raw_data.source_field_tags.records must be an object")
        return issues

    for key, value in basic_payload.items():
        if key in _SKIP_DIRECT_CHILD_AUDIT_TOP_LEVEL_FIELDS:
            continue
        _audit_canonical_path(value, key, issues)

    _audit_canonical_path(
        basic_payload.get("failed_horses", []), "failed_horses[]", issues
    )
    _audit_race_info_items(
        basic_payload.get("race_info"),
        source_field_tags.get("records", {}).get("race_info_items"),
        issues,
    )
    _audit_flat_tagged_section(
        basic_payload.get("race_plan"),
        source_field_tags.get("records", {}).get("race_plan"),
        section_name="race_plan",
        issues=issues,
    )
    _audit_flat_tagged_section(
        basic_payload.get("track"),
        source_field_tags.get("records", {}).get("track"),
        section_name="track",
        issues=issues,
    )
    _audit_horse_rows(
        basic_payload.get("horses"),
        source_field_tags.get("records", {}).get("horses"),
        issues,
    )
    _audit_cancelled_rows(
        basic_payload.get("cancelled_horses"),
        source_field_tags.get("records", {}).get("cancelled_horses"),
        issues,
    )

    return issues


def _filter_race_info_items(
    basic_payload: dict[str, Any],
    source_field_tags: dict[str, Any],
    shadow_sections: dict[str, Any],
) -> tuple[int, int]:
    try:
        items = basic_payload["race_info"]["response"]["body"]["items"]["item"]
    except (KeyError, TypeError):
        return 0, 0

    if isinstance(items, dict):
        normalized_items = [items]
        singleton = True
    elif isinstance(items, list):
        normalized_items = items
        singleton = False
    else:
        return 0, 0

    tag_records = source_field_tags.get("records", {}).get("race_info_items", [])
    shadow_items: list[dict[str, Any]] = []
    blocked_count = 0
    copied_count = 0

    filtered_items: list[dict[str, Any]] = []
    for index, item in enumerate(normalized_items):
        if not isinstance(item, dict):
            filtered_items.append(item)
            continue
        tags = {}
        record_key = str(index + 1)
        if index < len(tag_records) and isinstance(tag_records[index], dict):
            tags = tag_records[index].get("field_tags", {})
            record_key = str(tag_records[index].get("record_key", record_key))

        filtered_item, shadow_item, blocked, copied = _partition_fields(item, tags)
        filtered_items.append(filtered_item)
        if shadow_item:
            shadow_items.append({"record_key": record_key, "fields": shadow_item})
        blocked_count += blocked
        copied_count += copied

    basic_payload["race_info"]["response"]["body"]["items"]["item"] = (
        filtered_items[0] if singleton and filtered_items else filtered_items
    )
    if shadow_items:
        shadow_sections["race_info_items"] = shadow_items
    return blocked_count, copied_count


def _filter_dict_section(
    basic_payload: dict[str, Any],
    source_field_tags: dict[str, Any],
    shadow_sections: dict[str, Any],
    *,
    section_name: str,
) -> tuple[int, int]:
    section = basic_payload.get(section_name)
    if not isinstance(section, dict):
        return 0, 0

    tag_record = source_field_tags.get("records", {}).get(section_name, {})
    if not isinstance(tag_record, dict):
        return 0, 0

    filtered, shadow, blocked, copied = _partition_fields(
        section,
        tag_record.get("field_tags", {}),
    )
    basic_payload[section_name] = filtered
    if shadow:
        shadow_sections[section_name] = shadow
    return blocked, copied


def _filter_horse_rows(
    basic_payload: dict[str, Any],
    source_field_tags: dict[str, Any],
    shadow_sections: dict[str, Any],
) -> tuple[int, int]:
    horses = basic_payload.get("horses")
    if not isinstance(horses, list):
        return 0, 0

    tag_records = source_field_tags.get("records", {}).get("horses", [])
    shadow_horses: list[dict[str, Any]] = []
    blocked_count = 0
    copied_count = 0

    filtered_horses: list[dict[str, Any]] = []
    for index, horse in enumerate(horses):
        if not isinstance(horse, dict):
            filtered_horses.append(horse)
            continue
        tags = {}
        record_key = str(index + 1)
        if index < len(tag_records) and isinstance(tag_records[index], dict):
            tags = tag_records[index].get("field_tags", {})
            record_key = str(tag_records[index].get("record_key", record_key))

        filtered_horse, shadow_horse, blocked, copied = _partition_fields(horse, tags)
        filtered_horses.append(filtered_horse)
        if shadow_horse:
            shadow_horses.append({"record_key": record_key, "fields": shadow_horse})
        blocked_count += blocked
        copied_count += copied

    basic_payload["horses"] = filtered_horses
    if shadow_horses:
        shadow_sections["horses"] = shadow_horses
    return blocked_count, copied_count


def _filter_cancelled_rows(
    basic_payload: dict[str, Any],
    source_field_tags: dict[str, Any],
    shadow_sections: dict[str, Any],
) -> tuple[int, int]:
    rows = basic_payload.get("cancelled_horses")
    if not isinstance(rows, list):
        return 0, 0

    tag_records = source_field_tags.get("records", {}).get("cancelled_horses", [])
    filtered_rows: list[dict[str, Any]] = []
    shadow_rows: list[dict[str, Any]] = []
    blocked_count = 0
    copied_count = 0

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            filtered_rows.append(row)
            continue

        tag = "pre_entry_allowed"
        record_key = str(index + 1)
        if index < len(tag_records) and isinstance(tag_records[index], dict):
            field_tags = tag_records[index].get("field_tags", {})
            tag = _resolve_tag(field_tags.get("cancelled_horses"))
            record_key = str(tag_records[index].get("record_key", record_key))

        action = _action_for_tag(tag)
        if action in {_KEEP, _KEEP_AND_SHADOW}:
            filtered_rows.append(deepcopy(row))
        if action in {_KEEP_AND_SHADOW, _SHADOW_ONLY}:
            shadow_rows.append({"record_key": record_key, "fields": deepcopy(row)})
        if action == _SHADOW_ONLY:
            blocked_count += 1
        if action == _KEEP_AND_SHADOW:
            copied_count += 1

    basic_payload["cancelled_horses"] = filtered_rows
    if shadow_rows:
        shadow_sections["cancelled_horses"] = shadow_rows
    return blocked_count, copied_count


def _partition_fields(
    record: dict[str, Any],
    field_tags: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], int, int]:
    filtered: dict[str, Any] = {}
    shadow: dict[str, Any] = {}
    blocked_count = 0
    copied_count = 0

    for field_name, value in record.items():
        tag = _resolve_tag(field_tags.get(field_name))
        action = _action_for_tag(tag)
        if action in {_KEEP, _KEEP_AND_SHADOW}:
            filtered[field_name] = deepcopy(value)
        if action in {_KEEP_AND_SHADOW, _SHADOW_ONLY}:
            shadow[field_name] = deepcopy(value)
        if action == _SHADOW_ONLY:
            blocked_count += 1
        if action == _KEEP_AND_SHADOW:
            copied_count += 1

    return filtered, shadow, blocked_count, copied_count


def _resolve_tag(field_info: Any) -> str:
    if isinstance(field_info, dict) and isinstance(field_info.get("tag"), str):
        return field_info["tag"]
    return "pre_entry_allowed"


def _action_for_tag(tag: str) -> str:
    if tag not in _TAG_ACTIONS:
        raise ValueError(f"unsupported storage tag: {tag}")
    return _TAG_ACTIONS[tag]


def _audit_canonical_path(node: Any, path: str, issues: list[str]) -> None:
    normalized_path = normalize_field_path(path)
    rule = match_field_metadata_rule(normalized_path)
    if rule is None:
        issues.append(f"{normalized_path} is missing field metadata")
        return

    _audit_rule_metadata(rule, normalized_path, issues)
    if normalized_path == "failed_horses[]":
        return

    if isinstance(node, dict):
        for key, value in node.items():
            _audit_canonical_path(value, f"{path}.{key}", issues)
        return

    if isinstance(node, list):
        if not node:
            return
        if any(isinstance(item, (dict, list)) for item in node):
            for index, item in enumerate(node):
                _audit_canonical_path(item, f"{path}[{index}]", issues)


def _audit_race_info_items(
    race_info: Any,
    tag_records: Any,
    issues: list[str],
) -> None:
    item_list = _extract_race_info_items(race_info)
    if item_list is None:
        issues.append(
            "race_info.response.body.items.item must exist in stored basic_data"
        )
        return

    if not isinstance(tag_records, list):
        issues.append("source_field_tags.records.race_info_items must be a list")
        return

    if len(tag_records) != len(item_list):
        issues.append(
            "source_field_tags.records.race_info_items count must match basic_data"
        )

    for index, item in enumerate(item_list):
        if not isinstance(item, dict):
            issues.append(
                f"race_info.response.body.items.item[{index}] must be an object"
            )
            continue

        tag_record = tag_records[index] if index < len(tag_records) else {}
        field_tags = (
            tag_record.get("field_tags", {}) if isinstance(tag_record, dict) else {}
        )
        for field_name in item:
            current_path = f"race_info.response.body.items.item[{index}].{field_name}"
            tag_info = field_tags.get(field_name)
            if tag_info is None:
                issues.append(
                    f"{normalize_field_path(current_path)} is missing source_field_tags metadata"
                )
                continue
            _audit_tag_info(tag_info, current_path, issues)


def _audit_flat_tagged_section(
    section: Any,
    tag_record: Any,
    *,
    section_name: str,
    issues: list[str],
) -> None:
    if not isinstance(section, dict):
        return

    field_tags = (
        tag_record.get("field_tags", {}) if isinstance(tag_record, dict) else {}
    )
    for field_name, value in section.items():
        current_path = f"{section_name}.{field_name}"
        tag_info = field_tags.get(field_name)
        if tag_info is None:
            issues.append(
                f"{normalize_field_path(current_path)} is missing source_field_tags metadata"
            )
            continue
        _audit_tag_info(tag_info, current_path, issues)
        if isinstance(value, dict):
            for nested_key, nested_value in value.items():
                _audit_canonical_path(
                    nested_value, f"{current_path}.{nested_key}", issues
                )


def _audit_horse_rows(rows: Any, tag_records: Any, issues: list[str]) -> None:
    if not isinstance(rows, list):
        return

    if not isinstance(tag_records, list):
        issues.append("source_field_tags.records.horses must be a list")
        return

    if len(tag_records) != len(rows):
        issues.append("source_field_tags.records.horses count must match basic_data")

    for index, horse in enumerate(rows):
        current_row_path = f"horses[{index}]"
        if not isinstance(horse, dict):
            issues.append(f"{current_row_path} must be an object")
            continue

        tag_record = tag_records[index] if index < len(tag_records) else {}
        field_tags = (
            tag_record.get("field_tags", {}) if isinstance(tag_record, dict) else {}
        )

        for field_name, value in horse.items():
            current_path = f"{current_row_path}.{field_name}"
            tag_info = field_tags.get(field_name)
            if tag_info is None:
                _audit_canonical_path(value, current_path, issues)
                continue

            _audit_tag_info(tag_info, current_path, issues)
            if isinstance(value, dict):
                for nested_key, nested_value in value.items():
                    _audit_canonical_path(
                        nested_value, f"{current_path}.{nested_key}", issues
                    )


def _audit_cancelled_rows(rows: Any, tag_records: Any, issues: list[str]) -> None:
    if not isinstance(rows, list):
        return

    if not rows:
        _audit_canonical_path(rows, "cancelled_horses[]", issues)
        return

    if not isinstance(tag_records, list):
        issues.append("source_field_tags.records.cancelled_horses must be a list")
        return

    if len(tag_records) != len(rows):
        issues.append(
            "source_field_tags.records.cancelled_horses count must match basic_data"
        )

    for index, row in enumerate(rows):
        current_path = f"cancelled_horses[{index}]"
        if not isinstance(row, dict):
            issues.append(f"{current_path} must be an object")
            continue

        tag_record = tag_records[index] if index < len(tag_records) else {}
        field_tags = (
            tag_record.get("field_tags", {}) if isinstance(tag_record, dict) else {}
        )
        tag_info = field_tags.get("cancelled_horses")
        if tag_info is None:
            issues.append(
                f"{normalize_field_path(current_path)} is missing source_field_tags metadata"
            )
            continue
        _audit_tag_info(tag_info, current_path, issues)


def _extract_race_info_items(race_info: Any) -> list[Any] | None:
    if not isinstance(race_info, dict):
        return None

    try:
        items = race_info["response"]["body"]["items"]["item"]
    except (KeyError, TypeError):
        return None

    if isinstance(items, list):
        return items
    if isinstance(items, dict):
        return [items]
    return None


def _audit_tag_info(tag_info: Any, current_path: str, issues: list[str]) -> None:
    normalized_path = normalize_field_path(current_path)
    if not isinstance(tag_info, dict):
        issues.append(f"{normalized_path} has invalid source_field_tags metadata")
        return

    required_tag_keys = (
        "field_path",
        "source_api",
        "source_field",
        "availability_stage",
        "operational_status",
        "train_inference_flag",
        "metadata_rule_found",
    )
    missing_keys = [key for key in required_tag_keys if key not in tag_info]
    if missing_keys:
        issues.append(
            f"{normalized_path} is missing source_field_tags keys: {', '.join(missing_keys)}"
        )
        return

    if not tag_info.get("metadata_rule_found"):
        issues.append(f"{normalized_path} is missing field metadata")
        return

    field_path = tag_info.get("field_path")
    rule = (
        match_field_metadata_rule(field_path) if isinstance(field_path, str) else None
    )
    if rule is None:
        issues.append(f"{normalized_path} is missing canonical field metadata")
        return

    if tag_info.get("train_inference_flag") != rule.train_inference_flag:
        issues.append(
            f"{normalized_path} source_field_tags flag does not match canonical metadata"
        )

    _audit_rule_metadata(rule, normalized_path, issues)


def _audit_rule_metadata(
    rule: FieldMetadataRule,
    normalized_path: str,
    issues: list[str],
) -> None:
    missing_attrs: list[str] = []
    for attr_name in _REQUIRED_RULE_METADATA_ATTRS:
        value = getattr(rule, attr_name)
        if isinstance(value, str) and not value:
            missing_attrs.append(attr_name)
        elif isinstance(value, tuple) and not value:
            missing_attrs.append(attr_name)

    if missing_attrs:
        issues.append(
            f"{normalized_path} missing required field metadata: {', '.join(missing_attrs)}"
        )

    if rule.train_inference_flag in _BLOCKED_STORAGE_FLAGS:
        issues.append(
            f"{normalized_path} includes blocked field with flag {rule.train_inference_flag}"
        )
