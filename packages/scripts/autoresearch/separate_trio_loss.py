"""Bound the exact-set loss and its tilt derivative for two fixed margins."""

from collections import Counter
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, DecimalException
from fractions import Fraction

from autoresearch.exact_trio_distribution import Trio, _finite, _id_key, partition_trios
from autoresearch.separate_trio_mode import (
    _Bounds,
    _circulation,
    _edges,
    _forest,
    _Interval,
    _Unverified,
)
from autoresearch.separate_trio_projection import (
    MarginalProjectionError,
    project_separate_trio_margins,
)

_ZERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class TrioLossCertificate:
    loss: tuple[Decimal, Decimal] | None
    directional_derivative: tuple[Decimal, Decimal] | None
    reason: str | None = None


def _max_abs(values):
    return max(max(item.lo.copy_abs(), item.hi.copy_abs()) for item in values)


def _negate(item):
    return _Interval(item.hi.copy_negate(), item.lo.copy_negate())


def _divide_positive(bounds, numerator, denominator):
    return _Interval(
        min(bounds.down.divide(x, y) for x in numerator for y in denominator),
        max(bounds.up.divide(x, y) for x in numerator for y in denominator),
    )


def _component_size(forest):
    root = list(range(forest.size))
    for parent, child, _ in forest.order:
        root[child] = root[parent]
    return max(Counter(root).values())


def _potential_values(edges, potentials):
    return tuple(potentials[u] + potentials[v] for u, v in edges)


def _feasible(bounds, roster, masks, trios, edges, base, tilt):
    exact_base = tuple(Fraction(base[t]) for t in trios)
    exact_tilt = tuple(Fraction(tilt[t]) for t in trios)
    base_prob = bounds.softmax(exact_base)
    forest = _forest(edges, exact_base)
    n = _component_size(forest)
    if _potential_values(edges, forest.potentials(exact_tilt)) == exact_tilt:
        return base_prob, tuple(map(bounds.ln, base_prob)), _ZERO, n

    candidate = project_separate_trio_margins(
        roster, base, tilt, unavailable_sets=masks
    )
    if candidate.trios != trios:
        raise _Unverified("projection_changed_the_declared_field")
    hint = tuple(map(Fraction, candidate.log_probabilities))
    proposed = bounds.softmax(hint)
    forest = _forest(edges, hint)
    movement = _circulation(
        edges,
        forest,
        tuple(
            Fraction(q.lo) - Fraction(p.lo)
            for p, q in zip(base_prob, proposed, strict=True)
        ),
    )
    feasible = tuple(
        bounds.translate(p, delta) for p, delta in zip(base_prob, movement, strict=True)
    )
    log_feasible = tuple(map(bounds.ln, feasible))
    tilted = tuple(a + b for a, b in zip(exact_base, exact_tilt, strict=True))
    potential = forest.potentials(
        tuple(q - k for q, k in zip(hint, tilted, strict=True))
    )
    residual = _max_abs(
        bounds.translate(log_q, -k - p)
        for log_q, k, p in zip(
            log_feasible, tilted, _potential_values(edges, potential), strict=True
        )
    )
    # A cut bound on the weighted residual map controls every log coordinate.
    log_error = bounds.up.multiply(Decimal(n), residual)
    return feasible, log_feasible, log_error, n


def _paths(edges, forest):
    parents = {}
    depth = [0] * forest.size
    for parent, child, i in forest.order:
        parents[child] = parent, i
        depth[child] = depth[parent] + 1
    for e, (u, v) in enumerate(edges):
        if e in forest.indices:
            continue
        left, right = [], []
        while u != v:
            if depth[u] >= depth[v]:
                u, i = parents[u]
                left.append(i)
            else:
                v, i = parents[v]
                right.append(i)
        path = left + right[::-1]
        if len(path) % 2 != 1:
            raise _Unverified("trio_forest_path_not_bipartite")
        yield e, tuple((i, 1 if k % 2 == 0 else -1) for k, i in enumerate(path))


def _solve(ctx, rows):
    """Proposal only; correctness is checked separately on the original graph."""
    n = len(rows)
    for i in range(n):
        best = max(range(i, n), key=lambda j: rows[j][i].copy_abs())
        rows[i], rows[best] = rows[best], rows[i]
        if not rows[i][i]:
            raise _Unverified("singular_derivative_proposal")
        for j in range(i + 1, n):
            if not rows[j][i]:
                continue
            ratio = ctx.divide(rows[j][i], rows[i][i])
            for k in range(i + 1, n + 1):
                rows[j][k] = ctx.subtract(rows[j][k], ctx.multiply(ratio, rows[i][k]))
    result = [_ZERO] * n
    for i in reversed(range(n)):
        rhs = rows[i][-1]
        for j in range(i + 1, n):
            rhs = ctx.subtract(rhs, ctx.multiply(rows[i][j], result[j]))
        result[i] = ctx.divide(rhs, rows[i][i])
    return result


def _proposal(bounds, edges, weight, f):
    forest = _forest(edges, tuple(map(Fraction, weight)))
    paths = tuple(_paths(edges, forest))
    active = sorted({i for _, path in paths for i, _ in path})
    index = {edge: j for j, edge in enumerate(active)}
    k = len(active)
    rows = [[Decimal(i == j) for j in range(k)] + [_ZERO] for i in range(k)]
    ctx = bounds.nearest
    for e, path in paths:
        delta = f[e] - sum(f[i] * sign for i, sign in path)
        value = ctx.divide(Decimal(delta.numerator), Decimal(delta.denominator))
        for i, sign in path:
            # A maximum-weight forest keeps every chord/tree ratio at most one.
            ratio = ctx.divide(weight[e], weight[i])
            if sign == -1:
                ratio = ratio.copy_negate()
            row = rows[index[i]]
            row[-1] = ctx.subtract(row[-1], ctx.multiply(ratio, value))
            for j, other in path:
                column = index[j]
                row[column] = (
                    ctx.add(row[column], ratio)
                    if other == 1
                    else ctx.subtract(row[column], ratio)
                )
    residual = dict(zip(active, map(Fraction, _solve(ctx, rows)), strict=True))
    potential = _potential_values(
        edges,
        forest.potentials(tuple(x - residual.get(i, 0) for i, x in enumerate(f))),
    )
    complement = tuple(x - p for x, p in zip(f, potential, strict=True))
    movement = _circulation(
        edges,
        forest,
        tuple(Fraction(w) * r for w, r in zip(weight, complement, strict=True)),
    )
    return complement, movement


def _derivative(bounds, edges, feasible, f, index, n, log_error):
    complement, movement = _proposal(bounds, edges, tuple(q.lo for q in feasible), f)
    if not any(complement):
        return _Interval(_ZERO, _ZERO)
    quotients = tuple(
        _divide_positive(bounds, bounds.rational(dq), q)
        for dq, q in zip(movement, feasible, strict=True)
    )
    residual = _max_abs(
        bounds.translate(r, -g) for r, g in zip(quotients, complement, strict=True)
    )
    # Along a log-weight interpolation the additive part forces a change in
    # the residual. The cut bounds for the two parts are n-1 and n.
    direction_size = bounds.rational(max(map(abs, f))).hi
    weight_effect = bounds.up.multiply(direction_size, log_error)
    rounding = bounds.up.multiply(Decimal(n), residual)
    stability = bounds.up.multiply(Decimal(n * (n - 1)), weight_effect)
    error = bounds.up.add(rounding, stability)
    return _negate(bounds.add(quotients[index], _Interval(error.copy_negate(), error)))


def certify_separate_trio_loss(
    roster: Iterable[str],
    base_log_weights: Mapping[Trio, float],
    log_tilts: Mapping[Trio, float],
    direction: Mapping[Trio, float],
    target: Collection[str],
    *,
    unavailable_sets: Sequence[Collection[str]],
) -> TrioLossCertificate:
    """Enclose the loss and one directional derivative; never fit or predict."""
    if isinstance(roster, (str, bytes)) or isinstance(target, (str, bytes)):
        raise ValueError("exact_trio_requires_id_collection")
    if len(unavailable_sets) != 2:
        raise ValueError("separate_projection_requires_two_channels")
    roster = tuple(roster)
    trios, _ = partition_trios(roster, unavailable_sets)
    masks = tuple(tuple(m) for m in unavailable_sets)
    if any(
        set(values) != set(trios) for values in (base_log_weights, log_tilts, direction)
    ):
        raise ValueError("exact_trio_inputs_not_the_complete_field")
    ordered = tuple(sorted(target, key=_id_key))
    if ordered not in trios:
        raise ValueError("exact_trio_target_outside_frozen_field")
    index = trios.index(ordered)
    base = {t: _finite(base_log_weights[t]) for t in trios}
    tilt = {t: _finite(log_tilts[t]) for t in trios}
    f = tuple(Fraction(_finite(direction[t])) for t in trios)
    edges = _edges(trios, masks)
    bounds = _Bounds()
    try:
        feasible, log_feasible, log_error, n = _feasible(
            bounds, roster, masks, trios, edges, base, tilt
        )
        loss = _negate(
            bounds.add(
                log_feasible[index], _Interval(log_error.copy_negate(), log_error)
            )
        )
        derivative = _derivative(bounds, edges, feasible, f, index, n, log_error)
    except (MarginalProjectionError, _Unverified) as exc:
        return TrioLossCertificate(None, None, str(exc))
    except DecimalException:
        return TrioLossCertificate(None, None, "trio_loss_interval_arithmetic_failed")
    return TrioLossCertificate(loss, derivative)
