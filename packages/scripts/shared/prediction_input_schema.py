"""예측 입력 레지스트리와 대체 랭킹 입력 스키마 계약."""

from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evaluation.leakage_checks import check_detailed_results_for_leakage

from shared.feature_source_timing_contract import rows_for_output_field
from shared.prerace_field_metadata_schema import TRAIN_INFERENCE_FLAGS
from shared.prerace_field_policy import validate_operational_dataset_payload

ALTERNATIVE_RANKING_INPUT_SCHEMA_VERSION = "alternative-ranking-input-v1"
ALTERNATIVE_RANKING_DATASET_METADATA_VERSION = "alternative-ranking-dataset-metadata-v1"
REGISTRY_RELATIVE_PATH = Path("data/contracts/prediction_input_field_registry_v1.csv")
TIMING_CONTRACT_RELATIVE_PATH = Path(
    "data/contracts/feature_source_timing_contract_v1.csv"
)
ROOT_DIR = Path(__file__).resolve().parents[3]
REGISTRY_PATH = ROOT_DIR / REGISTRY_RELATIVE_PATH
REGISTRY_ENCODING = "utf-8"

ALTERNATIVE_RANKING_ALLOWED_FLAGS = frozenset(
    {"ALLOW", "ALLOW_SNAPSHOT_ONLY", "ALLOW_STORED_ONLY"}
)
ALTERNATIVE_RANKING_ALLOWED_AS_OF_REQUIREMENTS = frozenset(
    {
        "DIRECT_PRE_RACE",
        "PRE_CUTOFF_SNAPSHOT",
        "STORED_AS_OF_SNAPSHOT",
        "HISTORICAL_LOOKBACK_BEFORE_RACE_DATE",
    }
)
ALTERNATIVE_RANKING_FORBIDDEN_AS_OF_REQUIREMENTS = frozenset(
    {"TIMING_UNVERIFIED", "POSTRACE_ONLY"}
)
ALTERNATIVE_RANKING_FORBIDDEN_JOIN_SCOPES = frozenset({"postrace_feedback"})
ALTERNATIVE_RANKING_CONTEXT_FIELDS: tuple[str, ...] = ("race_id", "race_date", "chulNo")
ALTERNATIVE_RANKING_LABEL_FIELDS: tuple[str, ...] = ("target",)
ALTERNATIVE_RANKING_RACE_REQUIRED_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "race_id",
    "race_date",
    "race_info",
    "horses",
)
ALTERNATIVE_RANKING_RACE_OPTIONAL_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "candidate_filter",
    "meet",
)
ALTERNATIVE_RANKING_RACE_INFO_REQUIRED_FIELDS: tuple[str, ...] = (
    "rcDate",
    "rcNo",
    "rcDist",
    "track",
    "weather",
    "meet",
)
ALTERNATIVE_RANKING_RACE_INFO_OPTIONAL_FIELDS: tuple[str, ...] = (
    "budam",
    "ageCond",
    "rcName",
)
ALTERNATIVE_RANKING_RACE_CANONICAL_ALIAS_MAP: dict[str, str] = {
    "raceInfo": "race_info",
    "horses[].rank": "horses[].class_rank",
}
_COMPUTED_FEATURE_EXTRA_FIELDS = frozenset(
    {
        "horse_avg_prize",
        "horse_consistency",
        "jk_qnl_rate_t",
        "jk_qnl_rate_y",
        "recent_race_count",
        "recent_top3_count",
        "recent_top3_rate",
        "recent_win_count",
        "recent_win_rate",
        "rest_days",
        "training_missing",
    }
)
ALTERNATIVE_RANKING_VALIDATION_RULES: tuple[dict[str, str], ...] = (
    {
        "rule_id": "allowlist_columns_only",
        "description": "최종 학습 입력 row는 context/label과 registry 허용 feature만 포함해야 한다.",
    },
    {
        "rule_id": "feature_type_contract",
        "description": "context/label/feature 컬럼은 선언된 타입 계약(text/int/float/binary)을 만족해야 한다.",
    },
    {
        "rule_id": "missing_value_policy",
        "description": "context/label은 결측 금지, feature는 schema가 허용한 결측 규칙만 허용한다.",
    },
    {
        "rule_id": "forbid_hold_block_label_meta_features",
        "description": "HOLD, BLOCK, LABEL_ONLY, META_ONLY 플래그 피처는 최종 학습 입력에서 실패 처리한다.",
    },
    {
        "rule_id": "forbid_unregistered_derived_features",
        "description": "registry에 없는 신규 파생변수는 누수 후보로 간주하고 실패 처리한다.",
    },
    {
        "rule_id": "single_canonical_source_owner",
        "description": "각 허용 feature는 feature_source_timing_contract 상 정확히 하나의 canonical source block만 가져야 한다.",
    },
    {
        "rule_id": "forbid_timing_unverified_or_postrace_sources",
        "description": "TIMING_UNVERIFIED, POSTRACE_ONLY 원천을 가진 feature는 최종 학습 입력에서 실패 처리한다.",
    },
    {
        "rule_id": "forbid_postrace_feedback_joins",
        "description": "postrace_feedback join_scope 를 가진 조인 결과는 최종 학습 입력에서 실패 처리한다.",
    },
    {
        "rule_id": "derived_feature_scope_is_fixed",
        "description": "파생 변수는 source/per_entry_derived/same_race_derived/race_relative_derived 중 선언된 범위 안에서만 생성한다.",
    },
)

_FEATURE_MISSING_RULE = "allow_nan"
_TEXT_PATTERN = re.compile(r"\S")


@dataclass(frozen=True, slots=True)
class PredictionInputFieldSpec:
    prediction_input_name: str
    metadata_schema_version: str
    field_path: str
    field_role: str
    source_api: str
    source_field: str
    availability_stage: str
    validation_status: str
    operational_status: str
    train_inference_flag: str
    value_type: str
    mutable_after_publish: str
    notes: str

    def __post_init__(self) -> None:
        if self.train_inference_flag not in TRAIN_INFERENCE_FLAGS:
            raise ValueError(
                f"unsupported train_inference_flag for {self.prediction_input_name}: "
                f"{self.train_inference_flag}"
            )

    @property
    def is_operationally_allowed(self) -> bool:
        return self.train_inference_flag in ALTERNATIVE_RANKING_ALLOWED_FLAGS


@dataclass(frozen=True, slots=True)
class AlternativeRankingColumnSpec:
    name: str
    column_role: str
    dtype: str
    missing_rule: str
    derivation_scope: str
    source_field: str
    train_inference_flag: str | None = None
    notes: str = ""

    @property
    def allows_missing(self) -> bool:
        return self.missing_rule != "required"


def _load_prediction_input_specs() -> tuple[PredictionInputFieldSpec, ...]:
    with REGISTRY_PATH.open(encoding=REGISTRY_ENCODING, newline="") as handle:
        rows = csv.DictReader(handle)
        return tuple(PredictionInputFieldSpec(**row) for row in rows)


PREDICTION_INPUT_SPECS: tuple[PredictionInputFieldSpec, ...] = (
    _load_prediction_input_specs()
)
PREDICTION_INPUT_NAME_TO_SPEC = {
    spec.prediction_input_name: spec for spec in PREDICTION_INPUT_SPECS
}
PREDICTION_INPUT_NAMES: tuple[str, ...] = tuple(
    spec.prediction_input_name for spec in PREDICTION_INPUT_SPECS
)
ALTERNATIVE_RANKING_ALLOWED_FEATURES: tuple[str, ...] = tuple(
    spec.prediction_input_name
    for spec in PREDICTION_INPUT_SPECS
    if spec.is_operationally_allowed
)
ALTERNATIVE_RANKING_BLOCKED_FEATURES: tuple[str, ...] = tuple(
    spec.prediction_input_name
    for spec in PREDICTION_INPUT_SPECS
    if not spec.is_operationally_allowed
)
_PREDICTION_INPUT_NAME_SET = frozenset(PREDICTION_INPUT_NAMES)
_ALTERNATIVE_RANKING_ALLOWED_FEATURE_SET = frozenset(
    ALTERNATIVE_RANKING_ALLOWED_FEATURES
)
_ALTERNATIVE_RANKING_CONTEXT_FIELD_SET = frozenset(ALTERNATIVE_RANKING_CONTEXT_FIELDS)
_ALTERNATIVE_RANKING_LABEL_FIELD_SET = frozenset(ALTERNATIVE_RANKING_LABEL_FIELDS)
_ALTERNATIVE_RANKING_RACE_REQUIRED_TOP_LEVEL_FIELD_SET = frozenset(
    ALTERNATIVE_RANKING_RACE_REQUIRED_TOP_LEVEL_FIELDS
)
_ALTERNATIVE_RANKING_RACE_ALLOWED_TOP_LEVEL_FIELD_SET = frozenset(
    (
        *ALTERNATIVE_RANKING_RACE_REQUIRED_TOP_LEVEL_FIELDS,
        *ALTERNATIVE_RANKING_RACE_OPTIONAL_TOP_LEVEL_FIELDS,
    )
)
_ALTERNATIVE_RANKING_RACE_INFO_REQUIRED_FIELD_SET = frozenset(
    ALTERNATIVE_RANKING_RACE_INFO_REQUIRED_FIELDS
)
_ALTERNATIVE_RANKING_RACE_INFO_ALLOWED_FIELD_SET = frozenset(
    (
        *ALTERNATIVE_RANKING_RACE_INFO_REQUIRED_FIELDS,
        *ALTERNATIVE_RANKING_RACE_INFO_OPTIONAL_FIELDS,
    )
)


def _computed_feature_field_names() -> frozenset[str]:
    names: set[str] = set(_COMPUTED_FEATURE_EXTRA_FIELDS)
    prefix = "horses[].computed_features."
    for spec in PREDICTION_INPUT_SPECS:
        for token in spec.source_field.split("|"):
            source_field = token.strip()
            if source_field.startswith(prefix):
                names.add(source_field[len(prefix) :])
    return frozenset(names)


ALTERNATIVE_RANKING_ALLOWED_COMPUTED_FEATURE_FIELDS = _computed_feature_field_names()


def _derivation_scope_for_feature(spec: PredictionInputFieldSpec) -> str:
    if spec.field_role == "source":
        return "source"
    if spec.prediction_input_name.endswith("_rr"):
        return "race_relative_derived"
    if spec.prediction_input_name.endswith("_rank"):
        return "same_race_derived"
    if spec.prediction_input_name in {
        "field_size",
        "field_size_live",
        "gap_3rd_4th",
        "wet_track",
        "cancelled_count",
    }:
        return "same_race_derived"
    return "per_entry_derived"


ALTERNATIVE_RANKING_CONTEXT_COLUMN_SPECS: tuple[AlternativeRankingColumnSpec, ...] = (
    AlternativeRankingColumnSpec(
        name="race_id",
        column_role="context",
        dtype="text",
        missing_rule="required",
        derivation_scope="context",
        source_field="race.race_id",
        notes="경주 단위 고유 식별자",
    ),
    AlternativeRankingColumnSpec(
        name="race_date",
        column_role="context",
        dtype="text",
        missing_rule="required",
        derivation_scope="context",
        source_field="race.race_date",
        notes="YYYYMMDD 형식의 경주일",
    ),
    AlternativeRankingColumnSpec(
        name="chulNo",
        column_role="context",
        dtype="int",
        missing_rule="required",
        derivation_scope="context",
        source_field="horses[].chulNo",
        notes="출전번호",
    ),
)
ALTERNATIVE_RANKING_LABEL_COLUMN_SPECS: tuple[AlternativeRankingColumnSpec, ...] = (
    AlternativeRankingColumnSpec(
        name="target",
        column_role="label",
        dtype="binary",
        missing_rule="required",
        derivation_scope="label",
        source_field="answer_key.top3 membership",
        notes="top3 포함 여부 라벨",
    ),
)
ALTERNATIVE_RANKING_FEATURE_COLUMN_SPECS: tuple[AlternativeRankingColumnSpec, ...] = (
    tuple(
        AlternativeRankingColumnSpec(
            name=spec.prediction_input_name,
            column_role="feature",
            dtype="float",
            missing_rule=_FEATURE_MISSING_RULE,
            derivation_scope=_derivation_scope_for_feature(spec),
            source_field=spec.source_field,
            train_inference_flag=spec.train_inference_flag,
            notes=spec.notes,
        )
        for spec in PREDICTION_INPUT_SPECS
        if spec.is_operationally_allowed
    )
)
ALTERNATIVE_RANKING_COLUMN_SPECS: tuple[AlternativeRankingColumnSpec, ...] = (
    *ALTERNATIVE_RANKING_CONTEXT_COLUMN_SPECS,
    *ALTERNATIVE_RANKING_LABEL_COLUMN_SPECS,
    *ALTERNATIVE_RANKING_FEATURE_COLUMN_SPECS,
)
ALTERNATIVE_RANKING_COLUMN_SPEC_BY_NAME = {
    spec.name: spec for spec in ALTERNATIVE_RANKING_COLUMN_SPECS
}


def alternative_ranking_input_schema() -> dict[str, Any]:
    """실전 대체 랭킹 모델 입력 스키마를 dict로 반환한다."""

    return {
        "schema_version": ALTERNATIVE_RANKING_INPUT_SCHEMA_VERSION,
        "registry_path": str(REGISTRY_RELATIVE_PATH),
        "timing_contract_path": str(TIMING_CONTRACT_RELATIVE_PATH),
        "context_fields": ALTERNATIVE_RANKING_CONTEXT_FIELDS,
        "label_fields": ALTERNATIVE_RANKING_LABEL_FIELDS,
        "allowed_feature_names": ALTERNATIVE_RANKING_ALLOWED_FEATURES,
        "blocked_feature_names": ALTERNATIVE_RANKING_BLOCKED_FEATURES,
        "allowed_flags": tuple(sorted(ALTERNATIVE_RANKING_ALLOWED_FLAGS)),
        "allowed_as_of_requirements": tuple(
            sorted(ALTERNATIVE_RANKING_ALLOWED_AS_OF_REQUIREMENTS)
        ),
        "forbidden_as_of_requirements": tuple(
            sorted(ALTERNATIVE_RANKING_FORBIDDEN_AS_OF_REQUIREMENTS)
        ),
        "forbidden_join_scopes": tuple(
            sorted(ALTERNATIVE_RANKING_FORBIDDEN_JOIN_SCOPES)
        ),
        "validation_rules": ALTERNATIVE_RANKING_VALIDATION_RULES,
        "column_specs": [
            {
                "name": spec.name,
                "column_role": spec.column_role,
                "dtype": spec.dtype,
                "missing_rule": spec.missing_rule,
                "derivation_scope": spec.derivation_scope,
                "source_field": spec.source_field,
                "train_inference_flag": spec.train_inference_flag,
                "notes": spec.notes,
            }
            for spec in ALTERNATIVE_RANKING_COLUMN_SPECS
        ],
    }


def build_alternative_ranking_dataset_metadata(
    *,
    source: str,
    race_ids: Sequence[str | int],
    requested_limit: int | None,
    with_past_stats: bool,
    dataset_name: str | None = None,
) -> dict[str, Any]:
    """평가 데이터셋 메타데이터를 canonical 입력 스키마 계약과 함께 생성한다."""

    normalized_race_ids = tuple(
        str(race_id) for race_id in race_ids if race_id not in ("", None)
    )
    input_schema_contract = alternative_ranking_input_schema()
    metadata = {
        "dataset_metadata_version": ALTERNATIVE_RANKING_DATASET_METADATA_VERSION,
        "source": source,
        "dataset_name": dataset_name,
        "requested_limit": requested_limit,
        "race_count": len(normalized_race_ids),
        "race_ids": list(normalized_race_ids),
        "feature_schema_version": input_schema_contract["schema_version"],
        "input_schema_contract": input_schema_contract,
        "with_past_stats": with_past_stats,
    }
    return validate_alternative_ranking_dataset_metadata(metadata)


def validate_alternative_ranking_dataset_metadata(
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """데이터셋 메타데이터가 canonical 입력 스키마 계약과 정확히 일치하는지 검증한다."""

    issues: list[str] = []
    canonical_contract = alternative_ranking_input_schema()

    dataset_metadata_version = metadata.get("dataset_metadata_version")
    if dataset_metadata_version != ALTERNATIVE_RANKING_DATASET_METADATA_VERSION:
        issues.append(
            "dataset_metadata_version must be "
            f"{ALTERNATIVE_RANKING_DATASET_METADATA_VERSION}"
        )

    source = metadata.get("source")
    if not isinstance(source, str) or not source.strip():
        issues.append("source must be non-empty text")

    race_ids = metadata.get("race_ids")
    if not isinstance(race_ids, Sequence) or isinstance(race_ids, (str, bytes)):
        issues.append("race_ids must be a sequence")
        normalized_race_ids: list[str] = []
    else:
        normalized_race_ids = [str(race_id) for race_id in race_ids]
        blank_race_ids = [
            race_id for race_id in normalized_race_ids if not race_id.strip()
        ]
        if blank_race_ids:
            issues.append("race_ids must not contain blank values")

    race_count = metadata.get("race_count")
    if not isinstance(race_count, int):
        issues.append("race_count must be an int")
    elif race_count != len(normalized_race_ids):
        issues.append(
            f"race_count {race_count} does not match len(race_ids) {len(normalized_race_ids)}"
        )

    requested_limit = metadata.get("requested_limit")
    if requested_limit is not None and not isinstance(requested_limit, int):
        issues.append("requested_limit must be int or null")

    with_past_stats = metadata.get("with_past_stats")
    if not isinstance(with_past_stats, bool):
        issues.append("with_past_stats must be bool")

    feature_schema_version = metadata.get("feature_schema_version")
    if feature_schema_version != ALTERNATIVE_RANKING_INPUT_SCHEMA_VERSION:
        issues.append(
            f"feature_schema_version must be {ALTERNATIVE_RANKING_INPUT_SCHEMA_VERSION}"
        )

    input_schema_contract = metadata.get("input_schema_contract")
    try:
        serialized_contract = json.dumps(
            input_schema_contract,
            ensure_ascii=False,
            sort_keys=True,
        )
    except TypeError:
        issues.append("input_schema_contract must be JSON-serializable")
    else:
        canonical_serialized_contract = json.dumps(
            canonical_contract,
            ensure_ascii=False,
            sort_keys=True,
        )
        if serialized_contract != canonical_serialized_contract:
            issues.append(
                "input_schema_contract must match the canonical alternative ranking input schema"
            )

    if issues:
        raise ValueError(
            "Alternative ranking dataset metadata validation failed: "
            + "; ".join(issues)
        )

    return {
        "dataset_metadata_version": ALTERNATIVE_RANKING_DATASET_METADATA_VERSION,
        "source": source.strip(),
        "dataset_name": metadata.get("dataset_name"),
        "requested_limit": requested_limit,
        "race_count": race_count,
        "race_ids": normalized_race_ids,
        "feature_schema_version": ALTERNATIVE_RANKING_INPUT_SCHEMA_VERSION,
        "input_schema_contract": canonical_contract,
        "with_past_stats": with_past_stats,
    }


def validate_alternative_ranking_feature_names(features: list[str]) -> None:
    """선택된 feature 목록이 대체 랭킹 입력 스키마를 만족하는지 검증한다."""

    duplicates = sorted(name for name, count in Counter(features).items() if count > 1)
    if duplicates:
        raise ValueError(f"Duplicate prediction input features requested: {duplicates}")

    unknown = sorted(set(features) - _PREDICTION_INPUT_NAME_SET)
    if unknown:
        raise ValueError(f"Unknown prediction input features requested: {unknown}")

    blocked = sorted(set(features) - _ALTERNATIVE_RANKING_ALLOWED_FEATURE_SET)
    if blocked:
        raise ValueError(
            "Non-operational features requested for alternative ranking schema: "
            f"{blocked}"
        )

    validate_prediction_input_source_contract(features)


def validate_prediction_input_source_contract(features: list[str]) -> None:
    """선택된 feature들의 시간 계약·조인 계약이 운영 허용 범위인지 검증한다."""

    issues: list[str] = []
    for feature_name in sorted(set(features)):
        output_field = f"prediction_input.{feature_name}"
        owners = rows_for_output_field(output_field)
        if not owners:
            issues.append(f"{feature_name}: missing canonical source owner")
            continue

        owner_ids = ", ".join(row.source_block_id for row in owners)
        if len(owners) != 1:
            issues.append(
                f"{feature_name}: expected exactly one canonical source owner, found {owner_ids}"
            )

        for owner in owners:
            if owner.train_inference_flag not in ALTERNATIVE_RANKING_ALLOWED_FLAGS:
                issues.append(
                    f"{feature_name}: owner {owner.source_block_id} has non-operational "
                    f"train_inference_flag={owner.train_inference_flag}"
                )
            if (
                owner.as_of_requirement
                in ALTERNATIVE_RANKING_FORBIDDEN_AS_OF_REQUIREMENTS
            ):
                issues.append(
                    f"{feature_name}: owner {owner.source_block_id} has forbidden "
                    f"as_of_requirement={owner.as_of_requirement}"
                )
            if owner.join_scope in ALTERNATIVE_RANKING_FORBIDDEN_JOIN_SCOPES:
                issues.append(
                    f"{feature_name}: owner {owner.source_block_id} has forbidden "
                    f"join_scope={owner.join_scope}"
                )

    if issues:
        raise ValueError(
            "Prediction input source contract violations: " + "; ".join(issues)
        )


def _safe_float(value: object, default: float = math.nan) -> float:
    if value in ("", None):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: object, default: int | None = None) -> int | None:
    if value in ("", None):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_leading_number(value: object, default: float = math.nan) -> float:
    if value in ("", None):
        return default
    match = re.match(r"^-?\d+(?:\.\d+)?", str(value))
    if not match:
        return default
    return _safe_float(match.group(0), default)


def _parse_weight_delta(value: object, default: float = math.nan) -> float:
    if value in ("", None):
        return default
    match = re.search(r"\(([+-]?\d+)\)", str(value))
    if not match:
        return default
    delta = _safe_float(match.group(1), default)
    if math.isnan(delta) or not -40 <= delta <= 40:
        return default
    return delta


def _place_rate(ord1: object, ord2: object, ord3: object, total: object) -> float:
    total_count = _safe_float(total, 0.0)
    if total_count <= 0:
        return 0.0
    return (
        _safe_float(ord1, 0.0) + _safe_float(ord2, 0.0) + _safe_float(ord3, 0.0)
    ) / total_count


def _year_place_rate(horse: Mapping[str, Any]) -> float:
    detail = horse.get("hrDetail") or {}
    starts_y = _safe_int(detail.get("rcCntY"), 0) or 0
    places_y = (
        (_safe_int(detail.get("ord1CntY"), 0) or 0)
        + (_safe_int(detail.get("ord2CntY"), 0) or 0)
        + (_safe_int(detail.get("ord3CntY"), 0) or 0)
    )
    if starts_y > 0:
        return places_y / (starts_y + 2)
    return _total_place_rate(horse)


def _total_place_rate(horse: Mapping[str, Any]) -> float:
    detail = horse.get("hrDetail") or {}
    starts_t = _safe_int(detail.get("rcCntT"), 0) or 0
    places_t = (
        (_safe_int(detail.get("ord1CntT"), 0) or 0)
        + (_safe_int(detail.get("ord2CntT"), 0) or 0)
        + (_safe_int(detail.get("ord3CntT"), 0) or 0)
    )
    return places_t / (starts_t + 15) if starts_t >= 0 else 0.0


def _percentile_rank(values: list[float], *, reverse: bool = False) -> list[float]:
    normalized: list[float] = []
    fill = -999999.0 if reverse else 999999.0
    for value in values:
        number = _safe_float(value, math.nan)
        normalized.append(number if math.isfinite(number) else fill)

    if len(normalized) <= 1:
        return [0.5] * len(normalized)

    ordered_values = sorted(set(normalized), reverse=reverse)
    if len(ordered_values) <= 1:
        return [0.5] * len(normalized)

    denominator = len(ordered_values) - 1
    rank_by_value = {
        value: rank_index / denominator
        for rank_index, value in enumerate(ordered_values)
    }
    return [rank_by_value[value] for value in normalized]


def _pre_race_horse_order(horses: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        (dict(horse) for horse in horses),
        key=lambda horse: (
            _safe_int(horse.get("chulNo"), 999999) or 999999,
            str(horse.get("hrNo") or ""),
        ),
    )


def _bool_to_float(value: object) -> float:
    if value is True:
        return 1.0
    if value is False:
        return 0.0
    return math.nan


def _sex_code(value: object) -> float:
    return {"수": 0.0, "암": 1.0, "거": 2.0}.get(value, math.nan)


def _weather_code(value: object) -> float:
    return {"맑음": 0.0, "흐림": 1.0, "비": 2.0, "눈": 3.0}.get(value, math.nan)


def _budam_code(value: object) -> float:
    return {"마령": 0.0, "별정A": 1.0, "별정B": 2.0, "핸디캡": 3.0}.get(value, math.nan)


def _rest_risk_code(value: object) -> float:
    return {"low": 0.0, "medium": 1.0, "high": 2.0}.get(value, math.nan)


def _class_code(value: object) -> float:
    mapping = {
        "국6등급": 1.0,
        "국5등급": 2.0,
        "국4등급": 3.0,
        "혼4등급": 3.0,
        "국3등급": 4.0,
        "혼3등급": 4.0,
        "2등급": 5.0,
        "1등급": 6.0,
        "국OPEN": 7.0,
        "혼OPEN": 7.0,
    }
    return mapping.get(str(value or ""), math.nan)


def _track_pct(value: object) -> float:
    if value in ("", None):
        return math.nan
    match = re.search(r"\((\d+)%\)", str(value))
    if not match:
        return math.nan
    return _safe_float(match.group(1), math.nan)


def _normalize_race_date_text(
    value: object,
    *,
    race_id: str | None = None,
    info: Mapping[str, Any] | None = None,
) -> str:
    candidates = [value, race_id]
    if info is not None:
        candidates.append(info.get("rcDate"))
    for candidate in candidates:
        if candidate in ("", None):
            continue
        digits = "".join(ch for ch in str(candidate) if ch.isdigit())
        if len(digits) >= 8:
            return digits[:8]
    raise ValueError(
        f"Unable to resolve canonical race_date: race_id={race_id!r}, value={value!r}"
    )


def _normalize_text(value: object, *, field_name: str) -> str:
    text = str(value or "").strip()
    if not _TEXT_PATTERN.search(text):
        raise ValueError(f"{field_name} must be non-empty text")
    return text


def _normalize_int(value: object, *, field_name: str) -> int:
    normalized = _safe_int(value)
    if normalized is None:
        raise ValueError(f"{field_name} must be an integer")
    return normalized


def _normalize_binary(value: object, *, field_name: str) -> int:
    normalized = _safe_int(value)
    if normalized not in {0, 1}:
        raise ValueError(f"{field_name} must be binary 0/1")
    return normalized


def _normalize_feature_value(value: object) -> float:
    if value in ("", None):
        return math.nan
    try:
        normalized = float(value)
    except (TypeError, ValueError):
        return math.nan
    if not math.isfinite(normalized):
        return math.nan
    return normalized


def normalize_alternative_ranking_row(
    row: Mapping[str, Any],
    *,
    require_label: bool,
) -> dict[str, Any]:
    """단일 row를 schema 타입/결측 규칙에 맞춰 정규화한다."""

    normalized: dict[str, Any] = {}

    for spec in ALTERNATIVE_RANKING_CONTEXT_COLUMN_SPECS:
        raw_value = row.get(spec.name)
        if spec.dtype == "text":
            normalized[spec.name] = _normalize_text(raw_value, field_name=spec.name)
        elif spec.dtype == "int":
            normalized[spec.name] = _normalize_int(raw_value, field_name=spec.name)
        else:
            raise ValueError(f"Unsupported context dtype: {spec.dtype}")

    if require_label:
        for spec in ALTERNATIVE_RANKING_LABEL_COLUMN_SPECS:
            normalized[spec.name] = _normalize_binary(
                row.get(spec.name),
                field_name=spec.name,
            )

    for spec in ALTERNATIVE_RANKING_FEATURE_COLUMN_SPECS:
        normalized[spec.name] = _normalize_feature_value(row.get(spec.name))

    return normalized


def _validate_row_value_types(
    row: Mapping[str, Any],
    *,
    require_label: bool,
) -> None:
    errors: list[str] = []

    for spec in ALTERNATIVE_RANKING_CONTEXT_COLUMN_SPECS:
        value = row.get(spec.name)
        try:
            if spec.dtype == "text":
                _normalize_text(value, field_name=spec.name)
            elif spec.dtype == "int":
                _normalize_int(value, field_name=spec.name)
        except ValueError as exc:
            errors.append(str(exc))

    if require_label:
        for spec in ALTERNATIVE_RANKING_LABEL_COLUMN_SPECS:
            try:
                _normalize_binary(row.get(spec.name), field_name=spec.name)
            except ValueError as exc:
                errors.append(str(exc))

    for spec in ALTERNATIVE_RANKING_FEATURE_COLUMN_SPECS:
        value = row.get(spec.name)
        if value in ("", None):
            continue
        try:
            normalized = float(value)
        except (TypeError, ValueError):
            errors.append(f"{spec.name} must be numeric or missing")
            continue
        if math.isnan(normalized):
            continue
        if not math.isfinite(normalized):
            errors.append(f"{spec.name} must be finite or missing")

    if errors:
        raise ValueError(
            "Alternative ranking row value contract violations: " + "; ".join(errors)
        )


def validate_alternative_ranking_row(
    row: dict[str, Any],
    *,
    require_label: bool,
) -> None:
    """조립된 입력 row가 허용 스키마를 벗어나지 않는지 fail-fast 검증한다."""

    row_keys = set(row)
    missing_context = sorted(_ALTERNATIVE_RANKING_CONTEXT_FIELD_SET - row_keys)
    if missing_context:
        raise ValueError(
            f"Alternative ranking row missing context fields: {missing_context}"
        )

    if require_label and not _ALTERNATIVE_RANKING_LABEL_FIELD_SET <= row_keys:
        missing_labels = sorted(_ALTERNATIVE_RANKING_LABEL_FIELD_SET - row_keys)
        raise ValueError(
            f"Alternative ranking row missing label fields: {missing_labels}"
        )

    feature_keys = (
        row_keys
        - _ALTERNATIVE_RANKING_CONTEXT_FIELD_SET
        - _ALTERNATIVE_RANKING_LABEL_FIELD_SET
    )
    unknown = sorted(feature_keys - _PREDICTION_INPUT_NAME_SET)
    if unknown:
        raise ValueError(
            f"Alternative ranking row contains unknown feature keys: {unknown}"
        )

    blocked = sorted(feature_keys - _ALTERNATIVE_RANKING_ALLOWED_FEATURE_SET)
    if blocked:
        raise ValueError(
            f"Alternative ranking row contains disallowed feature keys: {blocked}"
        )

    validate_prediction_input_source_contract(list(feature_keys))
    _validate_row_value_types(row, require_label=require_label)

    missing_features = sorted(_ALTERNATIVE_RANKING_ALLOWED_FEATURE_SET - feature_keys)
    if missing_features:
        raise ValueError(
            "Alternative ranking row missing declared allowed features: "
            f"{missing_features}"
        )


def validate_alternative_ranking_dataset_rows(
    rows: list[dict[str, Any]],
    *,
    require_label: bool,
    sample_limit: int = 5,
) -> None:
    """최종 학습 입력 row 집합을 검증하고 위반이 하나라도 있으면 실패한다."""

    issues: list[str] = []
    for index, row in enumerate(rows):
        try:
            validate_alternative_ranking_row(row, require_label=require_label)
        except ValueError as exc:
            race_id = row.get("race_id", "unknown")
            chul_no = row.get("chulNo", "unknown")
            issues.append(f"row[{index}] race_id={race_id} chulNo={chul_no}: {exc}")

    if issues:
        preview = "; ".join(issues[:sample_limit])
        remainder = len(issues) - sample_limit
        suffix = "" if remainder <= 0 else f"; ... (+{remainder} more)"
        raise ValueError(
            f"Alternative ranking dataset row validation failed: {preview}{suffix}"
        )


def _base_row_from_race_and_horse(
    race: Mapping[str, Any],
    horse: Mapping[str, Any],
    *,
    actual_top3: set[int] | None,
) -> dict[str, Any]:
    info = race.get("race_info") or race.get("raceInfo") or {}
    features = horse.get("computed_features") or {}
    jockey = horse.get("jkDetail") or {}
    trainer = horse.get("trDetail") or {}
    horse_detail = horse.get("hrDetail") or {}
    race_id = _normalize_text(race.get("race_id"), field_name="race_id")
    race_date = _normalize_race_date_text(
        race.get("race_date"),
        race_id=race_id,
        info=info,
    )
    chul_no = _normalize_int(horse.get("chulNo"), field_name="chulNo")
    dist = _safe_int(info.get("rcDist"), 0) or 0

    row: dict[str, Any] = {
        "race_id": race_id,
        "race_date": race_date,
        "chulNo": chul_no,
        "age": _safe_float(horse.get("age")),
        "age_prime": _bool_to_float(features.get("age_prime")),
        "allowance_flag": 1.0 if str(horse.get("wgBudamBigo") or "") == "*" else 0.0,
        "budam_code": _budam_code(info.get("budam")),
        "burden_ratio": _safe_float(features.get("burden_ratio")),
        "cancelled_count": _safe_float(features.get("cancelled_count")),
        "class_code": _class_code(horse.get("class_rank")),
        "days_since_training": _safe_float(features.get("days_since_training")),
        "dist": float(dist),
        "draw_no": float(chul_no),
        "field_size": float(len(race.get("horses") or [])),
        "field_size_live": _safe_float(features.get("field_size_live")),
        "gap_3rd_4th": _safe_float(features.get("gap_3rd_4th")),
        "horse_low_sample": _bool_to_float(features.get("horse_low_sample")),
        "horse_place_rate": _safe_float(features.get("horse_place_rate")),
        "horse_skill_rank": _safe_float(features.get("horse_skill_rank")),
        "horse_starts_y": _safe_float(features.get("horse_starts_y")),
        "horse_top3_skill": _safe_float(features.get("horse_top3_skill")),
        "horse_win_rate": _safe_float(features.get("horse_win_rate")),
        "hr_starts_t": _safe_float(horse_detail.get("rcCntT")),
        "hr_starts_y": _safe_float(horse_detail.get("rcCntY")),
        "is_handicap": 1.0 if "핸디캡" in str(info.get("budam", "")) else 0.0,
        "is_large": 1.0 if len(race.get("horses") or []) >= 12 else 0.0,
        "is_mile": 1.0 if 1200 < dist <= 1600 else 0.0,
        "is_route": 1.0 if dist > 1600 else 0.0,
        "is_sprint": 1.0 if dist <= 1200 else 0.0,
        "jk_place_rate_y": _place_rate(
            jockey.get("ord1CntY"),
            jockey.get("ord2CntY"),
            jockey.get("ord3CntY"),
            jockey.get("rcCntY"),
        ),
        "jk_skill": _safe_float(features.get("jk_skill")),
        "jk_skill_rank": _safe_float(features.get("jk_skill_rank")),
        "jockey_form": _safe_float(features.get("jockey_form")),
        "jockey_place_rate": _safe_float(features.get("jockey_place_rate")),
        "jockey_recent_win_rate": _safe_float(features.get("jockey_recent_win_rate")),
        "jockey_total_place_rate": _place_rate(
            jockey.get("ord1CntT"),
            jockey.get("ord2CntT"),
            jockey.get("ord3CntT"),
            jockey.get("rcCntT"),
        ),
        "jockey_win_rate": _safe_float(features.get("jockey_win_rate")),
        "owner_skill": _safe_float(features.get("owner_skill")),
        "owner_win_rate": _safe_float(features.get("owner_win_rate")),
        "rating": _safe_float(horse.get("rating")),
        "rating_rank": _safe_float(features.get("rating_rank")),
        "recent_training": _bool_to_float(features.get("recent_training")),
        "recent_race_count": _safe_float(features.get("recent_race_count")),
        "recent_top3_count": _safe_float(features.get("recent_top3_count")),
        "recent_top3_rate": _safe_float(features.get("recent_top3_rate")),
        "recent_win_count": _safe_float(features.get("recent_win_count")),
        "recent_win_rate": _safe_float(features.get("recent_win_rate")),
        "rest_days": _safe_float(features.get("rest_days")),
        "rest_risk_code": _rest_risk_code(features.get("rest_risk")),
        "sex_code": _sex_code(horse.get("sex")),
        "total_place_rate": _total_place_rate(horse),
        "tr_place_rate_y": _place_rate(
            trainer.get("ord1CntY"),
            trainer.get("ord2CntY"),
            trainer.get("ord3CntY"),
            trainer.get("rcCntY"),
        ),
        "tr_skill": _safe_float(features.get("tr_skill")),
        "tr_skill_rank": _safe_float(features.get("tr_skill_rank")),
        "track_pct": _track_pct(info.get("track")),
        "trainer_place_rate": _safe_float(features.get("trainer_place_rate")),
        "trainer_total_place_rate": _place_rate(
            trainer.get("ord1CntT"),
            trainer.get("ord2CntT"),
            trainer.get("ord3CntT"),
            trainer.get("rcCntT"),
        ),
        "trainer_win_rate": _safe_float(features.get("trainer_win_rate")),
        "training_score": _safe_float(features.get("training_score")),
        "weather_code": _weather_code(info.get("weather")),
        "wet_track": _bool_to_float(features.get("wet_track")),
        "weight_delta": _safe_float(
            horse.get("weight_delta"),
            _parse_weight_delta(horse.get("wgHr")),
        ),
        "wgBudam": _safe_float(horse.get("wgBudam")),
        "wgHr_value": _parse_leading_number(horse.get("wgHr")),
        "wg_budam_rank": _safe_float(features.get("wg_budam_rank")),
        "year_place_rate": _year_place_rate(horse),
    }
    if actual_top3 is not None:
        row["target"] = 1 if chul_no in actual_top3 else 0
    return row


def _apply_race_relative_features(rows: list[dict[str, Any]]) -> None:
    rank_sources = {
        "rating_rr": [row["rating"] for row in rows],
        "wgBudam_rr": [row["wgBudam"] for row in rows],
        "horse_place_rate_rr": [row["horse_place_rate"] for row in rows],
        "jockey_place_rate_rr": [row["jockey_place_rate"] for row in rows],
        "trainer_place_rate_rr": [row["trainer_place_rate"] for row in rows],
        "year_place_rate_rr": [row["year_place_rate"] for row in rows],
        "total_place_rate_rr": [row["total_place_rate"] for row in rows],
        "draw_rr": [row["draw_no"] for row in rows],
    }
    reverse_features = {
        "rating_rr",
        "horse_place_rate_rr",
        "jockey_place_rate_rr",
        "trainer_place_rate_rr",
        "year_place_rate_rr",
        "total_place_rate_rr",
    }
    for feature_name, values in rank_sources.items():
        ranks = _percentile_rank(values, reverse=feature_name in reverse_features)
        for row, rank in zip(rows, ranks, strict=False):
            row[feature_name] = rank


def build_alternative_ranking_rows_for_race(
    race: Mapping[str, Any],
    *,
    actual_top3: Sequence[int] | None = None,
    validate_rows: bool = True,
) -> list[dict[str, Any]]:
    """단일 경주의 학습/평가/운영 공통 입력 row를 생성한다."""

    horses = _pre_race_horse_order(race.get("horses") or [])
    if not horses:
        return []

    actual = None
    if actual_top3 is not None:
        actual = {
            normalized
            for normalized in (_safe_int(value) for value in actual_top3[:3])
            if normalized is not None
        }

    rows = [
        _base_row_from_race_and_horse(race, horse, actual_top3=actual)
        for horse in horses
    ]
    _apply_race_relative_features(rows)
    normalized_rows = [
        normalize_alternative_ranking_row(row, require_label=actual is not None)
        for row in rows
    ]
    if validate_rows:
        validate_alternative_ranking_dataset_rows(
            normalized_rows,
            require_label=actual is not None,
        )
    return normalized_rows


def validate_alternative_ranking_race_payload(
    race: Mapping[str, Any],
) -> dict[str, Any]:
    """운영 추론용 경주 payload가 단일 입력 스키마로 row 생성 가능한지 검증한다."""

    issues: list[str] = []

    top_level_keys = set(race)
    missing_top_level_fields = sorted(
        _ALTERNATIVE_RANKING_RACE_REQUIRED_TOP_LEVEL_FIELD_SET - top_level_keys
    )
    unexpected_top_level_fields = sorted(
        top_level_keys - _ALTERNATIVE_RANKING_RACE_ALLOWED_TOP_LEVEL_FIELD_SET
    )
    alias_paths = sorted(
        alias
        for alias in ALTERNATIVE_RANKING_RACE_CANONICAL_ALIAS_MAP
        if alias == "raceInfo" and alias in race
    )

    race_info = race.get("race_info")
    missing_race_info_fields: list[str] = []
    unexpected_race_info_fields: list[str] = []
    if "race_info" in race:
        if isinstance(race_info, Mapping):
            race_info_keys = set(race_info)
            missing_race_info_fields = sorted(
                _ALTERNATIVE_RANKING_RACE_INFO_REQUIRED_FIELD_SET - race_info_keys
            )
            unexpected_race_info_fields = sorted(
                race_info_keys - _ALTERNATIVE_RANKING_RACE_INFO_ALLOWED_FIELD_SET
            )
        else:
            issues.append("race_info must be a mapping")

    unexpected_computed_feature_fields: list[str] = []
    horses = race.get("horses") or []
    if "horses" in race and not isinstance(horses, list):
        issues.append("horses must be a list")
        horses = []

    for horse in horses:
        if not isinstance(horse, Mapping):
            issues.append("horses[] entries must be mappings")
            continue
        if "rank" in horse:
            alias_paths.append("horses[].rank")
        computed_features = horse.get("computed_features")
        if isinstance(computed_features, Mapping):
            for feature_name in computed_features:
                if (
                    feature_name
                    not in ALTERNATIVE_RANKING_ALLOWED_COMPUTED_FEATURE_FIELDS
                ):
                    unexpected_computed_feature_fields.append(
                        f"horses[].computed_features.{feature_name}"
                    )

    raw_leakage_report = check_detailed_results_for_leakage(
        [{"race_id": str(race.get("race_id") or "unknown"), "race_data": race}]
    )
    operational_dataset_report = validate_operational_dataset_payload(
        dict(race) if isinstance(race, dict) else dict(race.items())
    )

    rows: list[dict[str, Any]] = []
    row_validation_error: str | None = None
    try:
        rows = build_alternative_ranking_rows_for_race(
            race,
            actual_top3=None,
            validate_rows=True,
        )
    except ValueError as exc:
        row_validation_error = str(exc)

    if missing_top_level_fields:
        issues.append(f"missing top-level fields: {missing_top_level_fields}")
    if unexpected_top_level_fields:
        issues.append(f"unexpected top-level fields: {unexpected_top_level_fields}")
    if missing_race_info_fields:
        issues.append(f"missing race_info fields: {missing_race_info_fields}")
    if unexpected_race_info_fields:
        issues.append(f"unexpected race_info fields: {unexpected_race_info_fields}")
    if alias_paths:
        alias_preview = [
            f"{path} -> {ALTERNATIVE_RANKING_RACE_CANONICAL_ALIAS_MAP[path]}"
            for path in sorted(set(alias_paths))
        ]
        issues.append(f"canonical path mismatches: {alias_preview}")
    if unexpected_computed_feature_fields:
        issues.append(
            "unexpected computed_features fields: "
            f"{sorted(set(unexpected_computed_feature_fields))}"
        )
    if not raw_leakage_report["passed"]:
        issues.append(f"raw leakage report failed: {raw_leakage_report['issues'][:10]}")
    if not operational_dataset_report["passed"]:
        issues.append(
            "operational dataset policy failed: "
            f"{operational_dataset_report['violating_paths'][:10]}"
        )
    if row_validation_error is not None:
        issues.append(f"row validation failed: {row_validation_error}")

    report = {
        "schema_version": ALTERNATIVE_RANKING_INPUT_SCHEMA_VERSION,
        "row_count": len(rows),
        "feature_count": len(ALTERNATIVE_RANKING_ALLOWED_FEATURES),
        "required_top_level_fields": ALTERNATIVE_RANKING_RACE_REQUIRED_TOP_LEVEL_FIELDS,
        "required_race_info_fields": ALTERNATIVE_RANKING_RACE_INFO_REQUIRED_FIELDS,
        "missing_top_level_fields": missing_top_level_fields,
        "unexpected_top_level_fields": unexpected_top_level_fields,
        "missing_race_info_fields": missing_race_info_fields,
        "unexpected_race_info_fields": unexpected_race_info_fields,
        "canonical_path_mismatches": [
            {
                "path": path,
                "expected": ALTERNATIVE_RANKING_RACE_CANONICAL_ALIAS_MAP[path],
            }
            for path in sorted(set(alias_paths))
        ],
        "unexpected_computed_feature_fields": sorted(
            set(unexpected_computed_feature_fields)
        ),
        "raw_leakage_report": raw_leakage_report,
        "operational_dataset_report": operational_dataset_report,
    }

    if issues:
        raise ValueError(
            "Alternative ranking race payload validation failed: " + "; ".join(issues)
        )

    return report
