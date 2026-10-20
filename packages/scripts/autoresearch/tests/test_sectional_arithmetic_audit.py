import json
import socket
import subprocess
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest

from autoresearch import sectional_arithmetic_audit as audit


@pytest.mark.parametrize(
    "raw,expected",
    [("", None), ("0:00.0", Decimal(0)), ("1:15.6", Decimal("75.6"))],
)
def test_time_tokens_preserve_zero_and_missing(raw, expected):
    assert audit.seconds(raw) == expected


@pytest.mark.parametrize("raw", ["75.6", "1:60.0", "-0:01", "nan", " 0:01.0"])
def test_malformed_time_is_not_missing(raw):
    with pytest.raises(ValueError, match="unparsed_arithmetic_time"):
        audit.seconds(raw)


@pytest.mark.parametrize(
    "start,end,printed,origin,status,residual",
    [
        ("37.4", "75.6", "38.2", False, "exact", "0.0"),
        ("37.4", "75.6", "38.3", False, "arithmetic_conflict", "0.1"),
        (None, "75.6", "38.2", False, "missing_value", None),
        ("0", "75.6", "75.6", False, "nonpositive_value", None),
        ("0", "75.6", "75.6", True, "exact", "0.0"),
        ("37.4", "75.6", "0", False, "nonpositive_value", None),
        ("75.6", "37.4", "38.2", False, "nonincreasing_clock", None),
    ],
)
def test_relation_states_do_not_tune_tolerance(
    start, end, printed, origin, status, residual
):
    result = audit.check_relation(
        None if start is None else Decimal(start),
        Decimal(end),
        Decimal(printed),
        origin=origin,
    )
    assert result == {"status": status, "residual_seconds": residual}


def seoul_values():
    return ["0:13.6", "", "", "", "0:37.4", "", "1:02.2", "0:38.2", "0:13.4", "1:15.6"]


def busan_values(distance):
    header = audit.source.headers("busan_cumulative", distance)[1]

    def stamp(metres):
        return f"{metres // 600}:00.0"

    cumulative = ["" if h == "-" else stamp(int(h[:-1])) for h in header]
    return {
        "busan_cumulative": cumulative + ["2:00.0"],
        "busan_segment": ["0:10.0"] * 8 + ["2:00.0"],
    }


def test_seoul_checkpoint_is_not_final_duration_and_overlap_is_not_added():
    checks = audit.evaluate("seoul", 1200, {"seoul": seoul_values()})
    assert [r["status"] for r in checks] == ["exact", "exact"]
    assert [(r["start_m"], r["end_m"]) for r in checks] == [(600, 1200), (1000, 1200)]
    changed = seoul_values()
    changed[7] = changed[4]
    assert audit.evaluate("seoul", 1200, {"seoul": changed})[0]["status"] == (
        "arithmetic_conflict"
    )


def test_jeju_is_retained_without_invented_cumulative_clock():
    assert audit.evaluate("jeju", 1000, {"jeju": ["0:17.1"] * 8}) == []


@pytest.mark.parametrize("distance", [1200, 1300, 1400, 1600, 1800, 2200])
def test_busan_uses_labelled_positions_not_s1f_first(distance):
    v = busan_values(distance)
    header = audit.source.headers("busan_cumulative", distance)[1]
    v["busan_cumulative"][header.index("200M")] = "0:13.6"
    v["busan_segment"][0] = "0:13.6"
    first = audit.evaluate("busan", distance, v)[0]
    assert first["status"] == "exact"
    assert (first["start_m"], first["end_m"]) == (0, 200)


def test_busan_1300_generic_8f_6f_column_means_initial_100m():
    v = busan_values(1300)
    v["busan_cumulative"][1] = v["busan_segment"][2] = "0:08.5"
    check = audit.evaluate("busan", 1300, v)[2]
    assert check["relation"] == "8f_6f_initial_100"
    assert (check["start_m"], check["end_m"], check["status"]) == (0, 100, "exact")


def test_unknown_distance_and_unlabelled_positive_value_are_rejected():
    with pytest.raises(ValueError, match="unobserved_busan_distance"):
        audit.relations("busan", 2000, {})
    values = busan_values(1200)
    values["busan_cumulative"][0] = "0:10.0"
    with pytest.raises(ValueError, match="unlabelled_checkpoint"):
        audit.evaluate("busan", 1200, values)


def test_impossible_endpoint_with_printed_value_is_not_silently_dropped():
    result = audit.evaluate("busan", 1200, busan_values(1200))[1]
    assert result["status"] == "unsupported_endpoint_with_value"
    assert result["raw_printed_segment"] == "0:10.0"


def pipeline(tmp_path, monkeypatch):
    rid = "20260502_1_1"
    headers = audit.source.headers("seoul", 1200)
    text = "<table><caption>경주성적을</caption>" + "".join(
        "<tr>" + "".join(f"<th>{c}</th>" for c in row) + "</tr>" for row in headers
    )
    for gate in (1, 2):
        text += (
            "<tr>"
            + "".join(
                f"<td>{c}</td>" for c in [str(gate), str(gate), ""] + seoul_values()
            )
            + "</tr>"
        )
    text += "</table>"
    directory = tmp_path / "official"
    directory.mkdir()
    content = text.encode()
    (directory / "race.html").write_bytes(content)
    rows = [
        {"chul_no": i, "horse_id": str(i), "rank_text": str(i), "time_text": "1:15.6"}
        for i in (1, 2)
    ]
    evidence = {
        rid: {
            "parsed": {"race_id": rid, "event_support": "confirmed", "rows": rows},
            "capture": {
                "raw": {"path": "race.html", "sha256": audit.digest(content)},
                "encoding": "utf-8",
            },
        }
    }
    records = [
        {
            "race_id": rid,
            "chul_no": i,
            "horse_id": str(i),
            "raw_ord": i,
            "raw_rc_time": 75.6,
            "evidence": "ranked_finish_observed",
        }
        for i in (1, 2)
    ]
    seed = {"records": records, "status_counts": {"empty_unconfirmed": 1}}
    baseline = {"rows": 2, "races": 1, "exceptions": [], "official_sources": []}
    monkeypatch.setattr(audit.source, "audit", lambda *a: baseline)
    monkeypatch.setattr(audit, "replay_frozen", lambda *a, **k: seed)
    monkeypatch.setattr(audit, "replay_archive", lambda *a: evidence)
    monkeypatch.setattr(
        audit, "replay_guide", lambda *a: {"sha256": audit.GUIDE_RAW_SHA}
    )
    monkeypatch.setattr(
        audit, "parse_conditions", lambda *a: {"status": "observed", "distance_m": 1200}
    )
    return seed, evidence, baseline


def test_pipeline_is_read_only_and_preserves_full_population(tmp_path, monkeypatch):
    seed, _, _ = pipeline(tmp_path, monkeypatch)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    seed_before = deepcopy(seed)

    def forbidden(*a, **k):
        pytest.fail("unexpected live operation")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    result = audit.audit(tmp_path)
    assert (result["races"], result["rows"]) == (1, 2)
    assert result["checks"] == {"exact": 4}
    assert result["eligibility"] == {"supported": 2}
    assert result["target_outcomes_loaded"] is False
    assert result["fits"] == result["network_requests"] == 0
    assert result["seed_status_counts"] == {"empty_unconfirmed": 1}
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert seed == seed_before


@pytest.mark.parametrize("case", ["whole_race_conflict", "positive_unresolved"])
def test_arithmetic_never_reinstates_excluded_starts(tmp_path, monkeypatch, case):
    seed, _, _ = pipeline(tmp_path, monkeypatch)
    if case == "whole_race_conflict":
        seed["records"][0]["raw_ord"] = 2
        expected = {"whole_race_conflict": 2}
    else:
        seed["records"][0]["evidence"] = "unresolved"
        expected = {"unsupported_start": 1, "supported": 1}
    result = audit.audit(tmp_path)
    assert result["checks"] == {"exact": 4}
    assert result["eligibility"] == expected
    assert result["existing_exclusions_changed"] is False


@pytest.mark.parametrize("case", ["source_conflict", "changed_raw", "lost_identity"])
def test_pipeline_fails_closed_on_broken_evidence(tmp_path, monkeypatch, case):
    _, evidence, baseline = pipeline(tmp_path, monkeypatch)
    if case == "source_conflict":
        baseline["exceptions"] = [{"status": "numeric_conflict"}]
    elif case == "changed_raw":
        (tmp_path / "official" / "race.html").write_text("changed")
    else:
        evidence["20260502_1_1"]["parsed"]["rows"][0]["horse_id"] = "99"
    with pytest.raises(ValueError):
        audit.audit(tmp_path)


def test_guide_pin_rejects_changed_receipt(tmp_path):
    (tmp_path / "capture.json").write_text("{}")
    with pytest.raises(ValueError):
        audit.replay_guide(tmp_path)


@pytest.mark.parametrize("case", ["final_duration", "missing_gate", "header"])
def test_html_changes_are_checked_after_pin_verification(tmp_path, monkeypatch, case):
    _, evidence, _ = pipeline(tmp_path, monkeypatch)
    path = tmp_path / "official" / "race.html"
    text = path.read_text()
    if case == "final_duration":
        text = text.replace("0:38.2", "0:38.3", 1)
    elif case == "missing_gate":
        start = text.index("<tr><td>2</td>")
        text = text[:start] + "</table>"
    else:
        text = text.replace("3F-G", "wrong-section")
    content = text.encode()
    path.write_bytes(content)
    evidence["20260502_1_1"]["capture"]["raw"]["sha256"] = audit.digest(content)
    if case != "final_duration":
        with pytest.raises(ValueError):
            audit.audit(tmp_path)
    else:
        result = audit.audit(tmp_path)
        assert result["rows"] == 2
        assert result["checks"] == {"arithmetic_conflict": 1, "exact": 3}
        assert result["exceptions"][0]["residual_seconds"] == "0.1"
        assert result["exceptions"][0]["chul_no"] == 1


def test_report_reconciles_full_population_and_never_claims_training():
    path = Path(__file__).resolve().parents[4] / (
        "docs/research/experiments/2026-10-20-sectional-arithmetic/report.json"
    )
    content = path.read_bytes()
    assert audit.digest(content) == (
        "94fbd92c4f5506da4516bfe1e92858018ca9b2be24f567013eb8a4cccd53f18d"
    )
    result = json.loads(content)
    assert (result["races"], result["rows"]) == (102, 1029)
    assert result["eligibility"] == {
        "supported": 1001,
        "unsupported_start": 17,
        "whole_race_conflict": 11,
    }
    assert result["checks"] == {
        "exact": 2805,
        "missing_value": 40,
        "unsupported_endpoint": 417,
    }
    assert len(result["observations"]) == 1029
    assert (
        len(
            {
                (r["race_id"], r["chul_no"], r["horse_id"])
                for r in result["observations"]
            }
        )
        == 1029
    )
    counts = audit.Counter()
    for row in result["observations"]:
        counts.update(row["check_counts"])
    assert counts == result["checks"]
    assert (
        sum(
            r["arithmetic_scope"] == "no_independent_cumulative_counterpart"
            for r in result["observations"]
        )
        == 298
    )
    assert result["by_relation"]["busan:8f_6f_initial_100"] == {"exact": 44}
    assert result["by_relation"]["seoul:final_600"] == {
        "exact": 417,
        "missing_value": 14,
    }
    assert result["by_relation"]["seoul:final_200"] == {
        "exact": 417,
        "missing_value": 14,
    }
    assert not result["exceptions"]
    assert result["fits"] == result["network_requests"] == 0
    assert result["accuracy"] is None
    for field in (
        "counts_as_70_percent_evidence",
        "existing_exclusions_changed",
        "target_outcomes_loaded",
        "training_approved",
        "historical_prerace_verified",
    ):
        assert result[field] is False
