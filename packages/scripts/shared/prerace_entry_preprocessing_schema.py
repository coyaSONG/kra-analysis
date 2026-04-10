"""출전마 단위 전처리 규칙표 저장 계약."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

RULE_SCHEMA_VERSION = "prerace-entry-preprocessing-rules-v1"
CANONICAL_STORAGE_RELATIVE_PATH = Path(
    "data/contracts/prerace_entry_preprocessing_rules_v1.csv"
)
CANONICAL_STORAGE_FORMAT = "csv"
CANONICAL_STORAGE_ENCODING = "utf-8"
ROW_PRIMARY_KEY: tuple[str, ...] = ("field_path",)

FIELD_GROUPS: tuple[str, ...] = (
    "core_card",
    "optional_card",
    "derived",
    "detail_block",
)

PRIORITY_GRADES: tuple[str, ...] = (
    "P0",
    "P1",
    "P2",
)


@dataclass(frozen=True, slots=True)
class RuleColumnSpec:
    """전처리 규칙 CSV의 단일 컬럼 정의."""

    name: str
    required: bool
    description: str


COLUMN_SPECS: tuple[RuleColumnSpec, ...] = (
    RuleColumnSpec(
        name="rule_schema_version",
        required=True,
        description=(
            "규칙 행이 따르는 저장 계약 버전. 현재 값은 "
            "prerace-entry-preprocessing-rules-v1."
        ),
    ),
    RuleColumnSpec(
        name="field_path",
        required=True,
        description="표준 필드 카탈로그 기준 경로. 예: horses[].chul_no.",
    ),
    RuleColumnSpec(
        name="field_group",
        required=True,
        description="core_card/optional_card/derived/detail_block 중 하나.",
    ),
    RuleColumnSpec(
        name="source_aliases",
        required=True,
        description="허용 raw alias를 | 순서로 기록한다.",
    ),
    RuleColumnSpec(
        name="priority_grade",
        required=True,
        description="장애 등급. P0/P1/P2 중 하나.",
    ),
    RuleColumnSpec(
        name="allowed_range",
        required=True,
        description="허용 값 범위와 최소 형식 계약.",
    ),
    RuleColumnSpec(
        name="correction_priority",
        required=True,
        description="보정 시도 우선순위. 왼쪽에서 오른쪽으로 적용한다.",
    ),
    RuleColumnSpec(
        name="replacement_priority",
        required=True,
        description="결측 또는 sentinel 대체 우선순위. 왼쪽에서 오른쪽으로 적용한다.",
    ),
    RuleColumnSpec(
        name="exclusion_priority",
        required=True,
        description="제외 판단 우선순위. 가장 왼쪽이 가장 강한 조치다.",
    ),
    RuleColumnSpec(
        name="raw_preservation",
        required=True,
        description="원문 raw 값을 어떤 형태로 보존할지 고정한다.",
    ),
    RuleColumnSpec(
        name="normalized_output",
        required=True,
        description="정규화 후 downstream에 제공하는 값 형태.",
    ),
    RuleColumnSpec(
        name="generated_flags",
        required=True,
        description="전처리 단계에서 함께 남겨야 하는 품질 플래그.",
    ),
    RuleColumnSpec(
        name="notes",
        required=False,
        description="보충 설명 또는 운영 메모.",
    ),
)

REQUIRED_COLUMNS: tuple[str, ...] = tuple(
    column.name for column in COLUMN_SPECS if column.required
)
OPTIONAL_COLUMNS: tuple[str, ...] = tuple(
    column.name for column in COLUMN_SPECS if not column.required
)
ALL_COLUMNS: tuple[str, ...] = tuple(column.name for column in COLUMN_SPECS)


def csv_header() -> str:
    """정규 CSV 헤더 문자열을 반환한다."""

    return ",".join(ALL_COLUMNS)
