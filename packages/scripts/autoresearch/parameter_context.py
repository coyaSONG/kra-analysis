"""Autoresearch 평가용 단일 설정 소스 기반 파라미터 컨텍스트."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from shared.autoresearch_config_schema import (
    AutoresearchConfig,
    EvaluationContract,
    InputDataVersion,
    PrimarySplitWindow,
    RollingWindow,
)
from shared.execution_matrix import (
    DEFAULT_EVALUATION_SEEDS,
    DEFAULT_EXECUTION_GROUP_ID,
    ExecutionMatrix,
    ExecutionMatrixRun,
    validate_evaluation_seeds,
)

from autoresearch.reproducibility import model_random_state_for_config
from autoresearch.split_plan import build_execution_matrix_from_config

LEGACY_RUNTIME_PARAM_KEYS = frozenset({"model_random_state"})
EVALUATION_INPUT_CONTRACT_VERSION = "autoresearch-evaluation-input-contract-v1"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvaluationRuntimeParameters(_FrozenModel):
    model_random_state: int | None = None


class EvaluationModelParameters(_FrozenModel):
    candidate_name: str | None = None
    kind: str = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)
    positive_class_weight: float = Field(gt=0)
    imputer_strategy: str = Field(min_length=1)
    prediction_top_k: int = Field(ge=1)
    random_state: int | None = None
    random_state_source: str = Field(min_length=1)


class EvaluationInputContract(_FrozenModel):
    format_version: str = EVALUATION_INPUT_CONTRACT_VERSION
    dataset: str = Field(min_length=1)
    input_data: InputDataVersion
    split: PrimarySplitWindow
    rolling_windows: tuple[RollingWindow, ...] = ()
    evaluation_contract: EvaluationContract
    execution_matrix: ExecutionMatrix
    selected_run: ExecutionMatrixRun | None = None


class EvaluationParameterContext(_FrozenModel):
    config_path: str = Field(min_length=1)
    config_sha256: str = Field(min_length=1)
    config: dict[str, Any]
    evaluation_seeds: tuple[int, ...] = ()
    seed_index: int | None = Field(default=None, ge=1)
    run_id: str | None = None
    runtime_params: EvaluationRuntimeParameters
    model_parameters: EvaluationModelParameters
    parameter_source: str = Field(min_length=1)
    model_parameter_source: str = Field(min_length=1)
    input_contract: EvaluationInputContract | None = None
    input_contract_signature: str | None = None

    def runtime_params_dict(self) -> dict[str, int | None]:
        return self.runtime_params.model_dump(mode="json")


class SeedMatrixRuntimeParameters(_FrozenModel):
    evaluation_seeds: tuple[int, ...] = ()
    group_id: str = Field(min_length=1)
    max_workers: int = Field(ge=1)
    execution_journal_path: str | None = None


class SeedMatrixParameterContext(_FrozenModel):
    config_path: str = Field(min_length=1)
    config_sha256: str = Field(min_length=1)
    config: dict[str, Any]
    runtime_params: SeedMatrixRuntimeParameters
    evaluation_seed_source: str = Field(min_length=1)
    group_id_source: str = Field(min_length=1)
    max_workers_source: str = Field(min_length=1)
    execution_journal_path_source: str = Field(min_length=1)
    execution_matrix: ExecutionMatrix | None = None


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object expected: {path}")
    return payload


def _stable_payload_sha256(payload: Any) -> str:
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _load_config_payload(config_path: Path) -> dict[str, Any]:
    payload = _read_json(config_path)
    try:
        validated = AutoresearchConfig.model_validate(payload)
    except ValidationError:
        return payload
    return validated.model_dump(mode="json")


def _parse_seed_index_from_run_id(run_id: str | None) -> int | None:
    if not run_id:
        return None
    parts = run_id.split("_")
    if len(parts) >= 2 and parts[1].isdigit():
        return int(parts[1])
    return None


def _extract_config_evaluation_seeds(config: dict[str, Any]) -> tuple[int, ...]:
    experiment = config.get("experiment")
    if not isinstance(experiment, dict):
        return ()
    raw = experiment.get("evaluation_seeds")
    if not isinstance(raw, (list, tuple)):
        return ()
    return tuple(int(seed) for seed in raw)


def _validated_autoresearch_config(
    config: dict[str, Any],
) -> AutoresearchConfig | None:
    try:
        return AutoresearchConfig.model_validate(config)
    except ValidationError:
        return None


def _selected_execution_run(
    execution_matrix: ExecutionMatrix,
    *,
    seed_index: int | None,
    model_random_state: int | None,
) -> ExecutionMatrixRun | None:
    if seed_index is None:
        return None

    runs = execution_matrix.build_runs()
    if seed_index > len(runs):
        raise ValueError(
            f"seed_index exceeds execution_matrix length: {seed_index} > {len(runs)}"
        )

    run = runs[seed_index - 1]
    if model_random_state is not None and run.model_random_state != model_random_state:
        raise ValueError(
            "Resolved model_random_state does not match execution_matrix selected run."
        )
    return run


def _build_evaluation_input_contract(
    validated: AutoresearchConfig,
    *,
    seed_index: int | None,
    model_random_state: int | None,
) -> EvaluationInputContract:
    execution_matrix = build_execution_matrix_from_config(validated)
    return EvaluationInputContract(
        dataset=validated.dataset,
        input_data=validated.experiment.input_data,
        split=validated.split,
        rolling_windows=validated.rolling_windows,
        evaluation_contract=validated.evaluation_contract,
        execution_matrix=execution_matrix,
        selected_run=_selected_execution_run(
            execution_matrix,
            seed_index=seed_index,
            model_random_state=model_random_state,
        ),
    )


def _load_legacy_runtime_seed(runtime_params_path: Path | None) -> int | None:
    if runtime_params_path is None:
        return None
    payload = _read_json(runtime_params_path)
    unknown_keys = sorted(set(payload) - LEGACY_RUNTIME_PARAM_KEYS)
    if unknown_keys:
        raise ValueError(f"Unknown runtime params requested: {unknown_keys}")
    seed = payload.get("model_random_state")
    return None if seed is None else int(seed)


def resolve_runtime_seed_parameters(
    *,
    config: dict[str, Any],
    seed_index: int | None = None,
    run_id: str | None = None,
    runtime_params_path: Path | None = None,
    model_random_state: int | None = None,
) -> tuple[tuple[int, ...], int | None, EvaluationRuntimeParameters, str]:
    config_evaluation_seeds = _extract_config_evaluation_seeds(config)
    resolved_seed_index = seed_index or _parse_seed_index_from_run_id(run_id)
    resolved_config_seed: int | None = None
    if resolved_seed_index is not None and config_evaluation_seeds:
        if resolved_seed_index > len(config_evaluation_seeds):
            raise ValueError(
                "seed_index exceeds experiment.evaluation_seeds length: "
                f"{resolved_seed_index} > {len(config_evaluation_seeds)}"
            )
        resolved_config_seed = config_evaluation_seeds[resolved_seed_index - 1]

    legacy_runtime_seed = _load_legacy_runtime_seed(runtime_params_path)
    explicit_seed = None if model_random_state is None else int(model_random_state)

    if (
        legacy_runtime_seed is not None
        and explicit_seed is not None
        and legacy_runtime_seed != explicit_seed
    ):
        raise ValueError(
            "runtime_params_path.model_random_state and model_random_state must match."
        )

    candidate_legacy_seed = (
        explicit_seed if explicit_seed is not None else legacy_runtime_seed
    )

    if resolved_config_seed is not None:
        if (
            candidate_legacy_seed is not None
            and candidate_legacy_seed != resolved_config_seed
        ):
            raise ValueError(
                "Runtime seed override is no longer allowed; "
                "config.experiment.evaluation_seeds must remain authoritative."
            )
        effective_seed = resolved_config_seed
        parameter_source = "config.experiment.evaluation_seeds"
    else:
        effective_seed = candidate_legacy_seed
        if effective_seed is None:
            effective_seed = model_random_state_for_config(config)
            parameter_source = "config.model_default"
        else:
            parameter_source = "legacy.runtime_params"

    return (
        config_evaluation_seeds,
        resolved_seed_index,
        EvaluationRuntimeParameters(model_random_state=effective_seed),
        parameter_source,
    )


def resolve_evaluation_model_parameters(
    config: dict[str, Any],
    *,
    model_random_state: int | None,
) -> tuple[EvaluationModelParameters, str]:
    validated = _validated_autoresearch_config(config)
    model = config.get("model")
    if not isinstance(model, dict):
        raise ValueError("config.model must be an object")

    kind = str(model.get("kind") or "").strip()
    if not kind:
        raise ValueError("config.model.kind must be configured")

    params = model.get("params")
    normalized_params = dict(params) if isinstance(params, dict) else {}

    candidate_name: str | None = None
    model_parameter_source = "parameter_context.fallback"
    if validated is not None:
        for candidate in validated.experiment.model_search.candidates:
            if candidate.kind == kind and candidate.params == normalized_params:
                candidate_name = candidate.name
                break
        common = validated.experiment.common_hyperparameters
        positive_class_weight = common.positive_class_weight
        imputer_strategy = common.imputer_strategy
        prediction_top_k = common.prediction_top_k
        random_state_source = common.random_state_source
        model_parameter_source = "config.experiment.common_hyperparameters"
    else:
        experiment = config.get("experiment")
        if isinstance(experiment, dict):
            model_search = experiment.get("model_search")
            if isinstance(model_search, dict):
                raw_candidates = model_search.get("candidates")
                if isinstance(raw_candidates, list):
                    for candidate in raw_candidates:
                        if not isinstance(candidate, dict):
                            continue
                        if (
                            candidate.get("kind") == kind
                            and candidate.get("params") == normalized_params
                        ):
                            raw_name = candidate.get("name")
                            if raw_name is not None:
                                candidate_name = str(raw_name)
                            break

        positive_class_weight = float(
            model.get(
                "positive_class_weight",
                (
                    (config.get("experiment") or {}).get("common_hyperparameters") or {}
                ).get(
                    "positive_class_weight",
                    1.0,
                ),
            )
        )
        imputer_strategy = str(
            ((config.get("experiment") or {}).get("common_hyperparameters") or {}).get(
                "imputer_strategy",
                "median",
            )
        )
        prediction_top_k = int(
            ((config.get("experiment") or {}).get("common_hyperparameters") or {}).get(
                "prediction_top_k",
                3,
            )
        )
        random_state_source = str(
            ((config.get("experiment") or {}).get("common_hyperparameters") or {}).get(
                "random_state_source",
                "parameter_context.runtime_seed",
            )
        )
        if candidate_name is not None:
            model_parameter_source = "config.experiment.model_search"
        elif "positive_class_weight" in model:
            model_parameter_source = "config.model"

    return (
        EvaluationModelParameters(
            candidate_name=candidate_name,
            kind=kind,
            params=normalized_params,
            positive_class_weight=positive_class_weight,
            imputer_strategy=imputer_strategy,
            prediction_top_k=prediction_top_k,
            random_state=model_random_state,
            random_state_source=random_state_source,
        ),
        model_parameter_source,
    )


def load_evaluation_parameter_context(
    *,
    config_path: Path,
    seed_index: int | None = None,
    run_id: str | None = None,
    runtime_params_path: Path | None = None,
    model_random_state: int | None = None,
) -> EvaluationParameterContext:
    """설정 파일을 단일 소스로 읽어 불변 실행 컨텍스트를 만든다.

    runtime_params_path / model_random_state 는 더 이상 오버라이드가 아니라,
    기존 호출부와의 호환을 위해 config 기반 해석 결과와 일치하는지만 검증한다.
    """

    config_bytes = config_path.read_bytes()
    config = _load_config_payload(config_path)
    (
        config_evaluation_seeds,
        resolved_seed_index,
        runtime_params,
        parameter_source,
    ) = resolve_runtime_seed_parameters(
        config=config,
        seed_index=seed_index,
        run_id=run_id,
        runtime_params_path=runtime_params_path,
        model_random_state=model_random_state,
    )
    model_parameters, model_parameter_source = resolve_evaluation_model_parameters(
        config,
        model_random_state=runtime_params.model_random_state,
    )
    validated_config = _validated_autoresearch_config(config)
    input_contract = (
        _build_evaluation_input_contract(
            validated_config,
            seed_index=resolved_seed_index,
            model_random_state=runtime_params.model_random_state,
        )
        if validated_config is not None
        else None
    )

    return EvaluationParameterContext(
        config_path=str(config_path.resolve()),
        config_sha256=sha256(config_bytes).hexdigest(),
        config=config,
        evaluation_seeds=config_evaluation_seeds,
        seed_index=resolved_seed_index,
        run_id=run_id,
        runtime_params=runtime_params,
        model_parameters=model_parameters,
        parameter_source=parameter_source,
        model_parameter_source=model_parameter_source,
        input_contract=input_contract,
        input_contract_signature=(
            _stable_payload_sha256(
                input_contract.model_dump(
                    mode="json",
                    exclude={"selected_run"},
                )
            )
            if input_contract is not None
            else None
        ),
    )


def load_seed_matrix_parameter_context(
    *,
    config_path: Path,
    evaluation_seeds: tuple[int, ...] | None = None,
    group_id: str | None = None,
    max_workers: int | None = None,
    execution_journal_path: Path | None = None,
) -> SeedMatrixParameterContext:
    if config_path.exists():
        config_bytes = config_path.read_bytes()
        config = _load_config_payload(config_path)
    else:
        config_bytes = b"{}"
        config = {}

    if evaluation_seeds is not None:
        resolved_evaluation_seeds = validate_evaluation_seeds(evaluation_seeds)
        evaluation_seed_source = "cli.evaluation_seeds"
    else:
        config_evaluation_seeds = _extract_config_evaluation_seeds(config)
        if config_evaluation_seeds:
            resolved_evaluation_seeds = validate_evaluation_seeds(
                config_evaluation_seeds
            )
            evaluation_seed_source = "config.experiment.evaluation_seeds"
        else:
            resolved_evaluation_seeds = DEFAULT_EVALUATION_SEEDS
            evaluation_seed_source = "execution_matrix.default_evaluation_seeds"

    resolved_group_id = group_id or DEFAULT_EXECUTION_GROUP_ID
    group_id_source = (
        "cli.group_id" if group_id else "execution_matrix.default_group_id"
    )

    resolved_max_workers = 1 if max_workers is None else int(max_workers)
    if resolved_max_workers < 1:
        raise ValueError("max_workers must be >= 1")
    max_workers_source = (
        "cli.max_workers"
        if max_workers is not None
        else "seed_matrix.default_max_workers"
    )

    runtime_params = SeedMatrixRuntimeParameters(
        evaluation_seeds=resolved_evaluation_seeds,
        group_id=resolved_group_id,
        max_workers=resolved_max_workers,
        execution_journal_path=(
            str(execution_journal_path.resolve())
            if execution_journal_path is not None
            else None
        ),
    )
    validated_config = _validated_autoresearch_config(config)
    execution_matrix = (
        build_execution_matrix_from_config(
            validated_config,
            evaluation_seeds=resolved_evaluation_seeds,
        )
        if validated_config is not None
        else None
    )

    return SeedMatrixParameterContext(
        config_path=str(config_path.resolve()),
        config_sha256=sha256(config_bytes).hexdigest(),
        config=config,
        runtime_params=runtime_params,
        evaluation_seed_source=evaluation_seed_source,
        group_id_source=group_id_source,
        max_workers_source=max_workers_source,
        execution_journal_path_source=(
            "cli.execution_journal_path"
            if execution_journal_path is not None
            else "seed_matrix.output_dir_default"
        ),
        execution_matrix=execution_matrix,
    )
