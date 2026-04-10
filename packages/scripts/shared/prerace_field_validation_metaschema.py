"""출전표 확정 시점 기준 입력 필드 허용 여부 검증 메타스키마."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from shared.feature_source_timing_contract import AS_OF_REQUIREMENTS
from shared.prerace_field_metadata_schema import (
    AVAILABILITY_STAGES,
    TRAIN_INFERENCE_FLAGS,
)

VALIDATION_SPEC_VERSION = "prerace-field-validation-spec-v1"
CANONICAL_STORAGE_RELATIVE_PATH = Path(
    "data/contracts/prerace_field_validation_spec_v1.csv"
)
CANONICAL_STORAGE_FORMAT = "csv"
CANONICAL_STORAGE_ENCODING = "utf-8"
ROW_PRIMARY_KEY: tuple[str, ...] = ("field_path",)

CONSUMER_SCOPES: tuple[str, ...] = (
    "train_inference",
    "label_only",
    "metadata_only",
)

ALLOWED_DATA_CATEGORIES: tuple[str, ...] = (
    "core_card_direct",
    "race_plan_direct",
    "snapshot_locked_race_state",
    "stored_detail_lookup",
    "historical_aggregate",
    "timing_unverified_market",
    "postrace_feedback",
    "label_result",
    "metadata_anchor",
)

TIME_BOUNDARY_RULES: tuple[str, ...] = (
    "VALUE_AT_OR_BEFORE_ENTRY_FINALIZED_AT",
    "SNAPSHOT_CAPTURED_AT_OR_BEFORE_ENTRY_FINALIZED_AT",
    "STORED_ROW_AT_OR_BEFORE_ENTRY_FINALIZED_AT",
    "LOOKBACK_EVENT_DATE_STRICTLY_BEFORE_RACE_DATE",
    "MEASUREMENT_REQUIRED_BEFORE_ENTRY_USE",
    "GENERATED_AFTER_RESULT_CONFIRMATION",
)

EXCEPTION_RULE_TYPES: tuple[str, ...] = (
    "NONE",
    "ENTRY_DROP_FROM_OPERATIONAL_SNAPSHOT",
    "KEEP_LOCKED_SNAPSHOT",
    "KEEP_STORED_AS_OF_SNAPSHOT",
    "STRICT_PAST_ONLY",
    "SOFT_FAIL_EMPTY_BLOCK",
    "RAW_STORE_ONLY",
    "LABEL_RECOMPUTE_ONLY",
    "METADATA_RETAIN_ONLY",
)

IDENTIFIER_KINDS: tuple[str, ...] = (
    "canonical_path",
    "leaf_key",
    "prefix_path",
    "regex_pattern",
)

TIME_REFERENCE_TYPES: tuple[str, ...] = (
    "SOURCE_PUBLICATION_TIME",
    "SNAPSHOT_COLLECTION_TIME",
    "STORED_AS_OF_TIME",
    "DERIVED_PARENT_LOCK_TIME",
    "POSTRACE_CONFIRMATION_TIME",
    "UNVERIFIED_TIME",
)


@dataclass(frozen=True, slots=True)
class ValidationColumnSpec:
    name: str
    required: bool
    description: str


COLUMN_SPECS: tuple[ValidationColumnSpec, ...] = (
    ValidationColumnSpec(
        name="validation_spec_version",
        required=True,
        description="검증 규격 버전. 현재 값은 prerace-field-validation-spec-v1.",
    ),
    ValidationColumnSpec(
        name="field_path",
        required=True,
        description="판정 대상 canonical field path.",
    ),
    ValidationColumnSpec(
        name="consumer_scope",
        required=True,
        description="train_inference, label_only, metadata_only 중 하나.",
    ),
    ValidationColumnSpec(
        name="availability_stage",
        required=True,
        description="L-1, L0, L0 snapshot, ?, L+1 중 하나.",
    ),
    ValidationColumnSpec(
        name="as_of_requirement",
        required=True,
        description="출전표 확정 시점 이전 사용을 위해 필요한 시간 조건.",
    ),
    ValidationColumnSpec(
        name="train_inference_flag",
        required=True,
        description="ALLOW/ALLOW_SNAPSHOT_ONLY/ALLOW_STORED_ONLY/HOLD/BLOCK/LABEL_ONLY/META_ONLY 중 하나.",
    ),
    ValidationColumnSpec(
        name="allowed_data_category",
        required=True,
        description="허용/차단 판정 대상이 속한 데이터 범주.",
    ),
    ValidationColumnSpec(
        name="time_boundary_rule",
        required=True,
        description="출전표 확정 시점 이전 사용을 위해 만족해야 하는 시간 경계 규칙.",
    ),
    ValidationColumnSpec(
        name="data_source",
        required=True,
        description="판정 대상 값의 직접 원천. API 필드, 저장 테이블, 내부 파생 경로를 적는다.",
    ),
    ValidationColumnSpec(
        name="generated_at_kind",
        required=True,
        description="생성 시점 근거 분류.",
    ),
    ValidationColumnSpec(
        name="generated_at_basis",
        required=True,
        description="해당 값이 언제 생성되는지 설명하는 근거 문장 또는 timestamp anchor.",
    ),
    ValidationColumnSpec(
        name="updated_at_kind",
        required=True,
        description="갱신 시점 근거 분류.",
    ),
    ValidationColumnSpec(
        name="updated_at_basis",
        required=True,
        description="해당 값이 언제까지 갱신될 수 있는지와 cutoff 이후 처리 규칙을 설명한다.",
    ),
    ValidationColumnSpec(
        name="judgment_basis",
        required=True,
        description="허용/보류/차단 판정을 내린 핵심 근거 요약.",
    ),
    ValidationColumnSpec(
        name="judgment_basis_refs",
        required=True,
        description="근거 문서/코드 목록. | 구분자를 사용한다.",
    ),
    ValidationColumnSpec(
        name="identifier_kind",
        required=True,
        description="금지/허용 탐지 규칙 유형. canonical_path, leaf_key, prefix_path, regex_pattern 중 하나.",
    ),
    ValidationColumnSpec(
        name="identifier_pattern",
        required=True,
        description="검증기가 직접 사용할 canonical path, leaf key, prefix, 또는 regex 패턴.",
    ),
    ValidationColumnSpec(
        name="identifier_aliases",
        required=True,
        description="대체 식별자 목록. | 구분자를 사용하며 없으면 빈 문자열을 쓴다.",
    ),
    ValidationColumnSpec(
        name="identifier_source_tags",
        required=True,
        description="source_field_tags 기반 탐지용 태그 목록. | 구분자를 사용한다.",
    ),
    ValidationColumnSpec(
        name="late_update_rule",
        required=True,
        description="cutoff 이후 정정이나 재조회가 들어왔을 때의 처리 규칙.",
    ),
    ValidationColumnSpec(
        name="exception_rule",
        required=True,
        description="soft-fail, snapshot 유지, raw 저장 전용 등 운영 예외 규칙 식별자.",
    ),
    ValidationColumnSpec(
        name="notes",
        required=False,
        description="보충 메모.",
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
    return ",".join(ALL_COLUMNS)


@dataclass(frozen=True, slots=True)
class InputFieldValidationSpecRow:
    field_path: str
    consumer_scope: str
    availability_stage: str
    as_of_requirement: str
    train_inference_flag: str
    allowed_data_category: str
    time_boundary_rule: str
    data_source: str
    generated_at_kind: str
    generated_at_basis: str
    updated_at_kind: str
    updated_at_basis: str
    judgment_basis: str
    judgment_basis_refs: tuple[str, ...]
    identifier_kind: str
    identifier_pattern: str
    identifier_aliases: tuple[str, ...]
    identifier_source_tags: tuple[str, ...]
    late_update_rule: str
    exception_rule: str
    notes: str = ""

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

    def to_csv_row(self) -> dict[str, str]:
        return {
            "validation_spec_version": VALIDATION_SPEC_VERSION,
            "field_path": self.field_path,
            "consumer_scope": self.consumer_scope,
            "availability_stage": self.availability_stage,
            "as_of_requirement": self.as_of_requirement,
            "train_inference_flag": self.train_inference_flag,
            "allowed_data_category": self.allowed_data_category,
            "time_boundary_rule": self.time_boundary_rule,
            "data_source": self.data_source,
            "generated_at_kind": self.generated_at_kind,
            "generated_at_basis": self.generated_at_basis,
            "updated_at_kind": self.updated_at_kind,
            "updated_at_basis": self.updated_at_basis,
            "judgment_basis": self.judgment_basis,
            "judgment_basis_refs": "|".join(self.judgment_basis_refs),
            "identifier_kind": self.identifier_kind,
            "identifier_pattern": self.identifier_pattern,
            "identifier_aliases": "|".join(self.identifier_aliases),
            "identifier_source_tags": "|".join(self.identifier_source_tags),
            "late_update_rule": self.late_update_rule,
            "exception_rule": self.exception_rule,
            "notes": self.notes,
        }


def _row(
    *,
    field_path: str,
    consumer_scope: str,
    availability_stage: str,
    as_of_requirement: str,
    train_inference_flag: str,
    allowed_data_category: str,
    time_boundary_rule: str,
    data_source: str,
    generated_at_kind: str,
    generated_at_basis: str,
    updated_at_kind: str,
    updated_at_basis: str,
    judgment_basis: str,
    judgment_basis_refs: tuple[str, ...],
    identifier_kind: str,
    identifier_pattern: str,
    identifier_aliases: tuple[str, ...],
    identifier_source_tags: tuple[str, ...],
    late_update_rule: str,
    exception_rule: str,
    notes: str = "",
) -> InputFieldValidationSpecRow:
    return InputFieldValidationSpecRow(
        field_path=field_path,
        consumer_scope=consumer_scope,
        availability_stage=availability_stage,
        as_of_requirement=as_of_requirement,
        train_inference_flag=train_inference_flag,
        allowed_data_category=allowed_data_category,
        time_boundary_rule=time_boundary_rule,
        data_source=data_source,
        generated_at_kind=generated_at_kind,
        generated_at_basis=generated_at_basis,
        updated_at_kind=updated_at_kind,
        updated_at_basis=updated_at_basis,
        judgment_basis=judgment_basis,
        judgment_basis_refs=judgment_basis_refs,
        identifier_kind=identifier_kind,
        identifier_pattern=identifier_pattern,
        identifier_aliases=identifier_aliases,
        identifier_source_tags=identifier_source_tags,
        late_update_rule=late_update_rule,
        exception_rule=exception_rule,
        notes=notes,
    )


_RULEBOOK_REFS = (
    "docs/prerace-field-validation-metaschema.md",
    "docs/prerace-field-availability-judgment-rules.md",
    "docs/holdout-entry-finalization-rule.md",
)
_API_PIPELINE_REFS = (
    "apps/api/services/race_processing_workflow.py",
    "apps/api/services/collection_service.py",
    "apps/api/services/kra_api_service.py",
)
_FEATURE_REFS = (
    "packages/scripts/shared/prerace_field_policy.py",
    "packages/scripts/shared/entry_snapshot_metadata.py",
    "packages/scripts/shared/feature_source_timing_contract.py",
)
_LEAKAGE_REFS = (
    "packages/scripts/evaluation/leakage_checks.py",
    "apps/api/services/result_collection_service.py",
)

_PRE_ENTRY_SOURCE_TAGS = ("pre_entry_allowed",)
_SNAPSHOT_SOURCE_TAGS = ("snapshot_only",)
_STORED_ONLY_SOURCE_TAGS = ("stored_only",)
_HOLD_SOURCE_TAGS = ("hold",)
_POST_ENTRY_SOURCE_TAGS = ("post_entry_only",)
_METADATA_SOURCE_TAGS = ("metadata_only",)

FIELD_VALIDATION_SPEC_ROWS: tuple[InputFieldValidationSpecRow, ...] = (
    _row(
        field_path="horses[].chul_no",
        consumer_scope="train_inference",
        availability_stage="L0",
        as_of_requirement="DIRECT_PRE_RACE",
        train_inference_flag="ALLOW",
        allowed_data_category="core_card_direct",
        time_boundary_rule="VALUE_AT_OR_BEFORE_ENTRY_FINALIZED_AT",
        data_source="API214_1.response.body.items.item.chulNo",
        generated_at_kind="SOURCE_PUBLICATION_TIME",
        generated_at_basis="핵심 출전번호는 공식 출전표 row가 공개될 때 생성되며 entry_finalized_at 시점 전에 이미 확정돼 있어야 한다.",
        updated_at_kind="SOURCE_PUBLICATION_TIME",
        updated_at_basis="출전표 정정이 있어도 cutoff 이후 변경분으로 잠긴 입력을 덮어쓸 수 없고 core key 결손은 운영 snapshot에서 제외 처리한다.",
        judgment_basis="모든 KRA 경주 예측 생성에 필요한 핵심 카드 식별자라 direct pre-race 허용 대상이다.",
        judgment_basis_refs=(*_RULEBOOK_REFS, *_API_PIPELINE_REFS),
        identifier_kind="canonical_path",
        identifier_pattern="horses[].chul_no",
        identifier_aliases=("chulNo",),
        identifier_source_tags=_PRE_ENTRY_SOURCE_TAGS,
        late_update_rule="pre-cutoff 값만 채택 / cutoff 이후 정정은 감사 로그만 남기고 운영 입력은 잠근다.",
        exception_rule="ENTRY_DROP_FROM_OPERATIONAL_SNAPSHOT",
    ),
    _row(
        field_path="race_plan.rank",
        consumer_scope="train_inference",
        availability_stage="L-1",
        as_of_requirement="DIRECT_PRE_RACE",
        train_inference_flag="ALLOW",
        allowed_data_category="race_plan_direct",
        time_boundary_rule="VALUE_AT_OR_BEFORE_ENTRY_FINALIZED_AT",
        data_source="API72_2.response.body.items.item.rank",
        generated_at_kind="SOURCE_PUBLICATION_TIME",
        generated_at_basis="경주계획표 원천이 사전 공지될 때 생성되는 등급 값이며 rcDate + rcNo + meet key로 식별한다.",
        updated_at_kind="SOURCE_PUBLICATION_TIME",
        updated_at_basis="cutoff 이전 최신 정상 row까지만 채택하고 cutoff 이후 정정은 잠긴 입력을 갱신하지 않는다.",
        judgment_basis="현재 경주의 사전 공지 정보이고 결과 확정 후에만 생기는 필드와 무관하므로 직접 입력 허용.",
        judgment_basis_refs=(*_RULEBOOK_REFS, *_API_PIPELINE_REFS),
        identifier_kind="canonical_path",
        identifier_pattern="race_plan.rank",
        identifier_aliases=("rank",),
        identifier_source_tags=_PRE_ENTRY_SOURCE_TAGS,
        late_update_rule="pre-cutoff 최신 리비전만 허용 / cutoff 이후 재발행은 감사 로그만 남긴다.",
        exception_rule="NONE",
    ),
    _row(
        field_path="track.weather",
        consumer_scope="train_inference",
        availability_stage="L0 snapshot",
        as_of_requirement="PRE_CUTOFF_SNAPSHOT",
        train_inference_flag="ALLOW_SNAPSHOT_ONLY",
        allowed_data_category="snapshot_locked_race_state",
        time_boundary_rule="SNAPSHOT_CAPTURED_AT_OR_BEFORE_ENTRY_FINALIZED_AT",
        data_source="API189_1.response.body.items.item.weather",
        generated_at_kind="SNAPSHOT_COLLECTION_TIME",
        generated_at_basis="날씨/주로 상태는 수집 시점 snapshot에 의해만 고정되며 snapshot_meta.entry_finalized_at 이전 수집본이어야 한다.",
        updated_at_kind="SNAPSHOT_COLLECTION_TIME",
        updated_at_basis="cutoff 이후 상태 변동이 가능하므로 cutoff 이전 snapshot만 유지하고 이후 값은 운영 입력에 반영하지 않는다.",
        judgment_basis="사전 정보이지만 변동성이 있으므로 snapshot 잠금 없이는 누수와 재현 불일치가 발생한다.",
        judgment_basis_refs=(*_RULEBOOK_REFS, *_API_PIPELINE_REFS),
        identifier_kind="canonical_path",
        identifier_pattern="track.weather",
        identifier_aliases=("weather",),
        identifier_source_tags=_SNAPSHOT_SOURCE_TAGS,
        late_update_rule="cutoff 이전 최초 정상 snapshot 또는 잠긴 최신 snapshot만 허용 / 이후 변동은 버린다.",
        exception_rule="KEEP_LOCKED_SNAPSHOT",
    ),
    _row(
        field_path="horses[].training",
        consumer_scope="train_inference",
        availability_stage="L0 snapshot",
        as_of_requirement="PRE_CUTOFF_SNAPSHOT",
        train_inference_flag="ALLOW_SNAPSHOT_ONLY",
        allowed_data_category="snapshot_locked_race_state",
        time_boundary_rule="SNAPSHOT_CAPTURED_AT_OR_BEFORE_ENTRY_FINALIZED_AT",
        data_source="API329.response.body.items.item[]",
        generated_at_kind="SNAPSHOT_COLLECTION_TIME",
        generated_at_basis="조교 현황은 cutoff 이전에 수집된 snapshot 블록만 허용되며 이름 fallback 매칭 로그를 남겨야 한다.",
        updated_at_kind="SNAPSHOT_COLLECTION_TIME",
        updated_at_basis="cutoff 이후 재수집·재매칭 결과로 기존 training 블록을 덮어쓰지 않고 soft-fail empty block을 유지한다.",
        judgment_basis="사전 공개 정보지만 변동성과 이름 매칭 불확실성이 있어 snapshot 잠금과 soft-fail 규칙이 동시에 필요하다.",
        judgment_basis_refs=(
            *_RULEBOOK_REFS,
            "docs/prerace-data-whitelist-blacklist-policy.md",
            *_API_PIPELINE_REFS,
        ),
        identifier_kind="canonical_path",
        identifier_pattern="horses[].training",
        identifier_aliases=("training",),
        identifier_source_tags=_SNAPSHOT_SOURCE_TAGS,
        late_update_rule="cutoff 이전 snapshot만 허용 / 미매칭은 empty block으로 남기고 예측은 계속 생성한다.",
        exception_rule="SOFT_FAIL_EMPTY_BLOCK",
    ),
    _row(
        field_path="horses[].jkDetail.winRateT",
        consumer_scope="train_inference",
        availability_stage="L-1",
        as_of_requirement="STORED_AS_OF_SNAPSHOT",
        train_inference_flag="ALLOW_STORED_ONLY",
        allowed_data_category="stored_detail_lookup",
        time_boundary_rule="STORED_ROW_AT_OR_BEFORE_ENTRY_FINALIZED_AT",
        data_source="API12_1.response.body.items.item.winRateT",
        generated_at_kind="STORED_AS_OF_TIME",
        generated_at_basis="기수 누적 성적은 당시 수집된 저장본의 created_at/collected_at 기준으로만 해석해야 한다.",
        updated_at_kind="STORED_AS_OF_TIME",
        updated_at_basis="과거 재조회 최신값은 금지하며 해당 경주의 출전표 확정 이전에 저장된 row만 유효하다.",
        judgment_basis="사전 공개 통계지만 재조회 시점 오염 위험이 커서 stored-only 조건을 만족할 때만 허용.",
        judgment_basis_refs=(*_RULEBOOK_REFS, *_API_PIPELINE_REFS, *_FEATURE_REFS),
        identifier_kind="canonical_path",
        identifier_pattern="horses[].jkDetail.winRateT",
        identifier_aliases=("winRateT",),
        identifier_source_tags=_STORED_ONLY_SOURCE_TAGS,
        late_update_rule="당시 저장본만 사용하고 이후 재조회 값으로 덮어쓰지 않는다.",
        exception_rule="KEEP_STORED_AS_OF_SNAPSHOT",
    ),
    _row(
        field_path="horses[].past_stats.recent_top3_rate",
        consumer_scope="train_inference",
        availability_stage="L0",
        as_of_requirement="HISTORICAL_LOOKBACK_BEFORE_RACE_DATE",
        train_inference_flag="ALLOW_STORED_ONLY",
        allowed_data_category="historical_aggregate",
        time_boundary_rule="LOOKBACK_EVENT_DATE_STRICTLY_BEFORE_RACE_DATE",
        data_source="POSTGRES.races + results historical aggregate",
        generated_at_kind="DERIVED_PARENT_LOCK_TIME",
        generated_at_basis="과거 성적 집계는 현재 경주 race_date 이전 결과만 사용해 내부 파생하며 동일 날짜 이후 row는 포함하지 않는다.",
        updated_at_kind="DERIVED_PARENT_LOCK_TIME",
        updated_at_basis="집계 재실행 시에도 lookup anchor 이전 historical row만 허용하고 현재 경주 또는 미래 row가 섞이면 실패 처리한다.",
        judgment_basis="과거 경기력 집계는 허용 가능하지만 현재 경주보다 엄격히 과거인 결과만 써야 하므로 별도 시간 경계가 필요하다.",
        judgment_basis_refs=(
            "docs/prerace-field-availability-judgment-rules.md",
            "packages/scripts/shared/db_client.py",
            "packages/scripts/feature_engineering.py",
        ),
        identifier_kind="canonical_path",
        identifier_pattern="horses[].past_stats.recent_top3_rate",
        identifier_aliases=("recent_top3_rate",),
        identifier_source_tags=_STORED_ONLY_SOURCE_TAGS,
        late_update_rule="lookback 범위를 race_date 이전으로 고정 / 미래 row 유입 시 집계 실패로 처리한다.",
        exception_rule="STRICT_PAST_ONLY",
    ),
    _row(
        field_path="horses[].win_odds",
        consumer_scope="train_inference",
        availability_stage="?",
        as_of_requirement="TIMING_UNVERIFIED",
        train_inference_flag="HOLD",
        allowed_data_category="timing_unverified_market",
        time_boundary_rule="MEASUREMENT_REQUIRED_BEFORE_ENTRY_USE",
        data_source="API214_1.response.body.items.item.winOdds",
        generated_at_kind="UNVERIFIED_TIME",
        generated_at_basis="원천 필드는 존재하지만 실제 pre-cutoff 공개 시점 실측이 아직 끝나지 않았다.",
        updated_at_kind="UNVERIFIED_TIME",
        updated_at_basis="언제까지 변동하는지와 cutoff 이전 가용 여부가 확정되지 않아 운영 규격에 넣을 수 없다.",
        judgment_basis="실측 근거가 확보되기 전까지는 연구/raw 저장만 허용하고 최종 입력에서는 보류해야 한다.",
        judgment_basis_refs=(
            "docs/kra-race-lifecycle-timing-matrix.md",
            "docs/holdout-entry-finalization-rule.md",
            "docs/prerace-field-validation-metaschema.md",
        ),
        identifier_kind="canonical_path",
        identifier_pattern="horses[].win_odds",
        identifier_aliases=("horses[].winOdds", "winOdds"),
        identifier_source_tags=_HOLD_SOURCE_TAGS,
        late_update_rule="실측 로그가 확보될 때까지 HOLD 유지 / 임시 운영 승격 금지.",
        exception_rule="RAW_STORE_ONLY",
    ),
    _row(
        field_path="race_odds.win",
        consumer_scope="train_inference",
        availability_stage="L+1",
        as_of_requirement="POSTRACE_ONLY",
        train_inference_flag="BLOCK",
        allowed_data_category="postrace_feedback",
        time_boundary_rule="GENERATED_AFTER_RESULT_CONFIRMATION",
        data_source="POSTGRES.race_odds.odds",
        generated_at_kind="POSTRACE_CONFIRMATION_TIME",
        generated_at_basis="확정 배당 테이블은 결과 직후 수집되며 현재 경주 출전표 확정 시점에는 존재하지 않는다.",
        updated_at_kind="POSTRACE_CONFIRMATION_TIME",
        updated_at_basis="결과 이후 적재/정정될 수 있으나 어느 경우에도 현재 경주 입력으로는 사용할 수 없다.",
        judgment_basis="현재 경주의 post-race 피드백이므로 학습/추론 입력에서는 항상 차단해야 한다.",
        judgment_basis_refs=(*_RULEBOOK_REFS, *_LEAKAGE_REFS),
        identifier_kind="prefix_path",
        identifier_pattern="race_odds",
        identifier_aliases=("race_odds", "odds"),
        identifier_source_tags=_POST_ENTRY_SOURCE_TAGS,
        late_update_rule="raw 감사 보존만 허용하고 feature 조인에서는 무조건 차단한다.",
        exception_rule="RAW_STORE_ONLY",
    ),
    _row(
        field_path="result_data.top3",
        consumer_scope="label_only",
        availability_stage="L+1",
        as_of_requirement="POSTRACE_ONLY",
        train_inference_flag="LABEL_ONLY",
        allowed_data_category="label_result",
        time_boundary_rule="GENERATED_AFTER_RESULT_CONFIRMATION",
        data_source="INTERNAL.result_data.top3",
        generated_at_kind="POSTRACE_CONFIRMATION_TIME",
        generated_at_basis="정답 라벨은 결과 수집 완료 후 내부적으로 계산된다.",
        updated_at_kind="POSTRACE_CONFIRMATION_TIME",
        updated_at_basis="정답 정정이 있더라도 평가/라벨 재계산에만 사용하고 현재 경주 입력에는 연결하지 않는다.",
        judgment_basis="모델 정답과 평가 전용 데이터이므로 feature 입력으로 전환하면 즉시 누수가 된다.",
        judgment_basis_refs=(*_RULEBOOK_REFS, *_LEAKAGE_REFS),
        identifier_kind="leaf_key",
        identifier_pattern="top3",
        identifier_aliases=("actual_result", "is_top3"),
        identifier_source_tags=_POST_ENTRY_SOURCE_TAGS,
        late_update_rule="라벨 재생성만 허용하고 train/inference feature 공간에는 절대 병합하지 않는다.",
        exception_rule="LABEL_RECOMPUTE_ONLY",
    ),
    _row(
        field_path="finish_position",
        consumer_scope="train_inference",
        availability_stage="L+1",
        as_of_requirement="POSTRACE_ONLY",
        train_inference_flag="BLOCK",
        allowed_data_category="postrace_feedback",
        time_boundary_rule="GENERATED_AFTER_RESULT_CONFIRMATION",
        data_source="API214_1.result fields",
        generated_at_kind="POSTRACE_CONFIRMATION_TIME",
        generated_at_basis="착순은 현재 경주 주행 종료 후 상세 결과 payload나 평가 answer key를 만들 때만 확정된다.",
        updated_at_kind="POSTRACE_CONFIRMATION_TIME",
        updated_at_basis="재심/정정으로 바뀔 수 있지만 어느 경우에도 출전표 확정 시점 입력으로는 사용할 수 없다.",
        judgment_basis="현재 경주의 결승 순위를 직접 복원하는 값이라 top-3 적중 과제를 즉시 오염시킨다.",
        judgment_basis_refs=(*_RULEBOOK_REFS, *_LEAKAGE_REFS),
        identifier_kind="leaf_key",
        identifier_pattern="finish_position",
        identifier_aliases=("rank", "ord"),
        identifier_source_tags=_POST_ENTRY_SOURCE_TAGS,
        late_update_rule="정답/감사 레이어에서만 유지하고 feature payload에서는 즉시 제거한다.",
        exception_rule="RAW_STORE_ONLY",
    ),
    _row(
        field_path="ordBigo",
        consumer_scope="train_inference",
        availability_stage="L+1",
        as_of_requirement="POSTRACE_ONLY",
        train_inference_flag="BLOCK",
        allowed_data_category="postrace_feedback",
        time_boundary_rule="GENERATED_AFTER_RESULT_CONFIRMATION",
        data_source="API214_1.response.body.items.item.ordBigo",
        generated_at_kind="POSTRACE_CONFIRMATION_TIME",
        generated_at_basis="심판 판정 코멘트는 결승 순위와 함께 경주 종료 후에만 기록된다.",
        updated_at_kind="POSTRACE_CONFIRMATION_TIME",
        updated_at_basis="결과 정정 시 재기록될 수 있으나 pre-cutoff 입력에는 사용할 수 없다.",
        judgment_basis="결승 판정의 설명 변수여서 결과 확정 정보를 우회적으로 노출한다.",
        judgment_basis_refs=(*_RULEBOOK_REFS, *_LEAKAGE_REFS),
        identifier_kind="leaf_key",
        identifier_pattern="ordBigo",
        identifier_aliases=(),
        identifier_source_tags=_POST_ENTRY_SOURCE_TAGS,
        late_update_rule="raw 감사 보존만 허용하고 feature 파생·프롬프트 컨텍스트에서 제거한다.",
        exception_rule="RAW_STORE_ONLY",
    ),
    _row(
        field_path="diffUnit",
        consumer_scope="train_inference",
        availability_stage="L+1",
        as_of_requirement="POSTRACE_ONLY",
        train_inference_flag="BLOCK",
        allowed_data_category="postrace_feedback",
        time_boundary_rule="GENERATED_AFTER_RESULT_CONFIRMATION",
        data_source="API214_1.response.body.items.item.diffUnit",
        generated_at_kind="POSTRACE_CONFIRMATION_TIME",
        generated_at_basis="도착 차이는 결승선 통과 후 말 간 상대 결과를 계산해야만 생긴다.",
        updated_at_kind="POSTRACE_CONFIRMATION_TIME",
        updated_at_basis="사진 판독/정정 시 값이 바뀔 수 있지만 현재 경주 입력에는 절대 연결할 수 없다.",
        judgment_basis="현재 경주의 상대 우열을 직접 드러내는 사후 성적 지표다.",
        judgment_basis_refs=(*_RULEBOOK_REFS, *_LEAKAGE_REFS),
        identifier_kind="leaf_key",
        identifier_pattern="diffUnit",
        identifier_aliases=(),
        identifier_source_tags=_POST_ENTRY_SOURCE_TAGS,
        late_update_rule="정답 해석에만 남기고 feature/랭킹 입력에서는 즉시 차단한다.",
        exception_rule="RAW_STORE_ONLY",
    ),
    _row(
        field_path="rankRise",
        consumer_scope="train_inference",
        availability_stage="L+1",
        as_of_requirement="POSTRACE_ONLY",
        train_inference_flag="BLOCK",
        allowed_data_category="postrace_feedback",
        time_boundary_rule="GENERATED_AFTER_RESULT_CONFIRMATION",
        data_source="API214_1.response.body.items.item.rankRise",
        generated_at_kind="POSTRACE_CONFIRMATION_TIME",
        generated_at_basis="순위 상승/하락은 주행 중 위치 변화와 최종 성적을 합쳐야 계산된다.",
        updated_at_kind="POSTRACE_CONFIRMATION_TIME",
        updated_at_basis="결과 정정 시 재계산될 수 있으나 pre-cutoff 입력에서는 사용 금지다.",
        judgment_basis="현재 경주 페이스와 결과를 함께 압축한 사후 요약치라 누수 강도가 높다.",
        judgment_basis_refs=(*_RULEBOOK_REFS, *_LEAKAGE_REFS),
        identifier_kind="leaf_key",
        identifier_pattern="rankRise",
        identifier_aliases=(),
        identifier_source_tags=_POST_ENTRY_SOURCE_TAGS,
        late_update_rule="raw 감사 보존만 허용하고 feature 파생은 금지한다.",
        exception_rule="RAW_STORE_ONLY",
    ),
    _row(
        field_path="rcTime",
        consumer_scope="train_inference",
        availability_stage="L+1",
        as_of_requirement="POSTRACE_ONLY",
        train_inference_flag="BLOCK",
        allowed_data_category="postrace_feedback",
        time_boundary_rule="GENERATED_AFTER_RESULT_CONFIRMATION",
        data_source="API214_1.result clock",
        generated_at_kind="POSTRACE_CONFIRMATION_TIME",
        generated_at_basis="완주 기록은 결승 후 심판/계측 시스템이 확정할 때 생성된다.",
        updated_at_kind="POSTRACE_CONFIRMATION_TIME",
        updated_at_basis="공식 기록 정정 가능성이 있어도 pre-cutoff 입력에는 어떤 경우에도 허용되지 않는다.",
        judgment_basis="현재 경주의 주행 결과를 수치로 직접 제공하는 핵심 사후 필드다.",
        judgment_basis_refs=(*_RULEBOOK_REFS, *_LEAKAGE_REFS),
        identifier_kind="leaf_key",
        identifier_pattern="rcTime",
        identifier_aliases=("resultTime",),
        identifier_source_tags=_POST_ENTRY_SOURCE_TAGS,
        late_update_rule="라벨/감사 레이어 외 사용 금지. feature payload 생성 전 제거한다.",
        exception_rule="RAW_STORE_ONLY",
    ),
    _row(
        field_path="result",
        consumer_scope="train_inference",
        availability_stage="L+1",
        as_of_requirement="POSTRACE_ONLY",
        train_inference_flag="BLOCK",
        allowed_data_category="postrace_feedback",
        time_boundary_rule="GENERATED_AFTER_RESULT_CONFIRMATION",
        data_source="API214_1.response.body.items.item.result",
        generated_at_kind="POSTRACE_CONFIRMATION_TIME",
        generated_at_basis="결과 상태 코드는 주행 종료 후 실격/중지/낙마 등 판정과 함께만 생성된다.",
        updated_at_kind="POSTRACE_CONFIRMATION_TIME",
        updated_at_basis="사후 판정 정정이 가능해도 pre-cutoff 입력에서는 항상 금지다.",
        judgment_basis="주행 결과 상태 자체가 현재 경주의 outcome 정보를 직접 포함한다.",
        judgment_basis_refs=(*_RULEBOOK_REFS, *_LEAKAGE_REFS),
        identifier_kind="leaf_key",
        identifier_pattern="result",
        identifier_aliases=(),
        identifier_source_tags=_POST_ENTRY_SOURCE_TAGS,
        late_update_rule="결과 감사용으로만 보관하고 feature 또는 설명 입력에는 병합하지 않는다.",
        exception_rule="RAW_STORE_ONLY",
    ),
    _row(
        field_path="payout",
        consumer_scope="train_inference",
        availability_stage="L+1",
        as_of_requirement="POSTRACE_ONLY",
        train_inference_flag="BLOCK",
        allowed_data_category="postrace_feedback",
        time_boundary_rule="GENERATED_AFTER_RESULT_CONFIRMATION",
        data_source="API160_1|API301 payout/dividend",
        generated_at_kind="POSTRACE_CONFIRMATION_TIME",
        generated_at_basis="환급/배당 수치는 결과 확정과 매출 정산이 끝난 뒤에만 계산된다.",
        updated_at_kind="POSTRACE_CONFIRMATION_TIME",
        updated_at_basis="사후 정산 정정이 가능하더라도 현재 경주 입력으로는 사용할 수 없다.",
        judgment_basis="시장 결과를 그대로 노출해 top-3 결과를 우회 복원할 수 있는 전형적 사후 피드백이다.",
        judgment_basis_refs=(*_RULEBOOK_REFS, *_LEAKAGE_REFS),
        identifier_kind="leaf_key",
        identifier_pattern="payout",
        identifier_aliases=("dividend",),
        identifier_source_tags=_POST_ENTRY_SOURCE_TAGS,
        late_update_rule="정산/감사 레이어만 허용하고 feature 조인·prompt 컨텍스트에서는 즉시 제거한다.",
        exception_rule="RAW_STORE_ONLY",
    ),
    _row(
        field_path="sectional_live_metric_pattern",
        consumer_scope="train_inference",
        availability_stage="L+1",
        as_of_requirement="POSTRACE_ONLY",
        train_inference_flag="BLOCK",
        allowed_data_category="postrace_feedback",
        time_boundary_rule="GENERATED_AFTER_RESULT_CONFIRMATION",
        data_source="API214_1 sectional live metrics",
        generated_at_kind="POSTRACE_CONFIRMATION_TIME",
        generated_at_basis="구간 통과 순위/누적시간/구간시간은 현재 경주가 진행되거나 종료된 뒤에만 의미 있는 값이 채워진다.",
        updated_at_kind="POSTRACE_CONFIRMATION_TIME",
        updated_at_basis="실황/결과 재처리 시 재계산될 수 있지만 pre-cutoff 입력에는 절대 사용할 수 없다.",
        judgment_basis="현재 경주 페이스와 구간별 위치를 직접 담아 예측 목표를 거의 복원하는 대표 누수 패턴이다.",
        judgment_basis_refs=(
            *_RULEBOOK_REFS,
            "docs/knowledge/discovery-2026-03-15-sectional-data-leakage.md",
            *_LEAKAGE_REFS,
        ),
        identifier_kind="regex_pattern",
        identifier_pattern=r"^(sj|bu|se)(G[1-8]f|S[12]f|_[1-4]c)(Ord|AccTime|GTime)$",
        identifier_aliases=("sjG1fOrd", "buG6fOrd", "se_1cAccTime"),
        identifier_source_tags=_POST_ENTRY_SOURCE_TAGS,
        late_update_rule="raw 인입에서는 shadow 저장만 허용하고 canonical export 및 피처 탐색에서는 즉시 실패 처리한다.",
        exception_rule="RAW_STORE_ONLY",
    ),
    _row(
        field_path="snapshot_meta.entry_finalized_at",
        consumer_scope="metadata_only",
        availability_stage="L0 snapshot",
        as_of_requirement="PRE_CUTOFF_SNAPSHOT",
        train_inference_flag="META_ONLY",
        allowed_data_category="metadata_anchor",
        time_boundary_rule="SNAPSHOT_CAPTURED_AT_OR_BEFORE_ENTRY_FINALIZED_AT",
        data_source="INTERNAL.snapshot_meta.entry_finalized_at",
        generated_at_kind="DERIVED_PARENT_LOCK_TIME",
        generated_at_basis="race_plan.sch_st_time와 collected_at 계열 timestamp를 조합해 출전표 확정 anchor를 내부 파생한다.",
        updated_at_kind="DERIVED_PARENT_LOCK_TIME",
        updated_at_basis="부모 snapshot이 잠기면 동일 anchor를 유지하며 cutoff 이후 재발행은 replay_status만 바꾼다.",
        judgment_basis="직접 feature는 아니지만 모든 필드의 허용 여부를 판정하는 기준 시각이므로 메타 전용으로 반드시 유지해야 한다.",
        judgment_basis_refs=(*_RULEBOOK_REFS, *_FEATURE_REFS),
        identifier_kind="prefix_path",
        identifier_pattern="snapshot_meta",
        identifier_aliases=("entry_finalized_at",),
        identifier_source_tags=_METADATA_SOURCE_TAGS,
        late_update_rule="anchor 재계산은 감사/복구 시에만 허용하고 이미 잠긴 운영 입력은 덮어쓰지 않는다.",
        exception_rule="METADATA_RETAIN_ONLY",
    ),
)


def canonical_validation_spec_rows() -> list[dict[str, str]]:
    return [row.to_csv_row() for row in FIELD_VALIDATION_SPEC_ROWS]


def forbidden_post_race_validation_rows() -> tuple[InputFieldValidationSpecRow, ...]:
    return tuple(
        row
        for row in FIELD_VALIDATION_SPEC_ROWS
        if row.train_inference_flag in {"BLOCK", "LABEL_ONLY"}
        and "post_entry_only" in row.identifier_source_tags
    )


def validation_spec_row_by_field_path(field_path: str) -> InputFieldValidationSpecRow:
    for row in FIELD_VALIDATION_SPEC_ROWS:
        if row.field_path == field_path:
            return row
    raise KeyError(f"unknown validation spec field_path: {field_path}")


def validation_rows_by_category(
    category: str,
) -> tuple[InputFieldValidationSpecRow, ...]:
    return tuple(
        row
        for row in FIELD_VALIDATION_SPEC_ROWS
        if row.allowed_data_category == category
    )
