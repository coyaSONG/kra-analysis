"""Pinned raw evidence, canonical identity, and complete capture replay."""

import asyncio
import copy
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import kra_race_card_pdf_replay as replay
from autoresearch.tests.race_card_pdf_capture_fixture import (
    IDENTITY,
    capture_chain,
    capture_reused_entry_chain,
    entry,
    save_json,
)


@pytest.fixture
def chain(tmp_path):
    pytest.importorskip("pdfplumber")
    return asyncio.run(capture_chain(tmp_path))


def run_replay(chain, root, **overrides):
    path = Path(chain["pdf"]["manifest_path"])
    arguments = {
        "archive_root": root,
        "expected_sha256": replay.sha256(path.read_bytes()),
        "expected_identity": IDENTITY,
        "expected_pdf_sha256": chain["pdf"]["sha256"],
    }
    arguments.update(overrides)
    return replay.replay_race_card_snapshot(path, **arguments)


def assert_blocked(result, code=None):
    assert not result["eligible_for_prerace_features"]
    assert result["feature_rows"] == []
    assert result["reasons"]
    if code:
        assert code in result["reasons"]


def test_complete_replay_preserves_ids_and_raw_evidence(chain, tmp_path):
    result = run_replay(chain, tmp_path)
    assert result["eligible_for_prerace_features"]
    assert [row["hrNo"] for row in result["feature_rows"]] == ["001", "002"]
    assert result["features_available_at"] == chain["pdf"]["collected_at"]
    assert result["evidence"]["pdf"]["sha256"] == chain["pdf"]["sha256"]
    assert len(result["evidence"]["entry"]["pages"]) == 1
    assert not result["model_promoted"]


def test_pinned_pdf_manifest_cannot_be_edited(chain, tmp_path):
    path = Path(chain["pdf"]["manifest_path"])
    pin = replay.sha256(path.read_bytes())
    chain["pdf"]["collected_at"] = "2026-06-26T00:00:00+00:00"
    save_json(path, chain["pdf"])
    assert_blocked(
        run_replay(chain, tmp_path, expected_sha256=pin), "pdf_manifest_sha256_mismatch"
    )


def test_planned_pdf_digest_must_match_original_bytes(chain, tmp_path):
    assert_blocked(
        run_replay(chain, tmp_path, expected_pdf_sha256="0" * 64),
        "planned_pdf_sha256_mismatch",
    )


@pytest.mark.parametrize("kind", ["pdf", "entry_page"])
def test_changed_raw_bytes_never_emit_features(chain, tmp_path, kind):
    path = Path(
        chain["pdf"]["raw_path"]
        if kind == "pdf"
        else chain["entries"]["pages"][0]["raw_path"]
    )
    path.write_bytes(path.read_bytes() + b" ")
    assert_blocked(run_replay(chain, tmp_path), "raw_sha256_mismatch")


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("source_id", "unofficial", "pdf_manifest_contract_mismatch"),
        ("snapshot_version", "v2", "pdf_manifest_contract_mismatch"),
        ("url", "https://example.com/card.pdf", "pdf_manifest_contract_mismatch"),
        ("final_url", "https://example.com/card.pdf", "pdf_manifest_contract_mismatch"),
        ("race_no", 2, "source_race_identity_mismatch"),
        ("meet", True, "source_race_identity_mismatch"),
        ("byte_count", 1, "raw_byte_count_mismatch"),
        ("byte_count", True, "raw_byte_count_mismatch"),
        ("collected_at", "2026-06-27T01:00:00", "capture_timestamp_requires_timezone"),
        (
            "attempt_finished_at",
            "2026-06-27T00:59:59+00:00",
            "pdf_capture_order_mismatch",
        ),
        ("entry_snapshot", None, "missing_entry_capture_provenance"),
    ],
)
def test_pdf_manifest_contract_cannot_authorize_bad_sources(
    chain, tmp_path, field, value, code
):
    chain["pdf"][field] = value
    save_json(chain["pdf"]["manifest_path"], chain["pdf"])
    assert_blocked(run_replay(chain, tmp_path), code)


@pytest.mark.parametrize(
    "change", ["feature", "parser_version", "audit", "eligibility"]
)
def test_saved_derived_fields_are_recomputed_not_trusted(chain, tmp_path, change):
    pdf = chain["pdf"]
    if change == "feature":
        pdf["parsed"]["rows"][0]["training_count"] = 9999
        code = "pdf_parser_output_mismatch"
    elif change == "parser_version":
        pdf["parsed"]["parser_version"] = "unreviewed-parser"
        code = "parser_version_mismatch"
    elif change == "audit":
        pdf["audit"]["feature_rows"][0]["hrNo"] = "999"
        code = "saved_audit_mismatch"
    else:
        pdf["eligible_for_prerace_features"] = False
        code = "saved_audit_mismatch"
    save_json(pdf["manifest_path"], pdf)
    assert_blocked(run_replay(chain, tmp_path), code)


@pytest.mark.parametrize(
    "change,code",
    [
        ("request", "entry_page_request_mismatch"),
        ("boolean_request", "entry_page_request_mismatch"),
        ("page_number", "entry_page_request_mismatch"),
        ("page_rows", "entry_page_row_count_mismatch"),
        ("total", "incomplete_entry_capture"),
        ("timestamp", "entry_capture_order_mismatch"),
        ("projection", "entry_projection_mismatch"),
        ("projection_file", "entry_projection_file_mismatch"),
        ("url", "entry_manifest_contract_mismatch"),
        ("missing_pages", "missing_or_invalid_entry_pages"),
    ],
)
def test_entry_provenance_rebuilt_from_every_page(chain, tmp_path, change, code):
    entries = chain["entries"]
    if change == "request":
        entries["pages"][0]["request_parameters"]["rc_no"] = 2
    elif change == "boolean_request":
        entries["pages"][0]["request_parameters"]["rc_no"] = True
    elif change == "page_number":
        entries["pages"][0]["page_no"] = 2
    elif change == "page_rows":
        entries["pages"][0]["row_count"] = 1
    elif change == "total":
        entries["total_count"] = 3
    elif change == "timestamp":
        entries["pages"][0]["collected_at"] = "2026-06-27T02:00:00+00:00"
    elif change == "projection":
        entries["entry_snapshot"]["entries"][0]["hrNo"] = "999"
    elif change == "projection_file":
        payload = copy.deepcopy(entries["entry_snapshot"])
        payload["entries"][0]["hrNo"] = "999"
        save_json(entries["entry_snapshot_path"], payload)
    elif change == "url":
        entries["url"] += "?serviceKey=must-not-be-used"
    else:
        entries["pages"] = []
    save_json(entries["manifest_path"], entries)
    result = run_replay(chain, tmp_path)
    assert_blocked(result, code)
    assert "must-not-be-used" not in json.dumps(result)


def test_entry_manifest_digest_is_also_pinned(chain, tmp_path):
    path = Path(chain["entries"]["manifest_path"])
    pin = replay.sha256(path.read_bytes())
    chain["entries"]["pages"][0]["row_count"] = 1
    save_json(path, chain["entries"])
    assert_blocked(
        run_replay(chain, tmp_path, expected_entry_manifest_sha256=pin),
        "entry_manifest_sha256_mismatch",
    )


@pytest.mark.asyncio
async def test_shared_day_capture_rebuilds_target_race_without_rewriting_source(
    tmp_path,
):
    pytest.importorskip("pdfplumber")
    chain = await capture_reused_entry_chain(tmp_path)
    source_path = Path(chain["entries"]["manifest_path"])
    before = source_path.read_bytes()
    result = run_replay(chain, tmp_path, expected_identity={**IDENTITY, "race_no": 2})
    assert result["eligible_for_prerace_features"]
    assert result["evidence"]["entry"]["source_requested_identity"]["race_no"] == 1
    assert result["evidence"]["entry"]["target_identity"]["race_no"] == 2
    assert source_path.read_bytes() == before


@pytest.mark.parametrize("field,value", [("meet", 2), ("race_date", "20260628")])
def test_shared_entry_source_cannot_cross_meeting_or_date(
    chain, tmp_path, field, value
):
    chain["entries"][field] = value
    save_json(chain["entries"]["manifest_path"], chain["entries"])
    assert_blocked(run_replay(chain, tmp_path), "source_race_identity_mismatch")


def test_unexpected_parser_exception_is_a_blocker_not_a_partial_export(
    chain, tmp_path, monkeypatch
):
    class PDFLibraryError(Exception):
        pass

    def broken_parser(*args, **kwargs):
        raise PDFLibraryError("must-not-appear-in-output")

    monkeypatch.setattr(replay, "parse_race_card_pdf", broken_parser)
    result = run_replay(chain, tmp_path)
    assert_blocked(result, "pdf_reparse_failed")
    assert "must-not-appear-in-output" not in json.dumps(result)


@pytest.mark.asyncio
async def test_all_pages_are_required_even_when_requested_race_is_on_first(tmp_path):
    pytest.importorskip("pdfplumber")
    rows = [entry(1), entry(2)]
    rows.extend(
        entry(number, race_no=race_no, count=12)
        for race_no in range(2, 11)
        for number in range(1, 13)
    )
    chain = await capture_chain(tmp_path, rows=rows)
    assert len(chain["entries"]["pages"]) == 2
    assert run_replay(chain, tmp_path)["eligible_for_prerace_features"]
    chain["entries"]["pages"].pop()
    save_json(chain["entries"]["manifest_path"], chain["entries"])
    assert_blocked(run_replay(chain, tmp_path), "incomplete_entry_capture")


@pytest.mark.asyncio
async def test_late_capture_cannot_be_rehabilitated_by_replay(tmp_path):
    pytest.importorskip("pdfplumber")
    chain = await capture_chain(
        tmp_path, captured_at=datetime(2026, 6, 27, 2, 0, tzinfo=UTC)
    )
    assert_blocked(run_replay(chain, tmp_path), "source_after_cutoff")


@pytest.mark.asyncio
async def test_whole_race_with_name_mismatch_remains_blocked(tmp_path):
    pytest.importorskip("pdfplumber")
    rows = [entry(1), entry(2)]
    rows[0]["hrName"] = "different-official-name"
    chain = await capture_chain(tmp_path, rows=rows)
    result = run_replay(chain, tmp_path)
    assert_blocked(result, "incomplete_or_mismatched_entry_join")
    assert result["entry_horse_count"] == 2
    assert result["evidence"]["pdf"]["sha256"]


def test_relative_paths_are_resolved_from_explicit_archive_root(chain, tmp_path):
    result = replay.replay_race_card_snapshot(
        Path(chain["pdf"]["manifest_path"]).relative_to(tmp_path),
        archive_root=tmp_path,
        expected_sha256=replay.sha256(Path(chain["pdf"]["manifest_path"]).read_bytes()),
        expected_identity=IDENTITY,
    )
    assert result["eligible_for_prerace_features"]


def test_manifest_path_cannot_escape_archive_root(chain, tmp_path):
    assert_blocked(run_replay(chain, tmp_path / "other"), "archive_path_escapes_root")


def test_raw_symlink_escape_is_rejected_before_reading(chain, tmp_path):
    path = Path(chain["pdf"]["raw_path"])
    outside = tmp_path.parent / f"outside-{tmp_path.name}.pdf"
    outside.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(outside)
    assert_blocked(run_replay(chain, tmp_path), "archive_path_escapes_root")


def test_oversize_manifest_read_is_bounded(chain, tmp_path, monkeypatch):
    monkeypatch.setattr(replay, "MAX_MANIFEST_BYTES", 10)
    assert_blocked(run_replay(chain, tmp_path), "archive_file_too_large")


@pytest.mark.parametrize(
    "value,code",
    [
        (b'{"x":1,"x":2}', "duplicate_json_key"),
        (b'{"x":NaN}', "nonfinite_json_value"),
        (b"[]", "archive_json_not_object"),
    ],
)
def test_ambiguous_archive_json_is_rejected(value, code):
    with pytest.raises(replay.ReplayError, match=code):
        replay.parse_json(value)


def test_absent_raw_file_blocks_without_fabricating_features(chain, tmp_path):
    Path(chain["pdf"]["raw_path"]).unlink()
    assert_blocked(run_replay(chain, tmp_path), "archive_file_unavailable")
