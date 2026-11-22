from collections import defaultdict
from decimal import ROUND_UP, Context, Decimal, localcontext
from fractions import Fraction
from itertools import combinations
from math import log

import pytest

from autoresearch import separate_trio_mode as mode
from autoresearch.separate_trio_projection import (
    MarginalProjectionError,
    SeparateTrioProjection,
    project_separate_trio_margins,
)

ROSTER = tuple("12345")
MASKS = ({"4"}, {"5"})
TRIOS = tuple(combinations(ROSTER, 3))
BASE_WINNER = ("1", "2", "3")
TILT_WINNER = ("1", "4", "5")


def cell(t):
    return 2 * ("4" in t) + ("5" in t)


def certify(base, tilt, masks=MASKS):
    return mode.certify_separate_trio_mode(
        iter(ROSTER), base, tilt, unavailable_sets=masks
    )


def oracle(base, tilt):
    """Independently solve the present 2-by-2 cell case in probability space."""
    with localcontext() as ctx:
        ctx.prec = 100
        raw = [Decimal.from_float(v).exp() for v in base.values()]
        kernel = [
            (Decimal.from_float(base[t]) + Decimal.from_float(tilt[t])).exp()
            for t in base
        ]
        masses = [Decimal(0) for _ in range(4)]
        tilted = masses.copy()
        for t, p, k in zip(base, raw, kernel, strict=True):
            masses[cell(t)] += p
            tilted[cell(t)] += k
        total = sum(masses)
        r = (masses[0] + masses[1]) / total
        c = (masses[0] + masses[2]) / total
        ratio = tilted[0] * tilted[3] / (tilted[1] * tilted[2])
        low, high = max(Decimal(0), r + c - 1), min(r, c)
        for _ in range(285):
            x = (low + high) / 2
            if x * (1 - r - c + x) > ratio * (r - x) * (c - x):
                high = x
            else:
                low = x
        x = (high + low) / 2
        cells = (x, r - x, c - x, 1 - r - c + x)
        return {
            t: cells[cell(t)] * k / tilted[cell(t)]
            for t, k in zip(base, kernel, strict=True)
        }


def test_exact_additive_certificate_repairs_documented_near_tie_reversal():
    base = {
        t: (-90 - log(3) if cell(t) in (1, 2) else -80 if cell(t) == 3 else -1e-12)
        for t in TRIOS
    }
    base[TILT_WINNER] = 0.0
    tilt = {t: float(64 * (("5" in t) - ("4" in t))) for t in TRIOS}
    d = project_separate_trio_margins(ROSTER, base, tilt, unavailable_sets=MASKS)
    approximate = dict(zip(d.trios, d.log_probabilities, strict=True))
    assert max(approximate, key=approximate.__getitem__) == BASE_WINNER
    c = certify(base, tilt)
    assert c.trio == TILT_WINNER
    assert c.method == "exact_additive_tilt" and c.kl_upper is None


def test_exact_tie_and_single_supported_trio():
    base, tilt = dict.fromkeys(TRIOS, 0.0), dict.fromkeys(TRIOS, -900.0)
    c = certify(base, tilt)
    assert c.trio is None and c.reason == "exact_mode_tie"
    only = {BASE_WINNER: -1e300}
    r = mode.certify_separate_trio_mode(
        "1 2 3".split(), only, only, unavailable_sets=([], [])
    )
    assert r.trio == BASE_WINNER and r.method == "exact_additive_tilt"


@pytest.mark.parametrize("raise_value", [0.05, 0.4, 1.2, 5.0, 8.0])
def test_nonadditive_unique_mode_agrees_with_independent_table_oracle(raise_value):
    base = {t: log(5) if t == BASE_WINNER else log(3) for t in TRIOS}
    tilt = {t: raise_value if t == TILT_WINNER else 0.0 for t in TRIOS}
    q = oracle(base, tilt)
    wanted = max(q, key=q.__getitem__)
    assert q[wanted] - max(v for t, v in q.items() if t != wanted) > Decimal("0.005")
    if raise_value == 5.0:
        assert wanted == TILT_WINNER and wanted != max(base, key=base.__getitem__)
    c = certify(base, tilt)
    assert c.trio == wanted and c.method == "kl_upper_bound"
    assert c.kl_upper is not None and 0 <= c.kl_upper < Decimal("1e-15")
    assert c.feasible_probability_gap_lower > 0


def test_exact_nonadditive_tie_does_not_acquire_a_stable_id_tiebreak():
    base = dict.fromkeys(TRIOS, 0.0)
    tilt = {t: float(t in (BASE_WINNER, TILT_WINNER)) for t in TRIOS}
    c = certify(base, tilt, (set(), set()))
    assert c.trio is None and c.reason == "probability_gap_not_verified"


def test_sub_precision_separation_is_rejected_instead_of_guessing():
    base = dict.fromkeys(TRIOS, -10.0)
    base[BASE_WINNER] = 0.0
    base[TILT_WINNER] = 1e-200
    tilt = {t: float(t not in (BASE_WINNER, TILT_WINNER)) for t in TRIOS}
    c = certify(base, tilt, (set(), set()))
    assert c.trio is None and c.reason == "probability_gap_not_verified"


def test_concentrated_parallel_edges_keep_positive_tails_after_exact_translation():
    base = dict.fromkeys(TRIOS, 0.0)
    tilt = dict.fromkeys(TRIOS, -400.0)
    tilt[TILT_WINNER] = 0.0
    c = certify(base, tilt, (set(), set()))
    # With only the total mass constrained, the exact largest tilt wins.
    assert c.trio == TILT_WINNER and c.method == "kl_upper_bound"
    assert c.feasible_probability_gap_lower > Decimal("0.99")


def test_trusted_interval_arithmetic_is_independent_of_ambient_context():
    base = {t: log(5) if t == BASE_WINNER else log(3) for t in TRIOS}
    tilt = {t: 5.0 if t == TILT_WINNER else 0.0 for t in TRIOS}
    expected = certify(base, tilt)
    assert expected.trio == TILT_WINNER
    with localcontext(Context(prec=3, rounding=ROUND_UP)):
        assert certify(base, tilt) == expected


def test_enclosures_cover_independent_higher_precision_math():
    b = mode._Bounds()
    values = [-1900, Fraction(-1, 3), 0, Fraction(2, 7), 18]

    def real(x):
        q = Fraction(x)
        return Decimal(q.numerator) / Decimal(q.denominator)

    with localcontext() as ctx:
        ctx.prec = 160
        for x in values:
            interval = b.rational(Fraction(x))
            wide = b.exp(interval)
            log_wide = b.ln(wide)
            assert wide.lo <= real(x).exp() <= wide.hi
            assert log_wide.lo <= real(x) <= log_wide.hi
        a = mode._Interval(Decimal("-3"), Decimal("1"))
        b0 = mode._Interval(Decimal("-5"), Decimal("-1"))
        assert b.multiply(a, b0) == mode._Interval(Decimal("-5"), Decimal("15"))


def test_circulation_preserves_both_margins_parallel_edges_and_a_bridge():
    edges = ((0, 2), (0, 2), (0, 3), (1, 2), (1, 3), (4, 5))
    forest = mode._forest(edges, tuple(map(Fraction, (6, 5, 4, 3, 2, 1))))
    amount = Fraction(1, 10**450)
    proposed = tuple(amount / (i + 1) for i in range(len(edges)))
    delta = mode._circulation(edges, forest, proposed)
    by_vertex = defaultdict(Fraction)
    for i, (d, (u, v)) in enumerate(zip(delta, edges, strict=True)):
        by_vertex[u] += d
        by_vertex[v] += d
        if i not in forest.indices:
            assert d == proposed[i]
    assert not any(by_vertex.values())
    assert delta[-1] == 0


def test_arbitrary_incorrect_numerical_proposal_does_not_certify_a_wrong_mode(
    monkeypatch,
):
    base = {t: log(5) if t == BASE_WINNER else log(3) for t in TRIOS}
    tilt = {t: 5.0 if t == TILT_WINNER else 0.0 for t in TRIOS}
    # Give the verifier an unjustifiably large proposed advantage for the wrong trio.
    guess = tuple(0.0 if t == BASE_WINNER else -35.0 for t in TRIOS)
    monkeypatch.setattr(
        mode,
        "project_separate_trio_margins",
        lambda *args, **kwargs: SeparateTrioProjection(
            TRIOS, guess, 1, 0, 0.0, 0.0, 0.0
        ),
    )
    assert certify(base, tilt).trio is None


def test_nonconvergence_and_out_of_range_never_return_a_fallback(monkeypatch):
    base, tilt = dict.fromkeys(TRIOS, 0.0), dict.fromkeys(TRIOS, 0.0)
    tilt[TILT_WINNER] = 1.0

    def reject(*args, **kwargs):
        raise MarginalProjectionError("synthetic_failure")

    monkeypatch.setattr(mode, "project_separate_trio_margins", reject)
    assert certify(base, tilt) == mode.TrioModeCertificate(
        None, None, "projection_not_verified"
    )
    tilt[TILT_WINNER] = 1e5
    assert certify(base, tilt) == mode.TrioModeCertificate(
        None, None, "certificate_log_span_exceeded"
    )


@pytest.mark.parametrize(
    "change", ["infinite", "missing", "duplicate_mask", "bad_id", "one_mask"]
)
def test_original_complete_field_and_finite_operand_rules_are_kept(change):
    base, tilt = dict.fromkeys(TRIOS, 0.0), dict.fromkeys(TRIOS, 0.0)
    masks = MASKS
    if change == "infinite":
        tilt[TILT_WINNER] = float("inf")
    elif change == "missing":
        del base[BASE_WINNER]
    elif change == "duplicate_mask":
        masks = (("4", "4"), ("5",))
    elif change == "bad_id":
        masks = (("6",), ("5",))
    else:
        masks = MASKS[:1]
    with pytest.raises(ValueError):
        certify(base, tilt, masks)
