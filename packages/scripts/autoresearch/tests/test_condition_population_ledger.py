"""Synthetic public archives and raw HTML, never an enrolled research interval."""

from copy import deepcopy
from datetime import timedelta

import pytest

from autoresearch import condition_population_ledger as ledger
from autoresearch import condition_population_sources as sources
from autoresearch.condition_forward_publication import ARCHIVE_FILES
from autoresearch.restricted_cohort import encoded, parse_json, sha256
from autoresearch.tests.condition_forward_fixture import archive_publication
from autoresearch.tests.test_condition_population_chain import event, journal
from autoresearch.tests.test_kra_schedule import NOW, SOURCE_URLS, capture, page


def bundle(tmp_path, *, events=None, pages=None):
    captured = capture(tmp_path / "raw", pages=pages)
    scope = {
        "format_version": ledger.SCOPE_VERSION,
        "weeks": [
            {
                "week_id": "week-01",
                "start_date": "20261012",
                "end_date": "20261018",
                "venues": [1, 2, 3, 4],
            },
            {
                "week_id": "week-02",
                "start_date": "20261019",
                "end_date": "20261025",
                "venues": [1, 2, 3, 4],
            },
        ],
    }

    def pin(path):
        return {
            "path": str(path.relative_to(tmp_path)),
            "sha256": sha256(path.read_bytes()),
        }

    def publish(kind, value, number, when):
        raw = encoded(value)
        directory = tmp_path / kind
        document = f"docs/research/protocols/synthetic-{kind}.json"
        archive_publication(
            directory, raw, number, document, when, NOW + timedelta(hours=2)
        )
        return {
            "pull_number": number,
            "document": document,
            "sha256": sha256(raw),
            "files": {name: pin(directory / name) for name in ARCHIVE_FILES},
        }

    scope_ref = publish("scope", scope, 900, NOW - timedelta(hours=1))
    capture_ref = pin(captured)
    first = {
        **event(),
        "umbrella_sha256": scope_ref["sha256"],
        "recorded_at": (NOW + timedelta(minutes=1)).isoformat(),
        "evidence_refs": [capture_ref["sha256"]],
        "payload": {"capture_sha256": capture_ref["sha256"]},
    }
    rows = [first]
    if events:
        for changes in events:
            rows.append(
                {
                    **first,
                    **changes,
                    "sequence": len(rows) + 1,
                    "previous_event_sha256": sha256(encoded(rows[-1])),
                }
            )
    value = journal(rows)
    value["umbrella_sha256"] = scope_ref["sha256"]
    manifest = {
        "format_version": ledger.VERSION,
        "umbrella": scope_ref,
        "journal": publish("journal", value, 901, NOW + timedelta(hours=1)),
        "snapshots": {capture_ref["sha256"]: capture_ref},
    }
    path = tmp_path / "manifest.json"
    path.write_bytes(encoded(manifest))
    return path, sha256(path.read_bytes()), captured


def test_raw_snapshot_and_public_journal_keep_missing_week_unknown(tmp_path):
    path, digest, _ = bundle(tmp_path)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    result = ledger.audit(path, digest)
    assert result["status"] == "observations_replayed"
    assert len(result["expected_scopes"]) == 56
    assert result["observed_identifier_count_not_physical_n"] == 4
    assert all(s["closure"] == "not_verified" for s in result["expected_scopes"])
    assert all(
        not s["observed_race_ids"]
        for s in result["expected_scopes"]
        if s["week_id"] == "week-02"
    )
    assert result["denominator"] is None
    assert result["full_population_verified"] is False
    assert not result["usable_for_scoring"]
    assert not result["outcomes_loaded"]
    assert result["actual_fit_count"] == 0
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


@pytest.mark.parametrize(
    "kind,slot",
    [
        ("week_closure", None),
        ("identity_link", "race-a"),
        ("race_change", "race-a"),
        ("execution_binding", "race-a"),
        ("race_enrolled", "race-a"),
    ],
)
def test_public_semantic_claims_never_override_source_completeness(
    tmp_path, kind, slot
):
    path, digest, _ = bundle(
        tmp_path,
        events=[
            {
                "event_type": kind,
                "slot_id": slot,
                "payload": {"complete": True, "no_races": True, "merge_into": "race-b"},
            }
        ],
    )
    result = ledger.audit(path, digest)
    assert result["semantic_events"][0]["status"] == "unverified_assertion"
    assert result["observed_identifier_count_not_physical_n"] == 4
    assert result["denominator"] is None


def test_missing_local_original_keeps_other_observations_and_unknown_n(tmp_path):
    path, digest, captured = bundle(tmp_path)
    raw = parse_json(captured.read_bytes())["sources"]["region_1"]["raw_file"]
    (captured.parent / raw).unlink()
    result = ledger.audit(path, digest)
    assert (
        result["inventories"][0]["source_failures"][0]["status"]
        == "missing_local_original"
    )
    assert result["observed_identifier_count_not_physical_n"] == 4
    assert result["denominator"] is None


def test_corrupt_original_blocks_instead_of_becoming_pending_or_no_races(tmp_path):
    path, digest, captured = bundle(tmp_path)
    raw = parse_json(captured.read_bytes())["sources"]["national"]["raw_file"]
    (captured.parent / raw).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="hash_mismatch"):
        ledger.audit(path, digest)


def test_missing_capture_is_not_zero_population(tmp_path):
    path, digest, captured = bundle(tmp_path)
    captured.unlink()
    result = ledger.audit(path, digest)
    assert result["inventories"][0]["status"] == "pending_local_capture"
    assert result["denominator"] is None
    assert len(result["expected_scopes"]) == 56


def test_missing_public_journal_keeps_declared_expected_scopes(tmp_path):
    path, digest, _ = bundle(tmp_path)
    (tmp_path / "journal/pull.json").unlink()
    result = ledger.audit(path, digest)
    assert result["status"] == "pending_publication"
    assert len(result["expected_scopes"]) == 56
    assert result["denominator"] is None


def test_corrupt_public_document_blocks(tmp_path):
    path, digest, _ = bundle(tmp_path)
    (tmp_path / "scope/published-document.md").write_bytes(b"{}")
    with pytest.raises(ValueError, match="hash_mismatch"):
        ledger.audit(path, digest)


def test_outside_scope_observations_retained(tmp_path):
    pages = {
        s: page(s, dates=dict.fromkeys(range(1, 5), "2026/10/30(\uae08)"))
        for s in SOURCE_URLS
    }
    path, digest, _ = bundle(tmp_path, pages=pages)
    result = ledger.audit(path, digest)
    assert len(result["outside_declared_scope"]) == 4
    assert result["denominator"] is None


@pytest.mark.parametrize(
    "change",
    [
        {"start_date": "20261013"},
        {"end_date": "20261019"},
        {"venues": [1, 2, 3]},
        {"venues": [True, 2, 3, 4]},
        {"venues": [1, 2, 3, 4, 4]},
        {"venues": []},
    ],
)
def test_partial_or_malformed_expected_scope_rejected(change):
    scope = {
        "format_version": ledger.SCOPE_VERSION,
        "weeks": [
            {
                "week_id": "w",
                "start_date": "20261012",
                "end_date": "20261018",
                "venues": [1, 2, 3, 4],
                **change,
            }
        ],
    }
    with pytest.raises(ValueError):
        ledger.expected_scopes(scope)


def test_source_clock_after_event_rejected(tmp_path):
    captured = capture(tmp_path / "raw")
    ref = {
        "path": str(captured.relative_to(tmp_path)),
        "sha256": sha256(captured.read_bytes()),
    }
    with pytest.raises(ValueError, match="capture_clock"):
        sources.snapshot(tmp_path, ref, NOW - timedelta(seconds=1))


def test_oversized_original_rejected(tmp_path, monkeypatch):
    captured = capture(tmp_path / "raw")
    ref = {
        "path": str(captured.relative_to(tmp_path)),
        "sha256": sha256(captured.read_bytes()),
    }
    monkeypatch.setattr(sources, "MAX_SOURCE_BYTES", 1)
    with pytest.raises(ValueError, match="too_large"):
        sources.snapshot(tmp_path, ref, NOW)


def test_symlink_original_rejected(tmp_path):
    path, digest, captured = bundle(tmp_path)
    raw = parse_json(captured.read_bytes())["sources"]["national"]["raw_file"]
    original = captured.parent / raw
    moved = tmp_path / "moved.html"
    original.rename(moved)
    original.symlink_to(moved)
    with pytest.raises(ValueError, match="symlink"):
        ledger.audit(path, digest)


def test_unparseable_pinned_source_not_no_races(tmp_path):
    captured = capture(
        tmp_path / "raw", pages=dict.fromkeys(SOURCE_URLS, b"<html>unpublished</html>")
    )
    ref = {
        "path": str(captured.relative_to(tmp_path)),
        "sha256": sha256(captured.read_bytes()),
    }
    result = sources.snapshot(tmp_path, ref, NOW)
    assert len(result["source_failures"]) == 4
    assert result["dates"] == []
    assert not result["full_population_verified"]


def test_manifest_pin_and_cli_failure(tmp_path, capsys):
    path, _, _ = bundle(tmp_path)
    assert ledger.main(["--manifest", str(path), "--sha256", "a" * 64]) == 2
    result = parse_json(capsys.readouterr().out.encode())
    assert result["status"] == "blocked"
    assert result["denominator"] is None


def test_smaller_later_inventory_does_not_erase_original_ids(tmp_path):
    path, _, captured = bundle(tmp_path)
    manifest = parse_json(path.read_bytes())
    original = parse_json((tmp_path / "journal/published-document.md").read_bytes())
    pages = {s: page(s, dates={1: "2026/10/17(\ud1a0)"}) for s in SOURCE_URLS}
    later = capture(tmp_path / "later", pages=pages)
    ref = {
        "path": str(later.relative_to(tmp_path)),
        "sha256": sha256(later.read_bytes()),
    }
    manifest["snapshots"][ref["sha256"]] = ref
    first = original["events"][0]
    original["events"].append(
        {
            **deepcopy(first),
            "sequence": 2,
            "previous_event_sha256": sha256(encoded(first)),
            "payload": {"capture_sha256": ref["sha256"]},
            "evidence_refs": [ref["sha256"]],
        }
    )
    original["event_count"] = 2
    original["head_sha256"] = sha256(encoded(original["events"][-1]))
    directory = tmp_path / "later-journal"
    document = manifest["journal"]["document"]
    archive_publication(
        directory,
        encoded(original),
        902,
        document,
        NOW + timedelta(hours=1),
        NOW + timedelta(hours=2),
    )
    manifest["journal"] = {
        "pull_number": 902,
        "document": document,
        "sha256": sha256(encoded(original)),
        "files": {
            n: {
                "path": str((directory / n).relative_to(tmp_path)),
                "sha256": sha256((directory / n).read_bytes()),
            }
            for n in ARCHIVE_FILES
        },
    }
    path.write_bytes(encoded(manifest))
    result = ledger.audit(path, sha256(path.read_bytes()))
    assert "20261016_1_1" in result["observed_canonical_ids"]
    assert "20261017_1_1" in result["observed_canonical_ids"]
    assert result["observed_identifier_count_not_physical_n"] == 5
    assert result["denominator"] is None
