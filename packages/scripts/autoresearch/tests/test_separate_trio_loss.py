"""Independent oracles for an enclosure, not a claimed fit or prediction."""

from dataclasses import replace
from decimal import ROUND_CEILING, Decimal, localcontext
from fractions import Fraction
from itertools import combinations

import pytest

from autoresearch import separate_trio_loss as loss

IDS = ("1", "2", "3", "4", "5")
MASKS = ({"4"}, {"5"})
TRIOS = tuple(combinations(IDS, 3))
TARGET = ("1", "4", "5")
ZERO = dict.fromkeys(TRIOS, 0.0)
CORNER = {t: float(t == ("1", "2", "3")) for t in TRIOS}


def _cell(t):
    return "4" in t, "5" in t


def cross_ratio_oracle(base, tilt, f, target):
    """Use the scalar 2-by-2 equation, not IPF, a forest, or a linear solve."""
    with localcontext() as ctx:
        ctx.prec = 140
        one = Decimal(1)
        raw = {t: Decimal.from_float(base[t]).exp() for t in TRIOS}
        tilted = {
            t: (Decimal.from_float(base[t]) + Decimal.from_float(tilt[t])).exp()
            for t in TRIOS
        }
        cells = {
            (a, b): [t for t in TRIOS if _cell(t) == (a, b)]
            for a in (0, 1)
            for b in (0, 1)
        }
        total = sum(raw.values())
        p = {k: sum(raw[t] for t in v) / total for k, v in cells.items()}
        g = {k: sum(tilted[t] for t in v) for k, v in cells.items()}
        mean = {
            k: sum(tilted[t] * Decimal.from_float(f[t]) for t in v) / g[k]
            for k, v in cells.items()
        }
        row, col = p[1, 0] + p[1, 1], p[0, 1] + p[1, 1]
        if any(tilt.values()):
            lo, hi = max(Decimal(0), row + col - one), min(row, col)
            k = g[0, 0] * g[1, 1] / (g[0, 1] * g[1, 0])
            for _ in range(470):
                x = (lo + hi) / 2
                if x * (one - row - col + x) < k * (row - x) * (col - x):
                    lo = x
                else:
                    hi = x
            x = (lo + hi) / 2
            q = {
                (1, 1): x,
                (1, 0): row - x,
                (0, 1): col - x,
                (0, 0): one - row - col + x,
            }
        else:
            q = p
        x_prime = (mean[0, 0] + mean[1, 1] - mean[0, 1] - mean[1, 0]) / sum(
            one / z for z in q.values()
        )
        group = _cell(target)
        sign = 1 if group[0] == group[1] else -1
        probability = q[group] * tilted[target] / g[group]
        gradient = (
            mean[group] - Decimal.from_float(f[target]) - sign * x_prime / q[group]
        )
        return probability.ln().copy_negate(), gradient


def verify_contains(cert, exact, *, width=Decimal("1e-7")):
    assert cert.reason is None
    for bounds, value in zip(
        (cert.loss, cert.directional_derivative), exact, strict=True
    ):
        lo, hi = map(Fraction, bounds)
        assert lo <= Fraction(value) <= hi
        if width is not None:
            assert hi - lo < Fraction(width)


def certificate(base, tilt, f, target=TARGET):
    return loss.certify_separate_trio_loss(
        IDS, base, tilt, f, target, unavailable_sets=MASKS
    )


def test_every_original_cell_and_parallel_trio_agrees_with_cross_ratio():
    base = {t: (i - 4) * 0.19 for i, t in enumerate(TRIOS)}
    tilt = {t: (i % 3 - 1) * 0.41 for i, t in enumerate(TRIOS)}
    step = {t: (i % 5 - 2) * 0.34 for i, t in enumerate(TRIOS)}
    for target in TRIOS:
        cert = certificate(base, tilt, step, target[::-1])
        verify_contains(cert, cross_ratio_oracle(base, tilt, step, target))


def test_positive_mass_below_binary64_range_is_never_dropped():
    base = {t: (-900.0 if _cell(t)[0] != _cell(t)[1] else 0.0) for t in TRIOS}
    step = {t: (i % 4 - 1.0) for i, t in enumerate(TRIOS)}
    target = ("1", "2", "4")
    assert _cell(target) == (1, 0)
    exact = cross_ratio_oracle(base, ZERO, step, target)
    assert exact[0] > 900
    cert = certificate(base, ZERO, step, target)
    verify_contains(cert, exact)


def test_additive_tilt_is_exact_but_nonadditive_direction_is_not_zero(monkeypatch):
    def forbidden(*_a, **_kw):
        pytest.fail("exactly additive tilt needs no numerical forward projection")

    monkeypatch.setattr(loss, "project_separate_trio_margins", forbidden)
    tilt = {t: float(11 * ("4" in t) - 27 * ("5" in t)) for t in TRIOS}
    cert = certificate(ZERO, tilt, CORNER)
    assert Fraction(cert.directional_derivative[0]) <= -Fraction(1, 6)
    assert Fraction(cert.directional_derivative[1]) >= -Fraction(1, 6)
    assert cert.directional_derivative[1] < 0


def test_additive_direction_has_exactly_zero_derivative_for_a_nonadditive_tilt():
    tilt = {t: float(i % 5) / 4 for i, t in enumerate(TRIOS)}
    direction = {t: 10000.0 * ("4" in t) - 17000.0 * ("5" in t) for t in TRIOS}
    cert = certificate(ZERO, tilt, direction)
    assert cert.reason is None
    assert cert.directional_derivative == (0, 0)


def test_disconnected_groups_keep_parallel_edges_and_fixed_singletons():
    ids = IDS + ("6",)
    masks = ({"4", "5", "6"}, {"4", "5", "6"})
    all_trios = tuple(combinations(ids, 3))
    base = dict.fromkeys(all_trios, 0.0)
    tilt = {t: 0.125 * (i % 5) for i, t in enumerate(all_trios)}
    f = {t: float(i % 7) for i, t in enumerate(all_trios)}
    for selected in (("1", "2", "4"), ("4", "5", "6")):
        key = set(selected) & masks[0]
        group = [t for t in all_trios if set(t) & masks[0] == key]
        with localcontext() as ctx:
            ctx.prec = 140
            weight = {t: Decimal.from_float(tilt[t]).exp() for t in group}
            denominator = sum(weight.values())
            mass = Decimal(len(group)) / len(all_trios)
            log_loss = (mass * weight[selected] / denominator).ln().copy_negate()
            grad = (
                sum(weight[t] * Decimal.from_float(f[t]) for t in group) / denominator
            )
            grad -= Decimal.from_float(f[selected])
        cert = loss.certify_separate_trio_loss(
            ids, base, tilt, f, selected, unavailable_sets=masks
        )
        verify_contains(cert, (log_loss, grad))


def test_exact_enumeration_of_weighted_tree_solutions_on_another_graph():
    # At uniform weights all spanning trees have the same weight. Enumerate
    # exactly instead of trusting the calculator's chosen tree and system.
    masks = ({"4"}, {"3", "5"})
    edges = [
        tuple((i, tuple(sorted(set(t) & m))) for i, m in enumerate(masks))
        for t in TRIOS
    ]
    vertices = {v for edge in edges for v in edge}
    features = {t: (i % 7 - 3) / 8 for i, t in enumerate(TRIOS)}
    f = tuple(Fraction(features[t]) for t in TRIOS)
    totals = [Fraction(0)] * len(TRIOS)
    trees = 0
    for picked in combinations(range(len(edges)), len(vertices) - 1):
        known = {edges[picked[0]][0]: Fraction(0)}
        pending = list(picked)
        while pending:
            step = next(
                (e for e in pending if sum(v in known for v in edges[e]) == 1), None
            )
            if step is None:
                break
            pending.remove(step)
            u, v = edges[step]
            if u not in known:
                u, v = v, u
            known[v] = f[step] - known[u]
        if pending:
            continue
        assert known.keys() == vertices
        trees += 1
        for i, (u, v) in enumerate(edges):
            totals[i] += known[u] + known[v] - f[i]
    assert trees > 1
    for i, t in enumerate(TRIOS):
        got = loss.certify_separate_trio_loss(
            IDS, ZERO, ZERO, features, t, unavailable_sets=masks
        )
        lo, hi = map(Fraction, got.directional_derivative)
        assert lo <= totals[i] / trees <= hi


def test_a_true_single_edge_bridge_has_fixed_probability(monkeypatch):
    def forbidden(*_a, **_kw):
        pytest.fail("the bridge's mass is exact even with a nonadditive tilt elsewhere")

    monkeypatch.setattr(loss, "project_separate_trio_margins", forbidden)
    tilt = {t: float(i % 3) for i, t in enumerate(TRIOS)}
    selected = ("1", "2", "4")
    cert = loss.certify_separate_trio_loss(
        IDS, ZERO, tilt, CORNER, selected, unavailable_sets=({"4"}, {"3", "5"})
    )
    with localcontext() as ctx:
        ctx.prec = 140
        exact_loss = Decimal(10).ln()
    verify_contains(cert, (exact_loss, Decimal(0)))
    assert cert.directional_derivative == (0, 0)


def test_additivity_in_the_target_component_does_not_require_global_convergence(
    monkeypatch,
):
    def forbidden(*_a, **_kw):
        pytest.fail("irrelevant components do not affect the target's derivative")

    monkeypatch.setattr(loss, "project_separate_trio_margins", forbidden)
    masks = ({"4", "5"}, {"4", "5"})
    selected = ("1", "2", "4")
    tilt = {t: float(i % 5) if "5" in t else 0.0 for i, t in enumerate(TRIOS)}
    f = {t: float(t == selected) for t in TRIOS}
    cert = loss.certify_separate_trio_loss(
        IDS, ZERO, tilt, f, selected, unavailable_sets=masks
    )
    assert cert.reason is None
    lo, hi = map(Fraction, cert.directional_derivative)
    assert lo <= -Fraction(2, 3) <= hi


def test_false_linear_proposal_does_not_get_a_narrow_enclosure(monkeypatch):
    tilt = {t: 0.25 * v for t, v in CORNER.items()}
    monkeypatch.setattr(loss, "_solve", lambda _ctx, rows: [Decimal(0)] * len(rows))
    cert = certificate(ZERO, tilt, CORNER)
    verify_contains(cert, cross_ratio_oracle(ZERO, tilt, CORNER, TARGET), width=None)
    lo, hi = map(Fraction, cert.directional_derivative)
    assert hi - lo > Fraction(1, 10)


def test_perturbed_forward_proposal_is_not_trusted(monkeypatch):
    tilt = {t: 0.25 * v for t, v in CORNER.items()}
    project = loss.project_separate_trio_margins

    def changed(*args, **kwargs):
        result = project(*args, **kwargs)
        log_p = list(result.log_probabilities)
        log_p[0] += 0.1
        return replace(result, log_probabilities=tuple(log_p))

    monkeypatch.setattr(loss, "project_separate_trio_margins", changed)
    cert = certificate(ZERO, tilt, CORNER)
    verify_contains(cert, cross_ratio_oracle(ZERO, tilt, CORNER, TARGET), width=None)
    lo, hi = map(Fraction, cert.loss)
    assert hi - lo > Fraction(1, 10)


def test_no_reduced_field_or_outside_target_can_return_a_loss():
    with pytest.raises(ValueError, match="complete_field"):
        certificate(ZERO, ZERO, dict(list(CORNER.items())[1:]))
    with pytest.raises(ValueError, match="outside_frozen_field"):
        certificate(ZERO, ZERO, CORNER, ("1", "1", "3"))


def test_ambient_decimal_context_does_not_affect_the_proof():
    tilt = {t: 0.375 * v for t, v in CORNER.items()}
    expected = certificate(ZERO, tilt, CORNER)
    with localcontext() as ctx:
        ctx.prec = 9
        ctx.rounding = ROUND_CEILING
        assert expected == certificate(ZERO, tilt, CORNER)


def test_log_spans_outside_verified_range_do_not_return_fit_operands():
    base = {t: (-25000.0 if _cell(t) == (0, 0) else 0.0) for t in TRIOS}
    result = certificate(base, ZERO, CORNER)
    assert result == loss.TrioLossCertificate(
        None, None, "certificate_log_span_exceeded"
    )


def test_asymmetric_two_by_two_has_negative_curvature_on_the_exact_target_loss():
    # At uniform weights x = q00 = 1/10, q11 = x+1/5, q10 = q01 = 2/5-x.
    # Tilt only q00: the log cross ratio increases by theta.
    x, opposite, adjacent = Fraction(1, 10), Fraction(3, 10), Fraction(3, 10)
    slope = 1 / x + 1 / opposite + 2 / adjacent
    second = -1 / x**2 - 1 / opposite**2 + 2 / adjacent**2
    speed, acceleration = 1 / slope, -second / slope**3
    assert (speed / opposite) ** 2 - acceleration / opposite == -Fraction(1, 108)
    before = certificate(ZERO, {t: -v / 16 for t, v in CORNER.items()}, CORNER)
    after = certificate(ZERO, {t: v / 16 for t, v in CORNER.items()}, CORNER)
    assert after.directional_derivative[1] < before.directional_derivative[0]
