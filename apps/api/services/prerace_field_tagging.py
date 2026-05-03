"""Source-field availability tagging for prereace collection payloads."""

from __future__ import annotations

import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS_ROOT = _PROJECT_ROOT / "packages" / "scripts"
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

from shared.prerace_field_metadata_schema import (  # noqa: E402
    FIELD_METADATA_RULES,
    METADATA_SCHEMA_VERSION,
    FieldMetadataRule,
    match_field_metadata_rule,
)
from shared.prerace_field_policy import (  # noqa: E402
    ALLOW,
    ALLOW_SNAPSHOT_ONLY,
    ALLOW_STORED_ONLY,
    BLOCK,
    HOLD,
    LABEL_ONLY,
    META_ONLY,
    resolve_train_inference_flag,
)
from shared.prerace_source_schema import SOURCE_FIELD_MAPPINGS  # noqa: E402

SOURCE_FIELD_TAGS_VERSION = "source-field-tags-v1"

_RECORD_TAG_ORDER: tuple[str, ...] = (
    "post_entry_only",
    "hold",
    "snapshot_only",
    "stored_only",
    "pre_entry_allowed",
    "metadata_only",
)
_IGNORED_CANONICAL_HORSE_FIELDS = frozenset(
    {"weight", "country", "normalization_flags"}
)


@lru_cache(maxsize=1)
def _schema_mapping_index() -> dict[str, Any]:
    return {spec.schema_path: spec for spec in SOURCE_FIELD_MAPPINGS}


@lru_cache(maxsize=1)
def _source_mapping_index() -> dict[tuple[str, str], Any]:
    return {
        (spec.source_api, spec.source_field): spec for spec in SOURCE_FIELD_MAPPINGS
    }


def build_source_field_tags(payload: dict[str, Any]) -> dict[str, Any]:
    """Annotate prereace payload records with field availability tags."""

    records = {
        "race_info_items": _annotate_race_info_items(payload.get("race_info")),
        "race_plan": _annotate_simple_record(
            source_api="API72_2",
            record_key="race_plan",
            container=payload.get("race_plan"),
            prefix="race_plan",
        ),
        "track": _annotate_simple_record(
            source_api="API189_1",
            record_key="track",
            container=payload.get("track"),
            prefix="track",
        ),
        "cancelled_horses": _annotate_cancelled_rows(payload.get("cancelled_horses")),
        "horses": _annotate_horse_rows(payload.get("horses")),
    }
    return {
        "tag_schema_version": SOURCE_FIELD_TAGS_VERSION,
        "metadata_schema_version": METADATA_SCHEMA_VERSION,
        "summary": _build_summary(records),
        "records": records,
    }


def _annotate_race_info_items(race_info: Any) -> list[dict[str, Any]]:
    if not isinstance(race_info, dict):
        return []
    try:
        items = race_info["response"]["body"]["items"]["item"]
    except (KeyError, TypeError):
        return []

    if isinstance(items, dict):
        normalized_items = [items]
    elif isinstance(items, list):
        normalized_items = [item for item in items if isinstance(item, dict)]
    else:
        return []

    records: list[dict[str, Any]] = []
    for index, item in enumerate(normalized_items, start=1):
        field_tags: dict[str, dict[str, Any]] = {}
        for source_field in sorted(item):
            spec = _source_mapping_index().get(("API214_1", source_field))
            schema_path = spec.schema_path if spec is not None else None
            field_tags[source_field] = _classify_field(
                source_api="API214_1",
                source_field=source_field,
                schema_path=schema_path,
                fallback_path=source_field,
            )

        record_key = item.get("chulNo") or item.get("hrNo") or index
        records.append(
            _build_record_annotation(
                source_api="API214_1",
                record_key=str(record_key),
                field_tags=field_tags,
            )
        )
    return records


def _annotate_simple_record(
    *,
    source_api: str,
    record_key: str,
    container: Any,
    prefix: str,
) -> dict[str, Any]:
    if not isinstance(container, dict):
        return _build_record_annotation(
            source_api=source_api,
            record_key=record_key,
            field_tags={},
        )

    field_tags: dict[str, dict[str, Any]] = {}
    for key in sorted(container):
        schema_path = f"{prefix}.{key}"
        spec = _schema_mapping_index().get(schema_path)
        source_field = spec.source_field if spec is not None else key
        field_tags[key] = _classify_field(
            source_api=source_api,
            source_field=source_field,
            schema_path=schema_path,
            fallback_path=schema_path,
        )

    return _build_record_annotation(
        source_api=source_api,
        record_key=record_key,
        field_tags=field_tags,
    )


def _annotate_cancelled_rows(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []

    row_classification = _classify_field(
        source_api="API9_1",
        source_field="item[]",
        schema_path="cancelled_horses[]",
        fallback_path="cancelled_horses",
    )

    records: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        record_key = row.get("chul_no") or row.get("chulNo") or index
        records.append(
            _build_record_annotation(
                source_api="API9_1",
                record_key=str(record_key),
                field_tags={"cancelled_horses": row_classification},
            )
        )
    return records


def _annotate_horse_rows(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []

    records: list[dict[str, Any]] = []
    for index, horse in enumerate(rows, start=1):
        if not isinstance(horse, dict):
            continue

        field_tags: dict[str, dict[str, Any]] = {}
        for key in sorted(horse):
            if key in _IGNORED_CANONICAL_HORSE_FIELDS:
                continue
            schema_path = f"horses[].{key}"
            spec = _schema_mapping_index().get(schema_path)
            if spec is None:
                continue
            field_tags[key] = _classify_field(
                source_api=spec.source_api,
                source_field=spec.source_field,
                schema_path=schema_path,
                fallback_path=schema_path,
            )

        record_key = horse.get("chul_no") or horse.get("hr_no") or index
        records.append(
            _build_record_annotation(
                source_api="MULTI_SOURCE",
                record_key=str(record_key),
                field_tags=field_tags,
            )
        )
    return records


def _classify_field(
    *,
    source_api: str,
    source_field: str,
    schema_path: str | None,
    fallback_path: str,
) -> dict[str, Any]:
    rule = _match_rule_by_source(source_api=source_api, source_field=source_field)
    if rule is None and schema_path is not None:
        rule = match_field_metadata_rule(schema_path)

    if rule is not None:
        flag = rule.train_inference_flag
        availability_stage = rule.availability_stage
        operational_status = rule.operational_status
        field_path = rule.field_path
        metadata_rule_found = True
    else:
        field_path = schema_path or fallback_path
        if schema_path is not None:
            flag = ALLOW
            availability_stage = "L0"
            operational_status = _default_operational_status(flag)
        else:
            flag = resolve_train_inference_flag(fallback_path)
            availability_stage = "L+1" if flag in {BLOCK, LABEL_ONLY} else "L0"
            operational_status = _default_operational_status(flag)
        metadata_rule_found = False

    return {
        "tag": _tag_for_flag(flag),
        "train_inference_flag": flag,
        "availability_stage": availability_stage,
        "operational_status": operational_status,
        "field_path": field_path,
        "source_api": source_api,
        "source_field": source_field,
        "metadata_rule_found": metadata_rule_found,
    }


def _match_rule_by_source(
    *, source_api: str, source_field: str
) -> FieldMetadataRule | None:
    for rule in FIELD_METADATA_RULES:
        if source_field != rule.source_field:
            continue
        source_apis = tuple(part.strip() for part in rule.source_api.split("|"))
        if source_api in source_apis:
            return rule
    return None


def _build_record_annotation(
    *,
    source_api: str,
    record_key: str,
    field_tags: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    grouped: dict[str, list[str]] = {tag: [] for tag in _RECORD_TAG_ORDER}
    for field_name, info in field_tags.items():
        grouped.setdefault(info["tag"], []).append(field_name)

    return {
        "source_api": source_api,
        "record_key": record_key,
        "field_tags": field_tags,
        "post_entry_only_fields": sorted(grouped["post_entry_only"]),
        "hold_fields": sorted(grouped["hold"]),
        "snapshot_only_fields": sorted(grouped["snapshot_only"]),
        "stored_only_fields": sorted(grouped["stored_only"]),
        "pre_entry_allowed_fields": sorted(grouped["pre_entry_allowed"]),
        "metadata_only_fields": sorted(grouped["metadata_only"]),
        "field_count": len(field_tags),
    }


def _build_summary(records: dict[str, Any]) -> dict[str, Any]:
    counter: Counter[str] = Counter()
    record_count = 0
    for group in records.values():
        if isinstance(group, list):
            iterable = group
        elif isinstance(group, dict):
            iterable = [group]
        else:
            iterable = []

        for record in iterable:
            if not isinstance(record, dict):
                continue
            record_count += 1
            for info in record.get("field_tags", {}).values():
                if isinstance(info, dict):
                    counter.update([info.get("tag", "unknown")])

    return {
        "record_count": record_count,
        "tag_counts": {tag: counter.get(tag, 0) for tag in _RECORD_TAG_ORDER},
        "post_entry_field_count": counter.get("post_entry_only", 0),
        "hold_field_count": counter.get("hold", 0),
    }


def _tag_for_flag(flag: str) -> str:
    mapping = {
        ALLOW: "pre_entry_allowed",
        ALLOW_SNAPSHOT_ONLY: "snapshot_only",
        ALLOW_STORED_ONLY: "stored_only",
        HOLD: "hold",
        BLOCK: "post_entry_only",
        LABEL_ONLY: "post_entry_only",
        META_ONLY: "metadata_only",
    }
    return mapping.get(flag, "pre_entry_allowed")


def _default_operational_status(flag: str) -> str:
    defaults = {
        ALLOW: "허용",
        ALLOW_SNAPSHOT_ONLY: "조건부 허용",
        ALLOW_STORED_ONLY: "조건부 허용",
        HOLD: "보류",
        BLOCK: "금지",
        LABEL_ONLY: "라벨 전용",
        META_ONLY: "메타 전용",
    }
    return defaults.get(flag, "허용")
