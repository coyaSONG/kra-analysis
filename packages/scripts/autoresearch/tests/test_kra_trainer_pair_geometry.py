from collections import Counter
from itertools import product
from math import comb
from pathlib import Path
from runpy import run_path

import pytest

_MODULE = (
    Path(__file__).resolve().parents[4]
    / "docs/research/tools/kra_trainer_pair_geometry.py"
)
analyze = run_path(str(_MODULE))["analyze_trainer_pairs"]
IDS = ("1", "2", "3", "4", "5")


def rows(trainers):
    return {
        str(i): {"trNo": t, "trName": f"Trainer {t}"} for i, t in enumerate(trainers, 1)
    }


def test_same_trainer_count_distinguishes_a_balanced_pair_of_trios():
    data = rows((1, 1, 2, 2, 3))
    field = analyze(IDS, data)
    witness = field.nonadditive_contrast
    assert witness is not None
    assert Counter(h for s in witness.positive for h in s) == Counter(
        h for s in witness.negative for h in s
    )
    counts = field.confirmed_pair_counts
    assert len(counts) == 10
    assert (
        sum(counts[s] for s in witness.positive)
        - sum(counts[s] for s in witness.negative)
        == witness.difference
        == 2
    )
    assert analyze(reversed(IDS), dict(reversed(data.items()))) == field


@pytest.mark.parametrize(
    "trainers",
    [(1, 1, 2), (1, 1, 2, 2), (1, 2, 3, 4, 5), (1, 1, 1, 1, 2), (1, 1, 1, 1, 1)],
)
def test_only_number_of_confirmed_pairs_does_not_imply_nonadditivity(trainers):
    roster = IDS[: len(trainers)]
    result = analyze(roster, rows(trainers))
    assert len(result.confirmed_pair_counts) == comb(len(roster), 3)
    assert result.nonadditive_contrast is None


def test_unknown_and_conflicting_roles_remain_in_every_trio():
    roles = {
        "1": {"trNo": "00012", "trName": "Cafe\u0301 J"},
        "2": {"trNo": 12, "trName": "Caf\u00e9 J"},
        "3": {"trNo": "12", "trName": None},
        "4": {"trNo": "014", "trName": "Trainer 14"},
        "5": {"trNo": "015", "trName": "Trainer 14"},
        "6": {"trNo": "14", "trName": "Unexpected name"},
        "7": {"trNo": True, "trName": "Trainer 1"},
        "8": {"trNo": "-", "trName": "Trainer 8"},
        "9": {"trNo": "17", "trName": {"value": "not a name"}},
    }
    result = analyze(roles, roles)
    assert result.role_states == {
        "1": "verified_within_field",
        "2": "verified_within_field",
        "3": "missing_name",
        "4": "id_has_conflicting_names",
        "5": "name_has_conflicting_ids",
        "6": "id_has_conflicting_names",
        "7": "invalid_id",
        "8": "missing_id",
        "9": "invalid_name",
    }
    assert len(result.confirmed_pair_counts) == comb(9, 3)
    assert result.confirmed_pair_counts[("1", "2", "3")] == 1
    assert result.confirmed_pair_counts[("1", "3", "4")] == 0
    assert result.confirmed_pair_counts[("4", "5", "6")] == 0


@pytest.mark.parametrize("change", ["extra", "missing", "duplicates"])
def test_original_roster_cannot_be_reduced_to_known_rows(change):
    data = rows((1, 1, 2, 2, 3))
    roster = IDS
    if change == "extra":
        data["6"] = data["1"]
    elif change == "missing":
        data.pop("5")
    else:
        roster = (*IDS, "5")
    with pytest.raises(ValueError):
        analyze(roster, data)


def test_group_size_formula_agrees_for_every_small_role_layout():
    roster = (*IDS, "6")
    for pattern in product(range(4), repeat=len(roster)):
        result = analyze(roster, rows(pattern))
        groups = Counter(x for x in pattern if x != 0)
        observed = Counter(result.confirmed_pair_counts.values())
        assert observed[3] == sum(comb(k, 3) for k in groups.values())
        assert observed[1] == sum(
            comb(k, 2) * (len(roster) - k) for k in groups.values()
        )
        assert sum(observed.values()) == comb(len(roster), 3)
        assert (result.nonadditive_contrast is not None) == any(
            2 <= k <= len(roster) - 2 for k in groups.values()
        )
