"""배치 예측/평가 대상 KRA 경주 선정 고정 규칙."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

BATCH_RACE_SELECTION_POLICY_VERSION = "kra-batch-race-selection-policy-v1"
ALL_KRA_TARGET_SCOPE = "all_kra_races"
KRA_OFFICIAL_MEETS = (1, 2, 3)
STRICT_DATASET_SELECTOR = "include_in_strict_dataset_true"
REQUIRED_RESULT_STATUS = "collected"
MINIMUM_ACTIVE_RUNNERS = 3


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class BatchRaceSelectionPolicy(_FrozenModel):
    """실행 입력과 분리된 배치 대상 경주 선정 규칙 묶음."""

    policy_version: Literal["kra-batch-race-selection-policy-v1"] = (
        BATCH_RACE_SELECTION_POLICY_VERSION
    )
    target_scope: Literal["all_kra_races"] = ALL_KRA_TARGET_SCOPE
    allowed_meets: tuple[int, ...] = KRA_OFFICIAL_MEETS
    strict_dataset_selector: Literal["include_in_strict_dataset_true"] = (
        STRICT_DATASET_SELECTOR
    )
    required_result_status: Literal["collected"] = REQUIRED_RESULT_STATUS
    require_basic_data: Literal[True] = True
    require_payload_conversion: Literal[True] = True
    minimum_active_runners: Literal[3] = MINIMUM_ACTIVE_RUNNERS
    require_exact_top3_label_count: Literal[3] = 3
    require_unique_top3_label: Literal[True] = True
    require_top3_subset_of_active_runners: Literal[True] = True
    require_leakage_check_pass: Literal[True] = True
    execution_input_override_allowed: Literal[False] = False

    @field_validator("allowed_meets")
    @classmethod
    def _validate_allowed_meets(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        normalized = tuple(int(meet) for meet in value)
        if normalized != KRA_OFFICIAL_MEETS:
            raise ValueError(
                f"allowed_meets 는 공식 KRA 경마장 코드 {list(KRA_OFFICIAL_MEETS)} 와 정확히 일치해야 한다."
            )
        return normalized


DEFAULT_BATCH_RACE_SELECTION_POLICY = BatchRaceSelectionPolicy()


def default_batch_race_selection_policy_payload() -> dict[str, object]:
    """설정 파일에 기록할 기본 선정 정책 payload를 반환한다."""

    return DEFAULT_BATCH_RACE_SELECTION_POLICY.model_dump(mode="json")
