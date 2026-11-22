"""Offline certificates for a unique mode of the separate-margin trio model."""

from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import (
    ROUND_CEILING,
    ROUND_FLOOR,
    ROUND_HALF_EVEN,
    Clamped,
    Context,
    Decimal,
    DecimalException,
    DivisionByZero,
    InvalidOperation,
    Overflow,
    Subnormal,
    Underflow,
)
from fractions import Fraction
from typing import NamedTuple

from autoresearch.exact_trio_distribution import Trio, _finite, partition_trios
from autoresearch.separate_trio_projection import (
    MarginalProjectionError,
    project_separate_trio_margins,
)

_PRECISION = 80
_MAX_LOG_SPAN = 20_000
_ZERO = Decimal(0)
_ONE = Decimal(1)


@dataclass(frozen=True, slots=True)
class TrioModeCertificate:
    trio: Trio | None
    method: str | None
    reason: str | None = None
    kl_upper: Decimal | None = None
    feasible_probability_gap_lower: Decimal | None = None


class _Unverified(ValueError):
    pass


class _Interval(NamedTuple):
    lo: Decimal
    hi: Decimal


class _Bounds:
    def __init__(self):
        settings = {
            "prec": _PRECISION,
            "Emin": -99_999,
            "Emax": 99_999,
            "traps": [
                Clamped,
                DivisionByZero,
                InvalidOperation,
                Overflow,
                Subnormal,
                Underflow,
            ],
        }
        self.down = Context(rounding=ROUND_FLOOR, **settings)
        self.up = Context(rounding=ROUND_CEILING, **settings)
        self.nearest = Context(rounding=ROUND_HALF_EVEN, **settings)

    def rational(self, value: Fraction) -> _Interval:
        a, b = Decimal(value.numerator), Decimal(value.denominator)
        return _Interval(self.down.divide(a, b), self.up.divide(a, b))

    def translate(self, a: _Interval, offset: Fraction) -> _Interval:
        # Round after the exact addition so cancellation preserves tiny tails.
        return _Interval(
            self.rational(Fraction(a.lo) + offset).lo,
            self.rational(Fraction(a.hi) + offset).hi,
        )

    def add(self, a: _Interval, b: _Interval) -> _Interval:
        return _Interval(self.down.add(a.lo, b.lo), self.up.add(a.hi, b.hi))

    def subtract(self, a: _Interval, b: _Interval) -> _Interval:
        return _Interval(self.down.subtract(a.lo, b.hi), self.up.subtract(a.hi, b.lo))

    def multiply(self, a: _Interval, b: _Interval) -> _Interval:
        return _Interval(
            min(self.down.multiply(x, y) for x in a for y in b),
            max(self.up.multiply(x, y) for x in a for y in b),
        )

    def sum(self, items: Iterable[_Interval]) -> _Interval:
        total = _Interval(_ZERO, _ZERO)
        for item in items:
            total = self.add(total, item)
        return total

    def exp(self, a: _Interval) -> _Interval:
        # Decimal transcendental results round to nearest, not down or up.
        lo = self.nearest.next_minus(self.nearest.exp(a.lo)) if a.lo else _ONE
        hi = self.nearest.next_plus(self.nearest.exp(a.hi)) if a.hi else _ONE
        return _Interval(lo, hi)

    def ln(self, a: _Interval) -> _Interval:
        if a.lo <= _ZERO:
            raise _Unverified("positive_feasible_point_not_verified")
        lo = self.nearest.next_minus(self.nearest.ln(a.lo)) if a.lo != _ONE else _ZERO
        hi = self.nearest.next_plus(self.nearest.ln(a.hi)) if a.hi != _ONE else _ZERO
        return _Interval(lo, hi)

    def softmax(self, log_weights: tuple[Fraction, ...]) -> tuple[_Interval, ...]:
        top = max(log_weights)
        if top - min(log_weights) > _MAX_LOG_SPAN:
            raise _Unverified("certificate_log_span_exceeded")
        weights = tuple(self.exp(self.rational(v - top)) for v in log_weights)
        total = self.sum(weights)
        if any(w.lo <= _ZERO for w in weights) or total.lo <= _ZERO:
            raise _Unverified("positive_reference_not_verified")
        return tuple(
            _Interval(self.down.divide(w.lo, total.hi), self.up.divide(w.hi, total.lo))
            for w in weights
        )


class _Forest(NamedTuple):
    size: int
    order: tuple[tuple[int, int, int], ...]
    indices: frozenset[int]

    def potentials(self, edge_values: tuple[Fraction, ...]) -> list[Fraction]:
        values = [Fraction(0)] * self.size
        for parent, child, i in self.order:
            values[child] = edge_values[i] - values[parent]
        return values


def _forest(
    edges: tuple[tuple[int, int], ...], priority: tuple[Fraction, ...]
) -> _Forest:
    n = max(max(edge) for edge in edges) + 1
    union = list(range(n))

    def root(u: int) -> int:
        while union[u] != u:
            union[u] = union[union[u]]
            u = union[u]
        return u

    adj: list[list[tuple[int, int]]] = [[] for _ in range(n)]
    indices = set()
    for i in sorted(range(len(edges)), key=priority.__getitem__, reverse=True):
        u, v = edges[i]
        p, q = root(u), root(v)
        if p != q:
            union[p] = q
            adj[u].append((v, i))
            adj[v].append((u, i))
            indices.add(i)
    seen = set()
    order = []
    for u in range(n):
        if u in seen:
            continue
        seen.add(u)
        pending = [u]
        while pending:
            parent = pending.pop()
            for child, i in adj[parent]:
                if child not in seen:
                    seen.add(child)
                    pending.append(child)
                    order.append((parent, child, i))
    return _Forest(n, tuple(order), frozenset(indices))


def _circulation(
    edges: tuple[tuple[int, int], ...],
    forest: _Forest,
    proposed: tuple[Fraction, ...],
) -> tuple[Fraction, ...]:
    delta = list(proposed)
    balance = [Fraction(0)] * forest.size
    for i, (u, v) in enumerate(edges):
        if i not in forest.indices:
            balance[u] += delta[i]
            balance[v] += delta[i]
    for parent, child, i in reversed(forest.order):
        delta[i] = -balance[child]
        balance[parent] += delta[i]
    # Check all original vertices using the completed, exact edge changes.
    sums = [Fraction(0)] * forest.size
    for d, (u, v) in zip(delta, edges, strict=True):
        sums[u] += d
        sums[v] += d
    if any(sums):
        raise _Unverified("exact_circulation_not_verified")
    return tuple(delta)


def _edges(
    trios: tuple[Trio, ...], channels: tuple[tuple[str, ...], ...]
) -> tuple[tuple[int, int], ...]:
    left, right = map(set, channels)
    nodes: dict[tuple[int, tuple[str, ...]], int] = {}
    return tuple(
        (
            nodes.setdefault((0, tuple(h for h in t if h in left)), len(nodes)),
            nodes.setdefault((1, tuple(h for h in t if h in right)), len(nodes)),
        )
        for t in trios
    )


def _bound(
    trios: tuple[Trio, ...],
    edges: tuple[tuple[int, int], ...],
    base: tuple[Fraction, ...],
    tilted: tuple[Fraction, ...],
    hint: tuple[Fraction, ...],
) -> TrioModeCertificate:
    b = _Bounds()
    p0, proposal = b.softmax(base), b.softmax(hint)
    forest = _forest(edges, hint)
    delta = _circulation(
        edges,
        forest,
        tuple(
            Fraction(q.lo) - Fraction(p.lo) for p, q in zip(p0, proposal, strict=True)
        ),
    )
    feasible = tuple(b.translate(p, d) for p, d in zip(p0, delta, strict=True))
    if any(p.lo <= _ZERO for p in feasible):
        raise _Unverified("positive_feasible_point_not_verified")

    potentials = forest.potentials(
        tuple(q - k for q, k in zip(hint, tilted, strict=True))
    )
    dual = b.softmax(
        tuple(
            k + potentials[u] + potentials[v]
            for k, (u, v) in zip(tilted, edges, strict=True)
        )
    )
    # This KL uses a genuinely feasible point, not the original IPF iterate.
    upper = b.sum(
        b.multiply(p, b.subtract(b.ln(p), b.ln(q)))
        for p, q in zip(feasible, dual, strict=True)
    ).hi
    if not upper.is_finite() or upper < _ZERO:
        raise _Unverified("kl_upper_not_verified")
    best = max(range(len(feasible)), key=lambda i: feasible[i].lo)
    runner_up = max(v.hi for i, v in enumerate(feasible) if i != best)
    gap = b.down.subtract(feasible[best].lo, runner_up)
    if gap <= _ZERO or b.down.multiply(gap, gap) <= b.up.multiply(Decimal(2), upper):
        return TrioModeCertificate(
            None, None, "probability_gap_not_verified", upper, gap
        )
    return TrioModeCertificate(
        trios[best],
        "kl_upper_bound",
        kl_upper=upper,
        feasible_probability_gap_lower=gap,
    )


def certify_separate_trio_mode(
    roster: Iterable[str],
    base_log_weights: Mapping[Trio, float],
    log_tilts: Mapping[Trio, float],
    *,
    unavailable_sets: Sequence[Collection[str]],
) -> TrioModeCertificate:
    """Return a unique mathematical argmax or an explicit numerical rejection."""
    if isinstance(roster, (str, bytes)) or any(
        isinstance(m, (str, bytes)) for m in unavailable_sets
    ):
        raise ValueError("declared_roster_and_masks_require_id_collections")
    ids = tuple(roster)
    channels = tuple(tuple(m) for m in unavailable_sets)
    if len(channels) != 2:
        raise ValueError("separate_projection_requires_two_channels")
    trios, _ = partition_trios(ids, channels)
    if set(base_log_weights) != set(trios) or set(log_tilts) != set(trios):
        raise ValueError("exact_trio_inputs_not_the_complete_field")
    base_float = tuple(_finite(base_log_weights[t]) for t in trios)
    tilt_float = tuple(_finite(log_tilts[t]) for t in trios)
    base = tuple(map(Fraction.from_float, base_float))
    tilt = tuple(map(Fraction.from_float, tilt_float))
    edges = _edges(trios, channels)
    potentials = _forest(edges, base).potentials(tilt)
    if all(
        potentials[u] + potentials[v] == v0
        for v0, (u, v) in zip(tilt, edges, strict=True)
    ):
        maximum = max(base)
        if base.count(maximum) != 1:
            return TrioModeCertificate(None, "exact_additive_tilt", "exact_mode_tie")
        return TrioModeCertificate(trios[base.index(maximum)], "exact_additive_tilt")

    if any(max(x) - min(x) > _MAX_LOG_SPAN for x in (base, tilt)):
        return TrioModeCertificate(None, None, "certificate_log_span_exceeded")
    try:
        result = project_separate_trio_margins(
            ids,
            dict(zip(trios, base_float, strict=True)),
            dict(zip(trios, tilt_float, strict=True)),
            unavailable_sets=channels,
        )
    except MarginalProjectionError:
        return TrioModeCertificate(None, None, "projection_not_verified")
    if result.trios != trios:
        return TrioModeCertificate(None, None, "projection_support_not_verified")
    try:
        return _bound(
            trios,
            edges,
            base,
            tuple(p + d for p, d in zip(base, tilt, strict=True)),
            tuple(map(Fraction.from_float, result.log_probabilities)),
        )
    except _Unverified as exc:
        return TrioModeCertificate(None, None, str(exc))
    except DecimalException:
        return TrioModeCertificate(None, None, "interval_arithmetic_not_verified")
