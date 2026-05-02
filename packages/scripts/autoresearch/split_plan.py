"""Autoresearch 기간 경계/시드 계약을 재사용 가능한 분할 계획으로 변환한다."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from shared.autoresearch_config_schema import (
    AutoresearchConfig,
    EvaluationContract,
    PrimarySplitWindow,
    RollingWindow,
)
from shared.execution_matrix import (
    DEFAULT_LEAKAGE_POLICY_VERSION,
    ExecutionMatrix,
    build_execution_matrix,
)
from shared.holdout_split_manifest_schema import HoldoutSplitManifest
from shared.read_contract import RaceSnapshot

from .holdout_split import plan_recent_holdout_manifests


@dataclass(frozen=True, slots=True)
class PrimaryTemporalSplitPlan:
    """주 학습/dev/test 기간 경계와 데이터 인덱스."""

    train_end: str
    dev_end: str
    test_start: str
    train_indices: tuple[int, ...]
    dev_indices: tuple[int, ...]
    test_indices: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class RollingWindowSplitPlan:
    """추가 walk-forward 검증 창."""

    name: str
    train_end: str
    eval_start: str
    eval_end: str
    train_indices: tuple[int, ...]
    eval_indices: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ConfiguredTemporalSplitPlan:
    """설정 파일에서 파생된 재현 가능한 분할 계획."""

    primary_split: PrimaryTemporalSplitPlan
    rolling_windows: tuple[RollingWindowSplitPlan, ...]
    execution_matrix: ExecutionMatrix


def _coerce_config(config: AutoresearchConfig | dict[str, Any]) -> AutoresearchConfig:
    if isinstance(config, AutoresearchConfig):
        return config
    return AutoresearchConfig.model_validate(config)


def _sorted_unique_indices(indices: list[int]) -> tuple[int, ...]:
    return tuple(sorted(set(indices)))


def _select_indices(
    dates: tuple[str, ...],
    *,
    include: Callable[[str], bool],
) -> tuple[int, ...]:
    return _sorted_unique_indices(
        [index for index, race_date in enumerate(dates) if include(race_date)]
    )


def _validate_non_empty_split(
    *,
    name: str,
    train_indices: tuple[int, ...],
    eval_indices: tuple[int, ...],
) -> None:
    if not train_indices:
        raise ValueError(f"{name} train 구간이 비어 있습니다.")
    if not eval_indices:
        raise ValueError(f"{name} eval 구간이 비어 있습니다.")


def _validate_contract_against_execution_matrix(
    contract: EvaluationContract,
    execution_matrix: ExecutionMatrix,
) -> None:
    holdout = execution_matrix.holdout
    if contract.selection_method != holdout.selection_method:
        raise ValueError(
            "evaluation_contract.selection_method 가 실행 매트릭스와 다릅니다."
        )
    if contract.boundary_unit != holdout.boundary_unit:
        raise ValueError(
            "evaluation_contract.boundary_unit 이 실행 매트릭스와 다릅니다."
        )
    if contract.selection_seed_invariant != holdout.selection_seed_invariant:
        raise ValueError(
            "evaluation_contract.selection_seed_invariant 가 실행 매트릭스와 다릅니다."
        )
    if contract.active_runner_rule != holdout.active_runner_rule:
        raise ValueError(
            "evaluation_contract.active_runner_rule 이 실행 매트릭스와 다릅니다."
        )
    if contract.target_label != holdout.target_label:
        raise ValueError(
            "evaluation_contract.target_label 이 실행 매트릭스와 다릅니다."
        )


def build_execution_matrix_from_config(
    config: AutoresearchConfig | dict[str, Any],
    *,
    evaluation_seeds: tuple[int, ...] | None = None,
    leakage_policy_version: str = DEFAULT_LEAKAGE_POLICY_VERSION,
) -> ExecutionMatrix:
    """설정 계약과 일치하는 10-seed 실행 매트릭스를 만든다."""

    config_model = _coerce_config(config)
    resolved_evaluation_seeds = (
        evaluation_seeds
        if evaluation_seeds is not None
        else config_model.experiment.evaluation_seeds
    )
    execution_matrix = build_execution_matrix(
        evaluation_seeds=resolved_evaluation_seeds,
        leakage_policy_version=leakage_policy_version,
    )
    _validate_contract_against_execution_matrix(
        config_model.evaluation_contract,
        execution_matrix,
    )
    return execution_matrix


def _build_primary_split_plan(
    dates: tuple[str, ...],
    split: PrimarySplitWindow,
) -> PrimaryTemporalSplitPlan:
    train_indices = _select_indices(
        dates,
        include=lambda race_date: race_date <= split.train_end,
    )
    dev_indices = _select_indices(
        dates,
        include=lambda race_date: split.train_end < race_date <= split.dev_end,
    )
    test_indices = _select_indices(
        dates,
        include=lambda race_date: race_date >= split.test_start,
    )
    _validate_non_empty_split(
        name="primary(dev)",
        train_indices=train_indices,
        eval_indices=dev_indices,
    )
    _validate_non_empty_split(
        name="primary(test)",
        train_indices=train_indices,
        eval_indices=test_indices,
    )
    return PrimaryTemporalSplitPlan(
        train_end=split.train_end,
        dev_end=split.dev_end,
        test_start=split.test_start,
        train_indices=train_indices,
        dev_indices=dev_indices,
        test_indices=test_indices,
    )


def _build_rolling_window_plan(
    dates: tuple[str, ...],
    window: RollingWindow,
) -> RollingWindowSplitPlan:
    train_indices = _select_indices(
        dates,
        include=lambda race_date: race_date <= window.train_end,
    )
    eval_indices = _select_indices(
        dates,
        include=lambda race_date: window.eval_start <= race_date <= window.eval_end,
    )
    _validate_non_empty_split(
        name=f"rolling_window({window.name})",
        train_indices=train_indices,
        eval_indices=eval_indices,
    )
    return RollingWindowSplitPlan(
        name=window.name,
        train_end=window.train_end,
        eval_start=window.eval_start,
        eval_end=window.eval_end,
        train_indices=train_indices,
        eval_indices=eval_indices,
    )


def build_temporal_split_plan(
    dates: Sequence[str],
    *,
    config: AutoresearchConfig | dict[str, Any],
    evaluation_seeds: tuple[int, ...] | None = None,
    leakage_policy_version: str = DEFAULT_LEAKAGE_POLICY_VERSION,
) -> ConfiguredTemporalSplitPlan:
    """설정된 기간 경계를 바탕으로 학습/dev/test 및 rolling window 계획을 만든다."""

    config_model = _coerce_config(config)
    normalized_dates = tuple(str(race_date) for race_date in dates)
    primary_split = _build_primary_split_plan(normalized_dates, config_model.split)
    rolling_windows = tuple(
        _build_rolling_window_plan(normalized_dates, window)
        for window in config_model.rolling_windows
    )
    execution_matrix = build_execution_matrix_from_config(
        config_model,
        evaluation_seeds=evaluation_seeds,
        leakage_policy_version=leakage_policy_version,
    )
    return ConfiguredTemporalSplitPlan(
        primary_split=primary_split,
        rolling_windows=rolling_windows,
        execution_matrix=execution_matrix,
    )


def plan_recent_holdout_manifests_from_config(
    snapshots: list[RaceSnapshot],
    *,
    config: AutoresearchConfig | dict[str, Any],
    manifest_created_at: datetime | str | None = None,
    evaluation_seeds: tuple[int, ...] | None = None,
    leakage_policy_version: str = DEFAULT_LEAKAGE_POLICY_VERSION,
) -> dict[str, HoldoutSplitManifest]:
    """설정 파일의 홀드아웃 계약으로 최근 기간 holdout/mini_val manifest를 생성한다."""

    config_model = _coerce_config(config)
    resolved_evaluation_seeds = (
        evaluation_seeds
        if evaluation_seeds is not None
        else config_model.experiment.evaluation_seeds
    )
    build_execution_matrix_from_config(
        config_model,
        evaluation_seeds=resolved_evaluation_seeds,
        leakage_policy_version=leakage_policy_version,
    )
    return plan_recent_holdout_manifests(
        snapshots,
        manifest_created_at=manifest_created_at,
        holdout_minimum_race_count=config_model.evaluation_contract.minimum_holdout_race_count,
        mini_val_minimum_race_count=config_model.evaluation_contract.minimum_mini_val_race_count,
        evaluation_seeds=resolved_evaluation_seeds,
        leakage_policy_version=leakage_policy_version,
    )
