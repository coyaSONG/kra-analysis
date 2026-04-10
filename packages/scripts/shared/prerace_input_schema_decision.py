"""입력 스키마만으로 허용/금지/검토 필요를 판정하는 보수적 결정 규칙."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from shared.feature_source_timing_contract import AS_OF_REQUIREMENTS
from shared.prerace_field_metadata_schema import (
    AVAILABILITY_STAGES,
    TRAIN_INFERENCE_FLAGS,
)
from shared.prerace_field_validation_metaschema import (
    ALLOWED_DATA_CATEGORIES,
    CONSUMER_SCOPES,
    EXCEPTION_RULE_TYPES,
    IDENTIFIER_KINDS,
    TIME_BOUNDARY_RULES,
    TIME_REFERENCE_TYPES,
)

INPUT_SCHEMA_DECISION_VERSION = "prerace-input-schema-decision-v1"

SCHEMA_DECISIONS: tuple[str, ...] = (
    "ALLOW",
    "BLOCK",
    "REVIEW_REQUIRED",
)

DECISION_PRIORITY_ORDER: tuple[str, ...] = (
    "BLOCK",
    "REVIEW_REQUIRED",
    "ALLOW",
)

_ALLOWED_INPUT_FLAGS = frozenset({"ALLOW", "ALLOW_SNAPSHOT_ONLY", "ALLOW_STORED_ONLY"})
_BLOCKING_INPUT_FLAGS = frozenset({"BLOCK"})
_REVIEW_INPUT_FLAGS = frozenset({"HOLD"})
_ALLOWED_INPUT_AVAILABILITY_STAGES = frozenset({"L-1", "L0", "L0 snapshot"})
_BLOCKING_INPUT_AVAILABILITY_STAGES = frozenset({"L+1"})
_REVIEW_INPUT_AVAILABILITY_STAGES = frozenset({"?"})
_ALLOWED_INPUT_AS_OF_REQUIREMENTS = frozenset(
    {
        "DIRECT_PRE_RACE",
        "PRE_CUTOFF_SNAPSHOT",
        "STORED_AS_OF_SNAPSHOT",
        "HISTORICAL_LOOKBACK_BEFORE_RACE_DATE",
    }
)
_BLOCKING_INPUT_AS_OF_REQUIREMENTS = frozenset({"POSTRACE_ONLY"})
_REVIEW_INPUT_AS_OF_REQUIREMENTS = frozenset({"TIMING_UNVERIFIED"})
_ALLOWED_INPUT_TIME_BOUNDARY_RULES = frozenset(
    {
        "VALUE_AT_OR_BEFORE_ENTRY_FINALIZED_AT",
        "SNAPSHOT_CAPTURED_AT_OR_BEFORE_ENTRY_FINALIZED_AT",
        "STORED_ROW_AT_OR_BEFORE_ENTRY_FINALIZED_AT",
        "LOOKBACK_EVENT_DATE_STRICTLY_BEFORE_RACE_DATE",
    }
)
_BLOCKING_TIME_BOUNDARY_RULES = frozenset({"GENERATED_AFTER_RESULT_CONFIRMATION"})
_REVIEW_TIME_BOUNDARY_RULES = frozenset({"MEASUREMENT_REQUIRED_BEFORE_ENTRY_USE"})
_BLOCKING_TIME_REFERENCE_TYPES = frozenset({"POSTRACE_CONFIRMATION_TIME"})
_REVIEW_TIME_REFERENCE_TYPES = frozenset({"UNVERIFIED_TIME"})
_BLOCKING_SOURCE_TAGS = frozenset({"post_entry_only"})
_REVIEW_SOURCE_TAGS = frozenset({"hold"})


@dataclass(frozen=True, slots=True)
class InputSchemaDecisionRule:
    rule_id: str
    priority: int
    verdict: str
    description: str


SCHEMA_DECISION_RULES: tuple[InputSchemaDecisionRule, ...] = (
    InputSchemaDecisionRule(
        rule_id="block_postrace_or_leakage_signal",
        priority=100,
        verdict="BLOCK",
        description=(
            "L+1, POSTRACE_ONLY, 결과 확정 후 생성, post_entry_only 태그는 "
            "입력 스키마만 봐도 즉시 차단한다."
        ),
    ),
    InputSchemaDecisionRule(
        rule_id="block_non_feature_scope",
        priority=90,
        verdict="BLOCK",
        description=(
            "label_only, metadata_only, LABEL_ONLY, META_ONLY 는 "
            "입력 스키마 관점에서 허용 대상이 아니다."
        ),
    ),
    InputSchemaDecisionRule(
        rule_id="review_unverified_timing_signal",
        priority=80,
        verdict="REVIEW_REQUIRED",
        description=(
            "HOLD, TIMING_UNVERIFIED, ?, UNVERIFIED_TIME, 실측 필요 규칙은 "
            "운영 승격 전에 검토가 필요하다."
        ),
    ),
    InputSchemaDecisionRule(
        rule_id="review_inconsistent_allowed_contract",
        priority=70,
        verdict="REVIEW_REQUIRED",
        description=(
            "허용 플래그와 snapshot/stored-only 시간 계약이 서로 어긋나면 "
            "사람 검토로 되돌린다."
        ),
    ),
    InputSchemaDecisionRule(
        rule_id="allow_explicit_prerace_contract",
        priority=10,
        verdict="ALLOW",
        description=(
            "train_inference 범위에서 pre-race 시간 계약이 명시적으로 "
            "완결된 경우만 허용한다."
        ),
    ),
    InputSchemaDecisionRule(
        rule_id="review_fallback_incomplete_schema",
        priority=0,
        verdict="REVIEW_REQUIRED",
        description=(
            "어느 규칙에도 명확히 맞지 않는 불완전한 입력 스키마는 "
            "기본적으로 검토 대상으로 분류한다."
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class InputSchemaDecisionInput:
    field_path: str
    consumer_scope: str
    availability_stage: str
    as_of_requirement: str
    train_inference_flag: str
    allowed_data_category: str
    time_boundary_rule: str
    generated_at_kind: str
    updated_at_kind: str
    identifier_kind: str
    identifier_pattern: str
    identifier_source_tags: tuple[str, ...] = ()
    exception_rule: str = "NONE"

    def __post_init__(self) -> None:
        if self.consumer_scope not in CONSUMER_SCOPES:
            raise ValueError(f"unsupported consumer_scope: {self.consumer_scope}")
        if self.availability_stage not in AVAILABILITY_STAGES:
            raise ValueError(
                f"unsupported availability_stage: {self.availability_stage}"
            )
        if self.as_of_requirement not in AS_OF_REQUIREMENTS:
            raise ValueError(f"unsupported as_of_requirement: {self.as_of_requirement}")
        if self.train_inference_flag not in TRAIN_INFERENCE_FLAGS:
            raise ValueError(
                f"unsupported train_inference_flag: {self.train_inference_flag}"
            )
        if self.allowed_data_category not in ALLOWED_DATA_CATEGORIES:
            raise ValueError(
                f"unsupported allowed_data_category: {self.allowed_data_category}"
            )
        if self.time_boundary_rule not in TIME_BOUNDARY_RULES:
            raise ValueError(
                f"unsupported time_boundary_rule: {self.time_boundary_rule}"
            )
        if self.generated_at_kind not in TIME_REFERENCE_TYPES:
            raise ValueError(f"unsupported generated_at_kind: {self.generated_at_kind}")
        if self.updated_at_kind not in TIME_REFERENCE_TYPES:
            raise ValueError(f"unsupported updated_at_kind: {self.updated_at_kind}")
        if self.identifier_kind not in IDENTIFIER_KINDS:
            raise ValueError(f"unsupported identifier_kind: {self.identifier_kind}")
        if self.exception_rule not in EXCEPTION_RULE_TYPES:
            raise ValueError(f"unsupported exception_rule: {self.exception_rule}")

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
    ) -> InputSchemaDecisionInput:
        source_tags = payload.get("identifier_source_tags", ())
        if isinstance(source_tags, str):
            parsed_source_tags = tuple(
                tag.strip() for tag in source_tags.split("|") if tag.strip()
            )
        elif isinstance(source_tags, Sequence):
            parsed_source_tags = tuple(str(tag) for tag in source_tags)
        else:
            raise TypeError("identifier_source_tags must be str or sequence")

        return cls(
            field_path=str(payload["field_path"]),
            consumer_scope=str(payload["consumer_scope"]),
            availability_stage=str(payload["availability_stage"]),
            as_of_requirement=str(payload["as_of_requirement"]),
            train_inference_flag=str(payload["train_inference_flag"]),
            allowed_data_category=str(payload["allowed_data_category"]),
            time_boundary_rule=str(payload["time_boundary_rule"]),
            generated_at_kind=str(payload["generated_at_kind"]),
            updated_at_kind=str(payload["updated_at_kind"]),
            identifier_kind=str(payload["identifier_kind"]),
            identifier_pattern=str(payload["identifier_pattern"]),
            identifier_source_tags=parsed_source_tags,
            exception_rule=str(payload.get("exception_rule", "NONE")),
        )


@dataclass(frozen=True, slots=True)
class InputSchemaDecisionResult:
    verdict: str
    rule_id: str
    priority: int
    reason: str


@dataclass(frozen=True, slots=True)
class InputSchemaDecisionExample:
    case_id: str
    description: str
    schema: InputSchemaDecisionInput
    expected_verdict: str
    expected_rule_id: str


def _as_input(
    schema: InputSchemaDecisionInput | Mapping[str, Any],
) -> InputSchemaDecisionInput:
    if isinstance(schema, InputSchemaDecisionInput):
        return schema
    return InputSchemaDecisionInput.from_mapping(schema)


def _rule(rule_id: str) -> InputSchemaDecisionRule:
    for rule in SCHEMA_DECISION_RULES:
        if rule.rule_id == rule_id:
            return rule
    raise KeyError(f"unknown schema decision rule: {rule_id}")


def _has_blocking_postrace_signal(schema: InputSchemaDecisionInput) -> bool:
    source_tags = set(schema.identifier_source_tags)
    return any(
        (
            schema.train_inference_flag in _BLOCKING_INPUT_FLAGS,
            schema.availability_stage in _BLOCKING_INPUT_AVAILABILITY_STAGES,
            schema.as_of_requirement in _BLOCKING_INPUT_AS_OF_REQUIREMENTS,
            schema.time_boundary_rule in _BLOCKING_TIME_BOUNDARY_RULES,
            schema.generated_at_kind in _BLOCKING_TIME_REFERENCE_TYPES,
            schema.updated_at_kind in _BLOCKING_TIME_REFERENCE_TYPES,
            bool(source_tags & _BLOCKING_SOURCE_TAGS),
        )
    )


def _is_non_feature_scope(schema: InputSchemaDecisionInput) -> bool:
    return schema.consumer_scope != "train_inference"


def _has_review_timing_signal(schema: InputSchemaDecisionInput) -> bool:
    source_tags = set(schema.identifier_source_tags)
    return any(
        (
            schema.train_inference_flag in _REVIEW_INPUT_FLAGS,
            schema.availability_stage in _REVIEW_INPUT_AVAILABILITY_STAGES,
            schema.as_of_requirement in _REVIEW_INPUT_AS_OF_REQUIREMENTS,
            schema.time_boundary_rule in _REVIEW_TIME_BOUNDARY_RULES,
            schema.generated_at_kind in _REVIEW_TIME_REFERENCE_TYPES,
            schema.updated_at_kind in _REVIEW_TIME_REFERENCE_TYPES,
            bool(source_tags & _REVIEW_SOURCE_TAGS),
        )
    )


def _has_inconsistent_allowed_contract(schema: InputSchemaDecisionInput) -> bool:
    if not schema.identifier_pattern.strip():
        return True

    if schema.train_inference_flag == "ALLOW":
        return not (
            schema.availability_stage in {"L-1", "L0"}
            and schema.as_of_requirement == "DIRECT_PRE_RACE"
            and schema.time_boundary_rule == "VALUE_AT_OR_BEFORE_ENTRY_FINALIZED_AT"
        )

    if schema.train_inference_flag == "ALLOW_SNAPSHOT_ONLY":
        return not (
            schema.availability_stage == "L0 snapshot"
            and schema.as_of_requirement == "PRE_CUTOFF_SNAPSHOT"
            and schema.time_boundary_rule
            == "SNAPSHOT_CAPTURED_AT_OR_BEFORE_ENTRY_FINALIZED_AT"
        )

    if schema.train_inference_flag == "ALLOW_STORED_ONLY":
        return not (
            schema.as_of_requirement
            in {"STORED_AS_OF_SNAPSHOT", "HISTORICAL_LOOKBACK_BEFORE_RACE_DATE"}
            and schema.time_boundary_rule
            in {
                "STORED_ROW_AT_OR_BEFORE_ENTRY_FINALIZED_AT",
                "LOOKBACK_EVENT_DATE_STRICTLY_BEFORE_RACE_DATE",
            }
        )

    return False


def _is_explicit_prerace_allow(schema: InputSchemaDecisionInput) -> bool:
    source_tags = set(schema.identifier_source_tags)
    return all(
        (
            schema.consumer_scope == "train_inference",
            schema.train_inference_flag in _ALLOWED_INPUT_FLAGS,
            schema.availability_stage in _ALLOWED_INPUT_AVAILABILITY_STAGES,
            schema.as_of_requirement in _ALLOWED_INPUT_AS_OF_REQUIREMENTS,
            schema.time_boundary_rule in _ALLOWED_INPUT_TIME_BOUNDARY_RULES,
            schema.generated_at_kind not in _BLOCKING_TIME_REFERENCE_TYPES,
            schema.updated_at_kind not in _BLOCKING_TIME_REFERENCE_TYPES,
            schema.generated_at_kind not in _REVIEW_TIME_REFERENCE_TYPES,
            schema.updated_at_kind not in _REVIEW_TIME_REFERENCE_TYPES,
            not bool(source_tags & (_BLOCKING_SOURCE_TAGS | _REVIEW_SOURCE_TAGS)),
            bool(schema.identifier_pattern.strip()),
        )
    )


def decide_input_schema(
    schema: InputSchemaDecisionInput | Mapping[str, Any],
) -> InputSchemaDecisionResult:
    normalized = _as_input(schema)

    if _has_blocking_postrace_signal(normalized):
        matched_rule = _rule("block_postrace_or_leakage_signal")
        return InputSchemaDecisionResult(
            verdict=matched_rule.verdict,
            rule_id=matched_rule.rule_id,
            priority=matched_rule.priority,
            reason=matched_rule.description,
        )

    if _is_non_feature_scope(normalized):
        matched_rule = _rule("block_non_feature_scope")
        return InputSchemaDecisionResult(
            verdict=matched_rule.verdict,
            rule_id=matched_rule.rule_id,
            priority=matched_rule.priority,
            reason=matched_rule.description,
        )

    if _has_review_timing_signal(normalized):
        matched_rule = _rule("review_unverified_timing_signal")
        return InputSchemaDecisionResult(
            verdict=matched_rule.verdict,
            rule_id=matched_rule.rule_id,
            priority=matched_rule.priority,
            reason=matched_rule.description,
        )

    if _has_inconsistent_allowed_contract(normalized):
        matched_rule = _rule("review_inconsistent_allowed_contract")
        return InputSchemaDecisionResult(
            verdict=matched_rule.verdict,
            rule_id=matched_rule.rule_id,
            priority=matched_rule.priority,
            reason=matched_rule.description,
        )

    if _is_explicit_prerace_allow(normalized):
        matched_rule = _rule("allow_explicit_prerace_contract")
        return InputSchemaDecisionResult(
            verdict=matched_rule.verdict,
            rule_id=matched_rule.rule_id,
            priority=matched_rule.priority,
            reason=matched_rule.description,
        )

    matched_rule = _rule("review_fallback_incomplete_schema")
    return InputSchemaDecisionResult(
        verdict=matched_rule.verdict,
        rule_id=matched_rule.rule_id,
        priority=matched_rule.priority,
        reason=matched_rule.description,
    )


SCHEMA_DECISION_EXAMPLES: tuple[InputSchemaDecisionExample, ...] = (
    InputSchemaDecisionExample(
        case_id="core_card_direct_allow",
        description="출전표 핵심 카드 식별자는 pre-race 직접 사용 허용.",
        schema=InputSchemaDecisionInput(
            field_path="horses[].chul_no",
            consumer_scope="train_inference",
            availability_stage="L0",
            as_of_requirement="DIRECT_PRE_RACE",
            train_inference_flag="ALLOW",
            allowed_data_category="core_card_direct",
            time_boundary_rule="VALUE_AT_OR_BEFORE_ENTRY_FINALIZED_AT",
            generated_at_kind="SOURCE_PUBLICATION_TIME",
            updated_at_kind="SOURCE_PUBLICATION_TIME",
            identifier_kind="canonical_path",
            identifier_pattern="horses[].chul_no",
            identifier_source_tags=("pre_entry_allowed",),
            exception_rule="ENTRY_DROP_FROM_OPERATIONAL_SNAPSHOT",
        ),
        expected_verdict="ALLOW",
        expected_rule_id="allow_explicit_prerace_contract",
    ),
    InputSchemaDecisionExample(
        case_id="snapshot_locked_allow",
        description="주로 상태는 snapshot 잠금 계약이 완결되면 허용.",
        schema=InputSchemaDecisionInput(
            field_path="track.weather",
            consumer_scope="train_inference",
            availability_stage="L0 snapshot",
            as_of_requirement="PRE_CUTOFF_SNAPSHOT",
            train_inference_flag="ALLOW_SNAPSHOT_ONLY",
            allowed_data_category="snapshot_locked_race_state",
            time_boundary_rule="SNAPSHOT_CAPTURED_AT_OR_BEFORE_ENTRY_FINALIZED_AT",
            generated_at_kind="SNAPSHOT_COLLECTION_TIME",
            updated_at_kind="SNAPSHOT_COLLECTION_TIME",
            identifier_kind="canonical_path",
            identifier_pattern="track.weather",
            identifier_source_tags=("snapshot_only",),
            exception_rule="KEEP_LOCKED_SNAPSHOT",
        ),
        expected_verdict="ALLOW",
        expected_rule_id="allow_explicit_prerace_contract",
    ),
    InputSchemaDecisionExample(
        case_id="stored_detail_allow",
        description="stored-as-of 계약이 명시된 누적 통계는 허용.",
        schema=InputSchemaDecisionInput(
            field_path="horses[].jkDetail.winRateT",
            consumer_scope="train_inference",
            availability_stage="L-1",
            as_of_requirement="STORED_AS_OF_SNAPSHOT",
            train_inference_flag="ALLOW_STORED_ONLY",
            allowed_data_category="stored_detail_lookup",
            time_boundary_rule="STORED_ROW_AT_OR_BEFORE_ENTRY_FINALIZED_AT",
            generated_at_kind="STORED_AS_OF_TIME",
            updated_at_kind="STORED_AS_OF_TIME",
            identifier_kind="canonical_path",
            identifier_pattern="horses[].jkDetail.winRateT",
            identifier_source_tags=("stored_only",),
            exception_rule="KEEP_STORED_AS_OF_SNAPSHOT",
        ),
        expected_verdict="ALLOW",
        expected_rule_id="allow_explicit_prerace_contract",
    ),
    InputSchemaDecisionExample(
        case_id="timing_unverified_review",
        description="odds 계열처럼 공개 시점 미실측 신호는 검토 필요.",
        schema=InputSchemaDecisionInput(
            field_path="horses[].win_odds",
            consumer_scope="train_inference",
            availability_stage="?",
            as_of_requirement="TIMING_UNVERIFIED",
            train_inference_flag="HOLD",
            allowed_data_category="timing_unverified_market",
            time_boundary_rule="MEASUREMENT_REQUIRED_BEFORE_ENTRY_USE",
            generated_at_kind="UNVERIFIED_TIME",
            updated_at_kind="UNVERIFIED_TIME",
            identifier_kind="canonical_path",
            identifier_pattern="horses[].win_odds",
            identifier_source_tags=("hold",),
            exception_rule="RAW_STORE_ONLY",
        ),
        expected_verdict="REVIEW_REQUIRED",
        expected_rule_id="review_unverified_timing_signal",
    ),
    InputSchemaDecisionExample(
        case_id="postrace_feedback_block",
        description="사후 배당/오즈 블록은 즉시 차단.",
        schema=InputSchemaDecisionInput(
            field_path="race_odds.win",
            consumer_scope="train_inference",
            availability_stage="L+1",
            as_of_requirement="POSTRACE_ONLY",
            train_inference_flag="BLOCK",
            allowed_data_category="postrace_feedback",
            time_boundary_rule="GENERATED_AFTER_RESULT_CONFIRMATION",
            generated_at_kind="POSTRACE_CONFIRMATION_TIME",
            updated_at_kind="POSTRACE_CONFIRMATION_TIME",
            identifier_kind="prefix_path",
            identifier_pattern="race_odds",
            identifier_source_tags=("post_entry_only",),
            exception_rule="RAW_STORE_ONLY",
        ),
        expected_verdict="BLOCK",
        expected_rule_id="block_postrace_or_leakage_signal",
    ),
    InputSchemaDecisionExample(
        case_id="label_scope_block",
        description="정답 라벨은 입력 스키마 관점에서 차단.",
        schema=InputSchemaDecisionInput(
            field_path="result_data.top3",
            consumer_scope="label_only",
            availability_stage="L+1",
            as_of_requirement="POSTRACE_ONLY",
            train_inference_flag="LABEL_ONLY",
            allowed_data_category="label_result",
            time_boundary_rule="GENERATED_AFTER_RESULT_CONFIRMATION",
            generated_at_kind="POSTRACE_CONFIRMATION_TIME",
            updated_at_kind="POSTRACE_CONFIRMATION_TIME",
            identifier_kind="leaf_key",
            identifier_pattern="top3",
            identifier_source_tags=("post_entry_only",),
            exception_rule="LABEL_RECOMPUTE_ONLY",
        ),
        expected_verdict="BLOCK",
        expected_rule_id="block_postrace_or_leakage_signal",
    ),
    InputSchemaDecisionExample(
        case_id="metadata_scope_block",
        description="시점 anchor 메타데이터는 유지하되 입력 스키마에서는 차단.",
        schema=InputSchemaDecisionInput(
            field_path="snapshot_meta.entry_finalized_at",
            consumer_scope="metadata_only",
            availability_stage="L0 snapshot",
            as_of_requirement="PRE_CUTOFF_SNAPSHOT",
            train_inference_flag="META_ONLY",
            allowed_data_category="metadata_anchor",
            time_boundary_rule="SNAPSHOT_CAPTURED_AT_OR_BEFORE_ENTRY_FINALIZED_AT",
            generated_at_kind="DERIVED_PARENT_LOCK_TIME",
            updated_at_kind="DERIVED_PARENT_LOCK_TIME",
            identifier_kind="prefix_path",
            identifier_pattern="snapshot_meta",
            identifier_source_tags=("metadata_only",),
            exception_rule="METADATA_RETAIN_ONLY",
        ),
        expected_verdict="BLOCK",
        expected_rule_id="block_non_feature_scope",
    ),
)
