"""Complete-field exact-trio probabilities for offline research.

This numerical component does not load race data, fit models, or approve a
study. Its caller is responsible for the original roster and input authority.
"""

from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations
from math import exp, fsum, isfinite, log

Trio = tuple[str, str, str]


def _id_key(horse: str) -> tuple[int, str]:
    if (
        type(horse) is not str
        or not horse.isascii()
        or not horse.isdigit()
        or horse[0] == "0"
    ):
        raise ValueError("noncanonical_horse_id")
    return len(horse), horse


def partition_trios(
    roster: Iterable[str],
    unavailable_sets: Sequence[Collection[str]],
) -> tuple[tuple[Trio, ...], tuple[tuple[int, ...], ...]]:
    """Enumerate all triples and group by exact unavailable IDs per channel."""
    if isinstance(roster, (str, bytes)):
        raise ValueError("declared_roster_requires_id_collection")
    ids = sorted(roster, key=_id_key)
    declared = set(ids)
    if len(ids) < 3 or len(ids) != len(declared):
        raise ValueError("need_three_or_more_distinct_declared_runners")

    unavailable = []
    for channel in unavailable_sets:
        if isinstance(channel, (str, bytes)):
            raise ValueError("unavailable_runners_require_id_collection")
        missing = set(channel)
        if len(missing) != len(channel) or not missing <= declared:
            raise ValueError("unknown_or_duplicate_unavailable_runner")
        unavailable.append(missing)

    trios = tuple(combinations(ids, 3))
    groups: dict[tuple[tuple[str, ...], ...], list[int]] = {}
    for i, trio in enumerate(trios):
        key = tuple(tuple(h for h in trio if h in channel) for channel in unavailable)
        groups.setdefault(key, []).append(i)
    return trios, tuple(tuple(group) for group in groups.values())


def _finite(value: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("exact_trio_operand_not_finite_real")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError("exact_trio_operand_not_finite_real") from exc
    if not isfinite(result):
        raise ValueError("exact_trio_operand_not_finite_real")
    return result


def _total(values: Iterable[float]) -> float:
    try:
        return _finite(fsum(values))
    except (OverflowError, ValueError) as exc:
        raise ValueError("exact_trio_sum_outside_finite_range") from exc


def _center(values: Sequence[float]) -> tuple[float, ...]:
    top = max(values)
    return tuple(_finite(v - top) for v in values)


def _log_mass(log_weights: Sequence[float]) -> float:
    top = max(log_weights)
    return _finite(top + log(fsum(exp(v - top) for v in log_weights)))


def _normalized(values: Sequence[float]) -> tuple[float, ...]:
    centered = _center(values)
    normalizer = _log_mass(centered)
    return tuple(_finite(v - normalizer) for v in centered)


@dataclass(frozen=True, slots=True)
class _Group:
    indices: tuple[int, ...]
    log_mass: float
    baseline_conditional: tuple[float, ...]
    centered_features: tuple[tuple[float, ...], ...]

    def conditional(self, coefficients: tuple[float, ...]) -> tuple[float, ...]:
        offsets = tuple(
            _total(x * theta for x, theta in zip(row, coefficients, strict=True))
            for row in self.centered_features
        )
        if not any(offsets):
            return self.baseline_conditional
        return _normalized(
            tuple(
                _finite(base + delta)
                for base, delta in zip(self.baseline_conditional, offsets, strict=True)
            )
        )


@dataclass(frozen=True, slots=True)
class ExactTrioDistribution:
    trios: tuple[Trio, ...]
    _baseline: tuple[float, ...]
    _groups: tuple[_Group, ...]
    _width: int

    def _coefficients(self, values: Sequence[float]) -> tuple[float, ...]:
        if len(values) != self._width:
            raise ValueError("wrong_exact_trio_coefficient_count")
        return tuple(map(_finite, values))

    def log_probabilities(self, coefficients: Sequence[float]) -> dict[Trio, float]:
        """Keep all triples, including positive masses too small to exponentiate."""
        theta = self._coefficients(coefficients)
        result = list(self._baseline)
        for group in self._groups:
            conditional = group.conditional(theta)
            if conditional is group.baseline_conditional:
                continue
            for index, log_probability in zip(group.indices, conditional, strict=True):
                result[index] = _finite(group.log_mass + log_probability)
        return dict(zip(self.trios, result, strict=True))

    def mode(self, coefficients: Sequence[float]) -> Trio:
        """Return one unordered set with canonical ID order for exact-score ties."""
        probabilities = self.log_probabilities(coefficients)
        return max(probabilities, key=probabilities.__getitem__)

    def loss_and_gradient(
        self, target: Collection[str], coefficients: Sequence[float]
    ) -> tuple[float, tuple[float, ...]]:
        """Exact-set negative log likelihood and gradient for one defined target."""
        theta = self._coefficients(coefficients)
        if isinstance(target, (str, bytes)):
            raise ValueError("exact_trio_target_outside_frozen_field")
        ordered = tuple(sorted(target, key=_id_key))
        if len(ordered) != 3 or len(set(ordered)) != 3 or ordered not in self.trios:
            raise ValueError("exact_trio_target_outside_frozen_field")
        index = self.trios.index(ordered)
        group = next(g for g in self._groups if index in g.indices)
        local_index = group.indices.index(index)
        conditional = group.conditional(theta)
        observed = group.centered_features[local_index]
        probs = tuple(map(exp, conditional))

        # The group's mass does not depend on coefficients, only its shape does.
        gradient = tuple(
            _total(
                (
                    w * _finite(row[j] - observed[j])
                    for w, row in zip(probs, group.centered_features, strict=True)
                )
            )
            for j in range(self._width)
        )
        log_probability = (
            self._baseline[index]
            if conditional is group.baseline_conditional
            else _finite(group.log_mass + conditional[local_index])
        )
        return -log_probability, gradient


def prepare_exact_trio_distribution(
    roster: Iterable[str],
    base_log_weights: Mapping[Trio, float],
    trio_features: Mapping[Trio, Sequence[float]],
    *,
    unavailable_sets: Sequence[Collection[str]] = (),
) -> ExactTrioDistribution:
    """Prepare from a complete declared roster, never from a shortlist."""
    trios, groups = partition_trios(roster, unavailable_sets)
    if set(base_log_weights) != set(trios) or set(trio_features) != set(trios):
        raise ValueError("exact_trio_inputs_not_the_complete_field")
    weights = tuple(_finite(base_log_weights[s]) for s in trios)
    features = tuple(tuple(map(_finite, trio_features[s])) for s in trios)
    width = len(features[0])
    if any(len(row) != width for row in features):
        raise ValueError("ragged_exact_trio_features")
    global_weights = _center(weights)
    global_log_mass = _log_mass(global_weights)
    baseline = tuple(_finite(v - global_log_mass) for v in global_weights)
    prepared = []
    for group in groups:
        anchor = features[group[0]]
        centered = tuple(
            tuple(_finite(v - c) for v, c in zip(features[i], anchor, strict=True))
            for i in group
        )
        log_mass = _finite(
            _log_mass(tuple(global_weights[i] for i in group)) - global_log_mass
        )
        prepared.append(
            _Group(
                indices=group,
                log_mass=min(log_mass, 0.0),  # A partition cannot outweigh the field.
                baseline_conditional=_normalized(tuple(weights[i] for i in group)),
                centered_features=centered,
            )
        )
    return ExactTrioDistribution(trios, baseline, tuple(prepared), width)
