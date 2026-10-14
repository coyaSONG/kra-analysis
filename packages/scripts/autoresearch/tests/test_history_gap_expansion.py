"""Historical expansion must not mutate a frozen policy or hide missingness."""

from copy import deepcopy

import pytest

from autoresearch import history_gap_expansion as expansion


def fixture():
    target = {
        "20261016_4_1": [
            {"horse_id": "1", "chul_no": 1},
            {"horse_id": "2", "chul_no": 2},
        ]
    }
    old = [
        {
            "race_id": "20260801_3_1",
            "horse_id": "1",
            "rank": 1,
            "observed_roster_size": 3,
            "tier": "dual_supported",
        }
    ]
    new = [{**old[0], "race_id": "20260520_3_1"}]
    context = {
        "status": "observed",
        "meet": 4,
        "class_text": "classA",
        "distance_m": 1200,
    }
    contexts = {
        "20261016_4_1": context,
        "20260801_3_1": {**context, "meet": 3},
        "20260520_3_1": {**context, "meet": 3},
    }
    return target, old, new, contexts


def test_adds_old_history_without_relabelling_venue_or_changing_90d():
    args = fixture()
    before = deepcopy(args)
    result = expansion.coverage(*args)
    row = result["rows"][0]
    assert row["prior_90d_count_unchanged"] == 1
    assert (row["prior_180d_before"], row["prior_180d_after"]) == (1, 2)
    assert row["similar_180d_after"] == 0
    assert result["strata"]["all"]["runner_rows"] == 2
    assert result["rows"][1]["prior_180d_after"] == 0
    assert args == before


@pytest.mark.parametrize("day,expected", [("20260418", 0), ("20260419", 1)])
def test_180_day_boundary_is_separate_from_frozen_90(day, expected):
    targets, old, new, contexts = fixture()
    new[0]["race_id"] = day + "_3_1"
    row = expansion.coverage(targets, old, new, contexts)["rows"][0]
    assert len(row["new_prior_ids"]) == expected


@pytest.mark.parametrize(
    "day,error",
    [
        ("20260801", "duplicate"),
        ("20261016", "target_or_future"),
        ("20261017", "target_or_future"),
        ("20260718", "changes_frozen_90d"),
    ],
)
def test_rejects_overlap_recent_and_target_results(day, error):
    targets, old, new, contexts = fixture()
    new[0]["race_id"] = day + "_3_1"
    with pytest.raises(ValueError, match=error):
        expansion.coverage(targets, old, new, contexts)


def test_same_venue_exact_class_distance_and_missing_context():
    targets, old, new, contexts = fixture()
    new[0]["race_id"] = "20260520_4_1"
    contexts["20260520_4_1"] = {**contexts["20261016_4_1"], "distance_m": 1400}
    assert (
        expansion.coverage(targets, old, new, contexts)["rows"][0]["similar_180d_after"]
        == 1
    )
    contexts["20260520_4_1"]["distance_m"] = 1401
    assert (
        expansion.coverage(targets, old, new, contexts)["rows"][0]["similar_180d_after"]
        == 0
    )
    del contexts["20260520_4_1"]
    assert (
        expansion.coverage(targets, old, new, contexts)["rows"][0]["similar_180d_after"]
        == 0
    )


def matched():
    records = [
        {
            "race_id": "20260520_1_1",
            "horse_id": str(n),
            "chul_no": n,
            "evidence": "ranked_finish_observed",
            "raw_ord": n,
            "raw_rc_time": 72 + n,
        }
        for n in (1, 2, 3)
    ]
    official = {
        "event_support": "confirmed",
        "race_id": "20260520_1_1",
        "rows": [
            {
                "horse_id": str(n),
                "chul_no": n,
                "rank_text": str(n),
                "time_text": f"1:{12 + n}.0",
            }
            for n in (1, 2, 3)
        ],
    }
    return records, {"20260520_1_1": {"parsed": official, "receipt": {"sha256": "pin"}}}


def test_whole_roster_rank_time_supported_and_unresolved_retained():
    records, evidence = matched()
    records[2]["evidence"] = "unresolved"
    extra, groups = expansion.supported_extension(records, evidence)
    assert len(extra) == 2
    assert all(r["observed_roster_size"] == 3 for r in extra)
    assert groups[0]["observed_rows"] == 3
    assert len(groups[0]["rows"]) == 3


@pytest.mark.parametrize("mutation", ["rank", "time", "roster", "event"])
def test_conflict_never_adds_partially_supported_group(mutation):
    records, evidence = matched()
    if mutation == "rank":
        records[0]["raw_ord"] = 2
    if mutation == "time":
        records[0]["raw_rc_time"] = 999
    if mutation == "roster":
        records.pop()
    if mutation == "event":
        evidence["20260520_1_1"]["parsed"]["race_id"] = "20260520_2_1"
    extra, groups = expansion.supported_extension(records, evidence)
    assert extra == []
    assert groups[0]["admitted_rows"] == 0


def test_outcome_bearing_targets_are_rejected():
    targets, old, new, contexts = fixture()
    targets["20261016_4_1"][0]["rank"] = 1
    with pytest.raises(ValueError, match="identity_only"):
        expansion.coverage(targets, old, new, contexts)
