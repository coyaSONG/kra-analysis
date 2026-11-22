from itertools import combinations, permutations
from math import comb, exp, fsum, isfinite, log

import pytest

from autoresearch.exact_trio_distribution import (
    partition_trios,
    prepare_exact_trio_distribution,
)


def group_masses(log_probs, unavailable):
    out = {}
    for trio, p in log_probs.items():
        key = tuple(frozenset(trio) & s for s in unavailable)
        out.setdefault(key, []).append(exp(p))
    return {k: fsum(v) for k, v in out.items()}


def design():
    roster = ("8", "1", "2", "4", "5", "9")
    trios = tuple(combinations(sorted(roster, key=int), 3))
    base = {t: (i - 5) / 3 for i, t in enumerate(trios)}
    f = {t: (float(i % 4), float((i * i) % 11)) for i, t in enumerate(trios)}
    missing = ({"2", "9"}, {"2", "5"})
    return roster, base, f, missing


def test_groups_preserve_exact_id_not_just_count_in_two_channels():
    trios, groups = partition_trios(("1", "2", "3", "4", "5"), ({"3", "4"}, {"4", "5"}))
    assert len(trios) == comb(5, 3)
    assert sorted(i for g in groups for i in g) == list(range(len(trios)))
    for group in groups:
        assert (
            len(
                {
                    (
                        set(trios[i]) & {"3", "4"} == {"3"},
                        "5" in trios[i],
                        "4" in trios[i],
                    )
                    for i in group
                }
            )
            == 1
        )
    assert next(g for g in groups if trios.index(("1", "2", "3")) in g) != next(
        g for g in groups if trios.index(("1", "2", "4")) in g
    )


def test_normalization_preserved_group_masses_and_group_shift_invariance():
    roster, base, f, missing = design()
    d = prepare_exact_trio_distribution(roster, base, f, unavailable_sets=missing)
    initial = d.log_probabilities((0, 0))
    q = d.log_probabilities((1.25, -0.5))
    assert set(q) == set(base)
    assert q != initial
    assert fsum(map(exp, q.values())) == pytest.approx(1)
    assert group_masses(q, missing) == pytest.approx(group_masses(initial, missing))
    expected = exp(base[("1", "2", "4")]) / fsum(map(exp, base.values()))
    assert exp(initial[("1", "2", "4")]) == pytest.approx(expected)
    shifted = {
        t: tuple(v + 1000 * len(set(t) & {"5", "2"}) for v in fs) for t, fs in f.items()
    }
    other = prepare_exact_trio_distribution(
        roster, base, shifted, unavailable_sets=missing
    )
    assert other.log_probabilities((1.25, -0.5)) == q
    assert other.loss_and_gradient(("1", "2", "4"), (1.25, -0.5)) == (
        d.loss_and_gradient(("1", "2", "4"), (1.25, -0.5))
    )


def test_gradient_against_independent_central_differences_and_unordered_targets():
    roster, base, f, missing = design()
    d = prepare_exact_trio_distribution(roster, base, f, unavailable_sets=missing)
    theta = (0.27, -0.13)
    eps = 1e-6
    seen_nonzero = False
    for target in d.trios:
        loss, grad = d.loss_and_gradient(target, theta)
        assert loss == pytest.approx(-d.log_probabilities(theta)[target])
        assert d.loss_and_gradient(target[::-1], theta) == (loss, grad)
        for j in range(len(theta)):
            more, less = list(theta), list(theta)
            more[j], less[j] = theta[j] + eps, theta[j] - eps
            derivative = -(
                d.log_probabilities(more)[target] - d.log_probabilities(less)[target]
            ) / (2 * eps)
            assert grad[j] == pytest.approx(derivative, abs=2e-8)
            seen_nonzero |= abs(derivative) > 1e-3
    assert seen_nonzero


def test_synthetic_total_loss_has_known_finite_stationary_point():
    roster = ("1", "2", "3", "4", "5")
    originals = dict.fromkeys(combinations(roster, 3), 0)
    target = ("1", "3", "4")
    other = ("2", "3", "4")
    f = {t: (float(t == target),) for t in originals}
    d = prepare_exact_trio_distribution(
        roster, originals, f, unavailable_sets=({"3", "4", "5"},)
    )

    def derivative(theta):
        return (
            3 * d.loss_and_gradient(target, (theta,))[1][0]
            + d.loss_and_gradient(other, (theta,))[1][0]
        )

    assert abs(derivative(log(3))) < 1e-12
    assert derivative(0) < 0 < derivative(log(5))


def test_whole_field_can_choose_a_fictional_trio_disjoint_from_base_mode():
    roster = tuple(str(i) for i in range(1, 8))
    strengths = dict(zip(roster, (2, 1, 1, 0, 0, 0, -6), strict=True))
    base = {t: sum(strengths[h] for h in t) for t in combinations(roster, 3)}
    wanted = frozenset({"4", "5", "6"})
    f = {t: (comb(len(wanted & set(t)), 2),) for t in base}
    d = prepare_exact_trio_distribution(roster, base, f, unavailable_sets=({"7"},))
    assert d.mode((0,)) == ("1", "2", "3")
    assert d.mode((5,)) == ("4", "5", "6")
    assert len(d.log_probabilities((5,))) == comb(7, 3)
    assert group_masses(d.log_probabilities((5,)), ({"7"},)) == pytest.approx(
        group_masses(d.log_probabilities((0,)), ({"7"},))
    )


def test_all_unavailable_and_singleton_groups_make_no_change_or_gradient():
    roster, base, f, _ = design()
    d = prepare_exact_trio_distribution(
        roster, base, f, unavailable_sets=(set(roster),)
    )
    assert d.log_probabilities((30, -100)) == d.log_probabilities((0, 0))
    assert d.loss_and_gradient(d.mode((0, 0)), (30, -100))[1] == (0, 0)


def test_equally_likely_ties_are_canonical_not_input_order():
    for roster in permutations(("99", "2", "3", "10")):
        canonical, _ = partition_trios(roster, ())
        d = prepare_exact_trio_distribution(
            roster, dict.fromkeys(canonical, 0), dict.fromkeys(canonical, ())
        )
        assert d.mode(()) == ("2", "3", "10")


def test_small_group_mass_remains_in_log_space():
    roster = ("1", "2", "3", "4")
    base = {t: (-1000 if "4" in t else 0) for t in combinations(roster, 3)}
    f = {t: (float(i),) for i, t in enumerate(base)}
    d = prepare_exact_trio_distribution(roster, base, f, unavailable_sets=({"4"},))
    q = d.log_probabilities((2,))
    assert len(q) == 4 and all(map(isfinite, q.values()))
    assert q[("1", "2", "3")] == pytest.approx(0)
    assert q[("1", "2", "4")] < -1000
    assert d.loss_and_gradient(("1", "2", "4"), (2,))[0] == pytest.approx(
        -q[("1", "2", "4")]
    )


def test_concentrating_a_near_unit_group_cannot_make_negative_loss():
    roster = ("1", "2", "3", "4", "5")
    trios = tuple(combinations(roster, 3))
    dominant_weights = (
        -2.830761801364945,
        -5.2903429463868505,
        -3.9516740519392215,
        -2.2634250889616503,
    )
    base = dict.fromkeys(trios, -1000.0)
    base.update(zip((t for t in trios if "5" not in t), dominant_weights, strict=True))
    features = {t: (i,) for i, t in enumerate(trios)}
    dist = prepare_exact_trio_distribution(
        roster, base, features, unavailable_sets=({"5"},)
    )
    theta = (1000.0,)
    assert max(dist.log_probabilities(theta).values()) <= 0.0
    assert dist.loss_and_gradient(dist.mode(theta), theta)[0] >= 0.0


@pytest.mark.parametrize(
    ("roster", "masks"),
    [
        (("1", "1", "2"), ()),
        (("1", "2"), ()),
        (("1", "2", "03"), ()),
        ("123", ()),
        (("1", "2", "3"), ("1",)),
        (("1", "2", "3"), (("1", "1"),)),
        (("1", "2", "3"), ({"4"},)),
    ],
)
def test_invalid_frozen_membership_or_missing_ids_rejected(roster, masks):
    with pytest.raises(ValueError):
        partition_trios(roster, masks)


@pytest.mark.parametrize(
    "change",
    (
        "missing_base",
        "missing_row",
        "extra_row",
        "unsorted_row",
        "ragged",
        "nan",
        "inf",
        "bool",
    ),
)
def test_no_shortlists_extra_rows_or_invalid_inputs(change):
    roster, base, f, _ = design()
    t = next(iter(base))
    if change == "missing_base":
        del base[t]
    elif change == "missing_row":
        del f[t]
    elif change == "extra_row":
        f["1", "2", "30"] = (0, 0)
    elif change == "unsorted_row":
        f[t[::-1]] = f.pop(t)
    elif change == "ragged":
        f[t] = (0,)
    elif change == "nan":
        f[t] = (float("nan"), 0)
    elif change == "inf":
        base[t] = float("inf")
    else:
        base[t] = True
    with pytest.raises(ValueError):
        prepare_exact_trio_distribution(roster, base, f)


def test_invalid_targets_and_nonfinite_computed_offsets_rejected():
    roster, base, f, _ = design()
    d = prepare_exact_trio_distribution(roster, base, f)
    for target in ("124", ("1", "1", "2"), ("1", "2"), ("1", "2", "30")):
        with pytest.raises(ValueError, match="outside_frozen"):
            d.loss_and_gradient(target, (0, 0))
    with pytest.raises(ValueError, match="coefficient_count"):
        d.mode((1,))
    with pytest.raises(ValueError, match="finite"):
        d.mode((float("inf"), 0))
    with pytest.raises(ValueError, match="finite"):
        d.mode((1e308, 1e308))
