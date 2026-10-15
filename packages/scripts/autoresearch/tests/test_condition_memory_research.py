"""Older memory stays separate from fixed recent form and public predictions."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from fractions import Fraction

import pytest

from autoresearch import condition_memory_research as memory


def record(day, rank=1, meet=3, horse="1"):
    return {
        "race_id": f"{day}_{meet}_1",
        "horse_id": horse,
        "rank": rank,
        "observed_roster_size": 5,
        "tier": "dual_supported",
    }


def inputs():
    targets = {
        "20261016_4_1": [{"horse_id": str(i), "chul_no": i} for i in range(1, 4)]
    }
    baseline = [record("20260901", meet=4), record("20260902", 5, 3)]
    extension = [record("20260515", 5, 3)]
    contexts = {
        identity: {
            "status": "observed",
            "meet": int(identity.split("_")[1]),
            "distance_m": 1200,
            "class_text": "classA",
        }
        for identity in set(targets) | {r["race_id"] for r in baseline + extension}
    }
    return targets, baseline, extension, contexts


def test_separate_memory_no_relabelling_and_input_immutability():
    args = inputs()
    before = deepcopy(args)
    result = memory.project(*args)
    row = result["rows"][0]
    assert row["features"] == {
        "condition_delta90": "1/6",
        "prior90_count": 2,
        "similar90_count": 1,
        "fallback90": None,
        "older_count": 1,
        "older_career_form": "1/3",
        "older_same_venue_similar_count": 0,
        "older_other_venue_count": 1,
        "older_missing_condition_count": 0,
    }
    assert row["provenance"]["added_may_ids"] == ["20260515_3_1"]
    assert row["expansion_diagnostic"]["older_form_before"] is None
    assert row["deletion_diagnostic"]["nonzero_can_become_zero"]
    assert row["deletion_diagnostic"]["eligible_support_can_disappear"]
    assert not row["deletion_diagnostic"]["strict_sign_reversal"]
    assert memory.summarize(result["rows"])["runner_rows"] == 3
    assert args == before


def test_missing_old_history_is_not_observed_half_and_no_deletions():
    row = memory.project(*inputs())["rows"][1]
    assert row["features"]["older_career_form"] is None
    assert row["features"]["fallback90"] == "no_eligible_prior"
    assert row["deletion_diagnostic"]["minimum"] is None
    assert row["deletion_diagnostic"]["cases"] == []


def test_observed_half_is_not_missing():
    targets, base, ext, ctx = inputs()
    ext[0]["rank"] = 3
    assert (
        memory.project(targets, base, ext, ctx)["rows"][0]["features"][
            "older_career_form"
        ]
        == "1/2"
    )


def test_window_boundaries_and_disjoint_bands():
    targets, _, _, ctx = inputs()
    day = datetime(2026, 10, 16)
    base = [
        record((day - timedelta(days=n)).strftime("%Y%m%d"))
        for n in (89, 90, 91, 180, 181)
    ]
    row = memory.project(targets, base, [], ctx)["rows"][0]
    assert row["features"]["prior90_count"] == 2
    assert row["features"]["older_count"] == 2
    assert set(row["provenance"]["recent_ids"]).isdisjoint(
        row["provenance"]["older_ids"]
    )
    assert row["features"]["older_missing_condition_count"] == 2


@pytest.mark.parametrize("date", ["20261016", "20261017"])
def test_reject_same_day_and_future_any_horse(date):
    targets, base, ext, ctx = inputs()
    base.append(record(date, horse="999"))
    with pytest.raises(ValueError, match="target_or_future"):
        memory.project(targets, base, ext, ctx)


def test_reject_extension_inside_recent_window_even_if_delta_stays_zero():
    targets, base, _, ctx = inputs()
    with pytest.raises(ValueError, match="changed_recent"):
        memory.project(targets, base, [record("20260903", horse="2")], ctx)


def test_reject_duplicate_history():
    targets, base, _, ctx = inputs()
    with pytest.raises(ValueError, match="duplicate"):
        memory.project(targets, base, [base[0]], ctx)


@pytest.mark.parametrize("value", [0, 6, True, 1.5])
def test_reject_invalid_rank(value):
    targets, base, ext, ctx = inputs()
    ext[0]["rank"] = value
    with pytest.raises(ValueError, match="invalid_rank_size"):
        memory.project(targets, base, ext, ctx)


@pytest.mark.parametrize(
    "field,value", [("meet", 4), ("distance_m", 0), ("class_text", "")]
)
def test_reject_invalid_observed_context(field, value):
    targets, base, ext, ctx = inputs()
    ctx[ext[0]["race_id"]][field] = value
    with pytest.raises(ValueError, match="invalid_physical_context"):
        memory.project(targets, base, ext, ctx)


@pytest.mark.parametrize(
    "distance,label,count",
    [(1400, "classA", 1), (1401, "classA", 0), (1200, "classB", 0)],
)
def test_older_same_venue_exact_class_distance_boundary(distance, label, count):
    targets, base, _, ctx = inputs()
    ext = [record("20260515", meet=4)]
    ctx[ext[0]["race_id"]] = {
        "status": "observed",
        "meet": 4,
        "distance_m": distance,
        "class_text": label,
    }
    row = memory.project(targets, base, ext, ctx)["rows"][0]
    assert row["features"]["older_same_venue_similar_count"] == count


def test_target_labels_and_empty_targets_rejected():
    targets, base, ext, ctx = inputs()
    with pytest.raises(ValueError, match="empty_targets"):
        memory.project({}, base, ext, ctx)
    targets[next(iter(targets))][0]["rank"] = 1
    with pytest.raises(ValueError, match="identity_only"):
        memory.project(targets, base, ext, ctx)


def test_unknown_target_and_prior_conditions_do_not_drop_entrants():
    targets, base, ext, _ = inputs()
    rows = memory.project(targets, base, ext, {})["rows"]
    assert len(rows) == 3
    assert rows[0]["features"]["fallback90"] == "missing_target_conditions"
    assert rows[0]["features"]["older_missing_condition_count"] == 1
    assert rows[0]["features"]["older_same_venue_similar_count"] == 0


def test_sign_reversal_is_strict_not_merely_becoming_zero():
    prior = [
        record("20260901", 1),
        record("20260902", 5),
        record("20260903", 4),
        record("20260904", 3),
    ]
    matched = prior[:2]
    assert memory.contrast(prior, matched) == Fraction(1, 24)
    stress = memory.deletion_diagnostic(prior, matched)
    assert stress["strict_sign_reversal"]
    assert Fraction(stress["minimum"]) < 0 < Fraction(stress["maximum"])
    assert len(stress["cases"]) == 4


@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_cutoff_is_strict(offset):
    cutoff = datetime(2026, 10, 16, 1, 20, tzinfo=UTC)
    created = cutoff + timedelta(seconds=offset)
    if offset < 0:
        memory.check_time(created, cutoff)
    else:
        with pytest.raises(ValueError, match="not_before_cutoff"):
            memory.check_time(created, cutoff)


def test_naive_time_rejected():
    with pytest.raises(ValueError, match="not_before_cutoff"):
        memory.check_time(datetime(2026, 10, 15), datetime(2026, 10, 16, tzinfo=UTC))


def test_exclusive_report(tmp_path):
    path = tmp_path / "report.json"
    memory.save(path, {"original": True})
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        memory.save(path, {"original": False})
    assert path.read_bytes() == before
