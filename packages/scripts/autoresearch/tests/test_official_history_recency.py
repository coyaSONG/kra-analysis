"""Supported observation recency never certifies rest or historical availability."""

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.observed_partial_history import project_partial_history

from autoresearch import official_history_recency as r
from autoresearch.observed_history_seed import save
from autoresearch.tests.test_observed_result_history import add, fixture
from autoresearch.tests.test_official_history_support import captured


def base_for(race, seed, withheld=()):
    old = project_partial_history(race, seed)
    groups = []
    for event in seed["records"]:
        ranked = event["evidence"] == "ranked_finish_observed"
        groups.append(
            {
                "race_id": event["race_id"],
                "official_event_support": "confirmed",
                "roster_support": "exact",
                "evidence": {"receipt": {"path": event["race_id"], "sha256": "a" * 64}},
                "rows": [
                    {
                        "horse_id": event["horse_id"],
                        "chul_no": event["chul_no"],
                        "ranked_feature_supported": ranked,
                        "event_linked_api_unresolved": not ranked,
                        "official_row": {"rank_text": str(event["raw_ord"])},
                    }
                ],
            }
        )
    lookup = {e["race_id"]: e for e in seed["records"]}
    members = []
    for row in old["feature_rows"]:
        used, unknown, excluded = [], [], []
        for link in row["lineage"]:
            if link["race_id"] in withheld:
                excluded.append(
                    {**link, "reason_codes": ["rank_or_time_not_supported"]}
                )
            elif lookup[link["race_id"]]["evidence"] == "ranked_finish_observed":
                used.append(link)
            else:
                unknown.append(link)
        members.append(
            {
                "horse_id": row["horse_id"],
                "chul_no": row["chul_no"],
                "features": {"ranked_finish_count_90d": len(used)},
                "used_ranked_lineage": used,
                "linked_unresolved_lineage": unknown,
                "withheld_lineage": excluded,
            }
        )
    return {
        "groups": groups,
        "races": [
            {
                "race_id": race["race_id"],
                "observed_partial_v1": old,
                "official_supported_partial_v1": members,
            }
        ],
    }


def values(base, runner=0):
    return r.project_recency(base)[0]["feature_rows"][runner]["features"]


def test_supported_recency_boundaries_and_evidence():
    race, seed = fixture()
    add(seed, day="20260713", rank=1)
    add(seed, day="20260911", rank=4)
    add(seed, day="20261001", rank=2)
    add(seed, day="20261009", rank=99, state="unresolved")
    base = base_for(race, seed)
    before = copy.deepcopy(base)
    result = r.project_recency(base)
    row = result[0]["feature_rows"][0]
    assert [row["features"][key] for key in r.FIELDS] == [2, 10, 2, 7 / 3, True]
    assert len(row["ranked_lineage"]) == 3
    assert all(
        link["official_receipt"]["sha256"] == "a" * 64 for link in row["ranked_lineage"]
    )
    assert len(result[0]["feature_rows"]) == 3
    assert base == before


def test_zero_observations_not_rest_or_debut():
    race, seed = fixture()
    base = base_for(race, seed)
    result = values(base)
    assert [result[key] for key in r.FIELDS] == [0, None, None, None, None]
    assert not result[r.FIELDS[0] + "_missing"]
    assert result[r.FIELDS[1] + "_missing"]
    assert r.project_recency(base)[0]["response_unit_status_counts"] == {
        "empty_unconfirmed": 360
    }


@pytest.mark.parametrize("status", ["failed", "identity_unresolved", "not_attempted"])
def test_partial_sources_keep_observed_values_and_explicit_gaps(status):
    race, seed = fixture()
    add(seed)
    seed["inventory"][0]["status"] = status
    result = values(base_for(race, seed))
    assert [result[key] for key in r.FIELDS] == [1, 10, 2, 2, False]
    assert result["response_window_incomplete"]
    assert result["response_30d_window_incomplete"]


def test_withheld_recent_event_does_not_replace_supported_rank():
    race, seed = fixture()
    add(seed, day="20260901", rank=7)
    rejected = add(seed, day="20261009", rank=1)
    base = base_for(race, seed, withheld=[rejected["race_id"]])
    result = values(base)
    assert [result[key] for key in r.FIELDS] == [0, 40, 7, 7, False]
    assert result["withheld_observation_count_90d"] == 1
    assert result["withheld_on_or_after_last_supported_date"]
    assert len(r.project_recency(base)[0]["feature_rows"][0]["withheld_lineage"]) == 1


def test_same_day_latest_rank_ambiguous_but_mean_of_both_defined():
    race, seed = fixture()
    event = add(seed, rank=2)
    seed["records"].append({**event, "race_id": "20261001_1_2", "raw_ord": 8})
    result = values(base_for(race, seed))
    assert [result[key] for key in r.FIELDS] == [2, 10, None, 5, False]
    assert result["last_supported_rank_same_day_ambiguous"]


def test_last_three_split_date_is_unknown_and_permutation_invariant():
    race, seed = fixture()
    first = add(seed, day="20260901", rank=1)
    seed["records"].append({**first, "race_id": "20260901_1_2", "raw_ord": 9})
    add(seed, day="20260911", rank=4)
    add(seed, rank=2)
    base = base_for(race, seed)
    result = values(base)
    assert [result[key] for key in r.FIELDS] == [2, 10, 2, None, False]
    assert result["last_three_boundary_same_day_ambiguous"]
    base["races"][0]["official_supported_partial_v1"][0][
        "used_ranked_lineage"
    ].reverse()
    assert values(base) == result


@pytest.mark.parametrize("later,expected", [(False, None), (True, True)])
def test_same_day_unresolved_is_not_artificially_ordered(later, expected):
    race, seed = fixture()
    event = add(seed)
    seed["records"].append(
        {**event, "race_id": "20261001_1_2", "raw_ord": 99, "evidence": "unresolved"}
    )
    if later:
        add(seed, day="20261009", state="unresolved", rank=99)
    assert values(base_for(race, seed))[r.FIELDS[4]] is expected


def test_target_future_and_old_events_or_labels_do_not_change_features():
    race, seed = fixture()
    event = add(seed)
    expected = r.project_recency(base_for(race, seed))
    for day in ("20260712", "20261011", "20261012"):
        seed["records"].append({**event, "race_id": f"{day}_1_1", "raw_ord": 1})
    race.update(label_top3=[9, 8, 7], training_selected=False)
    assert r.project_recency(base_for(race, seed)) == expected


@pytest.mark.parametrize(
    "change", ["duplicate", "window", "unsupported", "roster", "group"]
)
def test_invalid_intermediate_evidence_is_rejected(change):
    race, seed = fixture()
    add(seed)
    base = base_for(race, seed)
    members = base["races"][0]["official_supported_partial_v1"]
    links = members[0]["used_ranked_lineage"]
    if change == "duplicate":
        links.append(copy.deepcopy(links[0]))
    elif change == "window":
        links[0]["race_id"] = race["race_id"]
    elif change == "unsupported":
        base["groups"][0]["rows"][0]["ranked_feature_supported"] = False
    elif change == "roster":
        members.pop()
    else:
        base["groups"].append(copy.deepcopy(base["groups"][0]))
    with pytest.raises(ValueError, match="recency_"):
        r.project_recency(base)


def source_args(tmp_path):
    root, path, sha, seed, directory, receipt = captured(tmp_path)
    race, _ = fixture()
    race["roster"] = [
        {"horse_id": row["horse_id"], "chul_no": row["chul_no"]}
        for row in seed["records"]
    ]
    corpus = {"ledger": [race, {**copy.deepcopy(race), "race_id": "20261012_1_1"}]}
    cp = root / "corpus.json"
    cs = save(cp, corpus)
    return (root, path, sha, directory, receipt["sha256"], cp, cs), corpus


def test_raw_source_replay_retains_all_targets_and_is_reproducible(tmp_path):
    args, corpus = source_args(tmp_path)
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    result = r.materialize(*args)
    assert (result["race_count"], result["runner_count"]) == (2, 6)
    assert result == r.materialize(*args)
    assert before == {
        str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()
    }
    assert not result["training_approved"]
    assert not result["counts_as_70_percent_evidence"]
    assert not result["historical_pre_race_availability_verified"]
    assert values(result["support_projection"])[r.FIELDS[1]] == 1
    for race in corpus["ledger"]:
        race.update(label_top3=[], training_selected=False)
    cp = tmp_path / "changed-corpus.json"
    other = r.materialize(*args[:5], cp, save(cp, corpus))
    assert other["races"] == result["races"]
    with pytest.raises(ValueError, match="after_cutoff"):
        r.materialize(*args, cutoff="2026-01-01T00:00:00Z")


def test_corrupted_source_is_not_accepted_as_cached_projection(tmp_path):
    args, _ = source_args(tmp_path)
    path = next(args[3].glob("*.html"))
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="pin_mismatch"):
        r.materialize(*args)


def test_cli_writes_once_and_retains_previous_artifact(tmp_path):
    args, _ = source_args(tmp_path)
    flags = [
        "--root",
        "--seed",
        "--seed-sha256",
        "--archive-dir",
        "--archive-sha256",
        "--corpus",
        "--corpus-sha256",
    ]
    command = [
        part for pair in zip(flags, map(str, args), strict=True) for part in pair
    ]
    output = tmp_path / "new-output" / "features.json"
    command += ["--output", str(output)]
    assert r.main(command) == 0
    before = output.read_bytes()
    with pytest.raises(FileExistsError):
        r.main(command)
    assert output.read_bytes() == before
