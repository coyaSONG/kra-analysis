"""Selected versions, local source cutoffs, unchanged H0 and full membership."""

import asyncio
import copy
import json
import sys
from datetime import timedelta
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.observed_partial_history import FIELDS, project_partial_history
from shared.observed_result_history import H0, project_history

from autoresearch import observed_history_seed as seed
from autoresearch.frozen_history_view import replay_frozen
from autoresearch.observed_partial_projection import main, materialize
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.tests.test_history_identity_audit import source
from autoresearch.tests.test_observed_history_seed import execute, initialized, response
from autoresearch.tests.test_observed_result_history import add, fixture


def test_later_receipts_and_journal_do_not_change_frozen_input(tmp_path):
    root = initialized(tmp_path)
    asyncio.run(execute(root, lambda r: httpx.Response(503)))
    path = root / "frozen.json"
    original = seed.replay(root)
    sha = seed.save(path, original)
    assert replay_frozen(root, path, sha) == original
    asyncio.run(execute(root, response, retry_failed=True))
    assert seed.replay(root)["status_counts"] == {"api_reported_rows": 4}
    assert replay_frozen(root, path, sha) == original


@pytest.mark.parametrize(
    "change", ["pin", "rows", "inventory", "raw", "entry", "plan", "claim", "statuses"]
)
def test_selected_source_corruption_never_becomes_missing_or_zero(tmp_path, change):
    root, path, sha = source(tmp_path)
    value = json.loads(path.read_bytes())
    unit = next(r for r in value["inventory"] if r["status"] == "identity_unresolved")
    if change == "pin":
        sha = "0" * 64
    elif change == "raw":
        capture = root / unit["result"]["path"]
        manifest = json.loads(capture.read_bytes())
        (capture.parent / manifest["pages"][0]["raw_file"]).write_bytes(b"changed")
    elif change == "entry":
        capture = root / unit["entry"]["path"]
        capture.write_bytes(capture.read_bytes() + b" ")
    elif change == "plan":
        (root / "plan.json").write_bytes(b"{}")
    else:
        if change == "rows":
            value["records"].pop()
        elif change == "inventory":
            value["inventory"].pop()
        elif change == "claim":
            value["independent_timestamp_verified"] = True
        else:
            value["status_counts"] = {}
        path = root / "changed.json"
        sha = seed.save(path, value)
    with pytest.raises((ValueError, KeyError)):
        replay_frozen(root, path, sha)


def test_cutoff_is_aware_and_bounds_seed_creation(tmp_path):
    args = source(tmp_path)
    value = replay_frozen(*args)
    at = timestamp(value["materialized_at"])
    assert replay_frozen(*args, cutoff=at.isoformat()) == value
    with pytest.raises(ValueError, match="seed_after_cutoff"):
        replay_frozen(*args, cutoff=(at - timedelta(seconds=1)).isoformat())
    with pytest.raises(ValueError):
        replay_frozen(*args, cutoff="2099-01-01T00:00:00")


def test_cached_rows_cannot_replace_integer_with_equal_boolean(tmp_path):
    root, path, sha = source(tmp_path)
    value = replay_frozen(root, path, sha)
    value["records"][0]["chul_no"] = True
    path = root / "boolean.json"
    sha = seed.save(path, value)
    with pytest.raises(ValueError, match="source_replay_mismatch"):
        replay_frozen(root, path, sha)


def test_failed_partial_capture_bytes_remain_pinned(tmp_path):
    from autoresearch.tests.test_kra_result_snapshot import envelope, row

    root = initialized(tmp_path, budget=1)

    def pages(request):
        rows = [
            {**row(g, race_no=r), "meet": 1} for r in range(1, 7) for g in range(1, 19)
        ]
        return httpx.Response(200, json=envelope(rows[:100], total=108))

    asyncio.run(execute(root, pages))
    path = root / "frozen.json"
    sha = seed.save(path, seed.replay(root))
    assert replay_frozen(root, path, sha)["status_counts"]["failed"] == 1
    page = next((root / "results").rglob("page_*.json"))
    page.write_bytes(page.read_bytes() + b" ")
    with pytest.raises(ValueError, match="raw_pin_mismatch"):
        replay_frozen(root, path, sha)


@pytest.mark.parametrize("kind", ["result", "entry"])
def test_cutoff_checks_unresolved_source_including_api26(tmp_path, kind):
    root, path, sha = source(tmp_path)
    value = replay_frozen(root, path, sha)
    # Pin a seed claiming early creation: source clocks must independently fail.
    value["materialized_at"] = "2026-01-01T00:00:00+00:00"
    unit = next(r for r in value["inventory"] if r["status"] == "identity_unresolved")
    original = root / unit[kind]["path"]
    manifest = json.loads(original.read_bytes())
    manifest["collected_at" if kind == "entry" else "capture_completed_at"] = (
        "2099-01-01T00:00:00+00:00"
    )
    replacement = original.with_name("late.json")
    seed.save(replacement, manifest)
    unit[kind] = seed.pin(root, replacement)
    path = root / "late-seed.json"
    sha = seed.save(path, value)
    with pytest.raises(ValueError, match="source_after_cutoff_or_unknown"):
        replay_frozen(root, path, sha, cutoff="2098-12-31T00:00:00+00:00")


def test_partial_counts_do_not_change_legacy_gap_semantics():
    race, value = fixture()
    add(value, day="20260713", rank=1)
    add(value, rank=4)
    add(value, day="20261009", state="unresolved", rank=0)
    value["inventory"][0]["status"] = "identity_unresolved"
    original = copy.deepcopy(value)
    result = project_partial_history(race, value)
    assert result["legacy_projection"] == project_history(race, value)
    assert all(
        result["legacy_projection"]["feature_rows"][0]["features"][f] is None
        for f in H0
    )
    assert [result["feature_rows"][0]["features"][k] for k in FIELDS] == [
        2,
        1,
        1,
        0.5,
        1,
    ]
    assert result["feature_rows"][0]["ranked_denominator"] == 2
    assert result["feature_rows"][0]["observed_row_count"] == 3
    assert len(result["feature_rows"]) == 3
    assert result["response_unit_status_counts"]["identity_unresolved"] == 1
    assert sum(result["response_unit_status_counts"].values()) == 360
    assert value == original


def test_zero_observations_and_missing_units_are_explicit():
    race, value = fixture()
    value["inventory"].pop()
    result = project_partial_history(race, value)
    assert [result["feature_rows"][0]["features"][k] for k in FIELDS] == [
        0,
        0,
        0,
        None,
        0,
    ]
    assert result["response_unit_status_counts"] == {
        "empty_unconfirmed": 359,
        "missing": 1,
    }
    assert not result["complete_actual_start_history_verified"]


def test_labels_and_out_of_window_records_do_not_affect_partial_counts():
    race, value = fixture()
    event = add(value)
    expected = project_partial_history(race, value)
    for day in ("20260712", "20261011", "20261012"):
        value["records"].append({**event, "race_id": f"{day}_1_1", "raw_ord": 1})
    race["label_top3"] = [1, 2, 3]
    race["training_selected"] = False
    assert project_partial_history(race, value) == expected
    race["roster"][1]["horse_id"] = race["roster"][0]["horse_id"]
    with pytest.raises(ValueError, match="invalid_history_target_roster"):
        project_partial_history(race, value)


def test_materializer_keeps_all_rosters_collision_evidence_and_no_approvals(tmp_path):
    root, path, sha = source(tmp_path, ambiguous=True)
    race, _ = fixture()
    corpus = {
        "ledger": [
            race,
            {**race, "race_id": "20261012_3_1", "training_selected": False},
        ]
    }
    cp = root / "corpus.json"
    cs = seed.save(cp, corpus)
    result = materialize(root, path, sha, cp, cs)
    assert result["race_count"] == 2 and result["runner_count"] == 6
    assert result["quality_audit"]["observed_collision_group_count"] == 2
    assert result["quality_audit"]["unbound_row_count"] == 3
    assert (
        not result["training_approved"] and not result["counts_as_70_percent_evidence"]
    )
    assert not result["target_card_availability_verified"]
    for item in corpus["ledger"]:
        item.update(label_top3=[3, 1, 2], results=[{"ord": 1}], training_selected=True)
    cp2 = root / "corpus-labels.json"
    cs2 = seed.save(cp2, corpus)
    assert materialize(root, path, sha, cp2, cs2)["races"] == result["races"]
    output = root / "projection.json"
    args = [
        "--root",
        str(root),
        "--seed",
        str(path),
        "--seed-sha256",
        sha,
        "--corpus",
        str(cp),
        "--corpus-sha256",
        cs,
        "--output",
        str(output),
    ]
    assert main(args) == 0
    original = output.read_bytes()
    with pytest.raises(FileExistsError):
        main(args)
    assert output.read_bytes() == original
    with pytest.raises(ValueError, match="corpus_pin_mismatch"):
        materialize(root, path, sha, cp, "0" * 64)
    corpus["ledger"][1]["race_id"] = race["race_id"]
    cp3 = root / "duplicate.json"
    cs3 = seed.save(cp3, corpus)
    with pytest.raises(ValueError, match="invalid_race_membership"):
        materialize(root, path, sha, cp3, cs3)
