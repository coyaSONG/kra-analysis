"""Raw value inventory is neither a speed feature nor model validation."""

import socket
import subprocess
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest

from autoresearch import history_time_audit as time_audit
from autoresearch.restricted_cohort import parse_json, sha256
from autoresearch.tests.test_history_identity_audit import source


@pytest.mark.parametrize(
    "row,expected",
    [
        ({}, "absent"),
        ({"x": None}, "null"),
        ({"x": " "}, "empty"),
        ({"x": False}, "boolean"),
        ({"x": []}, "nonnumeric"),
        ({"x": "bad"}, "nonnumeric"),
        ({"x": "NaN"}, "nonfinite"),
        ({"x": "inf"}, "nonfinite"),
        ({"x": -1}, "negative"),
        ({"x": 0}, "zero"),
        ({"x": "0.0"}, "zero"),
        ({"x": 12.3}, "positive"),
        ({"x": "12.3"}, "positive"),
    ],
)
def test_states_preserve_missing_zero_and_invalid(row, expected):
    assert time_audit.state(row, "x") == expected


def fixture():
    raw = [
        {"rcNo": 1, "chulNo": 2, "hrNo": "00012", "rcTime": 70.2},
        {"rcNo": 1, "chulNo": 1, "hrNo": "00011", "rcTime": 70.0},
    ]
    selected = [
        {
            "race_id": "20260501_2_1",
            "chul_no": 1,
            "horse_id": "11",
            "raw_rc_time": 70.0,
        },
        {
            "race_id": "20260501_2_1",
            "chul_no": 2,
            "horse_id": "12",
            "raw_rc_time": 70.2,
        },
    ]
    return raw, selected


def test_join_is_by_full_identity_not_input_order():
    raw, selected = fixture()
    before = deepcopy([raw, selected])
    result = time_audit.join_rows(raw, selected, "20260501", 2)
    assert [r["identity"][1] for r in result] == [2, 1]
    assert [raw, selected] == before


@pytest.mark.parametrize(
    "change,reason",
    [
        (lambda r, s: r.append(r[0]), "raw_identity"),
        (lambda r, s: r.pop(), "missing_raw"),
        (lambda r, s: r[0].update(hrNo="13"), "raw_identity"),
        (lambda r, s: r[0].update(rcTime=70.0), "elapsed_value"),
        (lambda r, s: s.append(s[0]), "duplicate_selected"),
    ],
)
def test_join_refuses_incomplete_duplicate_or_changed_evidence(change, reason):
    raw, selected = fixture()
    change(raw, selected)
    with pytest.raises(ValueError, match=reason):
        time_audit.join_rows(raw, selected, "20260501", 2)


def test_venue_specific_zeroes_do_not_become_times_or_missing():
    rows = [
        {
            "identity": ("20260501_2_1", 1, "11"),
            "raw": {"rcTime": 70.0, "jeG1fTime": 12.0, "bu_1fGTime": 0},
        },
        {
            "identity": ("20260501_3_1", 1, "12"),
            "raw": {"rcTime": 80.0, "jeG1fTime": 0, "bu_1fGTime": 13.0},
        },
        {"identity": ("20260501_3_1", 2, "13"), "raw": {"rcTime": 0}},
    ]
    report = time_audit.profile(rows)
    assert report["by_meet"]["2"]["fields"]["bu_1fGTime"]["zero"] == 1
    assert report["by_meet"]["3"]["fields"]["bu_1fGTime"]["positive"] == 1
    assert report["by_meet"]["3"]["fields"]["bu_1fGTime"]["absent"] == 1
    for group in report["by_meet"].values():
        for counts in group["fields"].values():
            assert sum(counts.values()) == group["rows"]


def test_real_replay_is_required_before_raw_profile(monkeypatch, tmp_path):
    def stop(*args, **kwargs):
        raise ValueError("frozen_history_seed_pin_mismatch")

    monkeypatch.setattr(time_audit, "replay_frozen", stop)
    with pytest.raises(ValueError, match="seed_pin"):
        time_audit.audit(
            tmp_path, tmp_path / "seed.json", "0" * 64, "2026-10-16T01:20:00Z"
        )


def test_published_inventory_is_complete_but_never_training_approval():
    path = Path(__file__).resolve().parents[4] / (
        "docs/research/experiments/2026-10-20-history-time-audit/report.json"
    )
    raw = path.read_bytes()
    assert (
        sha256(raw)
        == "f844015088ae10ec754bbbfa8e2f0fc0867c9bd58881bdd16bdfed454baee75c"
    )
    report = parse_json(raw)
    assert report["rows"] == 1029
    assert report["races"] == 102
    assert report["seed_status_counts"] == {
        "api_reported_rows": 12,
        "empty_unconfirmed": 44,
    }
    assert len(report["fields"]) == 30
    assert sum(g["rows"] for g in report["by_meet"].values()) == report["rows"]
    assert sum(g["races"] for g in report["by_meet"].values()) == report["races"]
    assert (
        sum(g["fields"]["rcTime"]["positive"] for g in report["by_meet"].values())
        == 1011
    )
    for group in report["by_meet"].values():
        assert set(group["fields"]) == set(report["fields"])
        for counts in group["fields"].values():
            assert set(counts) == set(time_audit.STATES)
            assert sum(counts.values()) == group["rows"]
    assert report["fits"] == report["network_requests"] == 0
    for flag in (
        "training_approved",
        "models_modified",
        "counts_as_70_percent_evidence",
        "field_units_verified",
        "sectional_cross_source_agreement_verified",
        "zero_semantics_verified",
        "historical_prerace_availability_verified",
    ):
        assert report[flag] is False


def test_synthetic_archive_end_to_end_is_read_only(tmp_path, monkeypatch):
    root, path, sha = source(tmp_path)
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}

    def forbidden(*args, **kwargs):
        pytest.fail("unexpected live operation")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    report = time_audit.audit(root, path, sha, datetime.now(UTC).isoformat())
    assert report["rows"] == 3
    assert report["races"] == 1
    assert report["non_row_units_retained_by_status"]["identity_unresolved"] == 1
    assert set(report["by_meet"]) == {"3"}
    assert report["fits"] == report["network_requests"] == 0
    assert not report["training_approved"]
    assert before == {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_changed_original_cannot_be_profiled_as_new_observation(tmp_path):
    root, path, sha = source(tmp_path)
    seed = parse_json(path.read_bytes())
    unit = next(u for u in seed["inventory"] if u["status"] == "api_reported_rows")
    capture = root / unit["result"]["path"]
    manifest = parse_json(capture.read_bytes())
    (capture.parent / manifest["pages"][0]["raw_file"]).write_bytes(b"{}")
    with pytest.raises(ValueError, match="raw_pin_mismatch"):
        time_audit.audit(root, path, sha, datetime.now(UTC).isoformat())
