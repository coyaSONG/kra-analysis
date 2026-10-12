"""Complete archived membership, strict prior dates, and replay provenance."""

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import history_coverage_study as s
from autoresearch.tests.test_official_history_support import captured


def fixture():
    rows, groups = [], {}
    for day in (
        "20260712",
        "20260713",
        "20260901",
        "20261001",
        "20261010",
        "20261011",
        "20261012",
    ):
        identity = f"{day}_1_1"
        row = {"race_id": identity, "horse_id": "100", "chul_no": 1}
        rows.append(row)
        groups[identity] = {
            "race_id": identity,
            "official_event_support": "confirmed",
            "roster_support": "exact",
            "rows": [
                dict(
                    row,
                    ranked_feature_supported=True,
                    event_linked_api_unresolved=False,
                )
            ],
        }
    groups["20261001_1_1"].update(official_event_support="unknown", rows=[])
    groups["20261010_1_1"]["rows"][0].update(
        ranked_feature_supported=False,
        event_linked_api_unresolved=True,
    )
    return rows, groups


def test_full_membership_boundaries_unresolved_and_unknown():
    rows, groups = fixture()
    before = copy.deepcopy((rows, groups))
    result = s.project(rows, groups)
    assert len(result["rows"]) == len(rows)
    target = result["rows"][-2]
    assert target["race_id"] == "20261011_1_1"
    assert target["prior_supported_race_ids"] == ["20260713_1_1", "20260901_1_1"]
    assert target["prior_linked_unresolved_count_90d"] == 1
    assert target["prior_withheld_count_90d"] == 1
    assert result["strata"]["all"]["runner_rows"] == 7
    assert (rows, groups) == before


def test_same_day_other_race_excluded_and_order_invariant():
    rows, groups = fixture()
    other = dict(rows[-2], race_id="20261011_1_2")
    rows.append(other)
    groups[other["race_id"]] = copy.deepcopy(groups["20261011_1_1"])
    groups[other["race_id"]]["race_id"] = other["race_id"]
    result = s.project(rows, groups)
    counts = [
        r["prior_supported_ranked_count_90d"]
        for r in result["rows"]
        if r["race_id"][:8] == "20261011"
    ]
    assert counts == [2, 2]
    assert s.project(list(reversed(rows)), groups) == result


def test_missing_runner_not_removed_for_race_coverage():
    rows, groups = fixture()
    new = dict(rows[-1], horse_id="200", chul_no=2)
    rows.append(new)
    groups[new["race_id"]]["rows"].append(
        dict(
            new,
            ranked_feature_supported=True,
            event_linked_api_unresolved=False,
        )
    )
    result = s.project(rows, groups)
    assert result["strata"]["all"]["runner_rows"] == 8
    assert result["rows"][-1]["prior_supported_ranked_count_90d"] == 0
    assert result["strata"]["all"]["all_runners_have_prior_ranked"] == 5


@pytest.mark.parametrize("change", ["duplicate", "missing_group", "roster", "identity"])
def test_invalid_inputs_fail(change):
    rows, groups = fixture()
    if change == "duplicate":
        rows.append(rows[0])
    elif change == "missing_group":
        groups.pop(rows[0]["race_id"])
    elif change == "identity":
        groups[rows[0]["race_id"]]["race_id"] = "wrong"
    else:
        groups[rows[0]["race_id"]]["rows"] = []
    with pytest.raises(ValueError):
        s.project(rows, groups)


def test_full_replay_and_raw_tampering(tmp_path):
    root, path, sha, seed, directory, receipt = captured(tmp_path)
    args = root, path, sha, directory, receipt["sha256"]
    result = s.materialize(*args)
    assert len(result["rows"]) == len(seed["records"])
    assert result["training_approved"] is False
    assert result["counts_as_70_percent_evidence"] is False
    assert result["historical_pre_race_availability_verified"] is False
    assert result["strata"]["all"]["with_prior_ranked"] == 0
    raw = next(directory.glob("*.html"))
    raw.write_bytes(raw.read_bytes() + b" ")
    with pytest.raises(ValueError, match="pin_mismatch"):
        s.materialize(*args)


def test_extension_fixed_targets_and_overlap_rejection(monkeypatch):
    rows, groups = fixture()
    base_rows = rows[-2:]
    base_groups = {r["race_id"]: groups[r["race_id"]] for r in base_rows}
    extra_rows = rows[:-2]
    extra_groups = {r["race_id"]: groups[r["race_id"]] for r in extra_rows}

    def replay(root, *args):
        source_rows, source_groups = (
            (base_rows, base_groups) if root == "base" else (extra_rows, extra_groups)
        )
        return {
            "records": copy.deepcopy(source_rows),
            "status_counts": {},
        }, copy.deepcopy(source_groups)

    monkeypatch.setattr(s, "replay_source", replay)
    result = s.materialize(
        "base",
        None,
        "a" * 64,
        None,
        "b" * 64,
        extensions=[("extra", None, "c" * 64, None, "d" * 64)],
    )
    assert len(result["rows"]) == 2
    assert result["baseline_strata"]["all"]["with_prior_ranked"] == 1
    assert result["strata"]["all"]["with_prior_ranked"] == 2
    assert result["coverage_delta"]["all"]["runner_rows"] == 0
    with pytest.raises(ValueError, match="overlapping"):
        s.materialize(
            "base", None, "a", None, "b", extensions=[("base", None, "a", None, "b")]
        )


def test_unknown_targets_rejected():
    rows, groups = fixture()
    with pytest.raises(ValueError, match="target_membership"):
        s.project(rows, groups, target_ids={"20990101_1_1"})
