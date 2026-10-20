import json
from copy import deepcopy
from fractions import Fraction
from math import sqrt
from pathlib import Path

import pytest

from autoresearch import time_repeatability as audit


def source_row(day, horse="h", gate=1, meet="1", distance=1200):
    return {
        "race_id": f"{day}_{meet}_1",
        "horse_id": horse,
        "meet": meet,
        "distance_m": distance,
        "rank": gate,
        "observed_roster_size": 3,
        "tier": "dual_supported",
        "measurements": {
            "total": {"status": "positive_total", "seconds": str(70 + gate)},
            "final_600": {"status": "exact_endpoint", "seconds": str(35 + gate)},
        },
    }


def race(day):
    return [source_row(day, horse, i) for i, horse in enumerate(("a", "b", "c"), 1)]


def prepared(day, horse="a", meet="1", distance=1200, value="1/10", race_no=1):
    return {
        "race_id": f"{day}_{meet}_{race_no}",
        "horse_id": horse,
        "meet": meet,
        "distance_m": distance,
        "tier": "html_only",
        "centered_ratio": value,
        "measurement_status": "usable" if value else "incomplete_reference",
        "rank_fraction": "1/2",
    }


def test_exact_quantities_and_entire_reference_membership():
    rows = race("20260501")
    before = deepcopy(rows)
    result, refs = audit.quantities(rows)
    assert rows == before
    assert refs["20260501_1_1"]["median_ratio"] == "36/37"
    assert result[0]["raw_ratio"] == "71/72"
    assert Fraction(result[0]["centered_ratio"]) == Fraction(71, 72) - Fraction(36, 37)
    assert result[1]["centered_ratio"] == "0"
    assert [r["rank_fraction"] for r in result] == ["0", "1/2", "1"]
    assert audit.quantities(list(reversed(rows))) == (result, refs)


def test_one_withheld_member_withholds_whole_race_reference():
    rows = race("20260501")
    rows[0]["measurements"]["final_600"].update(
        status="withheld_conflict", seconds=None
    )
    result, refs = audit.quantities(rows)
    assert len(result) == 3
    assert refs["20260501_1_1"]["status"] == "incomplete_reference"
    assert all(r["centered_ratio"] is None for r in result)
    assert result[1]["raw_ratio"] is not None


def test_insufficient_reference_not_silent_small_sample():
    result, _ = audit.quantities(race("20260501")[:2])
    assert {r["measurement_status"] for r in result} == {"insufficient_reference"}


@pytest.mark.parametrize(
    "field,value",
    [
        ("rank", True),
        ("rank", 4),
        ("observed_roster_size", 1),
        ("distance_m", 600),
        ("distance_m", 1200.0),
    ],
)
def test_invalid_metadata_rejected(field, value):
    row = source_row("20260501")
    row[field] = value
    with pytest.raises(ValueError, match="invalid_historical_metadata"):
        audit.quantities([row])


@pytest.mark.parametrize(
    "change", ["duplicate", "horse", "future", "venue", "duration"]
)
def test_identity_scope_and_numeric_integrity(change):
    rows = race("20260501")
    if change == "duplicate":
        rows.append(deepcopy(rows[0]))
    elif change == "horse":
        rows[0]["horse_id"] = ""
    elif change == "future":
        rows[0]["race_id"] = "20261016_1_1"
    elif change == "venue":
        rows[0]["meet"] = "3"
    else:
        rows[0]["measurements"]["final_600"]["seconds"] = "100"
    with pytest.raises(ValueError):
        audit.quantities(rows)


def test_nearest_structural_prior_selected_before_measurement_no_fallback():
    rows = [
        prepared("20260501"),
        prepared("20260502", value=None),
        prepared("20260503"),
    ]
    result = audit.pair_rows(rows)
    assert result[-1]["prior_identity"] == ["20260502_1_1", "a"]
    assert result[-1]["pair_status"] == "prior_unavailable"
    assert result[1]["pair_status"] == "current_unavailable"
    assert result[0]["pair_status"] == "no_prior"
    assert len(result) == 3
    assert audit.pair_rows(list(reversed(rows))) == result


def test_same_latest_date_is_ambiguous_and_same_day_is_not_prior():
    rows = [prepared("20260501"), prepared("20260501", race_no=2), prepared("20260502")]
    result = audit.pair_rows(rows)
    assert [r["pair_status"] for r in result] == [
        "no_prior",
        "no_prior",
        "ambiguous_latest",
    ]
    assert result[-1]["prior_identity"] is None


@pytest.mark.parametrize("day,count", [("20261028", 180), ("20261029", None)])
def test_fixed_180_day_boundary(day, count):
    result = audit.pair_rows([prepared("20260501"), prepared(day)])[-1]
    assert result["prior_age_days"] == count


@pytest.mark.parametrize(
    "override", [{"horse": "z"}, {"meet": "3"}, {"distance": 1400}]
)
def test_cross_identity_pairs_not_admitted(override):
    result = audit.pair_rows([prepared("20260501"), prepared("20260502", **override)])
    assert all(r["pair_status"] == "no_prior" for r in result)


def test_both_unavailable_is_not_failure_or_zero_quantity():
    result = audit.pair_rows(
        [prepared("20260501", value=None), prepared("20260502", value=None)]
    )[-1]
    assert result["pair_status"] == "both_unavailable"
    assert result["centered_ratio"] is None


def test_midrank_ties_and_correlation_direction():
    assert audit.ranks([Fraction(1, 3), Fraction(2, 3), Fraction(1, 3)]) == [
        1.5,
        3,
        1.5,
    ]
    values = [(1, 1, 1, 3), (1, 2, 2, 2), (2, 3, 3, 1)]
    result = audit.associations(values)
    assert result["pace_recurrence"] == pytest.approx(sqrt(3) / 2)
    assert result["rank_recurrence"] == pytest.approx(-1)
    assert result["prior_pace_current_rank"] == pytest.approx(-sqrt(3) / 2)


@pytest.mark.parametrize("values", [[], [(1, 2, 3, 4)], [(1, 2, 3, 4)] * 3])
def test_undefined_correlation_is_not_zero(values):
    assert audit.associations(values) == dict.fromkeys(audit.ASSOCIATIONS)


def pairs():
    rows = []
    for horse in ("a", "b"):
        for i in range(2):
            rows.append(
                {
                    **prepared("20260502", horse, race_no=i + 1),
                    "pair_status": "paired",
                    "prior_centered_ratio": str(i),
                    "centered_ratio": str(i + 1),
                    "prior_rank_fraction": str(i),
                    "rank_fraction": str(1 - i),
                }
            )
    return rows


def test_bootstrap_is_reproducible_and_keeps_all_pairs_of_selected_horse(monkeypatch):
    class Sampler:
        def choices(self, names, k):
            assert names == ["a", "b"] and k == 2
            return ["a", "a"]

    monkeypatch.setattr(audit, "Random", lambda seed: Sampler())
    actual = audit.associations
    observed = []

    def checked(values):
        assert len(values) == 4 and values[:2] == values[2:]
        observed.append(values)
        return actual(values)

    monkeypatch.setattr(audit, "associations", checked)
    result = audit.bootstrap(pairs(), draws=4)
    assert len(observed) == 4
    assert result["clusters"] == 2
    assert result["intervals"]["pace_recurrence"]["nominal_95_percentile_interval"] == [
        1,
        1,
    ]


def test_bootstrap_undefined_and_fixed_seed():
    empty = audit.bootstrap([], draws=5)
    assert empty["intervals"]["pace_recurrence"]["undefined_draws"] == 5
    assert (
        empty["intervals"]["pace_recurrence"]["nominal_95_percentile_interval"] is None
    )
    assert audit.bootstrap(pairs(), draws=10) == audit.bootstrap(
        list(reversed(pairs())), draws=10
    )


def test_pinned_input_failure_stops_before_analysis(tmp_path, monkeypatch):
    (tmp_path / "source.json").write_text("{}")
    monkeypatch.setattr(audit, "SOURCE", {"path": "source.json", "sha256": "0" * 64})
    with pytest.raises(ValueError):
        audit.audit(tmp_path)


def test_audit_keeps_full_population_and_declares_no_validation(tmp_path, monkeypatch):
    data = {"observations": race("20260501") + race("20260502"), "rows": 6, "races": 2}
    raw = audit.encoded(data)
    (tmp_path / "source.json").write_bytes(raw)
    monkeypatch.setattr(
        audit, "SOURCE", {"path": "source.json", "sha256": audit.digest(raw)}
    )
    result = audit.audit(tmp_path)
    assert result["rows"] == 6 and sum(result["pair_status"].values()) == 6
    assert result["complete_pairs"] == 3
    assert result["fits"] == result["network_requests"] == 0
    assert result["historical_prerace_verified"] is False
    assert result["incremental_predictive_value_verified"] is False
    assert result["training_approved"] is False
    assert result["accuracy"] is None


def test_preserved_input_has_full_membership_and_original_conflict():
    root = Path(__file__).resolve().parents[4]
    source = json.loads(audit.pinned_path(root, audit.SOURCE).read_bytes())
    assert source["rows"] == len(source["observations"]) == 11523
    assert source["races"] == 1156
    assert source["issues"] == {"cumulative_clock_order_conflict": 1}
