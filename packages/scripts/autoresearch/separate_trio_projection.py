"""Separate missing-ID margin projection for the complete unordered trio space.

Offline numerical research only. This does not select authorized features,
define a real baseline, fit coefficients, or issue predictions.
"""

from collections import defaultdict
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from math import ulp

from autoresearch.exact_trio_distribution import (
    Trio,
    _center,
    _finite,
    _log_mass,
    _normalized,
    _total,
    partition_trios,
)

LOG_TOLERANCE = 1e-10
MAX_SWEEPS = 4096


class MarginalProjectionError(ValueError):
    """The requested numerical projection could not be verified."""


@dataclass(frozen=True, slots=True)
class SeparateTrioProjection:
    trios: tuple[Trio, ...]
    log_probabilities: tuple[float, ...]
    sweeps: int
    fixed_cell_count: int
    max_margin_log_error: float
    max_fixed_cell_log_error: float
    stationarity_log_error: float


def _resolved(value: float) -> float:
    value = _finite(value)
    if ulp(value) > LOG_TOLERANCE / 8:
        raise MarginalProjectionError("insufficient_log_resolution")
    return value


def _graph(edges: tuple[tuple[int, int], ...]) -> list[list[tuple[int, int]]]:
    adj: list[list[tuple[int, int]]] = [
        [] for _ in range(1 + max(max(e) for e in edges))
    ]
    for i, (u, v) in enumerate(edges):
        adj[u].append((v, i))
        adj[v].append((u, i))
    return adj


def _bridges(graph: list[list[tuple[int, int]]]) -> frozenset[int]:
    """Iterative low-link search on the simple cell graph."""
    entered = [-1] * len(graph)
    low = [0] * len(graph)
    parent = [(-1, -1)] * len(graph)
    fixed = set()
    tick = 0
    for root in range(len(graph)):
        if entered[root] >= 0:
            continue
        entered[root] = low[root] = tick
        tick += 1
        stack = [(root, iter(graph[root]))]
        while stack:
            u, visit = stack[-1]
            nxt = next(visit, None)
            if nxt is None:
                stack.pop()
                p, i = parent[u]
                if p >= 0:
                    if low[u] > entered[p]:
                        fixed.add(i)
                    low[p] = min(low[p], low[u])
                continue
            v, i = nxt
            if i == parent[u][1]:
                continue
            if entered[v] >= 0:
                low[u] = min(low[u], entered[v])
                continue
            parent[v] = u, i
            entered[v] = low[v] = tick
            tick += 1
            stack.append((v, iter(graph[v])))
    return frozenset(fixed)


def _cell_masses(
    base: tuple[float, ...],
    tilted: tuple[float, ...],
    edges: tuple[tuple[int, int], ...],
    fixed: frozenset[int],
    sweeps: int,
) -> tuple[list[float], int]:
    cells = [b if i in fixed else tilted[i] for i, b in enumerate(base)]
    if len(fixed) == len(edges):
        return cells, 0
    active = (defaultdict(list), defaultdict(list))
    for i, edge in enumerate(edges):
        if i not in fixed:
            for axis, g in enumerate(edge):
                active[axis][g].append(i)
    # Sum the flexible baseline cells directly; subtraction can erase tiny mass.
    rows = tuple(
        (indices, _log_mass(tuple(base[i] for i in indices)))
        for side in active
        for indices in side.values()
    )

    def error(indices: list[int], target: float) -> float:
        return _resolved(_log_mass(tuple(cells[i] for i in indices)) - target)

    for sweep in range(1, sweeps + 1):
        for indices, target in rows:
            shift = -error(indices, target)
            for i in indices:
                cells[i] = _resolved(cells[i] + shift)
        if (
            max(abs(error(indices, target)) for indices, target in rows)
            <= LOG_TOLERANCE / 2
        ):
            return cells, sweep
    raise MarginalProjectionError("separate_margins_did_not_converge")


def _stationarity_error(
    projected: tuple[float, ...],
    tilted: tuple[float, ...],
    groups: tuple[tuple[int, ...], ...],
    edges: tuple[tuple[int, int], ...],
    graph: list[list[tuple[int, int]]],
) -> float:
    # Reconstruct potentials from returned trio log ratios, not solver state.
    ratios = tuple(_resolved(q - k) for q, k in zip(projected, tilted, strict=True))
    potentials: dict[int, float] = {}
    for root in range(len(graph)):
        if root in potentials:
            continue
        potentials[root] = 0.0
        pending = [root]
        while pending:
            u = pending.pop()
            for v, i in graph[u]:
                if v not in potentials:
                    potentials[v] = _resolved(ratios[groups[i][0]] - potentials[u])
                    pending.append(v)
    return max(
        abs(_total((ratios[j], -potentials[u], -potentials[v])))
        for (u, v), indices in zip(edges, groups, strict=True)
        for j in indices
    )


def project_separate_trio_margins(
    roster: Iterable[str],
    base_log_weights: Mapping[Trio, float],
    log_tilts: Mapping[Trio, float],
    *,
    unavailable_sets: Sequence[Collection[str]],
    max_sweeps: int = MAX_SWEEPS,
) -> SeparateTrioProjection:
    """Project tilted weights onto both baseline marginals or raise, without fallback."""
    if len(unavailable_sets) != 2:
        raise ValueError("separate_projection_requires_two_channels")
    if type(max_sweeps) is not int or not 1 <= max_sweeps <= MAX_SWEEPS:
        raise ValueError("invalid_marginal_projection_sweep_limit")
    trios, groups = partition_trios(roster, unavailable_sets)
    if set(base_log_weights) != set(trios) or set(log_tilts) != set(trios):
        raise ValueError("exact_trio_inputs_not_the_complete_field")
    raw_base = _center(tuple(_finite(base_log_weights[t]) for t in trios))
    log_total = _log_mass(raw_base)
    base = tuple(_resolved(v - log_total) for v in raw_base)
    offsets = _center(tuple(_finite(log_tilts[t]) for t in trios))
    tilted = tuple(_resolved(p + d) for p, d in zip(base, offsets, strict=True))
    missing = tuple(set(m) for m in unavailable_sets)
    ids: dict[tuple[int, tuple[str, ...]], int] = {}
    pairs = []
    for indices in groups:
        representative = trios[indices[0]]
        keys = tuple(
            (axis, tuple(h for h in representative if h in absent))
            for axis, absent in enumerate(missing)
        )
        u, v = (ids.setdefault(key, len(ids)) for key in keys)
        pairs.append((u, v))
    edges = tuple(pairs)
    graph = _graph(edges)
    fixed = _bridges(graph)

    if any(offsets):
        base_cells = tuple(
            min(0.0, _log_mass(tuple(raw_base[i] for i in cell)) - log_total)
            for cell in groups
        )
        tilt_cells = tuple(_log_mass(tuple(tilted[i] for i in cell)) for cell in groups)
        cells, sweeps = _cell_masses(base_cells, tilt_cells, edges, fixed, max_sweeps)
        output = list(base)
        for i, cell in enumerate(groups):
            if i in fixed and all(offsets[j] == offsets[cell[0]] for j in cell):
                continue
            conditional = _normalized(tuple(tilted[j] for j in cell))
            for j, q in zip(cell, conditional, strict=True):
                output[j] = _resolved(cells[i] + q)
        projected = tuple(output)
    else:
        projected, sweeps = base, 0

    margin_error = abs(_log_mass(projected))
    for incident in graph:
        indices = tuple(j for _, i in incident for j in groups[i])
        current = _log_mass(tuple(projected[j] for j in indices))
        target = _log_mass(tuple(base[j] for j in indices))
        margin_error = max(margin_error, abs(current - target))
    if max(projected) > 0 or margin_error > LOG_TOLERANCE:
        raise MarginalProjectionError("complete_trio_margins_not_verified")
    fixed_error = max(
        (
            abs(
                _log_mass(tuple(projected[j] for j in groups[i]))
                - _log_mass(tuple(base[j] for j in groups[i]))
            )
            for i in fixed
        ),
        default=0.0,
    )
    if fixed_error > LOG_TOLERANCE:
        raise MarginalProjectionError("fixed_cell_mass_not_verified")
    stationarity = _stationarity_error(projected, tilted, groups, edges, graph)
    if stationarity > LOG_TOLERANCE:
        raise MarginalProjectionError("projection_stationarity_not_verified")
    return SeparateTrioProjection(
        trios, projected, sweeps, len(fixed), margin_error, fixed_error, stationarity
    )
