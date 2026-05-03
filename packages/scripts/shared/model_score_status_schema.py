"""모델 점수 산출 상태 코드 및 반환 DTO 계약."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

RULE_SCHEMA_VERSION = "model-score-status-rules-v1"
CANONICAL_STORAGE_RELATIVE_PATH = Path("data/contracts/model_score_status_rules_v1.csv")
CANONICAL_STORAGE_FORMAT = "csv"
CANONICAL_STORAGE_ENCODING = "utf-8"
ROW_PRIMARY_KEY: tuple[str, ...] = ("status_code",)

STATUS_CLASSES: tuple[str, ...] = ("scored", "deferred", "missing", "failed")

STATUS_CODES: tuple[str, ...] = (
    "FAIL_ACTUAL_TOP3_MISSING",
    "FAIL_ACTUAL_TOP3_INVALID",
    "FAIL_PREDICTION_PAYLOAD_MISSING",
    "MISSING_PREDICTED_TOP3",
    "FAIL_PREDICTED_TOP3_INVALID",
    "MISSING_CONFIDENCE",
    "FAIL_CONFIDENCE_INVALID",
    "DEFERRED_LOW_CONFIDENCE",
    "SCORED_OK",
)


@dataclass(frozen=True, slots=True)
class ScoreStatusSpec:
    """상태 코드별 집계/운영 계약 정의."""

    precedence: int
    status_code: str
    status_class: str
    status_reason: str
    trigger_condition: str
    json_ok: bool
    deferred: bool
    coverage_included: bool
    score_aggregated: bool
    fallback_required: bool
    fallback_action: str
    notes: str | None = None

    def race_status_payload(self) -> dict[str, Any]:
        """경주 단위 상태 DTO로 직렬화한다."""

        return {
            "status_code": self.status_code,
            "status_class": self.status_class,
            "status_reason": self.status_reason,
            "fallback_required": self.fallback_required,
            "fallback_action": self.fallback_action,
        }


@dataclass(frozen=True, slots=True)
class ScoreComputationResult:
    """compute_score() 반환 계약."""

    race_status: ScoreStatusSpec
    normalized_confidence: float | None
    set_match: float
    correct_count: int

    def to_dict(self) -> dict[str, Any]:
        """기존 평탄 필드와 새 nested DTO를 함께 반환한다."""

        status_payload = self.race_status.race_status_payload()
        return {
            "json_ok": self.race_status.json_ok,
            "deferred": self.race_status.deferred,
            "race_status": status_payload,
            "status_code": self.race_status.status_code,
            "status_class": self.race_status.status_class,
            "status_reason": self.race_status.status_reason,
            "fallback_required": self.race_status.fallback_required,
            "fallback_action": self.race_status.fallback_action,
            "normalized_confidence": self.normalized_confidence,
            "coverage_included": self.race_status.coverage_included,
            "score_aggregated": self.race_status.score_aggregated,
            "set_match": self.set_match,
            "correct_count": self.correct_count,
        }


STATUS_SPECS: tuple[ScoreStatusSpec, ...] = (
    ScoreStatusSpec(
        precedence=10,
        status_code="FAIL_ACTUAL_TOP3_MISSING",
        status_class="failed",
        status_reason="정답 키 actual_top3 구조가 누락되었거나 길이 3 계약을 만족하지 않는다.",
        trigger_condition="actual 이 list 가 아니거나 길이가 3이 아님",
        json_ok=False,
        deferred=False,
        coverage_included=True,
        score_aggregated=False,
        fallback_required=True,
        fallback_action="set_match=0, correct_count=0 으로 고정하고 answer_key 복구 이슈로 기록",
        notes="정답 키 누락은 모델 문제가 아니라 평가 데이터 계약 위반이므로 최우선 차단",
    ),
    ScoreStatusSpec(
        precedence=20,
        status_code="FAIL_ACTUAL_TOP3_INVALID",
        status_class="failed",
        status_reason="정답 키 actual_top3 값이 양수 정수 3개로 정규화되지 않거나 중복이 있다.",
        trigger_condition="actual 3개를 정수 양수로 정규화할 수 없거나 중복이 있음",
        json_ok=False,
        deferred=False,
        coverage_included=True,
        score_aggregated=False,
        fallback_required=True,
        fallback_action="set_match=0, correct_count=0 으로 고정하고 answer_key 정합성 이슈로 기록",
        notes="정답측 이상은 모델 출력보다 먼저 차단",
    ),
    ScoreStatusSpec(
        precedence=30,
        status_code="FAIL_PREDICTION_PAYLOAD_MISSING",
        status_class="failed",
        status_reason="예측 payload 자체가 dict 형태가 아니라 채점을 진행할 수 없다.",
        trigger_condition="prediction 이 dict 가 아님",
        json_ok=False,
        deferred=False,
        coverage_included=True,
        score_aggregated=False,
        fallback_required=True,
        fallback_action="set_match=0, correct_count=0 으로 고정",
        notes="예측 호출 실패/예외 복구 후 공통 상태 코드",
    ),
    ScoreStatusSpec(
        precedence=40,
        status_code="MISSING_PREDICTED_TOP3",
        status_class="missing",
        status_reason="예측 payload에 핵심 필드 predicted_top3가 없다.",
        trigger_condition="prediction dict 에 predicted 키가 없음",
        json_ok=False,
        deferred=False,
        coverage_included=True,
        score_aggregated=False,
        fallback_required=True,
        fallback_action="set_match=0, correct_count=0 으로 고정",
        notes="출력 스키마 핵심 필드 누락",
    ),
    ScoreStatusSpec(
        precedence=50,
        status_code="FAIL_PREDICTED_TOP3_INVALID",
        status_class="failed",
        status_reason="predicted_top3 값이 양수 정수 3개로 정규화되지 않거나 중복이 있다.",
        trigger_condition="predicted 가 길이 3 list 가 아니거나 3개의 서로 다른 양수 정수로 정규화되지 않음",
        json_ok=False,
        deferred=False,
        coverage_included=True,
        score_aggregated=False,
        fallback_required=True,
        fallback_action="set_match=0, correct_count=0 으로 고정",
        notes="중복 말번호와 비수치 값 포함",
    ),
    ScoreStatusSpec(
        precedence=60,
        status_code="MISSING_CONFIDENCE",
        status_class="missing",
        status_reason="confidence 값이 없어 보류/정상 채점 여부를 결정할 수 없다.",
        trigger_condition="confidence 키가 없거나 None/blank string 임",
        json_ok=False,
        deferred=False,
        coverage_included=True,
        score_aggregated=False,
        fallback_required=True,
        fallback_action="set_match=0, correct_count=0 으로 고정",
        notes="낮은 confidence 와 구분해 별도 집계",
    ),
    ScoreStatusSpec(
        precedence=70,
        status_code="FAIL_CONFIDENCE_INVALID",
        status_class="failed",
        status_reason="confidence 값이 숫자 정규화 또는 0..1 범위 검증을 통과하지 못했다.",
        trigger_condition="confidence 가 수치로 파싱되지 않거나 정규화 후 0~1 범위를 벗어나거나 finite 하지 않음",
        json_ok=False,
        deferred=False,
        coverage_included=True,
        score_aggregated=False,
        fallback_required=True,
        fallback_action="set_match=0, correct_count=0 으로 고정",
        notes="72 처럼 1 초과 값은 100 스케일로 보고 0.72 로 정규화 후 재판정",
    ),
    ScoreStatusSpec(
        precedence=80,
        status_code="DEFERRED_LOW_CONFIDENCE",
        status_class="deferred",
        status_reason="예측은 유효하지만 confidence가 defer 임계값보다 낮아 집계에서 보류된다.",
        trigger_condition="predicted/confidence/actual 이 모두 유효하고 normalized_confidence < defer_threshold",
        json_ok=True,
        deferred=True,
        coverage_included=False,
        score_aggregated=False,
        fallback_required=True,
        fallback_action="set_match 와 correct_count 는 계산하되 coverage 및 score 집계에서 제외",
        notes="보류는 실패가 아니라 의도적 미채점 상태",
    ),
    ScoreStatusSpec(
        precedence=90,
        status_code="SCORED_OK",
        status_class="scored",
        status_reason="예측과 confidence가 모두 유효하며 정상 집계 대상이다.",
        trigger_condition="predicted/confidence/actual 이 모두 유효하고 normalized_confidence >= defer_threshold",
        json_ok=True,
        deferred=False,
        coverage_included=True,
        score_aggregated=True,
        fallback_required=False,
        fallback_action="set_match 와 correct_count 를 정상 집계",
        notes="정상 채점 상태",
    ),
)
STATUS_SPEC_BY_CODE: dict[str, ScoreStatusSpec] = {
    spec.status_code: spec for spec in STATUS_SPECS
}


@dataclass(frozen=True, slots=True)
class RuleColumnSpec:
    """상태 코드 기준표 CSV의 단일 컬럼 정의."""

    name: str
    required: bool
    description: str


COLUMN_SPECS: tuple[RuleColumnSpec, ...] = (
    RuleColumnSpec(
        name="rule_schema_version",
        required=True,
        description="기준표가 따르는 저장 계약 버전.",
    ),
    RuleColumnSpec(
        name="precedence",
        required=True,
        description="동시 충족 시 우선 적용할 판정 순서. 숫자가 작을수록 우선이다.",
    ),
    RuleColumnSpec(
        name="status_code",
        required=True,
        description="단일 상태 코드 식별자.",
    ),
    RuleColumnSpec(
        name="status_class",
        required=True,
        description="scored/deferred/missing/failed 중 하나.",
    ),
    RuleColumnSpec(
        name="status_reason",
        required=True,
        description="compute_score()가 반환하는 경주 단위 판정 사유 고정 문구.",
    ),
    RuleColumnSpec(
        name="trigger_condition",
        required=True,
        description="이 상태 코드가 선택되는 판정 조건 요약.",
    ),
    RuleColumnSpec(
        name="json_ok",
        required=True,
        description="기존 json_ok 집계에 포함되는지 여부.",
    ),
    RuleColumnSpec(
        name="deferred",
        required=True,
        description="기존 deferred 집계에 포함되는지 여부.",
    ),
    RuleColumnSpec(
        name="coverage_included",
        required=True,
        description="coverage 분자에 포함되는지 여부.",
    ),
    RuleColumnSpec(
        name="score_aggregated",
        required=True,
        description="set_match 및 avg_correct 집계에 포함되는지 여부.",
    ),
    RuleColumnSpec(
        name="fallback_required",
        required=True,
        description="정상 채점 외의 후속 처리 또는 운영 fallback이 필요한지 여부.",
    ),
    RuleColumnSpec(
        name="fallback_action",
        required=True,
        description="점수 산출 단계가 취해야 하는 후속 처리.",
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
