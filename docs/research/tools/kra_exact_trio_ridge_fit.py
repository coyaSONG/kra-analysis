"""Offline numerical fit for one target per full declared race.

The caller must establish source, chronological split, and training authority.
This component neither loads those sources nor makes or publishes forecasts.
"""

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from math import fsum, hypot, isfinite

import numpy as np
from autoresearch.exact_trio_distribution import ExactTrioDistribution, partition_trios
from scipy.optimize import minimize

FIT_POLICY = "complete-trio-ridge-lbfgsb-v1"
_MAX_ESTIMATED_RADIUS = 1e-5
_SOLVER_OPTIONS = {
    "ftol": 1e-15,
    "gtol": 1e-11,
    "maxiter": 300,
    "maxfun": 1200,
    "maxcor": 10,
    "maxls": 20,
}


@dataclass(frozen=True, slots=True)
class FitResult:
    state: str
    race_ids: tuple[str, ...]
    feature_columns: tuple[str, ...]
    ridge: float
    coefficients: tuple[float, ...] | None = None
    objective: float | None = None
    gradient_norm: float | None = None
    estimated_stationarity_radius: float | None = None
    solver_status: int | None = None
    solver_evaluations: int | None = None
    solver_iterations: int | None = None
    policy: str = FIT_POLICY


class _NumericalFailure(ValueError):
    pass


def _finite(value):
    if not isfinite(value):
        raise _NumericalFailure("nonfinite_trio_fit_arithmetic")
    return value


def _complete_races(expected_rosters, distributions, targets):
    if (
        not expected_rosters
        or set(expected_rosters) != set(distributions)
        or set(expected_rosters) != set(targets)
    ):
        raise ValueError("trio_fit_requires_the_complete_race_population")
    if any(type(k) is not str or not k.strip() for k in expected_rosters):
        raise ValueError("invalid_frozen_race_id")
    race_ids = tuple(sorted(expected_rosters))
    cases = []
    for key in race_ids:
        full, _ = partition_trios(expected_rosters[key], ())
        distribution = distributions[key]
        if not isinstance(distribution, ExactTrioDistribution) or (
            distribution.trios != full
        ):
            raise ValueError("trio_fit_design_does_not_match_frozen_roster")
        target = targets[key]
        if not isinstance(target, Collection) or isinstance(target, (str, bytes)):
            raise ValueError("trio_fit_requires_one_defined_target_per_race")
        cases.append((distribution, tuple(target)))
    return race_ids, tuple(cases)


def _mean_objective(cases, ridge, coefficients):
    n = len(cases)
    theta = tuple(_finite(float(v)) for v in coefficients)
    # Divide before summing to keep the scale of each race contribution bounded.
    losses, gradients = zip(
        *(dist.loss_and_gradient(target, theta) for dist, target in cases), strict=True
    )
    regularization = tuple(_finite(ridge * v) for v in theta)
    cost = _finite(
        fsum(value / n for value in losses)
        + fsum(_finite(w * (v / 2)) for w, v in zip(regularization, theta, strict=True))
    )
    jacobian = [
        _finite(fsum(v / n for v in terms) + w)
        for terms, w in zip(zip(*gradients, strict=True), regularization, strict=True)
    ]
    return cost, np.array(jacobian, dtype=np.float64)


def fit_exact_trios(
    expected_rosters: Mapping[str, Collection[str]],
    distributions: Mapping[str, ExactTrioDistribution],
    targets: Mapping[str, Collection[str]],
    *,
    feature_columns: Sequence[str],
    ridge: float,
) -> FitResult:
    """Fit once within this call; rejected results do not supply coefficients."""
    if not isinstance(feature_columns, Sequence) or isinstance(
        feature_columns, (str, bytes)
    ):
        raise ValueError("trio_fit_requires_fixed_feature_order")
    columns = tuple(feature_columns)
    if (
        not columns
        or any(type(name) is not str or not name.strip() for name in columns)
        or len(set(columns)) != len(columns)
    ):
        raise ValueError("trio_fit_requires_fixed_feature_order")
    if type(ridge) not in (int, float):
        raise ValueError("trio_fit_requires_positive_finite_ridge")
    try:
        ridge = float(ridge)
    except OverflowError as exc:
        raise ValueError("trio_fit_requires_positive_finite_ridge") from exc
    if not (isfinite(ridge) and ridge > 0.0):
        raise ValueError("trio_fit_requires_positive_finite_ridge")
    race_ids, cases = _complete_races(expected_rosters, distributions, targets)
    zero = np.zeros(len(columns), dtype=np.float64)
    known = {"race_ids": race_ids, "feature_columns": columns, "ridge": ridge}

    def objective(x):
        try:
            return _mean_objective(cases, ridge, x)
        except (ValueError, OverflowError) as exc:
            raise _NumericalFailure("trio_fit_unrepresentable_objective") from exc

    # Reject invalid targets or columns before giving the solver any input.
    _mean_objective(cases, ridge, zero)
    try:
        result = minimize(
            objective, zero, method="L-BFGS-B", jac=True, options=dict(_SOLVER_OPTIONS)
        )
        solver = {
            "solver_status": int(result.status),
            "solver_evaluations": int(result.nfev),
            "solver_iterations": int(result.nit),
        }
        if not result.success:
            return FitResult("optimizer_failed", **known, **solver)
        theta = tuple(_finite(float(v)) for v in result.x)
        cost, gradient = objective(theta)
        norm = _finite(hypot(*gradient))
        radius = _finite(norm / ridge)
    except _NumericalFailure:
        return FitResult("numerical_failure", **known)

    accepted = radius <= _MAX_ESTIMATED_RADIUS
    return FitResult(
        "fit_reached_stationarity" if accepted else "stationarity_not_met",
        **known,
        **solver,
        coefficients=theta if accepted else None,
        objective=cost,
        gradient_norm=norm,
        estimated_stationarity_radius=radius,
    )
