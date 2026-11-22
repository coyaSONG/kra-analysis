"""Exercise only fictional full fields and their exact-set losses."""

import runpy
from decimal import Decimal, localcontext
from math import comb, exp, fsum, log
from pathlib import Path
from types import SimpleNamespace

import pytest

from autoresearch.exact_trio_distribution import (
    partition_trios,
    prepare_exact_trio_distribution,
)

_MODULE = (
    Path(__file__).resolve().parents[4]
    / "docs/research/tools/kra_exact_trio_ridge_fit.py"
)


@pytest.fixture
def fit():
    return runpy.run_path(str(_MODULE))["fit_exact_trios"]


def design(ids, indices, missing=(), base=None):
    trios, _ = partition_trios(ids, ())
    return prepare_exact_trio_distribution(
        ids,
        {s: 0.0 if base is None else base(s) for s in trios},
        {s: indices(s) for s in trios},
        unavailable_sets=missing,
    )


def panels(ids, distribution, labels):
    labels = {f"fixture-race-{k:04}": v for k, v in enumerate(labels)}
    return dict.fromkeys(labels, ids), dict.fromkeys(labels, distribution), labels


def optimum():
    with localcontext() as ctx:
        ctx.prec = 72
        lo, hi = Decimal(0), Decimal(3)
        for _ in range(200):
            midpoint = (lo + hi) / 2
            e = midpoint.exp()
            derivative = e / (e + 3) - Decimal("0.6") + Decimal("0.2") * midpoint
            if derivative > 0:
                hi = midpoint
            else:
                lo = midpoint
        return (hi + lo) / 2


def test_agrees_with_an_independent_high_precision_optimum(fit):
    ids = ("1", "2", "3", "4")
    a, b = ("1", "2", "3"), ("1", "2", "4")
    distribution = design(ids, lambda s: (int(s == a),))
    rosters, probabilities, observed = panels(ids, distribution, [a, a, a, b, b])
    result = fit(rosters, probabilities, observed, feature_columns=("edge",), ridge=0.2)
    assert result.state == "fit_reached_stationarity"
    assert result.policy == "complete-trio-ridge-lbfgsb-v1"
    (theta,) = result.coefficients
    error = abs(theta - float(optimum()))
    assert error < 1e-7
    assert error <= result.estimated_stationarity_radius + 1e-13
    assert result.objective == pytest.approx(
        log(exp(theta) + 3) - 0.6 * theta + 0.1 * theta**2
    )
    assert result.gradient_norm == pytest.approx(
        abs(exp(theta) / (exp(theta) + 3) - 0.6 + 0.2 * theta)
    )


def test_original_race_inputs_are_not_weighted_by_number_of_triples(fit, monkeypatch):
    a = ("1", "2", "3")
    races = {"early": (*a, "4"), "later": (*a, "4", "5")}
    ds = {k: design(v, lambda s: (int(s == a),)) for k, v in races.items()}
    calls = []

    def stop(objective, start, **kwargs):
        calls.append(kwargs)
        loss, gradient = objective(start)
        assert loss == pytest.approx((log(4) + log(10)) / 2)
        assert list(gradient) == pytest.approx([(1 / 4 - 1 + 1 / 10 - 1) / 2])
        return SimpleNamespace(status=1, nfev=1, nit=0, success=False)

    monkeypatch.setitem(fit.__globals__, "minimize", stop)
    result = fit(
        races, ds, dict.fromkeys(races, a), feature_columns=("edge",), ridge=0.2
    )
    assert len(calls) == 1 and calls[0]["jac"] is True
    assert calls[0]["method"] == "L-BFGS-B"
    assert result.state == "optimizer_failed" and result.coefficients is None
    assert result.race_ids == ("early", "later")


def test_additive_and_interaction_can_select_distinct_complete_field_modes(fit):
    ids = ("1", "2", "3", "4", "5")
    first = ("1", "2", "3")
    trios, _ = partition_trios(ids, ())
    labels = []
    for s in trios:
        count = 12 if s == first else (10 if "4" in s and "5" in s else 1)
        labels.extend([s] * count)

    def additive(s):
        return tuple(int(h in s) for h in ids[:-1])

    def interaction(s):
        return (*additive(s), int("4" in s and "5" in s))

    base = design(ids, additive)
    alternative = design(ids, interaction)
    columns = ("r1", "r2", "r3", "r4")
    a = fit(*panels(ids, base, labels), feature_columns=columns, ridge=0.002)
    b = fit(
        *panels(ids, alternative, labels),
        feature_columns=(*columns, "pair45"),
        ridge=0.002,
    )
    assert a.race_ids == b.race_ids
    assert len(a.race_ids) == 48
    assert a.state == b.state == "fit_reached_stationarity"
    assert {"4", "5"} <= set(base.mode(a.coefficients))
    assert alternative.mode(b.coefficients) == first
    assert len(alternative.log_probabilities(b.coefficients)) == comb(len(ids), 3)


def test_partition_group_mass_and_a_no_variation_field(fit):
    ids = ("1", "2", "3", "4", "5")
    a = ("1", "2", "3")
    conditioned = design(ids, lambda s: (int(s == a),), missing=(("5",),))
    f = fit(*panels(ids, conditioned, [a] * 3), feature_columns=("edge",), ridge=0.2)
    assert f.state == "fit_reached_stationarity"
    assert f.coefficients[0] > 0
    for contains in (False, True):
        before = conditioned.log_probabilities((0.0,))
        after = conditioned.log_probabilities(f.coefficients)
        assert fsum(
            exp(v) for s, v in after.items() if ("5" in s) == contains
        ) == pytest.approx(
            fsum(exp(v) for s, v in before.items() if ("5" in s) == contains)
        )
    singletons = design(ids, lambda s: (int(s == a),), missing=(ids,))
    fit0 = fit(*panels(ids, singletons, [a]), feature_columns=("edge",), ridge=0.2)
    assert fit0.state == "fit_reached_stationarity"
    assert fit0.coefficients == (0.0,)
    assert fit0.objective == pytest.approx(log(10))


def test_reordering_mapping_targets_and_rosters_does_not_change_fit(fit):
    ids = ("1", "2", "10", "12")
    a, b = ("1", "2", "10"), ("2", "10", "12")
    ds = design(ids, lambda s: (int(s == a),))
    races, probabilities, y = panels(ids, ds, [a, a, b])
    result = fit(races, probabilities, y, feature_columns=("a",), ridge=0.17)
    new_races = {k: tuple(reversed(races[k])) for k in reversed(races)}
    new_y = {k: tuple(reversed(y[k])) for k in reversed(y)}
    reversed_fit = fit(
        new_races, probabilities, new_y, feature_columns=("a",), ridge=0.17
    )
    assert result == reversed_fit
    assert ds.mode((0.0,)) == ("1", "2", "10")


@pytest.mark.parametrize(
    "change", ["missing race", "undefined", "wrong roster", "duplicate target"]
)
def test_bad_frozen_membership_never_reaches_solver(fit, monkeypatch, change):
    ids = ("1", "2", "3", "4", "5")
    ds = design(ids, lambda s: (0.0,))
    races, probabilities, targets = panels(ids, ds, [("1", "2", "3")] * 2)
    key = next(iter(races))
    if change == "missing race":
        probabilities.pop(key)
    elif change == "undefined":
        targets[key] = None
    elif change == "wrong roster":
        probabilities[key] = design(ids[:-1], lambda s: (0.0,))
    else:
        targets[key] = ("1", "1", "3")

    def cannot_fit(*args, **kwargs):
        raise AssertionError("incomplete populations cannot fit")

    monkeypatch.setitem(fit.__globals__, "minimize", cannot_fit)
    with pytest.raises(ValueError):
        fit(races, probabilities, targets, feature_columns=("edge",), ridge=0.2)


def test_claimed_solver_success_without_actual_stationarity_yields_no_model(
    fit, monkeypatch
):
    ids = ("1", "2", "3", "4")
    a = ("1", "2", "3")
    ds = design(ids, lambda s: (int(s == a),))

    def false_success(*args, **kwargs):
        return SimpleNamespace(
            status=0, nfev=2, nit=1, success=True, x=[0.0], jac=[0.0]
        )

    monkeypatch.setitem(fit.__globals__, "minimize", false_success)
    result = fit(*panels(ids, ds, [a]), feature_columns=("edge",), ridge=0.2)
    assert result.state == "stationarity_not_met" and result.coefficients is None
    assert result.gradient_norm == pytest.approx(0.75)


def test_nonfinite_trial_fails_without_coefficients(fit, monkeypatch):
    ids = ("1", "2", "3", "4")
    ds = design(ids, lambda s: (0.0,))

    def nonfinite(objective, start, **kwargs):
        objective([float("nan")])

    monkeypatch.setitem(fit.__globals__, "minimize", nonfinite)
    result = fit(*panels(ids, ds, [ids[:3]]), feature_columns=("edge",), ridge=0.2)
    assert result.state == "numerical_failure" and result.coefficients is None


def test_negligible_positive_target_mass_does_not_become_an_unusable_loss(fit):
    ids = ("1", "2", "3", "4")
    a = ids[:3]
    ds = design(
        ids,
        lambda s: (int(s == a),),
        base=lambda s: -1000.0 if s == a else 0.0,
    )
    result = fit(*panels(ids, ds, [a]), feature_columns=("edge",), ridge=0.2)
    assert result.state == "fit_reached_stationarity"
    assert result.coefficients == pytest.approx((5.0,))
    assert ds.log_probabilities(result.coefficients)[a] == pytest.approx(-995 - log(3))


def test_an_unordered_column_set_cannot_define_the_recipe(fit):
    with pytest.raises(ValueError, match="fixed_feature_order"):
        fit({}, {}, {}, feature_columns={"edge", "other"}, ridge=0.2)


@pytest.mark.parametrize(
    "ridge",
    [0, -1, float("inf"), float("nan"), True, pytest.param(10**400, id="too_large")],
)
def test_ridge_must_be_positive_finite(fit, ridge):
    with pytest.raises(ValueError, match="positive_finite_ridge"):
        fit({}, {}, {}, feature_columns=("edge",), ridge=ridge)
