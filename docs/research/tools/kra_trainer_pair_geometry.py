"""Inspect one outcome-free relation within a full declared field."""

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from itertools import combinations
from unicodedata import normalize

from autoresearch.exact_trio_distribution import Trio, partition_trios


@dataclass(frozen=True, slots=True)
class Contrast:
    positive: tuple[Trio, Trio]
    negative: tuple[Trio, Trio]
    difference: int


@dataclass(frozen=True, slots=True)
class TrainerPairGeometry:
    role_states: dict[str, str]
    known_group_sizes: tuple[int, ...]
    confirmed_pair_counts: dict[Trio, int]
    nonadditive_contrast: Contrast | None


def _role(raw: Mapping[str, object]) -> tuple[str, tuple[str, str] | None]:
    identity = raw.get("trNo")
    if identity is None or (type(identity) is str and identity.strip() in ("", "-")):
        return "missing_id", None
    if type(identity) not in (int, str):
        return "invalid_id", None
    text = str(identity).strip()
    normalized = text.lstrip("0")
    if not (normalized and text.isascii() and text.isdigit()):
        return "invalid_id", None
    name = raw.get("trName")
    if name is not None and type(name) is not str:
        return "invalid_name", None
    literal = "".join(normalize("NFC", name).split()) if name is not None else ""
    if literal in ("", "-"):
        return "missing_name", None
    return "candidate", (normalized, literal)


def _witness(horses, weight, trio_counts) -> Contrast | None:
    if len(horses) < 5:
        return None
    positions = {h: i for i, h in enumerate(horses)}

    def anchored(pairing, spare):
        return tuple(
            tuple(sorted((spare, *pair), key=positions.__getitem__)) for pair in pairing
        )

    for a, b, c, d in combinations(horses, 4):
        first = ((a, b), (c, d))
        reference = weight(a, b) + weight(c, d)
        for alternative in (((a, c), (b, d)), ((a, d), (b, c))):
            if reference != sum(weight(*pair) for pair in alternative):
                spare = next(h for h in horses if h not in (a, b, c, d))
                plus, minus = anchored(first, spare), anchored(alternative, spare)
                difference = sum(trio_counts[s] for s in plus) - sum(
                    trio_counts[s] for s in minus
                )
                return Contrast(plus, minus, difference)
    return None


def analyze_trainer_pairs(
    roster: Iterable[str], entries: Mapping[str, Mapping[str, object]]
) -> TrainerPairGeometry:
    """Return a confirmed pair count for every trio and an exact contrast.

    An unresolved runner contributes no confirmed pair. This does not assert
    that its actual trainer is different from every other runner's trainer.
    The caller must verify the pre-cutoff source and complete race roster.
    """
    ids = tuple(roster) if not isinstance(roster, (str, bytes)) else roster
    trios, _ = partition_trios(ids, ())
    if set(ids) != entries.keys():
        raise ValueError("trainer_pair_requires_exact_declared_entries")
    horses = tuple(dict.fromkeys(h for trio in trios for h in trio))
    states = {}
    candidates = {}
    names_by_id = defaultdict(set)
    ids_by_name = defaultdict(set)
    for h in horses:
        states[h], role = _role(entries[h])
        if role is not None:
            identity, name = role
            candidates[h] = role
            names_by_id[identity].add(name)
            ids_by_name[name].add(identity)

    groups = defaultdict(list)
    verified = {}
    for h, (identity, name) in candidates.items():
        if len(names_by_id[identity]) != 1:
            states[h] = "id_has_conflicting_names"
        elif len(ids_by_name[name]) != 1:
            states[h] = "name_has_conflicting_ids"
        else:
            states[h] = "verified_within_field"
            groups[identity].append(h)
            verified[h] = identity

    def weight(left, right):
        return int(left in verified and verified[left] == verified.get(right))

    counts = {s: sum(weight(*pair) for pair in combinations(s, 2)) for s in trios}
    return TrainerPairGeometry(
        states,
        tuple(sorted(map(len, groups.values()), reverse=True)),
        counts,
        _witness(horses, weight, counts),
    )
