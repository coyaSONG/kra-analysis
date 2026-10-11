"""Calendar lag, independent rosters, coverage and observed-event semantics."""

import copy
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.observed_result_history import H0, H1_ADDITIONS, project_history


def fixture():
    race = {
        "race_id": "20261011_1_1",
        "roster": [{"horse_id": str(i), "chul_no": i} for i in (1, 2, 3)],
    }
    target = datetime(2026, 10, 11)
    inventory = [
        {
            "day": (target - timedelta(days=i)).strftime("%Y%m%d"),
            "meet": meet,
            "status": "empty_unconfirmed",
            "result": {"sha256": f"{i}-{meet}"},
            "available_at": "2026-10-12T00:00:00+00:00",
        }
        for i in range(1, 91)
        for meet in (1, 2, 3, 4)
    ]
    return race, {"inventory": inventory, "records": []}


def add(seed, *, day="20261001", rank=2, state="ranked_finish_observed", horse="1"):
    source = next(r for r in seed["inventory"] if r["day"] == day and r["meet"] == 1)
    source["status"] = "api_reported_rows"
    row = {
        "race_id": f"{day}_1_1",
        "horse_id": horse,
        "chul_no": int(horse),
        "raw_ord": rank,
        "evidence": state,
        "source_capture_sha256": source["result"]["sha256"],
        "source_available_at": source["available_at"],
    }
    seed["records"].append(row)
    return row


def test_observed_history_and_unresolved_semantics():
    race, seed = fixture()
    add(seed, day="20260713", rank=1)  # Exactly 90 days before target.
    add(seed, day="20260911", rank=4)  # Exactly 30 days before target.
    add(seed)
    add(seed, day="20261009", rank=99, state="unresolved")
    result = project_history(race, seed)
    values = result["feature_rows"][0]["features"]
    assert [values[k] for k in H0] == [3, 1, 2, 2 / 3, 1]
    assert [values[k] for k in H1_ADDITIONS] == [2, 10, 2, 7 / 3, True]
    assert len(result["feature_rows"][0]["lineage"]) == 4
    assert not result["training_approved"]
    assert not result["historical_pre_race_availability_verified"]


def test_target_future_and_out_of_window_events_cannot_change_features():
    race, seed = fixture()
    event = add(seed)
    expected = project_history(race, seed)
    for day in ("20260712", "20261011", "20261012"):
        seed["records"].append({**event, "race_id": f"{day}_1_1", "raw_ord": 1})
    assert project_history(race, seed) == expected
    race["results"] = [{"horse_id": "1", "ord": 1}]
    race["roster"][0].update(rating=999, ord=1, winOdds=1.1)
    assert project_history(race, seed) == expected
    race["results"] = []
    assert project_history(race, seed) == expected


def test_zero_observations_are_not_debut_or_true_rest_interval():
    race, seed = fixture()
    result = project_history(race, seed)
    values = result["feature_rows"][0]["features"]
    assert values[H0[0]] == 0 and not values[f"{H0[0]}_missing"]
    assert values[H0[3]] is None
    assert values[H1_ADDITIONS[1]] is None
    assert values[H1_ADDITIONS[4]] is None
    assert not result["complete_actual_start_history_verified"]


@pytest.mark.parametrize("status", ["failed", "identity_unresolved", "not_attempted"])
def test_incomplete_window_is_null_not_zero_and_never_drops_runner(status):
    race, seed = fixture()
    add(seed)
    seed["inventory"][0]["status"] = status
    result = project_history(race, seed)
    assert len(result["feature_rows"]) == 3
    assert len(result["missing_response_units"]) == 1
    assert all(
        row["features"][k] is None
        for row in result["feature_rows"]
        for k in (*H0, *H1_ADDITIONS)
    )
    assert len(result["feature_rows"][0]["lineage"]) == 1


@pytest.mark.parametrize("change", ["coverage", "event", "source", "runner", "gate"])
def test_duplicate_or_mismatched_identity_is_rejected(change):
    race, seed = fixture()
    event = add(seed)
    if change == "coverage":
        seed["inventory"].append(copy.deepcopy(seed["inventory"][0]))
    elif change == "event":
        seed["records"].append(copy.deepcopy(event))
    elif change == "source":
        event["source_capture_sha256"] = "wrong"
    elif change == "runner":
        race["roster"][1]["horse_id"] = "1"
    else:
        race["roster"][1]["chul_no"] = 1
    with pytest.raises(ValueError):
        project_history(race, seed)


def test_later_revision_changes_new_view_not_frozen_view():
    race, seed = fixture()
    add(seed, rank=1)
    original = project_history(race, seed)
    changed = copy.deepcopy(seed)
    changed["records"][0]["raw_ord"] = 8
    assert project_history(race, changed)["feature_rows"][0]["features"][H0[2]] == 0
    assert project_history(race, seed) == original


def test_same_day_events_do_not_invent_an_observation_order():
    race, seed = fixture()
    add(seed, rank=1)
    second = add(seed, rank=5)
    second["race_id"] = "20261001_1_2"
    unknown = add(seed, rank=99, state="unresolved")
    unknown["race_id"] = "20261001_1_3"
    values = project_history(race, seed)["feature_rows"][0]["features"]
    assert values[H1_ADDITIONS[1]] == 10
    assert values[H1_ADDITIONS[2]] is None
    assert values[H1_ADDITIONS[3]] == 3
    assert values[H1_ADDITIONS[4]] is None
