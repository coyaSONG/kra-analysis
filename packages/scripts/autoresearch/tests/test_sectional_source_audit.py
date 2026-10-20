"""Sectional agreement is not approval to train or to reinterpret missingness."""

import socket
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest
from shared.official_result_support import Cell, Table, parse_detail

from autoresearch import sectional_source_audit as audit


@pytest.mark.parametrize(
    "api,text,status",
    [
        (74.7, "1:14.7", "positive_equal"),
        ("14.70", "0:14.7", "positive_equal"),
        (0, "", "zero_blank"),
        (0, "0:00.0", "zero_numeric_equal"),
        (1, "", "nonzero_blank_conflict"),
        (0, "0:01.0", "numeric_conflict"),
        (14.71, "0:14.7", "numeric_conflict"),
        (14, "14", "unparsed_html"),
        (14, "0:74.0", "unparsed_html"),
        (14, "-", "unparsed_html"),
        (14, "중지", "unparsed_html"),
        (None, "", "invalid_api_value"),
        (False, "", "invalid_api_value"),
        ([], "", "invalid_api_value"),
        ("NaN", "", "invalid_api_value"),
        ("inf", "", "invalid_api_value"),
        ("bad", "", "invalid_api_value"),
        (-1, "", "invalid_api_value"),
    ],
)
def test_compare_preserves_distinct_states(api, text, status):
    assert audit.compare(api, text) == status


@pytest.mark.parametrize(
    "distance,expected,labels",
    [
        (1200, ("G8f", "G6f", "S1f"), ["-", "-", "200M"]),
        (1300, ("G8f", "G6f", "S1f"), ["-", "100M", "200M"]),
        (1400, ("G8f", "G6f", "S1f"), ["-", "-", "200M"]),
        (1600, ("G8f", "S1f", "G6f"), ["-", "200M", "400M"]),
        (1800, ("G8f", "S1f", "G6f"), ["-", "200M", "600M"]),
        (2200, ("S1f", "G8f", "G6f"), ["200M", "600M", "1000M"]),
    ],
)
def test_busan_s1f_position_depends_on_observed_distance(distance, expected, labels):
    assert audit.fields("busan_cumulative", distance)[:3] == tuple(
        f"bu{part}AccTime" for part in expected
    )
    assert audit.headers("busan_cumulative", distance)[1][:3] == labels


def test_unknown_distance_is_not_extrapolated():
    with pytest.raises(ValueError, match="unobserved_busan_distance"):
        audit.headers("busan_cumulative", 2000)


def sample(kind="busan_cumulative", distance=1200):
    rows = [
        [Cell(text=x, tag="th") for x in row] for row in audit.headers(kind, distance)
    ]
    values = [""] * len(audit.fields(kind, distance))
    rows += [[Cell(text=x) for x in [str(g), str(g), "order", *values]] for g in (2, 1)]
    roster = {
        g: {"chul_no": g, "horse_id": str(10 + g), "rank_text": str(g)} for g in (1, 2)
    }
    return Table(rows=rows, closed=True), roster


@pytest.mark.parametrize("kind", ["seoul", "jeju", "busan_segment", "busan_cumulative"])
def test_roster_join_ignores_row_order_and_does_not_modify_tables(kind):
    table, roster = sample(kind)
    before = deepcopy((table, roster))
    result = audit.timing_rows(table, kind, 1200, roster)
    assert list(result) == [2, 1]
    assert (table, roster) == before


@pytest.mark.parametrize(
    "change,reason",
    [
        (lambda t, r: setattr(t, "closed", False), "malformed_sectional_table"),
        (lambda t, r: setattr(t.rows[0][0], "text", "changed"), "unknown_sectional"),
        (lambda t, r: t.rows.pop(), "missing_gate"),
        (lambda t, r: t.rows.append(t.rows[-1]), "gate_mismatch"),
        (lambda t, r: setattr(t.rows[-1][1], "text", "3"), "gate_mismatch"),
        (lambda t, r: setattr(t.rows[-1][0], "text", "9"), "rank_mismatch"),
        (lambda t, r: t.rows[-1].pop(), "malformed_sectional_row"),
        (lambda t, r: setattr(t.rows[-1][4], "span", True), "malformed_sectional_row"),
    ],
)
def test_changed_table_fails_closed(change, reason):
    table, roster = sample()
    change(table, roster)
    with pytest.raises(ValueError, match=reason):
        audit.timing_rows(table, "busan_cumulative", 1200, roster)


def test_distance_label_must_match():
    table, roster = sample()
    with pytest.raises(ValueError, match="unknown_sectional_headers"):
        audit.timing_rows(table, "busan_cumulative", 1400, roster)


def test_1200m_cumulative_example_matches_original_published_cells():
    table, roster = sample()
    values = ["", "", "0:13.6", "0:24.7", "0:36.5", "0:48.6", "1:01.1", "1:14.7"]
    table.rows[-1][3:] = [Cell(text=v) for v in values]
    api = {
        "buG8fAccTime": 0,
        "buG6fAccTime": 0,
        "buS1fAccTime": 13.6,
        "buG4fAccTime": 24.7,
        "buG3fAccTime": 36.5,
        "buG2fAccTime": 48.6,
        "buG1fAccTime": 61.1,
        "rcTime": 74.7,
    }
    parsed = audit.timing_rows(table, "busan_cumulative", 1200, roster)[1]
    counts = [
        audit.compare(api[field], value)
        for field, value in zip(
            audit.fields("busan_cumulative", 1200), parsed, strict=True
        )
    ]
    assert counts == ["zero_blank"] * 2 + ["positive_equal"] * 6


def test_original_seed_replay_is_mandatory(monkeypatch, tmp_path):
    def refuse(*args, **kwargs):
        raise ValueError("original_seed_pin_mismatch")

    monkeypatch.setattr(audit, "replay_frozen", refuse)
    with pytest.raises(ValueError, match="original_seed_pin"):
        audit.audit(tmp_path)


def pipeline(tmp_path, monkeypatch):
    """Exercise HTML parsers and joins; archive replayers have their own tests."""
    rid = "20260501_2_1"
    raw = {
        "rcNo": 1,
        "chulNo": 6,
        "hrNo": "00012",
        "rcTime": 73.6,
        "rcDist": 1000,
        "jeS1fTime": 17.1,
        "je_1cTime": 0,
        "je_2cTime": 0,
        "je_3cTime": 25.0,
        "je_4cTime": 40.9,
        "jeG3fTime": 48.6,
        "jeG1fTime": 16.7,
    }
    text = (
        "<table><tr><td>2026년 05월 01일 (금) 제1경주 제주</td>"
        + "<td></td>" * 5
        + "</tr><tr><td>제6등급</td><td>1000M</td>"
        + "<td></td>" * 5
        + "</tr></table>"
        "<table><caption>경주상세성적을</caption><tr><td>1</td><td>6</td>"
        "<td><a href=\"javascript:goHorse('00012','2')\">name</a></td>"
        "</tr></table>"
        "<table><caption>경주성적을</caption><tr>"
        "<th>순위</th><th>마번</th><th>S1F-1C-2C-3C-4C-G1F</th>"
        "<th>S-1F</th><th>1코너</th><th>2코너</th><th>3코너</th>"
        "<th>4코너</th><th>G-3F</th><th>G-1F</th><th>경주기록</th></tr>"
        "<tr><td>1</td><td>6</td><td>2- - - 1- 1- 1</td>"
        "<td>0:17.1</td><td></td><td></td><td>0:25.0</td>"
        "<td>0:40.9</td><td>0:48.6</td><td>0:16.7</td><td>1:13.6</td>"
        "</tr></table>"
    )
    directory = tmp_path / "official"
    directory.mkdir()
    content = text.encode()
    (directory / "race.html").write_bytes(content)
    ref = {"path": "race.html", "sha256": audit.digest(content)}
    (tmp_path / "capture.json").write_bytes(b"{}")
    pin = {"path": "capture.json", "sha256": audit.digest(b"{}")}
    seed = {
        "records": [
            {
                "race_id": rid,
                "chul_no": 6,
                "horse_id": "12",
                "raw_rc_time": 73.6,
                "source_capture_sha256": pin["sha256"],
            }
        ],
        "inventory": [
            {
                "status": "api_reported_rows",
                "day": "20260501",
                "meet": 2,
                "result": pin,
            },
            {"status": "empty_unconfirmed"},
        ],
        "status_counts": {"api_reported_rows": 1, "empty_unconfirmed": 1},
    }
    evidence = {
        rid: {
            "parsed": parse_detail(text),
            "receipt": {"path": "receipt.json"},
            "capture": {
                "raw": ref,
                "encoding": "utf-8",
                "request": {"url": "https://example.invalid/fixture"},
                "completed_at": "2026-10-15T12:00:00Z",
            },
        }
    }
    monkeypatch.setattr(audit, "replay_frozen", lambda *a, **k: seed)
    monkeypatch.setattr(audit, "replay_archive", lambda *a, **k: evidence)
    monkeypatch.setattr(
        audit,
        "replay_result_pages",
        lambda *a: {
            "capture_manifest_sha256": pin["sha256"],
            "rows": [raw],
        },
    )
    return raw, evidence, ref


def test_pipeline_preserves_inputs_and_denominators(tmp_path, monkeypatch):
    pipeline(tmp_path, monkeypatch)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    def forbidden(*args, **kwargs):
        pytest.fail("unexpected live operation")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    report = audit.audit(tmp_path)
    assert report["counts"] == {"positive_equal": 6, "zero_blank": 2}
    assert report["rows"] == report["races"] == 1
    assert report["by_venue_distance"]["2:1000"]["rows"] == 1
    assert report["seed_status_counts"]["empty_unconfirmed"] == 1
    assert report["fits"] == report["network_requests"] == 0
    assert report["training_approved"] is False
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


@pytest.mark.parametrize("issue", ["horse", "distance", "raw_pin"])
def test_pipeline_rejects_source_or_identity_change(tmp_path, monkeypatch, issue):
    raw, evidence, ref = pipeline(tmp_path, monkeypatch)
    if issue == "horse":
        evidence["20260501_2_1"]["parsed"]["rows"][0]["horse_id"] = "99"
    elif issue == "distance":
        raw["rcDist"] = 1100
    else:
        (tmp_path / "official" / ref["path"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="mismatch"):
        audit.audit(tmp_path)


def test_pipeline_retains_mismatches_not_a_matching_subset(tmp_path, monkeypatch):
    raw, _, _ = pipeline(tmp_path, monkeypatch)
    raw["jeG3fTime"] = 48.7
    result = audit.audit(tmp_path)
    assert result["counts"] == {
        "positive_equal": 5,
        "zero_blank": 2,
        "numeric_conflict": 1,
    }
    assert result["rows"] == 1
    assert result["exceptions"][0]["field"] == "jeG3fTime"
    assert result["exceptions"][0]["horse_id"] == "12"


def test_published_report_retains_entire_acquisition_population():
    import json

    path = Path(__file__).resolve().parents[4] / (
        "docs/research/experiments/2026-10-20-sectional-reconciliation/report.json"
    )
    content = path.read_bytes()
    assert audit.digest(content) == (
        "bb2d9ce7031efa252618a5411b3cb8530c028066aac1164671f0a7eb9a06badb"
    )
    report = json.loads(content)
    assert (report["races"], report["rows"]) == (102, 1029)
    assert report["counts"] == {"positive_equal": 8771, "zero_blank": 2161}
    assert not report["exceptions"]
    totals = {}
    fields = set()
    for group in report["by_venue_distance"].values():
        for name, counts in group["fields"].items():
            fields.add(name.split(":")[1])
            assert sum(counts.values()) == group["rows"]
            for status, count in counts.items():
                totals[status] = totals.get(status, 0) + count
    assert totals == report["counts"]
    assert len(fields) == 30
    assert sum(g["rows"] for g in report["by_venue_distance"].values()) == 1029
    assert len(report["official_sources"]) == 102
    assert len({s["race_id"] for s in report["official_sources"]}) == 102
    assert report["training_approved"] is False
    assert report["existing_exclusions_changed"] is False
    assert report["counts_as_70_percent_evidence"] is False
    assert report["accuracy"] is None
