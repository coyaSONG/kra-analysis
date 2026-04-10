from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import (
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

SNAPSHOT_DIR = Path(__file__).resolve().parent / "snapshots"
SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.append(str(SCRIPT_ROOT))

from evaluation.leakage_checks import check_detailed_results_for_leakage  # noqa: E402
from shared.alternative_ranking import rank_race_entries  # noqa: E402
from shared.prediction_input_schema import (  # noqa: E402
    ALTERNATIVE_RANKING_ALLOWED_FEATURES,
    PREDICTION_INPUT_NAMES,
    build_alternative_ranking_rows_for_race,
    normalize_alternative_ranking_row,
    validate_alternative_ranking_dataset_rows,
    validate_alternative_ranking_feature_names,
)
from shared.prerace_field_policy import (  # noqa: E402
    filter_prerace_payload,
    validate_operational_dataset_payload,
)

from autoresearch.dataset_artifacts import (  # noqa: E402
    OfflineEvaluationDatasetArtifacts,
    load_offline_evaluation_dataset,
    resolve_offline_evaluation_dataset_artifacts,
)
from autoresearch.parameter_context import (  # noqa: E402
    EvaluationModelParameters,
    EvaluationParameterContext,
    load_evaluation_parameter_context,
    resolve_runtime_seed_parameters,
)
from autoresearch.reproducibility import (  # noqa: E402
    write_research_evaluation_bundle,
)
from autoresearch.split_plan import build_temporal_split_plan  # noqa: E402

SAFE_FEATURES = list(PREDICTION_INPUT_NAMES)
OPERATIONAL_FEATURES = list(ALTERNATIVE_RANKING_ALLOWED_FEATURES)

MARKET_FEATURES = {
    "winOdds",
    "plcOdds",
    "odds_rank",
    "winOdds_rr",
    "plcOdds_rr",
}

VALIDATION_ISSUE_PREVIEW_LIMIT = 5


class PredictionCoverageError(RuntimeError):
    """Raised when an evaluation window does not emit a valid top-3 prediction for every race."""

    def __init__(
        self,
        message: str,
        *,
        reason_code: str = "prediction_coverage_validation_failed",
        missing_race_ids: list[str] | None = None,
        incomplete_top3_race_ids: list[str] | None = None,
        expected_race_count: int | None = None,
        predicted_race_count: int | None = None,
        train_end: str | None = None,
        eval_start: str | None = None,
        eval_end: str | None = None,
    ) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.missing_race_ids = tuple(missing_race_ids or ())
        self.incomplete_top3_race_ids = tuple(incomplete_top3_race_ids or ())
        self.expected_race_count = expected_race_count
        self.predicted_race_count = predicted_race_count
        self.train_end = train_end
        self.eval_start = eval_start
        self.eval_end = eval_end

    def to_failure_details(self) -> dict[str, Any]:
        return {
            "reason_code": self.reason_code,
            "reason": (
                "Coverage validation failed because one or more races did not emit "
                "a complete unordered top-3 prediction."
            ),
            "missing_count": len(self.missing_race_ids),
            "missing_items": list(self.missing_race_ids),
            "incomplete_top3_count": len(self.incomplete_top3_race_ids),
            "incomplete_top3_race_ids": list(self.incomplete_top3_race_ids),
            "expected_race_count": self.expected_race_count,
            "predicted_race_count": self.predicted_race_count,
            "evaluation_window": {
                "train_end": self.train_end,
                "eval_start": self.eval_start,
                "eval_end": self.eval_end,
            },
        }


def _compute_race_features(horses: list[dict]) -> list[dict]:
    module = importlib.import_module("feature_engineering")
    return module.compute_race_features(horses)


def _safe_float(value, default=np.nan) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _parse_leading_number(value, default=np.nan) -> float:
    if value in ("", None):
        return default
    text = str(value)
    match = re.match(r"^-?\d+(?:\.\d+)?", text)
    if not match:
        return default
    return _safe_float(match.group(0), default)


def _place_rate(ord1, ord2, ord3, total) -> float:
    total_count = _safe_float(total, 0.0)
    if not total_count or total_count <= 0:
        return 0.0
    return (
        _safe_float(ord1, 0.0) + _safe_float(ord2, 0.0) + _safe_float(ord3, 0.0)
    ) / total_count


def _year_place_rate(horse: dict) -> float:
    detail = horse.get("hrDetail") or {}
    starts_y = _safe_int(detail.get("rcCntY"))
    places_y = (
        _safe_int(detail.get("ord1CntY"))
        + _safe_int(detail.get("ord2CntY"))
        + _safe_int(detail.get("ord3CntY"))
    )
    if starts_y > 0:
        return places_y / (starts_y + 2)
    return _total_place_rate(horse)


def _total_place_rate(horse: dict) -> float:
    detail = horse.get("hrDetail") or {}
    starts_t = _safe_int(detail.get("rcCntT"))
    places_t = (
        _safe_int(detail.get("ord1CntT"))
        + _safe_int(detail.get("ord2CntT"))
        + _safe_int(detail.get("ord3CntT"))
    )
    return places_t / (starts_t + 15) if starts_t >= 0 else 0.0


def _sex_code(value) -> float:
    mapping = {"수": 0.0, "암": 1.0, "거": 2.0}
    return mapping.get(value, np.nan)


def _weather_code(value) -> float:
    mapping = {"맑음": 0.0, "흐림": 1.0, "비": 2.0, "눈": 3.0}
    return mapping.get(value, np.nan)


def _budam_code(value) -> float:
    mapping = {"마령": 0.0, "별정A": 1.0, "별정B": 2.0, "핸디캡": 3.0}
    return mapping.get(value, np.nan)


def _rest_risk_code(value) -> float:
    mapping = {"low": 0.0, "medium": 1.0, "high": 2.0}
    return mapping.get(value, np.nan)


def _class_code(value) -> float:
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
    return mapping.get(str(value or ""), np.nan)


def _track_pct(value) -> float:
    if value in ("", None):
        return np.nan
    match = re.search(r"\((\d+)%\)", str(value))
    if not match:
        return np.nan
    return _safe_float(match.group(1), np.nan)


def _pre_race_horse_order(horses: list[dict]) -> list[dict]:
    return sorted(
        horses,
        key=lambda horse: (
            _safe_int(horse.get("chulNo"), 999),
            str(horse.get("hrNo") or ""),
        ),
    )


def _is_blank_like(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, float):
        return not np.isfinite(value)
    return False


def _stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _coerce_chul_no(value: object) -> int | None:
    if isinstance(value, bool) or value in ("", None):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if np.isfinite(value) and value.is_integer():
            return int(value)
        return None
    match = re.search(r"\d+", str(value))
    if not match:
        return None
    return int(match.group(0))


def _normalize_race_date_text(
    value: object,
    *,
    race_id: str | None = None,
) -> str:
    candidates = [value]
    if race_id:
        candidates.append(race_id)

    for candidate in candidates:
        if candidate in ("", None):
            continue
        digits = "".join(ch for ch in str(candidate) if ch.isdigit())
        if len(digits) >= 8:
            return digits[:8]

    raise ValueError(
        f"Unable to resolve canonical race_date: race_id={race_id!r}, value={value!r}"
    )


def _population_score(value: object) -> int:
    if isinstance(value, dict):
        return sum(_population_score(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_population_score(item) for item in value)
    return 0 if _is_blank_like(value) else 1


def _select_canonical_record(candidates: list[dict]) -> dict:
    if not candidates:
        raise ValueError("Cannot select canonical record from empty candidates")
    ordered = sorted(
        (deepcopy(candidate) for candidate in candidates),
        key=lambda candidate: (-_population_score(candidate), _stable_json(candidate)),
    )
    return ordered[0]


def _percentile_rank(values: list[float], reverse: bool = False) -> list[float]:
    arr = np.asarray(values, dtype=float)
    fill = -999999.0 if reverse else 999999.0
    arr = np.where(np.isnan(arr), fill, arr)
    order = np.argsort(arr, kind="stable")
    if reverse:
        order = order[::-1]
    ranks = np.empty(len(arr), dtype=float)
    if len(arr) == 1:
        ranks[0] = 1.0
        return ranks.tolist()
    for idx, pos in enumerate(order):
        ranks[pos] = idx / (len(arr) - 1)
    return ranks.tolist()


def _validate_features(features: list[str]) -> None:
    unknown = sorted(set(features) - set(SAFE_FEATURES))
    if unknown:
        raise ValueError(f"Unknown or forbidden features requested: {unknown}")
    validate_alternative_ranking_feature_names(features)


def _sanitize_training_race_payload(race: dict) -> dict:
    filtered_race, _policy = filter_prerace_payload(deepcopy(race))
    return filtered_race


def _summarize_validation_issues(
    issues: list[str],
    *,
    sample_limit: int = VALIDATION_ISSUE_PREVIEW_LIMIT,
) -> str:
    preview = issues[:sample_limit]
    remainder = len(issues) - len(preview)
    suffix = "" if remainder <= 0 else f" ... (+{remainder} more)"
    return f"{preview}{suffix}"


def _validate_final_training_race_payload(race: dict) -> None:
    race_id = str(race.get("race_id") or "unknown")
    leakage_report = check_detailed_results_for_leakage(
        [{"race_id": race_id, "race_data": race}]
    )
    if not leakage_report["passed"]:
        raise ValueError(
            f"Race {race_id} training input leakage check failed: "
            f"{_summarize_validation_issues(leakage_report['issues'])}"
        )

    schema_report = validate_operational_dataset_payload(race)
    if not schema_report["passed"]:
        raise ValueError(
            f"Race {race_id} training input operational schema validation failed: "
            f"{_summarize_validation_issues(schema_report['violating_paths'])}"
        )


def _build_feature_rows(races: list[dict], answers: dict[str, list[int]]) -> list[dict]:
    rows: list[dict] = []
    for race in races:
        filtered_race = _sanitize_training_race_payload(race)
        horses = deepcopy(_pre_race_horse_order(filtered_race.get("horses") or []))
        if not horses:
            continue
        refreshed = _compute_race_features(deepcopy(horses))
        for horse, fresh in zip(horses, refreshed, strict=False):
            existing_features = horse.get("computed_features") or {}
            fresh_features = fresh.get("computed_features") or {}
            horse["computed_features"] = {**fresh_features, **existing_features}
        filtered_race["horses"] = horses
        filtered_race = _sanitize_training_race_payload(filtered_race)
        _validate_final_training_race_payload(filtered_race)
        local_rows = build_alternative_ranking_rows_for_race(
            filtered_race,
            actual_top3=answers.get(filtered_race["race_id"], [])[:3],
            validate_rows=True,
        )
        rows.extend(local_rows)

    return rows


def _normalize_dataset_before_split(
    races: list[dict],
    answers: dict[str, list[int]],
) -> tuple[list[dict], dict[str, list[int]], dict[str, int]]:
    race_candidates: dict[str, list[dict]] = defaultdict(list)
    duplicate_horse_group_count = 0
    dropped_horse_without_chul_count = 0

    for race in races:
        race_id = str(race.get("race_id") or "").strip()
        if not race_id:
            raise ValueError("Race sample missing race_id before split normalization")

        normalized_race = deepcopy(race)
        normalized_race["race_id"] = race_id
        normalized_race["race_date"] = _normalize_race_date_text(
            normalized_race.get("race_date")
            or (normalized_race.get("race_info") or {}).get("rcDate"),
            race_id=race_id,
        )

        horse_candidates: dict[int, list[dict]] = defaultdict(list)
        for horse in normalized_race.get("horses") or []:
            chul_no = _coerce_chul_no(horse.get("chulNo"))
            if chul_no is None:
                dropped_horse_without_chul_count += 1
                continue
            normalized_horse = deepcopy(horse)
            normalized_horse["chulNo"] = chul_no
            horse_candidates[chul_no].append(normalized_horse)

        duplicate_horse_group_count += sum(
            1 for candidates in horse_candidates.values() if len(candidates) > 1
        )
        normalized_race["horses"] = _pre_race_horse_order(
            [
                _select_canonical_record(candidates)
                for _, candidates in sorted(horse_candidates.items())
            ]
        )
        race_candidates[race_id].append(normalized_race)

    normalized_races = [
        _select_canonical_record(candidates)
        for _, candidates in sorted(
            race_candidates.items(),
            key=lambda item: (
                _normalize_race_date_text(
                    item[1][0].get("race_date"),
                    race_id=item[0],
                ),
                item[0],
            ),
        )
    ]
    normalized_races.sort(key=lambda race: (race["race_date"], race["race_id"]))

    normalized_answers: dict[str, list[int]] = {}
    for raw_race_id, raw_top3 in answers.items():
        race_id = str(raw_race_id)
        seen: set[int] = set()
        normalized_top3: list[int] = []
        values = raw_top3 if isinstance(raw_top3, list) else []
        for item in values:
            chul_no = _coerce_chul_no(item)
            if chul_no is None or chul_no in seen:
                continue
            normalized_top3.append(chul_no)
            seen.add(chul_no)
            if len(normalized_top3) == 3:
                break
        normalized_answers[race_id] = normalized_top3

    ordered_answers = {
        race_id: normalized_answers[race_id]
        for race_id in sorted(
            normalized_answers,
            key=lambda item: (_normalize_race_date_text(None, race_id=item), item),
        )
    }

    summary = {
        "input_race_count": len(races),
        "normalized_race_count": len(normalized_races),
        "duplicate_race_group_count": sum(
            1 for candidates in race_candidates.values() if len(candidates) > 1
        ),
        "duplicate_race_count": sum(
            max(len(candidates) - 1, 0) for candidates in race_candidates.values()
        ),
        "duplicate_horse_group_count": duplicate_horse_group_count,
        "dropped_horse_without_chul_count": dropped_horse_without_chul_count,
    }
    return normalized_races, ordered_answers, summary


def _normalize_feature_rows_before_split(
    rows: list[dict],
) -> tuple[list[dict], dict[str, int]]:
    row_candidates: dict[tuple[str, str, int], list[dict]] = defaultdict(list)

    for row in rows:
        normalized_row = normalize_alternative_ranking_row(row, require_label=True)
        race_id = normalized_row["race_id"]
        race_date = normalized_row["race_date"]
        chul_no = normalized_row["chulNo"]
        row_candidates[(race_date, race_id, chul_no)].append(normalized_row)

    normalized_rows = [
        _select_canonical_record(candidates)
        for _, candidates in sorted(row_candidates.items())
    ]
    validate_alternative_ranking_dataset_rows(normalized_rows, require_label=True)

    missing_feature_value_count = 0
    for row in normalized_rows:
        missing_feature_value_count += sum(
            1 for feature_name in OPERATIONAL_FEATURES if np.isnan(row[feature_name])
        )

    summary = {
        "input_row_count": len(rows),
        "normalized_row_count": len(normalized_rows),
        "duplicate_row_group_count": sum(
            1 for candidates in row_candidates.values() if len(candidates) > 1
        ),
        "duplicate_row_count": sum(
            max(len(candidates) - 1, 0) for candidates in row_candidates.values()
        ),
        "missing_feature_value_count": missing_feature_value_count,
    }
    return normalized_rows, summary


def _snapshot_order_alignment(
    races: list[dict], answers: dict[str, list[int]]
) -> dict[str, float]:
    checked = 0
    raw_match = 0
    normalized_match = 0

    for race in races:
        actual = answers.get(race["race_id"], [])[:3]
        if not actual:
            continue
        checked += 1
        raw_top3 = [horse.get("chulNo") for horse in race["horses"][:3]]
        normalized_top3 = [
            horse.get("chulNo") for horse in _pre_race_horse_order(race["horses"])[:3]
        ]
        if raw_top3 == actual:
            raw_match += 1
        if normalized_top3 == actual:
            normalized_match += 1

    return {
        "checked_races": checked,
        "raw_first3_match_rate": round(raw_match / checked, 6) if checked else 0.0,
        "normalized_first3_match_rate": round(normalized_match / checked, 6)
        if checked
        else 0.0,
    }


def _load_dataset(
    artifacts: OfflineEvaluationDatasetArtifacts,
) -> tuple[list[dict], dict[str, list[int]]]:
    return load_offline_evaluation_dataset(artifacts)


def _build_dataset_selection_snapshot(
    artifacts: OfflineEvaluationDatasetArtifacts,
) -> dict[str, Any]:
    manifest_payload = json.loads(artifacts.manifest_path.read_text(encoding="utf-8"))
    manifest_races = manifest_payload.get("races")
    if not isinstance(manifest_races, list) or not manifest_races:
        raise ValueError(
            "offline dataset manifest must contain a non-empty races list for dataset selection snapshot."
        )

    final_race_ids: list[str] = []
    for index, row in enumerate(manifest_races):
        if not isinstance(row, dict):
            raise ValueError(
                "offline dataset manifest races entries must be JSON objects: "
                f"dataset={artifacts.dataset}, index={index}"
            )
        race_id = str(row.get("race_id") or "").strip()
        if not race_id:
            raise ValueError(
                "offline dataset manifest races entries must include race_id: "
                f"dataset={artifacts.dataset}, index={index}"
            )
        final_race_ids.append(race_id)

    if len(final_race_ids) != len(set(final_race_ids)):
        raise ValueError(
            "offline dataset manifest races contains duplicate race_id values for dataset selection snapshot."
        )

    return {
        "source_artifact_path": str(artifacts.manifest_path),
        "source_artifact_sha256": sha256(
            artifacts.manifest_path.read_bytes()
        ).hexdigest(),
        "expected_race_count": len(final_race_ids),
        "final_race_ids": final_race_ids,
    }


def _build_arrays(
    rows: list[dict], features: list[str]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[int]]:
    X = np.array(
        [[row.get(name, np.nan) for name in features] for row in rows], dtype=float
    )
    y = np.array([row["target"] for row in rows], dtype=int)
    groups = np.array([row["race_id"] for row in rows])
    dates = np.array([row["race_date"] for row in rows])
    chuls = [row["chulNo"] for row in rows]
    return X, y, groups, dates, chuls


def _all_missing_features(X: np.ndarray, features: list[str]) -> list[str]:
    missing: list[str] = []
    for idx, feature in enumerate(features):
        column = X[:, idx]
        if np.isnan(column).all():
            missing.append(feature)
    return missing


def load_runtime_params(
    *,
    config: dict,
    runtime_params_path: Path | None = None,
    model_random_state: int | None = None,
) -> dict[str, int | None]:
    """기존 테스트/호출부 호환용 wrapper.

    실질적인 해석은 parameter_context 계층에서 수행한다.
    """

    _evaluation_seeds, _resolved_seed_index, runtime_params, _parameter_source = (
        resolve_runtime_seed_parameters(
            config=config,
            runtime_params_path=runtime_params_path,
            model_random_state=model_random_state,
        )
    )
    return runtime_params.model_dump(mode="json")


def _summarize(
    groups: np.ndarray,
    chuls: list[int],
    probs: np.ndarray,
    answers: dict[str, list[int]],
    race_lookup: dict[str, list[dict]] | None = None,
) -> dict[str, float | int]:
    predicted_by_race = _predict_top3_per_race(
        groups,
        chuls,
        probs,
        race_lookup=race_lookup,
    )
    prediction_rows = _build_prediction_rows(
        predicted_by_race=predicted_by_race,
        answers=answers,
    )
    return _summarize_prediction_rows(prediction_rows)


def _predict_top3_per_race(
    groups: np.ndarray,
    chuls: list[int],
    probs: np.ndarray,
    race_lookup: dict[str, list[dict]] | None = None,
) -> dict[str, list[int]]:
    bucket: dict[str, list[tuple[float, int]]] = defaultdict(list)
    for race_id, chul_no, prob in zip(groups, chuls, probs, strict=False):
        bucket[str(race_id)].append((float(prob), chul_no))

    predicted_by_race: dict[str, list[int]] = {}
    for race_id, values in bucket.items():
        predicted_by_race[race_id] = _predict_top3_for_race(
            race_lookup.get(race_id) if race_lookup else None,
            values,
        )
    return predicted_by_race


def _build_prediction_rows(
    *,
    predicted_by_race: dict[str, list[int]],
    answers: dict[str, list[int]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for race_id in sorted(predicted_by_race):
        predicted = [int(chul_no) for chul_no in predicted_by_race[race_id][:3]]
        actual = [int(chul_no) for chul_no in answers.get(race_id, [])[:3]]
        if not actual:
            continue
        hit_count = len(set(predicted) & set(actual))
        rows.append(
            {
                "race_id": race_id,
                "predicted_top3_unordered": predicted,
                "actual_top3_unordered": actual,
                "hit_count": hit_count,
                "exact_match": hit_count == 3,
            }
        )
    return rows


def _validate_prediction_coverage(
    *,
    predicted_by_race: dict[str, list[int]],
    answers: dict[str, list[int]],
    train_end: str,
    eval_start: str | None,
    eval_end: str | None,
) -> None:
    expected_race_ids = sorted(
        str(race_id) for race_id, actual in answers.items() if actual
    )
    expected_race_id_set = set(expected_race_ids)
    predicted_race_ids = sorted(
        str(race_id)
        for race_id, predicted in predicted_by_race.items()
        if race_id in expected_race_id_set and len(predicted) >= 3
    )
    predicted_race_id_set = set(predicted_race_ids)
    missing_race_ids = [
        race_id for race_id in expected_race_ids if race_id not in predicted_race_id_set
    ]
    incomplete_race_ids = sorted(
        str(race_id)
        for race_id, predicted in predicted_by_race.items()
        if race_id in expected_race_id_set and len(predicted) < 3
    )

    if not missing_race_ids:
        return

    window_label = f"train_end={train_end}, eval_start={eval_start or '-'}, eval_end={eval_end or '-'}"
    raise PredictionCoverageError(
        "prediction coverage validation failed for evaluation window "
        f"({window_label}); missing_race_ids={missing_race_ids}; "
        f"incomplete_top3_race_ids={incomplete_race_ids}",
        missing_race_ids=missing_race_ids,
        incomplete_top3_race_ids=incomplete_race_ids,
        expected_race_count=len(expected_race_ids),
        predicted_race_count=len(predicted_race_ids),
        train_end=train_end,
        eval_start=eval_start,
        eval_end=eval_end,
    )


def _summarize_prediction_rows(
    prediction_rows: list[dict[str, Any]],
) -> dict[str, float | int]:
    hits = [int(row["hit_count"]) for row in prediction_rows]
    exact = sum(1 for value in hits if value == 3)
    return {
        "races": len(hits),
        "exact_3of3": exact,
        "exact_3of3_rate": round(exact / len(hits), 6) if hits else 0.0,
        "hit_2of3": sum(1 for value in hits if value == 2),
        "hit_1of3": sum(1 for value in hits if value == 1),
        "miss_0of3": sum(1 for value in hits if value == 0),
        "avg_set_match": round(sum(value / 3 for value in hits) / len(hits), 6)
        if hits
        else 0.0,
    }


def _normalize_model_score(value: object) -> float | None:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(score):
        return None
    return score


def _predict_top3_for_race(
    race_horses: list[dict] | None,
    scored_values: list[tuple[float, int]],
) -> list[int]:
    model_scores: dict[int, float] = {}
    for raw_score, chul_no in scored_values:
        try:
            normalized_chul_no = int(chul_no)
        except (TypeError, ValueError):
            continue
        normalized_score = _normalize_model_score(raw_score)
        if normalized_score is not None:
            model_scores[normalized_chul_no] = normalized_score

    if race_horses:
        ranked_entries = rank_race_entries(
            race_horses,
            model_scores=model_scores or None,
        )
        predicted: list[int] = []
        seen: set[int] = set()
        for entry in ranked_entries:
            if entry.chul_no is None or entry.chul_no in seen:
                continue
            predicted.append(entry.chul_no)
            seen.add(entry.chul_no)
            if len(predicted) == 3:
                return predicted

    prepared: list[tuple[int, float, int]] = []
    for raw_score, chul_no in scored_values:
        try:
            normalized_chul_no = int(chul_no)
        except (TypeError, ValueError):
            continue
        normalized_score = _normalize_model_score(raw_score)
        prepared.append(
            (
                0 if normalized_score is not None else 1,
                -(normalized_score if normalized_score is not None else 0.0),
                normalized_chul_no,
            )
        )
    prepared.sort()
    return [chul_no for _flag, _score, chul_no in prepared[:3]]


def _evaluate_window(
    *,
    X: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    dates: np.ndarray,
    chuls: list[int],
    answers: dict[str, list[int]],
    race_lookup: dict[str, list[dict]],
    model_parameters: EvaluationModelParameters,
    train_end: str,
    eval_start: str | None,
    eval_end: str | None = None,
) -> dict[str, float | int]:
    return _evaluate_window_with_details(
        X=X,
        y=y,
        groups=groups,
        dates=dates,
        chuls=chuls,
        answers=answers,
        race_lookup=race_lookup,
        model_parameters=model_parameters,
        train_end=train_end,
        eval_start=eval_start,
        eval_end=eval_end,
    )["summary"]


def _evaluate_window_with_details(
    *,
    X: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    dates: np.ndarray,
    chuls: list[int],
    answers: dict[str, list[int]],
    race_lookup: dict[str, list[dict]],
    model_parameters: EvaluationModelParameters,
    train_end: str,
    eval_start: str | None,
    eval_end: str | None = None,
) -> dict[str, Any]:
    train_mask = dates <= train_end
    eval_mask = dates > train_end if eval_start is None else dates >= eval_start
    if eval_end:
        eval_mask = eval_mask & (dates <= eval_end)

    if not train_mask.any() or not eval_mask.any():
        raise ValueError(
            f"Window produced empty partition: train_end={train_end}, eval_start={eval_start}, eval_end={eval_end}"
        )

    model = _make_model(model_parameters)
    sample_weight = np.where(
        y[train_mask] == 1, model_parameters.positive_class_weight, 1.0
    )
    model.fit(X[train_mask], y[train_mask], clf__sample_weight=sample_weight)
    probs = model.predict_proba(X[eval_mask])[:, 1]

    eval_answers = {}
    for rid, ans in answers.items():
        date = rid[:8]
        if eval_start is None:
            if date <= train_end:
                continue
        elif date < eval_start:
            continue
        if eval_end and date > eval_end:
            continue
        eval_answers[rid] = ans

    predicted_by_race = _predict_top3_per_race(
        groups[eval_mask],
        [chuls[idx] for idx, flag in enumerate(eval_mask) if flag],
        probs,
        race_lookup=race_lookup,
    )
    _validate_prediction_coverage(
        predicted_by_race=predicted_by_race,
        answers=eval_answers,
        train_end=train_end,
        eval_start=eval_start,
        eval_end=eval_end,
    )
    prediction_rows = _build_prediction_rows(
        predicted_by_race=predicted_by_race,
        answers=eval_answers,
    )
    return {
        "summary": _summarize_prediction_rows(prediction_rows),
        "prediction_rows": prediction_rows,
        "window": {
            "train_end": train_end,
            "eval_start": eval_start,
            "eval_end": eval_end,
        },
    }


def _make_model(model_parameters: EvaluationModelParameters) -> Pipeline:
    params = model_parameters.params
    if model_parameters.kind == "hgb":
        clf = HistGradientBoostingClassifier(
            max_depth=params["max_depth"],
            learning_rate=params["learning_rate"],
            max_iter=params["max_iter"],
            min_samples_leaf=params["min_samples_leaf"],
            l2_regularization=params["l2_regularization"],
            random_state=model_parameters.random_state,
        )
    elif model_parameters.kind == "rf":
        clf = RandomForestClassifier(
            n_estimators=params["n_estimators"],
            max_depth=params["max_depth"],
            min_samples_leaf=params["min_samples_leaf"],
            random_state=model_parameters.random_state,
            n_jobs=-1,
        )
    elif model_parameters.kind == "et":
        clf = ExtraTreesClassifier(
            n_estimators=params["n_estimators"],
            max_depth=params["max_depth"],
            min_samples_leaf=params["min_samples_leaf"],
            random_state=model_parameters.random_state,
            n_jobs=-1,
        )
    elif model_parameters.kind == "logreg":
        clf = LogisticRegression(
            max_iter=params["max_iter"],
            C=params["C"],
            class_weight="balanced",
            random_state=model_parameters.random_state,
        )
    else:
        raise ValueError(f"Unsupported model kind: {model_parameters.kind}")

    return Pipeline(
        [
            ("imp", SimpleImputer(strategy=model_parameters.imputer_strategy)),
            ("clf", clf),
        ]
    )


def evaluate(
    config_path: Path,
    *,
    runtime_params_path: Path | None = None,
    model_random_state: int | None = None,
    seed_index: int | None = None,
    run_id: str | None = None,
    evaluation_context: EvaluationParameterContext | None = None,
) -> dict:
    context = evaluation_context or load_evaluation_parameter_context(
        config_path=config_path,
        seed_index=seed_index,
        run_id=run_id,
        runtime_params_path=runtime_params_path,
        model_random_state=model_random_state,
    )
    config = dict(context.config)
    runtime_params = context.runtime_params_dict()
    model_parameters = context.model_parameters
    features = config["features"]
    _validate_features(features)

    dataset_artifacts = resolve_offline_evaluation_dataset_artifacts(
        str(config["dataset"]),
        artifact_root=SNAPSHOT_DIR,
    )
    dataset_selection = _build_dataset_selection_snapshot(dataset_artifacts)
    races, answers = _load_dataset(dataset_artifacts)
    races, answers, dataset_normalization = _normalize_dataset_before_split(
        races, answers
    )
    race_lookup = {
        str(race["race_id"]): list(race.get("horses", []))
        for race in races
        if race.get("race_id")
    }
    rows = _build_feature_rows(races, answers)
    rows, row_normalization = _normalize_feature_rows_before_split(rows)
    X, y, groups, dates, chuls = _build_arrays(rows, features)

    split_plan = build_temporal_split_plan(
        dates=dates,
        config=config,
    )
    split = config["split"]
    primary_split = split_plan.primary_split

    dev_evaluation = _evaluate_window_with_details(
        X=X,
        y=y,
        groups=groups,
        dates=dates,
        chuls=chuls,
        answers=answers,
        race_lookup=race_lookup,
        model_parameters=model_parameters,
        train_end=primary_split.train_end,
        eval_start=None,
        eval_end=primary_split.dev_end,
    )
    dev_summary = dev_evaluation["summary"]
    test_evaluation = _evaluate_window_with_details(
        X=X,
        y=y,
        groups=groups,
        dates=dates,
        chuls=chuls,
        answers=answers,
        race_lookup=race_lookup,
        model_parameters=model_parameters,
        train_end=primary_split.train_end,
        eval_start=primary_split.test_start,
        eval_end=None,
    )
    test_summary = test_evaluation["summary"]
    robust_exact_rate = round(
        min(dev_summary["exact_3of3_rate"], test_summary["exact_3of3_rate"]), 6
    )
    blended_exact_rate = round(
        (dev_summary["exact_3of3_rate"] + test_summary["exact_3of3_rate"]) / 2, 6
    )
    rolling_results = []
    rolling_prediction_windows = []
    for window in split_plan.rolling_windows:
        rolling_evaluation = _evaluate_window_with_details(
            X=X,
            y=y,
            groups=groups,
            dates=dates,
            chuls=chuls,
            answers=answers,
            race_lookup=race_lookup,
            model_parameters=model_parameters,
            train_end=window.train_end,
            eval_start=window.eval_start,
            eval_end=window.eval_end,
        )
        summary = rolling_evaluation["summary"]
        rolling_results.append({"name": window.name, "summary": summary})
        rolling_prediction_windows.append(
            {
                "name": window.name,
                **rolling_evaluation["window"],
                "summary": summary,
                "prediction_rows": rolling_evaluation["prediction_rows"],
            }
        )

    rolling_min_exact_rate = round(
        min(
            (item["summary"]["exact_3of3_rate"] for item in rolling_results),
            default=robust_exact_rate,
        ),
        6,
    )
    rolling_mean_exact_rate = (
        round(
            (
                sum(item["summary"]["exact_3of3_rate"] for item in rolling_results)
                / len(rolling_results)
            ),
            6,
        )
        if rolling_results
        else robust_exact_rate
    )
    overfit_safe_exact_rate = round(min(robust_exact_rate, rolling_min_exact_rate), 6)

    integrity_payload = {
        **_snapshot_order_alignment(races, answers),
        "all_missing_features": _all_missing_features(X, features),
        "dataset_normalization": dataset_normalization,
        "row_normalization": row_normalization,
    }
    summary_payload = {
        "robust_exact_rate": robust_exact_rate,
        "blended_exact_rate": blended_exact_rate,
        "early_primary_exact_rate": robust_exact_rate,
        "rolling_min_exact_rate": rolling_min_exact_rate,
        "rolling_mean_exact_rate": rolling_mean_exact_rate,
        "overfit_safe_exact_rate": overfit_safe_exact_rate,
        "dev_test_gap": round(
            abs(dev_summary["exact_3of3_rate"] - test_summary["exact_3of3_rate"]),
            6,
        ),
    }

    return {
        "config_path": context.config_path,
        "config": config,
        "runtime_params": runtime_params,
        "parameter_context": context.model_dump(mode="json"),
        "input_contract": (
            context.input_contract.model_dump(mode="json")
            if context.input_contract is not None
            else None
        ),
        "dataset_selection": dataset_selection,
        "injected_model_parameters": model_parameters.model_dump(mode="json"),
        "feature_count": len(features),
        "market_feature_count": len([f for f in features if f in MARKET_FEATURES]),
        "split": split,
        "model": config["model"],
        "seeds": {"model_random_state": runtime_params["model_random_state"]},
        "integrity": integrity_payload,
        "summary": summary_payload,
        "dev": dev_summary,
        "test": test_summary,
        "rolling": rolling_results,
        "_reproducibility_artifacts": {
            "prediction_rows": {
                "format_version": "research-evaluation-prediction-rows-v1",
                "dataset": str(config["dataset"]),
                "run_id": run_id,
                "seed_index": seed_index,
                "model_random_state": runtime_params["model_random_state"],
                "dataset_selection": dataset_selection,
                "windows": [
                    {
                        "name": "dev",
                        **dev_evaluation["window"],
                        "summary": dev_summary,
                        "prediction_rows": dev_evaluation["prediction_rows"],
                    },
                    {
                        "name": "test",
                        **test_evaluation["window"],
                        "summary": test_summary,
                        "prediction_rows": test_evaluation["prediction_rows"],
                    },
                    *rolling_prediction_windows,
                ],
            },
            "metrics_summary": {
                "format_version": "research-evaluation-metrics-v1",
                "dataset": str(config["dataset"]),
                "run_id": run_id,
                "seed_index": seed_index,
                "model_random_state": runtime_params["model_random_state"],
                "feature_count": len(features),
                "market_feature_count": len(
                    [f for f in features if f in MARKET_FEATURES]
                ),
                "dataset_selection": dataset_selection,
                "integrity": integrity_payload,
                "summary": summary_payload,
                "dev": dev_summary,
                "test": test_summary,
                "rolling": rolling_results,
            },
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--runtime-params")
    parser.add_argument("--model-random-state", type=int)
    parser.add_argument("--output")
    args = parser.parse_args()

    config_path = Path(args.config)
    runtime_params_path = Path(args.runtime_params) if args.runtime_params else None
    evaluation_context = load_evaluation_parameter_context(
        config_path=config_path,
        runtime_params_path=runtime_params_path,
        model_random_state=args.model_random_state,
    )
    result = evaluate(
        config_path,
        evaluation_context=evaluation_context,
    )
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        write_research_evaluation_bundle(
            result=result,
            config_path=config_path,
            output_path=output_path,
            created_at=datetime.now().astimezone(),
            dataset_artifacts=resolve_offline_evaluation_dataset_artifacts(
                str(result["config"]["dataset"]),
                artifact_root=SNAPSHOT_DIR,
            ),
            runtime_params_path=runtime_params_path,
            runtime_params=result["runtime_params"],
        )
    print(payload)


if __name__ == "__main__":
    main()
