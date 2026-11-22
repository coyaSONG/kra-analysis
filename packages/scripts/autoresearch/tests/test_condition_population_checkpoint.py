"""Fictional public archives exercise version selection without a live study."""

import socket
from copy import deepcopy
from datetime import timedelta

import pytest

from autoresearch import condition_population_checkpoint as checkpoint
from autoresearch.condition_forward_publication import ARCHIVE_FILES
from autoresearch.restricted_cohort import encoded, parse_json, sha256
from autoresearch.tests.condition_forward_fixture import archive_publication
from autoresearch.tests.test_condition_population_chain import journal
from autoresearch.tests.test_condition_population_ledger import bundle
from autoresearch.tests.test_kra_schedule import NOW, SOURCE_URLS, capture, page

BOUNDARY = NOW + timedelta(hours=3)


def file_pin(root, path, value=None):
    if value is not None:
        path.write_bytes(encoded(value))
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256(path.read_bytes()),
    }


def read_json(path):
    return parse_json(path.read_bytes())


def index_for(root, **changes):
    original, _, _ = bundle(root)
    initial = read_json(original)
    index = {
        "format_version": checkpoint.VERSION,
        "evidence_as_of": BOUNDARY.isoformat(),
        "umbrella": deepcopy(initial["umbrella"]),
        "journal_document": initial["journal"]["document"],
        "candidates": [file_pin(root, original)],
        "observation_gaps": [],
        **changes,
    }
    return index, initial


def write_candidate(
    root,
    initial,
    *,
    merged=NOW + timedelta(minutes=90),
    retrieved=NOW + timedelta(minutes=110),
    mode="appended",
):
    first = read_json(root / "journal/published-document.md")["events"][0]
    candidate = deepcopy(initial)
    later_capture = capture(
        root / "later-raw",
        pages={
            source: page(source, dates=dict.fromkeys(range(1, 5), "2026/10/23(\uae08)"))
            for source in SOURCE_URLS
        },
        clock=lambda: NOW + timedelta(minutes=10),
    )
    snapshot = file_pin(root, later_capture)
    candidate["snapshots"][snapshot["sha256"]] = snapshot
    if mode == "fork":
        first["source_effective_at"] = NOW.isoformat()
    appended = {
        **first,
        "sequence": 2,
        "previous_event_sha256": sha256(encoded(first)),
        "week_id": "week-02",
        "recorded_at": (NOW + timedelta(minutes=11)).isoformat(),
        "evidence_refs": [snapshot["sha256"]],
        "payload": {"capture_sha256": snapshot["sha256"]},
    }
    events = [first, appended]
    if mode == "short":
        events = []
    if mode == "repeat":
        events = [first]
    raw = encoded(
        {**journal(events), "umbrella_sha256": candidate["umbrella"]["sha256"]}
    )
    directory = root / "candidate-archive"
    archive_publication(
        directory, raw, 902, initial["journal"]["document"], merged, retrieved
    )
    candidate["journal"] = {
        **initial["journal"],
        "pull_number": 902,
        "sha256": sha256(raw),
        "files": {name: file_pin(root, directory / name) for name in ARCHIVE_FILES},
    }
    path = root / "later.json"
    return file_pin(root, path, candidate), later_capture


def args_for(root, index):
    path = root / "index.json"
    return path, file_pin(root, path, index)["sha256"]


def assert_not_promoted(result):
    assert result["denominator"] is None
    assert not result["usable_for_scoring"]
    assert not result["candidate_inventory_complete_verified"]
    assert not result["full_population_verified"]
    assert not result["counts_as_70_percent_evidence"]
    assert not result["outcomes_loaded"]
    assert not result["registration_performed"]


def test_select_by_merge_not_list_or_retrieval_order_and_keep_old_ids(
    tmp_path, monkeypatch
):
    index, initial = index_for(tmp_path)
    later, _ = write_candidate(tmp_path, initial)
    index["candidates"].insert(0, later)
    args = args_for(tmp_path, index)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    def forbidden(*_args, **_kwargs):
        pytest.fail("checkpoint replay attempted a network call")

    monkeypatch.setattr(socket, "socket", forbidden)
    result = checkpoint.audit(*args)
    assert result["status"] == "checkpoint_selected"
    assert result["selected"]["replay_manifest"] == later
    assert result["selected"]["event_count"] == 2
    assert len(result["verifier_sha256"]) == 64
    assert result["declared_week_ids"] == ["week-01", "week-02"]
    assert result["replay"]["observed_canonical_ids"] == [
        f"{day}_{venue}_1" for day in ("20261016", "20261023") for venue in range(1, 5)
    ]
    assert all(
        s["closure"] == "not_verified" for s in result["replay"]["expected_scopes"]
    )
    assert_not_promoted(result)
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


def test_later_merge_outside_boundary_does_not_replace_earlier_version(tmp_path):
    index, initial = index_for(tmp_path)
    index["candidates"].append(
        write_candidate(
            tmp_path,
            initial,
            merged=BOUNDARY + timedelta(seconds=1),
            retrieved=BOUNDARY + timedelta(minutes=1),
        )[0]
    )
    result = checkpoint.audit(*args_for(tmp_path, index))
    assert result["status"] == "checkpoint_selected"
    assert result["selected"]["replay_manifest"] == index["candidates"][0]
    assert result["candidates"][1]["status"] == "published_after_boundary"
    assert result["replay"]["observed_identifier_count_not_physical_n"] == 4
    assert_not_promoted(result)


def test_archive_retrieved_exactly_at_the_boundary_is_eligible(tmp_path):
    index, initial = index_for(tmp_path)
    later, _ = write_candidate(tmp_path, initial, retrieved=BOUNDARY)
    index["candidates"].append(later)
    result = checkpoint.audit(*args_for(tmp_path, index))
    assert result["status"] == "checkpoint_selected"
    assert result["selected"]["replay_manifest"] == later


@pytest.mark.parametrize("unavailable", ["manifest", "archive", "late_archive", "gap"])
def test_incomplete_evidence_does_not_fall_back(tmp_path, unavailable):
    index, initial = index_for(tmp_path)
    retrieved = (
        BOUNDARY + timedelta(seconds=1)
        if unavailable == "late_archive"
        else NOW + timedelta(minutes=110)
    )
    later, _ = write_candidate(tmp_path, initial, retrieved=retrieved)
    index["candidates"].append(later)
    expected = {
        "manifest": "pending_manifest",
        "archive": "pending_archive",
        "late_archive": "retrieved_after_boundary",
        "gap": "verified_candidate",
    }
    if unavailable == "manifest":
        (tmp_path / later["path"]).unlink()
    elif unavailable == "archive":
        (tmp_path / "candidate-archive/observed.json").unlink()
    elif unavailable == "gap":
        index["observation_gaps"].append(
            {"expected_at": NOW.isoformat(), "status": "rate_limited"}
        )
    result = checkpoint.audit(*args_for(tmp_path, index))
    assert result["status"] == "pending_evidence"
    assert result["reason"] == "incomplete_candidate_evidence"
    assert result["selected"] is None
    assert result["candidates"][0]["status"] == "verified_candidate"
    assert result["candidates"][1]["status"] == expected[unavailable]
    assert result["observation_gaps"] == index["observation_gaps"]
    assert_not_promoted(result)


def test_missing_raw_capture_retained_not_replaced_by_an_older_selection(tmp_path):
    index, initial = index_for(tmp_path)
    later, raw = write_candidate(tmp_path, initial)
    index["candidates"].append(later)
    raw.unlink()
    result = checkpoint.audit(*args_for(tmp_path, index))
    assert result["selected"]["replay_manifest"] == later
    assert result["replay"]["inventories"][1]["status"] == "pending_local_capture"
    assert result["replay"]["observed_identifier_count_not_physical_n"] == 4
    assert_not_promoted(result)


@pytest.mark.parametrize("mode", ["fork", "short", "repeat"])
def test_rewritten_or_unextended_history_is_not_a_later_checkpoint(tmp_path, mode):
    index, initial = index_for(tmp_path)
    index["candidates"].append(write_candidate(tmp_path, initial, mode=mode)[0])
    with pytest.raises(ValueError, match="non_append_only_history"):
        checkpoint.audit(*args_for(tmp_path, index))


def test_same_merge_timestamp_requires_unambiguous_version_order(tmp_path):
    index, initial = index_for(tmp_path)
    index["candidates"].append(
        write_candidate(tmp_path, initial, merged=NOW + timedelta(hours=1))[0]
    )
    with pytest.raises(ValueError, match="ambiguous_merge_clock"):
        checkpoint.audit(*args_for(tmp_path, index))


@pytest.mark.parametrize("removed", [False, True])
def test_existing_snapshot_cannot_be_repointed_or_dropped(tmp_path, removed):
    index, initial = index_for(tmp_path)
    later, _ = write_candidate(tmp_path, initial)
    path = tmp_path / later["path"]
    changed = read_json(path)
    original_digest = next(iter(initial["snapshots"]))
    if removed:
        changed["snapshots"].pop(original_digest)
    else:
        changed["snapshots"][original_digest]["path"] = "unavailable/capture.json"
    index["candidates"].append(file_pin(tmp_path, path, changed))
    with pytest.raises(ValueError, match="replaced_snapshot_pin"):
        checkpoint.audit(*args_for(tmp_path, index))


def test_candidate_must_bind_the_same_umbrella_and_document(tmp_path):
    index, initial = index_for(tmp_path)
    index["journal_document"] = "docs/research/protocols/unrelated.json"
    with pytest.raises(ValueError, match="checkpoint_candidate_binding"):
        checkpoint.audit(*args_for(tmp_path, index))
    index["journal_document"] = initial["journal"]["document"]
    initial["umbrella"]["sha256"] = "0" * 64
    index["candidates"] = [file_pin(tmp_path, tmp_path / "manifest.json", initial)]
    with pytest.raises(ValueError, match="checkpoint_candidate_binding"):
        checkpoint.audit(*args_for(tmp_path, index))


def test_corrupted_selected_raw_blocks_without_fallback(tmp_path, capsys):
    index, initial = index_for(tmp_path)
    later, raw = write_candidate(tmp_path, initial)
    index["candidates"].append(later)
    raw.write_bytes(b"corrupt")
    path, digest = args_for(tmp_path, index)
    assert checkpoint.main(["--index", str(path), "--sha256", digest]) == 2
    result = parse_json(capsys.readouterr().out.encode())
    assert result["status"] == "blocked"
    assert "hash_mismatch" in result["reason"]
    assert result["selected"] is None
    assert_not_promoted(result)


def test_index_hash_not_replaceable_and_empty_index_not_no_racing(tmp_path):
    index, _ = index_for(tmp_path)
    index["candidates"].clear()
    path, digest = args_for(tmp_path, index)
    result = checkpoint.audit(path, digest)
    assert result["status"] == "pending_evidence"
    assert result["reason"] == "no_timely_candidate"
    assert_not_promoted(result)
    path.write_bytes(encoded({**index, "observation_gaps": [{"status": "unknown"}]}))
    with pytest.raises(ValueError, match="hash_mismatch"):
        checkpoint.audit(path, digest)


def test_umbrella_retrieved_after_boundary_keeps_scope_pending(tmp_path):
    index, _ = index_for(
        tmp_path, evidence_as_of=(NOW + timedelta(hours=1)).isoformat()
    )
    result = checkpoint.audit(*args_for(tmp_path, index))
    assert result["reason"] == "umbrella_not_witnessed_at_boundary"
    assert result["selected"] is None
    assert_not_promoted(result)


def test_publication_cannot_enter_index_twice_via_different_manifests(tmp_path):
    index, initial = index_for(tmp_path)
    second = deepcopy(initial)
    snapshot_pin = next(iter(second["snapshots"].values()))
    snapshot_pin["path"] = "other/capture.json"
    index["candidates"].append(file_pin(tmp_path, tmp_path / "duplicate.json", second))
    with pytest.raises(ValueError, match="checkpoint_duplicate_publication"):
        checkpoint.audit(*args_for(tmp_path, index))
