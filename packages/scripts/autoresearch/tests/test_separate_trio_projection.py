from collections import defaultdict, deque
from decimal import Decimal, localcontext
from itertools import combinations
from math import exp, fsum, isfinite, log

import pytest

from autoresearch.exact_trio_distribution import prepare_exact_trio_distribution
from autoresearch.separate_trio_projection import (
    LOG_TOLERANCE,
    MarginalProjectionError,
    _bridges,
    _graph,
    _stationarity_error,
    project_separate_trio_margins,
)


def key(trio, masks):
    return tuple(frozenset(trio) & m for m in masks)


def log_mass(weights):
    anchor = max(weights)
    return anchor + log(fsum(exp(x - anchor) for x in weights))


def aggregate(weights, masks, *, joint=False):
    by_key = defaultdict(list)
    for t, w in weights.items():
        a, b = key(t, masks)
        if joint:
            by_key[a, b].append(w)
        else:
            by_key[0, a].append(w)
            by_key[1, b].append(w)
    return {k: log_mass(v) for k, v in by_key.items()}


def probabilities(result):
    return dict(zip(result.trios, result.log_probabilities, strict=True))


def baseline(weights):
    n = log_mass(tuple(weights.values()))
    return {t: w - n for t, w in weights.items()}


def grid(bases, multipliers):
    roster = tuple("12345")
    masks = ({"4"}, {"5"})
    trios = tuple(combinations(roster, 3))
    cell = {t: 2 * ("4" in t) + ("5" in t) for t in trios}
    counts = {i: sum(j == i for j in cell.values()) for i in range(4)}
    base = {t: log(bases[i] / counts[i]) for t, i in cell.items()}
    tilt = {t: log(multipliers[i]) for t, i in cell.items()}
    return roster, masks, base, tilt, cell


def test_balanced_four_cell_symmetric_exact_example_changes_joint_mass():
    roster, masks, base, tilt, cell = grid((1, 1, 1, 1), (3, 1, 1, 3))
    d = project_separate_trio_margins(roster, base, tilt, unavailable_sets=masks)
    q = probabilities(d)
    for i, want in enumerate((3 / 8, 1 / 8, 1 / 8, 3 / 8)):
        assert fsum(exp(q[t]) for t, j in cell.items() if j == i) == pytest.approx(want)
    assert aggregate(q, masks) == pytest.approx(aggregate(baseline(base), masks))
    assert len(q) == 10 and d.fixed_cell_count == 0


def four_cell_reference(bases, multipliers):
    with localcontext() as context:
        context.prec = 70
        b = [Decimal(v) for v in bases]
        r = (b[0] + b[1]) / sum(b)
        c = (b[0] + b[2]) / sum(b)
        a, f, g, h = [x * w for x, w in zip(b, multipliers, strict=True)]
        cross_ratio = a * h / (f * g)
        lo, hi = max(Decimal(0), r + c - 1), min(r, c)
        for _ in range(200):
            x = (lo + hi) / 2
            if x * (1 - r - c + x) > cross_ratio * (r - x) * (c - x):
                hi = x
            else:
                lo = x
        x = (lo + hi) / 2
        return list(map(float, (x, r - x, c - x, 1 - r - c + x)))


def test_asymmetric_projection_matches_independent_high_precision_cross_ratio():
    bases, multipliers = (1, 2, 3, 4), (3, 1, 2, 5)
    roster, masks, base, tilt, cell = grid(bases, multipliers)
    with pytest.raises(MarginalProjectionError, match="did_not_converge"):
        project_separate_trio_margins(
            roster, base, tilt, unavailable_sets=masks, max_sweeps=1
        )
    d = project_separate_trio_margins(roster, base, tilt, unavailable_sets=masks)
    got = [
        fsum(exp(q) for t, q in probabilities(d).items() if cell[t] == i)
        for i in range(4)
    ]
    assert got == pytest.approx(four_cell_reference(bases, multipliers), abs=2e-11)
    assert 1 < d.sweeps < 100
    assert d.max_margin_log_error <= LOG_TOLERANCE
    assert d.stationarity_log_error <= LOG_TOLERANCE


def test_row_and_column_gauge_does_not_change_projection():
    roster, masks, base, tilt, _ = grid((1, 2, 3, 4), (3, 1, 2, 5))
    x = project_separate_trio_margins(roster, base, tilt, unavailable_sets=masks)
    shifted = {
        t: v + (8 if "4" in t else -9) - (4 if "5" in t else 7) for t, v in tilt.items()
    }
    y = project_separate_trio_margins(
        roster[::-1], base, shifted, unavailable_sets=masks
    )
    assert x.trios == y.trios
    assert x.log_probabilities == pytest.approx(y.log_probabilities, abs=2e-10)


def test_forest_joint_masses_are_fixed_but_parallel_conditionals_can_change():
    roster, _, base, _, _ = grid((1, 2, 3, 4), (1, 1, 1, 1))
    masks = ({"4"}, {"4", "5"})
    tilt = {t: (i - 4) / 7 for i, t in enumerate(base)}
    d = project_separate_trio_margins(roster, base, tilt, unavailable_sets=masks)
    old_formula = prepare_exact_trio_distribution(
        roster, base, {t: (v,) for t, v in tilt.items()}, unavailable_sets=masks
    )
    assert d.sweeps == 0 and d.fixed_cell_count == 4
    assert probabilities(d) != baseline(base)
    assert probabilities(d) == pytest.approx(
        old_formula.log_probabilities((1,)), abs=1e-12
    )
    assert aggregate(probabilities(d), masks, joint=True) == pytest.approx(
        aggregate(baseline(base), masks, joint=True), abs=1e-12
    )


def test_tiny_bridge_and_tiny_flexible_component_stay_in_log_space():
    roster = tuple("12345678")
    masks = ({"6", "7", "8"}, {"3", "4", "5", "8"})
    bridge = ("3", "4", "5")
    trios = tuple(combinations(roster, 3))
    base = {t: -950 if t == bridge else (-900 if "8" in t else 0) for t in trios}
    tilt = {t: (i % 5 - 2) / 7 for i, t in enumerate(trios)}
    tilt[bridge] = 700
    d = project_separate_trio_margins(roster, base, tilt, unavailable_sets=masks)
    q = probabilities(d)
    expected = baseline(base)
    assert q[bridge] == expected[bridge] < -900
    assert len(q) == len(base) and all(isfinite(i) for i in q.values())
    assert aggregate(q, masks) == pytest.approx(aggregate(expected, masks), abs=1e-10)
    assert any(q[t] != expected[t] for t in q if "8" in t)
    assert d.fixed_cell_count > 0 and d.max_fixed_cell_log_error <= LOG_TOLERANCE


def test_bridge_search_agrees_with_independent_edge_removal():
    candidates = [(a, b) for a in range(3) for b in range(3, 6)]
    for bit in range(1, 1 << len(candidates)):
        edges = tuple(p for i, p in enumerate(candidates) if bit & (1 << i))
        graph = _graph(edges)
        expected = set()
        for exclude, (a, b) in enumerate(edges):
            seen = {a}
            pending = deque([a])
            while pending:
                u = pending.popleft()
                for v, j in graph[u]:
                    if j != exclude and v not in seen:
                        seen.add(v)
                        pending.append(v)
            if b not in seen:
                expected.add(exclude)
        assert _bridges(graph) == expected


def test_stationarity_check_rejects_a_different_table_with_the_same_margins():
    edges = ((0, 2), (0, 3), (1, 2), (1, 3))
    tilt = (log(1 / 4),) * 4
    different = tuple(map(log, (3 / 8, 1 / 8, 1 / 8, 3 / 8)))
    groups = tuple((i,) for i in range(4))
    assert _stationarity_error(tilt, tilt, groups, edges, _graph(edges)) == 0
    assert _stationarity_error(different, tilt, groups, edges, _graph(edges)) > 1


def test_zero_or_constant_tilt_is_the_same_complete_baseline():
    roster, masks, base, _, _ = grid((1, 2, 3, 4), (1, 1, 1, 1))
    zero = project_separate_trio_margins(
        roster, base, dict.fromkeys(base, 0), unavailable_sets=masks
    )
    c = project_separate_trio_margins(
        roster[::-1], base, dict.fromkeys(base, 17), unavailable_sets=masks
    )
    assert zero == c and c.sweeps == 0
    assert probabilities(zero) == pytest.approx(baseline(base), abs=1e-13)


@pytest.mark.parametrize(
    "change",
    [
        "omitted",
        "extra",
        "infinite",
        "resolution",
        "boolean",
        "channel_count",
        "scope",
        "limit",
    ],
)
def test_input_and_resolution_failures_are_explicit(change):
    roster, masks, base, tilt, _ = grid((1, 2, 3, 4), (3, 1, 2, 5))
    first = next(iter(base))
    budget = 100
    if change == "omitted":
        del base[first]
    elif change == "extra":
        tilt["1", "2", "8"] = 0
    elif change == "infinite":
        base[first] = float("-inf")
    elif change == "resolution":
        base[first] = -1e9
    elif change == "boolean":
        tilt[first] = True
    elif change == "channel_count":
        masks = masks[:1]
    elif change == "scope":
        masks = ({"9"}, masks[1])
    else:
        budget = False
    error = "insufficient_log_resolution" if change == "resolution" else None
    with pytest.raises(ValueError, match=error):
        project_separate_trio_margins(
            roster, base, tilt, unavailable_sets=masks, max_sweeps=budget
        )
