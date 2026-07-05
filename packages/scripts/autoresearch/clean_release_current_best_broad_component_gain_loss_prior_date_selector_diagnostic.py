"""Gain/loss prior-date switch selector over current-best plus broad outputs."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from autoresearch import (  # noqa: E402
    adhoc_current_best_broad_component_output_complement_diagnostic as complement,
)
from autoresearch import (  # noqa: E402
    clean_release_current_best_broad_component_prior_date_selector_diagnostic as broad_selector,
)
from autoresearch import (  # noqa: E402
    clean_release_current_best_broad_component_source_score_selector_diagnostic as source_score,
)
from autoresearch import (  # noqa: E402
    clean_release_current_best_full_field_one_swap_static_repair_diagnostic as static_repair,
)
from autoresearch import (  # noqa: E402
    clean_release_top_clean_artifact_source_selector_probe as artifact_source,
)
from autoresearch.clean_release_row_feature_full_policy_classifier_probe import (  # noqa: E501
    DEFAULT_CACHE_DIR,
    DEFAULT_CONFIG,
)
from autoresearch.clean_release_row_feature_full_policy_output_agreement_prior_date_classifier_switch_probe import (  # noqa: E501
    _window_summary,
)
from autoresearch.clean_top50_history_overlay_probe import (  # noqa: E402
    _candidate_key,
    _summarize_predictions,
)

DEFAULT_SOURCE_ARTIFACT = DEFAULT_CACHE_DIR / (
    "clean_release_current_best_one_swap_broad_component_intersection_after_"
    "cached_probability_fallback_only_repro_diagnostic.json"
)
DEFAULT_OUTPUT = DEFAULT_CACHE_DIR / (
    "clean_release_current_best_broad_component_gain_loss_prior_date_"
    "selector_diagnostic.json"
)


@dataclass(frozen=True, slots=True)
class SurfaceSpec:
    score_spec_name: str
    top_k: int

    @property
    def name(self) -> str:
        return f"{self.score_spec_name}/top{self.top_k}"


@dataclass(frozen=True, slots=True)
class ModelSpec:
    model_c: float
    min_rows: int
    min_positive_rows: int
    cold_gain_probability: float
    cold_loss_probability: float
    cold_exact_probability: float

    @property
    def name(self) -> str:
        return (
            f"c{self.model_c:g}"
            f"/rows{self.min_rows}"
            f"/pos{self.min_positive_rows}"
            f"/coldg{self.cold_gain_probability:g}"
            f"/coldl{self.cold_loss_probability:g}"
            f"/colde{self.cold_exact_probability:g}"
        )


@dataclass(frozen=True, slots=True)
class ChoiceSpec:
    gain_weight: float
    loss_weight: float
    exact_weight: float
    signal_name: str
    signal_weight: float
    rank_penalty: float
    switch_margin: float
    max_surface_rank: int

    @property
    def name(self) -> str:
        return (
            f"gain{self.gain_weight:g}"
            f"/loss{self.loss_weight:g}"
            f"/exact{self.exact_weight:g}"
            f"/sig{self.signal_name}"
            f"/sigw{self.signal_weight:g}"
            f"/rankpen{self.rank_penalty:g}"
            f"/margin{self.switch_margin:g}"
            f"/maxrank{self.max_surface_rank}"
        )


@dataclass(frozen=True, slots=True)
class FitResult:
    model: Pipeline | None
    prior: float
    train_rows: int
    positive_rows: int
    negative_rows: int

    @property
    def fitted(self) -> bool:
        return self.model is not None


def _safe_mean(values: list[float]) -> float:
    return mean(values) if values else 0.0


def _surface_specs() -> tuple[SurfaceSpec, ...]:
    return tuple(
        SurfaceSpec(score_spec_name=score_spec_name, top_k=top_k)
        for score_spec_name in (
            "base/cur0/minsupport1",
            "prior_hit2/cur0.3/minsupport1",
            "prior_exact/cur0.3/minsupport1",
            "agreement_prior/cur0/minsupport1",
        )
        for top_k in (1, 2, 3)
    )


def _model_specs() -> tuple[ModelSpec, ...]:
    return (
        ModelSpec(0.15, 40, 3, 0.0, 1.0, 0.0),
        ModelSpec(1.0, 40, 3, 0.0, 1.0, 0.0),
        ModelSpec(0.15, 80, 5, 0.0, 1.0, 0.0),
        ModelSpec(1.0, 80, 5, 0.0, 1.0, 0.0),
    )


def _choice_specs() -> tuple[ChoiceSpec, ...]:
    return tuple(
        ChoiceSpec(
            gain_weight=gain_weight,
            loss_weight=loss_weight,
            exact_weight=exact_weight,
            signal_name=signal_name,
            signal_weight=signal_weight,
            rank_penalty=rank_penalty,
            switch_margin=switch_margin,
            max_surface_rank=max_surface_rank,
        )
        for gain_weight in (1.0, 2.0)
        for loss_weight in (1.5, 3.0)
        for exact_weight in (0.0, 0.25)
        for signal_name, signal_weight in (
            ("none", 0.0),
            ("surface_score", 0.02),
            ("support_blend", 0.02),
        )
        for rank_penalty in (0.0, 0.02)
        for switch_margin in (0.0, 0.05, 0.1)
        for max_surface_rank in (1, 2, 3)
    )


def _score_spec_by_name() -> dict[str, source_score.SourceScoreSpec]:
    return {spec.name: spec for spec in source_score._selector_specs()}


def _surface_score(
    *,
    row: dict[str, Any],
    score_spec: source_score.SourceScoreSpec,
    component_count: int,
) -> float:
    return source_score._candidate_score(
        row=row,
        spec=score_spec,
        component_count=component_count,
    )


def _rank_surface_rows(
    *,
    rows: list[dict[str, Any]],
    surface: SurfaceSpec,
    score_spec: source_score.SourceScoreSpec,
    component_count: int,
) -> list[dict[str, Any]]:
    eligible = source_score._eligible_rows(rows=rows, spec=score_spec)
    ranked = sorted(
        eligible,
        key=lambda row: (
            _surface_score(
                row=row,
                score_spec=score_spec,
                component_count=component_count,
            ),
            float(row["support_count"]),
            float(row["base_score"]),
            float(row["current_overlap"]),
            tuple(-chul_no for chul_no in row["combo"]),
        ),
        reverse=True,
    )
    default_rows = [row for row in rows if float(row["is_current_best"]) >= 1.0]
    by_combo: dict[tuple[int, int, int], dict[str, Any]] = {}
    for row in default_rows + ranked[: surface.top_k]:
        copy = dict(row)
        combo = broad_selector._combo_key(copy["combo"])
        if combo in by_combo:
            continue
        if float(copy["is_current_best"]) >= 1.0:
            copy["surface_rank"] = 0.0
            copy["surface_rank_score"] = 1.0
        else:
            rank = next(
                index
                for index, candidate in enumerate(ranked, start=1)
                if broad_selector._combo_key(candidate["combo"]) == combo
            )
            copy["surface_rank"] = float(rank)
            copy["surface_rank_score"] = 1.0 - (
                float(rank - 1) / float(max(surface.top_k - 1, 1))
            )
        copy["surface_score"] = _surface_score(
            row=copy,
            score_spec=score_spec,
            component_count=component_count,
        )
        copy["surface_name"] = surface.name
        by_combo[combo] = copy
    return sorted(
        by_combo.values(),
        key=lambda row: (
            float(row["is_current_best"]) < 1.0,
            float(row["surface_rank"]),
            tuple(int(chul_no) for chul_no in row["combo"]),
        ),
    )


def _support_blend(row: dict[str, Any]) -> float:
    return (
        float(row["support_fraction"])
        + float(row["pair_support_sum"]) / 201.0
        + float(row["horse_support_sum"]) / 201.0
        + float(row["source_match_mean"])
    )


def _signal(row: dict[str, Any], name: str) -> float:
    if name == "none":
        return 0.0
    if name == "surface_score":
        return float(row["surface_score"])
    if name == "support_blend":
        return _support_blend(row)
    return float(row.get(name, 0.0))


def _augment_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    default_row = next(row for row in rows if float(row["is_current_best"]) >= 1.0)
    default_exact = float(default_row["exact_label"])
    fields = (
        "base_score",
        "support_fraction",
        "source_exact_mean",
        "source_hit2_mean",
        "source_match_mean",
        "pair_support_sum",
        "horse_support_sum",
    )
    augmented: list[dict[str, Any]] = []
    for row in rows:
        copy = dict(row)
        row_exact = float(copy["exact_label"])
        is_switch = float(copy["is_current_best"]) < 1.0
        copy["fallback_exact_label"] = default_exact
        copy["switch_candidate"] = float(is_switch)
        copy["net_gain_label"] = float(is_switch and row_exact >= 1.0 and default_exact < 1.0)
        copy["net_loss_label"] = float(is_switch and row_exact < 1.0 and default_exact >= 1.0)
        copy["support_blend"] = _support_blend(copy)
        copy["fallback_support_blend"] = _support_blend(default_row)
        copy["surface_score_delta"] = float(copy["surface_score"]) - float(
            default_row["surface_score"]
        )
        copy["support_blend_delta"] = float(copy["support_blend"]) - float(
            copy["fallback_support_blend"]
        )
        for field in fields:
            copy[f"fallback_{field}"] = float(default_row[field])
            copy[f"{field}_delta"] = float(copy[field]) - float(default_row[field])
        augmented.append(copy)
    return augmented


def _feature_vector(row: dict[str, Any], component_names: tuple[str, ...]) -> list[float]:
    return [
        *broad_selector._features(row, component_names),
        float(row["surface_rank_score"]),
        float(row["surface_rank"]) / 5.0,
        float(row["surface_score"]),
        float(row["support_blend"]),
        float(row["fallback_base_score"]),
        float(row["fallback_support_fraction"]),
        float(row["fallback_source_exact_mean"]),
        float(row["fallback_source_hit2_mean"]),
        float(row["fallback_source_match_mean"]),
        float(row["base_score_delta"]),
        float(row["support_fraction_delta"]),
        float(row["source_exact_mean_delta"]),
        float(row["source_hit2_mean_delta"]),
        float(row["source_match_mean_delta"]),
        float(row["pair_support_sum_delta"]) / 201.0,
        float(row["horse_support_sum_delta"]) / 201.0,
        float(row["surface_score_delta"]),
        float(row["support_blend_delta"]),
    ]


def _fit_binary_model(
    records: list[dict[str, Any]],
    *,
    component_names: tuple[str, ...],
    label_key: str,
    min_rows: int,
    min_positive_rows: int,
    cold_probability: float,
    model_c: float,
) -> FitResult:
    candidates = [
        record for record in records if float(record["switch_candidate"]) >= 1.0
    ]
    labels = np.asarray(
        [int(float(record[label_key]) >= 1.0) for record in candidates],
        dtype=int,
    )
    positives = int(np.sum(labels == 1))
    negatives = int(np.sum(labels == 0))
    prior = (
        float(np.mean(labels.astype(float)))
        if labels.size > 0
        else float(cold_probability)
    )
    if (
        len(candidates) < min_rows
        or positives < min_positive_rows
        or negatives < min_positive_rows
    ):
        return FitResult(
            model=None,
            prior=prior,
            train_rows=len(candidates),
            positive_rows=positives,
            negative_rows=negatives,
        )
    matrix = np.asarray(
        [_feature_vector(record, component_names) for record in candidates],
        dtype=float,
    )
    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    C=model_c,
                    class_weight="balanced",
                    max_iter=400,
                    random_state=20260530,
                ),
            ),
        ]
    )
    model.fit(matrix, labels)
    return FitResult(
        model=model,
        prior=prior,
        train_rows=len(candidates),
        positive_rows=positives,
        negative_rows=negatives,
    )


def _positive_probability(*, fit: FitResult, vector: list[float]) -> float:
    if fit.model is None:
        return fit.prior
    probabilities = fit.model.predict_proba(np.asarray([vector], dtype=float))
    classifier = fit.model.named_steps["model"]
    class_index = int(np.where(classifier.classes_ == 1)[0][0])
    return float(probabilities[0, class_index])


def _score_candidate(
    row: dict[str, Any],
    *,
    gain_probability: float,
    loss_probability: float,
    exact_probability: float,
    spec: ChoiceSpec,
) -> float:
    if float(row["is_current_best"]) >= 1.0:
        return 0.0
    if float(row["surface_rank"]) > spec.max_surface_rank:
        return float("-inf")
    return (
        spec.gain_weight * gain_probability
        - spec.loss_weight * loss_probability
        + spec.exact_weight * exact_probability
        + spec.signal_weight * _signal(row, spec.signal_name)
        - spec.rank_penalty * float(row["surface_rank"])
        - spec.switch_margin
    )


def _fit_models(
    history_rows: list[dict[str, Any]],
    *,
    component_names: tuple[str, ...],
    model_spec: ModelSpec,
) -> dict[str, FitResult]:
    return {
        "gain": _fit_binary_model(
            history_rows,
            component_names=component_names,
            label_key="net_gain_label",
            min_rows=model_spec.min_rows,
            min_positive_rows=model_spec.min_positive_rows,
            cold_probability=model_spec.cold_gain_probability,
            model_c=model_spec.model_c,
        ),
        "loss": _fit_binary_model(
            history_rows,
            component_names=component_names,
            label_key="net_loss_label",
            min_rows=model_spec.min_rows,
            min_positive_rows=model_spec.min_positive_rows,
            cold_probability=model_spec.cold_loss_probability,
            model_c=model_spec.model_c,
        ),
        "exact": _fit_binary_model(
            history_rows,
            component_names=component_names,
            label_key="exact_label",
            min_rows=model_spec.min_rows,
            min_positive_rows=model_spec.min_positive_rows,
            cold_probability=model_spec.cold_exact_probability,
            model_c=model_spec.model_c,
        ),
    }


def _prediction_payload(
    predictions: dict[str, tuple[int, int, int]],
) -> dict[str, list[int]]:
    return {race_id: list(combo) for race_id, combo in sorted(predictions.items())}


def _predict_online_window(
    *,
    answers: dict[str, list[int]],
    current_best_predictions: dict[str, tuple[int, int, int]],
    component_predictions: dict[str, dict[str, tuple[int, int, int]]],
    component_names: tuple[str, ...],
    surface: SurfaceSpec,
    model_specs: tuple[ModelSpec, ...],
    choice_specs: tuple[ChoiceSpec, ...],
) -> dict[str, tuple[dict[str, tuple[int, int, int]], dict[str, Any]]]:
    source_stats: dict[str, broad_selector.SourceStats] = {}
    score_spec = _score_spec_by_name()[surface.score_spec_name]
    race_ids = sorted(
        race_id for race_id in answers if race_id in current_best_predictions
    )
    names = [
        f"{model_spec.name}/{choice_spec.name}"
        for model_spec in model_specs
        for choice_spec in choice_specs
    ]
    predicted_by_name: dict[str, dict[str, tuple[int, int, int]]] = {
        name: {} for name in names
    }
    metric_values: dict[str, dict[str, list[float]]] = {
        name: {
            "switch": [],
            "switched_exact": [],
            "kept_default_exact": [],
            "selected_current": [],
            "selected_gain_probability": [],
            "selected_loss_probability": [],
            "selected_exact_probability": [],
            "pool_available": [],
            "surface_candidate_count": [],
            "net_exact_delta": [],
        }
        for name in names
    }
    fit_info: dict[str, dict[str, list[int]]] = {
        spec.name: {
            "gain_fit_dates": [],
            "loss_fit_dates": [],
            "exact_fit_dates": [],
            "cold_dates": [],
            "train_rows": [],
            "gain_positive_rows": [],
            "loss_positive_rows": [],
            "exact_positive_rows": [],
        }
        for spec in model_specs
    }
    history_rows: list[dict[str, Any]] = []

    for _date_value, date_race_ids in broad_selector._date_groups(race_ids):
        models_by_spec: dict[str, dict[str, FitResult]] = {}
        for model_spec in model_specs:
            fits = _fit_models(
                history_rows,
                component_names=component_names,
                model_spec=model_spec,
            )
            models_by_spec[model_spec.name] = fits
            model_info = fit_info[model_spec.name]
            model_info["train_rows"].append(fits["gain"].train_rows)
            model_info["gain_positive_rows"].append(fits["gain"].positive_rows)
            model_info["loss_positive_rows"].append(fits["loss"].positive_rows)
            model_info["exact_positive_rows"].append(fits["exact"].positive_rows)
            if fits["gain"].fitted:
                model_info["gain_fit_dates"].append(1)
            if fits["loss"].fitted:
                model_info["loss_fit_dates"].append(1)
            if fits["exact"].fitted:
                model_info["exact_fit_dates"].append(1)
            if not any(fit.fitted for fit in fits.values()):
                model_info["cold_dates"].append(1)

        date_rows: list[dict[str, Any]] = []
        pending_updates: list[tuple[str, tuple[int, int, int], tuple[int, int, int]]] = []
        for race_id in date_race_ids:
            answer = broad_selector._answer_combo(answers, race_id)
            current_best_combo = broad_selector._combo_key(
                current_best_predictions[race_id]
            )
            raw_rows = broad_selector._candidate_rows_for_race(
                race_id=race_id,
                answer=answer,
                current_best_combo=current_best_combo,
                component_predictions=component_predictions,
                component_names=component_names,
                source_stats=source_stats,
            )
            if not raw_rows:
                continue
            ranked_rows = _rank_surface_rows(
                rows=raw_rows,
                surface=surface,
                score_spec=score_spec,
                component_count=len(component_names),
            )
            rows = _augment_rows(ranked_rows)
            default_row = next(
                row for row in rows if float(row["is_current_best"]) >= 1.0
            )
            default_combo = broad_selector._combo_key(default_row["combo"])
            default_exact = float(default_row["exact_label"])
            exact_by_combo = {
                broad_selector._combo_key(row["combo"]): float(row["exact_label"])
                for row in rows
            }
            pool_available = float(any(value >= 1.0 for value in exact_by_combo.values()))
            probabilities_by_model: dict[str, dict[int, dict[str, float]]] = {}
            for model_spec in model_specs:
                fits = models_by_spec[model_spec.name]
                probabilities: dict[int, dict[str, float]] = {}
                for index, row in enumerate(rows):
                    if float(row["is_current_best"]) >= 1.0:
                        probabilities[index] = {
                            "gain": 0.0,
                            "loss": 0.0,
                            "exact": float(fits["exact"].prior),
                        }
                        continue
                    vector = _feature_vector(row, component_names)
                    probabilities[index] = {
                        "gain": _positive_probability(fit=fits["gain"], vector=vector),
                        "loss": _positive_probability(fit=fits["loss"], vector=vector),
                        "exact": _positive_probability(fit=fits["exact"], vector=vector),
                    }
                probabilities_by_model[model_spec.name] = probabilities
            for model_spec in model_specs:
                probabilities = probabilities_by_model[model_spec.name]
                for choice_spec in choice_specs:
                    name = f"{model_spec.name}/{choice_spec.name}"
                    scored = [
                        (
                            _score_candidate(
                                row,
                                gain_probability=probabilities[index]["gain"],
                                loss_probability=probabilities[index]["loss"],
                                exact_probability=probabilities[index]["exact"],
                                spec=choice_spec,
                            ),
                            probabilities[index],
                            row,
                        )
                        for index, row in enumerate(rows)
                    ]
                    score, probability, selected_row = max(
                        scored,
                        key=lambda item: (
                            item[0],
                            item[1]["gain"] - item[1]["loss"],
                            item[1]["exact"],
                            float(item[2]["is_current_best"]),
                            -float(item[2]["surface_rank"]),
                            tuple(-chul_no for chul_no in item[2]["combo"]),
                        ),
                    )
                    if score <= 0.0:
                        selected_row = default_row
                        probability = {"gain": 0.0, "loss": 0.0, "exact": 0.0}
                    selected_combo = broad_selector._combo_key(selected_row["combo"])
                    switched = selected_combo != default_combo
                    exact = exact_by_combo.get(selected_combo, 0.0)
                    predicted_by_name[name][race_id] = selected_combo
                    values = metric_values[name]
                    values["switch"].append(float(switched))
                    values["switched_exact"].append(float(switched and exact >= 1.0))
                    values["kept_default_exact"].append(
                        float((not switched) and exact >= 1.0)
                    )
                    values["selected_current"].append(
                        float(selected_combo == default_combo)
                    )
                    values["selected_gain_probability"].append(probability["gain"])
                    values["selected_loss_probability"].append(probability["loss"])
                    values["selected_exact_probability"].append(probability["exact"])
                    values["pool_available"].append(pool_available)
                    values["surface_candidate_count"].append(float(len(rows)))
                    values["net_exact_delta"].append(exact - default_exact)
            date_rows.extend(rows)
            pending_updates.append(
                (broad_selector.CURRENT_SOURCE, current_best_combo, answer)
            )
            for source_name in component_names:
                combo_raw = component_predictions.get(source_name, {}).get(race_id)
                if combo_raw is None:
                    continue
                pending_updates.append(
                    (source_name, broad_selector._combo_key(combo_raw), answer)
                )
        history_rows.extend(date_rows)
        for source_name, combo, answer in pending_updates:
            broad_selector._update_stats(
                stats=source_stats.setdefault(source_name, broad_selector.SourceStats()),
                combo=combo,
                answer=answer,
            )

    output: dict[str, tuple[dict[str, tuple[int, int, int]], dict[str, Any]]] = {}
    for model_spec in model_specs:
        model_info = fit_info[model_spec.name]
        for choice_spec in choice_specs:
            name = f"{model_spec.name}/{choice_spec.name}"
            values = metric_values[name]
            output[name] = (
                predicted_by_name[name],
                {
                    "choice_model": name,
                    "surface_spec": surface.name,
                    "model_spec": model_spec.name,
                    "choice_spec": choice_spec.name,
                    "switch_rate": round(_safe_mean(values["switch"]), 6),
                    "switched_exact_rate": round(
                        _safe_mean(values["switched_exact"]),
                        6,
                    ),
                    "kept_default_exact_rate": round(
                        _safe_mean(values["kept_default_exact"]),
                        6,
                    ),
                    "selected_current_best_rate": round(
                        _safe_mean(values["selected_current"]),
                        6,
                    ),
                    "avg_selected_gain_probability": round(
                        _safe_mean(values["selected_gain_probability"]),
                        6,
                    ),
                    "avg_selected_loss_probability": round(
                        _safe_mean(values["selected_loss_probability"]),
                        6,
                    ),
                    "avg_selected_exact_probability": round(
                        _safe_mean(values["selected_exact_probability"]),
                        6,
                    ),
                    "avg_surface_candidate_count": round(
                        _safe_mean(values["surface_candidate_count"]),
                        3,
                    ),
                    "avg_net_exact_delta": round(
                        _safe_mean(values["net_exact_delta"]),
                        6,
                    ),
                    "pool_exact_available_rate": round(
                        _safe_mean(values["pool_available"]),
                        6,
                    ),
                    "pool_oracle_exact_rate": round(
                        _safe_mean(values["pool_available"]),
                        6,
                    ),
                    "fallback_plus_pool_exact_available_rate": round(
                        _safe_mean(values["pool_available"]),
                        6,
                    ),
                    "fallback_plus_pool_oracle_exact_rate": round(
                        _safe_mean(values["pool_available"]),
                        6,
                    ),
                    "gain_fit_date_count": sum(model_info["gain_fit_dates"]),
                    "loss_fit_date_count": sum(model_info["loss_fit_dates"]),
                    "exact_fit_date_count": sum(model_info["exact_fit_dates"]),
                    "cold_date_count": sum(model_info["cold_dates"]),
                    "max_train_rows": max(model_info["train_rows"])
                    if model_info["train_rows"]
                    else 0,
                    "max_gain_positive_rows": max(model_info["gain_positive_rows"])
                    if model_info["gain_positive_rows"]
                    else 0,
                    "max_loss_positive_rows": max(model_info["loss_positive_rows"])
                    if model_info["loss_positive_rows"]
                    else 0,
                    "max_exact_positive_rows": max(model_info["exact_positive_rows"])
                    if model_info["exact_positive_rows"]
                    else 0,
                    "history_update": "completed_prior_eval_dates_only",
                    "feature_contract": (
                        "current_best_broad_component_prior_date_gain_loss"
                    ),
                    "selection_uses_labels": False,
                },
            )
    return output


def run_diagnostic(
    *,
    config_path: Path,
    cache_dir: Path,
    output_path: Path,
    source_artifact: Path,
    component_cache: Path,
    max_rank: int,
) -> dict[str, Any]:
    started = time.time()
    answers_by_window = complement._window_answers_only(
        config_path=config_path,
        cache_dir=cache_dir,
    )
    current_best_by_window = static_repair._load_source_predictions(source_artifact)
    broad_predictions, broad_payload = artifact_source._load_broad_predictions(
        component_cache=component_cache,
        max_rank=max_rank,
    )
    component_names = tuple(str(name) for name in broad_payload["components"])
    surfaces = _surface_specs()
    model_specs = _model_specs()
    choice_specs = _choice_specs()
    predictions_by_window: dict[
        str,
        dict[str, tuple[dict[str, tuple[int, int, int]], dict[str, Any]]],
    ] = {}
    for window_name, answers in answers_by_window.items():
        for surface in surfaces:
            rows = _predict_online_window(
                answers=answers,
                current_best_predictions=current_best_by_window[window_name],
                component_predictions=broad_predictions[window_name],
                component_names=component_names,
                surface=surface,
                model_specs=model_specs,
                choice_specs=choice_specs,
            )
            predictions_by_window.setdefault(window_name, {}).update(
                {f"{surface.name}/{name}": value for name, value in rows.items()}
            )

    names = sorted(next(iter(predictions_by_window.values())).keys())
    results: list[dict[str, Any]] = []
    predictions_by_candidate: dict[str, dict[str, dict[str, tuple[int, int, int]]]] = {}
    for name in names:
        window_rows: list[dict[str, Any]] = []
        candidate = (
            "clean_current_best_broad_component_gain_loss_prior_date_selector/"
            f"max{max_rank}/{name}"
        )
        predictions_by_candidate[candidate] = {}
        for window_name, answers in answers_by_window.items():
            predicted, diagnostics = predictions_by_window[window_name][name]
            predictions_by_candidate[candidate][window_name] = predicted
            window_rows.append(
                {
                    "name": window_name,
                    "summary": _summarize_predictions(predicted, answers),
                    "diagnostics": diagnostics,
                }
            )
        summary = _window_summary(window_rows)
        summary["robust_pool_exact_available_rate"] = round(
            min(
                row["diagnostics"]["pool_exact_available_rate"]
                for row in window_rows
            ),
            6,
        )
        summary["robust_fallback_plus_pool_exact_available_rate"] = summary[
            "robust_pool_exact_available_rate"
        ]
        results.append(
            {
                "candidate": candidate,
                "selector_spec": name,
                "summary": summary,
                "windows": window_rows,
            }
        )

    results.sort(key=_candidate_key, reverse=True)
    retained_results = results[:80]
    best_candidate = retained_results[0]["candidate"]
    payload = {
        "format_version": (
            "current-best-broad-component-gain-loss-prior-date-selector-v1"
        ),
        "diagnostic_only": True,
        "diagnostic_only_reason": (
            "Clean strict-prior-date gain/loss selector over the current-best "
            "prediction artifact plus cached broad clean component outputs. "
            "Candidate outcomes are used only after each completed eval date "
            "has already been predicted; active-date and future outcomes do "
            "not enter feature construction or model training."
        ),
        "selection_contract": (
            "clean_current_best_plus_broad_component_prior_date_gain_loss_selector"
        ),
        "source_artifact": str(source_artifact),
        "component_cache": str(component_cache),
        "max_rank": max_rank,
        "component_count": len(component_names),
        "candidate_count": len(results),
        "retained_result_count": len(retained_results),
        "surface_spec_count": len(surfaces),
        "model_spec_count": len(model_specs),
        "choice_spec_count": len(choice_specs),
        "best": retained_results[0],
        "max_overfit_safe_exact_rate": max(
            row["summary"]["overfit_safe_exact_rate"] for row in results
        ),
        "max_test_exact_3of3_rate": max(
            row["summary"]["test_exact_3of3_rate"] for row in results
        ),
        "max_robust_pool_exact_available_rate": max(
            row["summary"]["robust_pool_exact_available_rate"] for row in results
        ),
        "ge_70_test_count": sum(
            1 for row in results if row["summary"]["test_exact_3of3_rate"] >= 0.7
        ),
        "ge_70_safe_count": sum(
            1
            for row in results
            if row["summary"]["overfit_safe_exact_rate"] >= 0.7
        ),
        "predictions_by_window": {
            window_name: _prediction_payload(
                predictions_by_candidate[best_candidate][window_name]
            )
            for window_name in answers_by_window
        },
        "results": retained_results,
        "elapsed_seconds": round(time.time() - started, 2),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--source-artifact", type=Path, default=DEFAULT_SOURCE_ARTIFACT)
    parser.add_argument(
        "--component-cache",
        type=Path,
        default=artifact_source.DEFAULT_COMPONENT_CACHE,
    )
    parser.add_argument("--max-rank", type=int, default=10)
    args = parser.parse_args()
    payload = run_diagnostic(
        config_path=args.config,
        cache_dir=args.cache_dir,
        output_path=args.output,
        source_artifact=args.source_artifact,
        component_cache=args.component_cache,
        max_rank=args.max_rank,
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "candidate_count": payload["candidate_count"],
                "max_overfit_safe_exact_rate": payload[
                    "max_overfit_safe_exact_rate"
                ],
                "max_test_exact_3of3_rate": payload["max_test_exact_3of3_rate"],
                "max_robust_pool_exact_available_rate": payload[
                    "max_robust_pool_exact_available_rate"
                ],
                "ge_70_safe_count": payload["ge_70_safe_count"],
                "elapsed_seconds": payload["elapsed_seconds"],
                "best": payload["best"]["candidate"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
