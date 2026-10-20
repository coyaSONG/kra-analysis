import json
import socket
import subprocess
from copy import deepcopy
from datetime import date, timedelta
from fractions import Fraction
from itertools import permutations
from pathlib import Path

import pytest

from autoresearch import time_information_audit as audit


def row(gate=1, total="80", **updates):
    return {
        "race_id": "20260501_1_1",
        "chul_no": gate,
        "horse_id": str(gate),
        "meet": "1",
        "distance_m": 1200,
        "rank": gate,
        "total_seconds": total,
        "initial_seconds": "14",
        "final_seconds": "40",
        "history_eligibility": "supported",
        "required_available_at": ["2026-10-15T00:00:00Z"],
        "pace_status": "missing_or_invalid_endpoint",
        **updates,
    }


def members():
    return [row(1, "80"), row(2, "81"), row(3, "82")]


def test_exact_quantities_and_reference_including_focal():
    result = audit.describe(members())
    first = result["observations"][0]
    assert first["quantities"] == {
        "relative_time": "-1/81",
        "initial_speed_ratio": "20/21",
        "final_speed_ratio": "1",
    }
    assert result["reference_groups"]["20260501_1_1"]["median_seconds"] == "81"
    assert result["historical_rank_pair_order"]["relative_time"] == {"same_order": 3}
    assert (
        result["by_venue_distance"]["1:1200"]["quantities"]["relative_time"]["distinct"]
        == 3
    )


def test_row_order_does_not_change_output_and_inputs_remain_intact():
    rows = members()
    before = deepcopy(rows)
    expected = audit.describe(rows)
    for ordered in permutations(rows):
        assert audit.describe(list(ordered)) == expected
    assert rows == before


@pytest.mark.parametrize("value", [None, "0", "-1"])
def test_missing_or_nonpositive_total_withholds_whole_reference(value):
    rows = members()
    rows[0]["total_seconds"] = value
    result = audit.describe(rows)
    assert result["reference_groups"]["20260501_1_1"]["status"] == (
        "invalid_reference_time"
    )
    assert all(r["quantities"]["relative_time"] is None for r in result["observations"])


@pytest.mark.parametrize("value", [None, "0", "-1", "80", "90"])
def test_invalid_segment_never_divides_by_zero_or_exceeds_total(value):
    rows = members()
    rows[0]["initial_seconds"] = value
    assert (
        audit.describe(rows)["observations"][0]["quantities"]["initial_speed_ratio"]
        is None
    )


def test_positive_excluded_time_never_enters_reference_or_quantities():
    rows = members() + [row(4, "1", history_eligibility="unsupported_start")]
    result = audit.describe(rows)
    reference = result["reference_groups"]["20260501_1_1"]
    assert reference["median_seconds"] == "81"
    assert len(reference["members"]) == 3
    assert reference["excluded"][0]["reason"] == "unsupported_start"
    assert all(v is None for v in result["observations"][3]["quantities"].values())


def test_requires_two_other_comparators_not_forced_single_runner_zero():
    for count in (1, 2):
        result = audit.describe(members()[:count])
        assert all(
            r["missing_reasons"]["relative_time"] == "insufficient_comparators"
            for r in result["observations"]
        )


@pytest.mark.parametrize("case", ["duplicate", "horse", "gate", "missing"])
def test_bad_identity_fails_closed(case):
    rows = members()
    if case == "duplicate":
        rows.append(deepcopy(rows[0]))
    elif case == "horse":
        rows[1]["horse_id"] = rows[0]["horse_id"]
    elif case == "gate":
        rows[1]["chul_no"] = rows[0]["chul_no"]
    else:
        rows[0]["horse_id"] = ""
    with pytest.raises(ValueError, match="duplicate_or_missing|duplicate_race"):
        audit.describe(rows)


def test_rank_and_quantity_ties_are_not_strict_equivalence():
    rows = members()
    rows[1]["total_seconds"] = "80"
    result = audit.describe(rows)
    assert result["historical_rank_pair_order"]["relative_time"] == {
        "quantity_tie_only": 1,
        "same_order": 2,
    }
    rows[1]["rank"] = 1
    rows[1]["total_seconds"] = "81"
    assert audit.describe(rows)["historical_rank_pair_order"]["relative_time"] == {
        "rank_tie_only": 1,
        "same_order": 2,
    }


def test_speed_ratio_order_can_differ_without_claiming_target_skill():
    rows = members()
    rows[0]["initial_seconds"] = "13"
    result = audit.describe(rows)
    counts = result["historical_rank_pair_order"]["initial_speed_ratio"]
    assert counts == {"opposite_order": 2, "same_order": 1}
    assert Fraction(result["observations"][0]["quantities"]["initial_speed_ratio"]) > 1


@pytest.mark.parametrize(
    "age,accepted", [(-1, False), (0, False), (1, True), (180, True), (181, False)]
)
def test_single_history_window_boundary(age, accepted):
    target = row(race_id="20261101_1_1")
    historical = row(race_id=f"{(date(2026, 11, 1) - timedelta(days=age)):%Y%m%d}_1_2")
    assert bool(audit.prior_rows([historical], target)) is accepted


@pytest.mark.parametrize(
    "change",
    [
        {"horse_id": "9"},
        {"meet": "3"},
        {"distance_m": 1400},
        {"history_eligibility": "whole_race_conflict"},
    ],
)
def test_repeat_requires_same_horse_venue_distance_and_eligibility(change):
    target = row(race_id="20260508_1_1")
    assert audit.prior_rows([row(**change)], target) == []


@pytest.mark.parametrize(
    "clocks,accepted",
    [
        (["2026-10-14T00:00:00Z"], True),
        (["2026-10-15T00:00:00Z"], False),
        (["2026-10-16T00:00:00Z"], False),
        ([], False),
        ([None], False),
        (["2026-10-14T00:00:00Z", "2026-10-20T17:51:17Z"], False),
    ],
)
def test_asof_requires_every_operand_reference_and_semantic_clock(clocks, accepted):
    target = row(race_id="20261016_1_1")
    old = row(required_available_at=clocks)
    assert (
        bool(
            audit.prior_rows(
                [old],
                target,
                freeze="2026-10-15T00:00:00Z",
                cutoff="2026-10-16T01:20:00Z",
            )
        )
        is accepted
    )


def test_late_reference_does_not_change_an_earlier_asof_view():
    rows = members()
    rows[1]["required_available_at"] = ["2026-10-21T00:00:00Z"]
    result = audit.describe(rows)
    target = row(race_id="20261023_1_1")
    assert (
        audit.prior_rows(
            result["observations"],
            target,
            freeze="2026-10-20T00:00:00Z",
            cutoff="2026-10-23T01:00:00Z",
        )
        == []
    )
    assert "2026-10-21T00:00:00Z" in result["observations"][0]["required_available_at"]
    assert audit.prior_rows(
        result["observations"],
        target,
        freeze="2026-10-22T00:00:00Z",
        cutoff="2026-10-23T01:00:00Z",
    )


@pytest.mark.parametrize(
    "freeze,cutoff",
    [
        (None, "2026-10-16T00:00:00Z"),
        ("2026-10-16T00:00:00Z", None),
        ("2026-10-16T00:00:00Z", "2026-10-16T00:00:00Z"),
    ],
)
def test_incomplete_or_equal_feature_boundary_is_rejected(freeze, cutoff):
    with pytest.raises(ValueError):
        audit.prior_rows([], row(), freeze=freeze, cutoff=cutoff)


def test_repeat_counts_are_structural_not_may_prerace_evidence():
    rows = members() + [
        row(1, "79", race_id="20260508_1_1"),
        row(2, "80", race_id="20260508_1_1"),
        row(3, "81", race_id="20260508_1_1"),
    ]
    result = audit.describe(rows)
    assert result["structural_repeat_counts"]["with_prior"] == 3
    assert result["observations"][3]["structural_prior_support"]["latest_age_days"] == 7
    assert result["last_possible_history_day"] == "2026-11-04"
    assert (
        audit.prior_rows(
            result["observations"],
            rows[3],
            freeze="2026-05-07T00:00:00Z",
            cutoff="2026-05-08T00:00:00Z",
        )
        == []
    )


def test_jeju_null_pace_retained_and_no_live_operation(monkeypatch):
    def forbidden(*a, **k):
        pytest.fail("unexpected live operation")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    rows = [
        row(
            i,
            str(80 + i),
            meet="2",
            race_id="20260501_2_1",
            initial_seconds=None,
            final_seconds=None,
            pace_status="unverified_jeju_endpoints",
        )
        for i in range(1, 4)
    ]
    result = audit.describe(rows)
    assert result["rows"] == 3
    for r in result["observations"]:
        assert r["quantities"]["relative_time"] is not None
        assert r["missing_reasons"]["final_speed_ratio"] == "unverified_jeju_endpoints"


def test_ambiguous_versions_cannot_be_silently_selected():
    old, newer = row(), row(total="79")
    with pytest.raises(ValueError, match="multiple_versions"):
        audit.prior_rows([old, newer], row(race_id="20260508_1_1"))


def pipeline(tmp_path, monkeypatch):
    rid = "20260501_1_1"
    time_values = [
        "0:14.0",
        "",
        "",
        "",
        "0:40.0",
        "",
        "1:05.0",
        "0:40.0",
        "0:15.0",
        "1:20.0",
    ]
    header = audit.arithmetic.source.headers("seoul", 1200)
    text = "<table><caption>경주성적을</caption>" + "".join(
        "<tr>" + "".join(f"<th>{c}</th>" for c in part) + "</tr>" for part in header
    )
    for i in (1, 2, 3):
        text += (
            "<tr>"
            + "".join(f"<td>{c}</td>" for c in [str(i), str(i), ""] + time_values)
            + "</tr>"
        )
    text += "</table>"
    directory = tmp_path / "official"
    directory.mkdir()
    content = text.encode()
    (directory / "race.html").write_bytes(content)
    raw = {"path": "race.html", "sha256": audit.arithmetic.digest(content)}
    records = [
        {
            "race_id": rid,
            "chul_no": i,
            "horse_id": str(i),
            "raw_ord": i,
            "source_available_at": "2026-10-15T00:00:00Z",
        }
        for i in (1, 2, 3)
    ]
    baseline = {
        "rows": 3,
        "races": 1,
        "exceptions": [],
        "implementation_sha256": "test",
        "eligibility": {"supported": 3},
        "official_sources": [],
        "observations": [{**r, "history_eligibility": "supported"} for r in records],
        "sectional_definition_source": {
            "capture_completed_at": "2026-10-20T17:51:17Z",
        },
    }
    seed = {"records": records, "status_counts": {"empty_unconfirmed": 1}}
    evidence = {
        "list_20260501_1": {"parsed": {"event_support": "unknown"}},
        rid: {
            "capture": {
                "raw": raw,
                "encoding": "utf-8",
                "completed_at": "2026-10-15T00:00:01Z",
            },
            "parsed": {
                "rows": [
                    {"chul_no": i, "horse_id": str(i), "rank_text": str(i)}
                    for i in (1, 2, 3)
                ]
            },
        },
    }
    monkeypatch.setattr(audit.arithmetic, "audit", lambda *a: baseline)
    monkeypatch.setattr(audit.arithmetic, "replay_frozen", lambda *a, **k: seed)
    monkeypatch.setattr(audit.arithmetic, "replay_archive", lambda *a: evidence)
    monkeypatch.setattr(
        audit.arithmetic,
        "parse_conditions",
        lambda *a: {"distance_m": 1200, "status": "observed"},
    )
    return baseline


def test_loader_uses_actual_guide_clock_schema_and_raw_html(tmp_path, monkeypatch):
    pipeline(tmp_path, monkeypatch)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    def forbidden(*a, **k):
        pytest.fail("unexpected network or training process")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    result = audit.audit(tmp_path)
    assert result["rows"] == 3
    assert result["eligibility"] == {"supported": 3}
    assert result["observations"][0]["quantities"]["relative_time"] == "0"
    assert "2026-10-20T17:51:17Z" in result["observations"][0]["required_available_at"]
    assert result["fits"] == result["network_requests"] == 0
    assert result["future_target_coverage"] is result["accuracy"] is None
    assert not result["training_approved"]
    assert not result["target_outcomes_loaded"]
    assert result["seed_status_counts"] == {"empty_unconfirmed": 1}
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


@pytest.mark.parametrize("case", ["pin", "conflict", "identity"])
def test_original_source_failures_stop_derivation(tmp_path, monkeypatch, case):
    baseline = pipeline(tmp_path, monkeypatch)
    if case == "pin":
        (tmp_path / "official" / "race.html").write_text("changed")
    elif case == "conflict":
        baseline["exceptions"] = [{"status": "arithmetic_conflict"}]
    else:
        baseline["observations"].pop()
    with pytest.raises(ValueError):
        audit.audit(tmp_path)


def test_published_population_report_and_no_training_claim():
    root = Path(__file__).resolve().parents[4]
    content = (
        root / "docs/research/experiments/2026-10-20-time-information/report.json"
    ).read_bytes()
    assert audit.arithmetic.digest(content) == (
        "f9d8e4843ba4144bb3ee5d154fb09af4aa2bd7a8582e99d49484314c7f65905f"
    )
    result = json.loads(content)
    assert (result["rows"], result["races"], result["unique_horses"]) == (
        1029,
        102,
        1029,
    )
    assert result["eligibility"] == {
        "supported": 1001,
        "unsupported_start": 17,
        "whole_race_conflict": 11,
    }
    assert len(result["by_venue_distance"]) == 18
    assert sum(g["rows"] for g in result["by_venue_distance"].values()) == 1029
    assert len({audit.identity(r) for r in result["observations"]}) == 1029
    assert result["horses_with_multiple_observations"] == 0
    assert result["max_observations_per_horse"] == 1
    assert result["last_possible_history_day"] == "2026-11-06"
    for metric, expected in zip(audit.METRICS, (1001, 705, 705), strict=True):
        assert (
            sum(r["quantities"][metric] is not None for r in result["observations"])
            == expected
        )
        assert (
            sum(
                g["quantities"][metric]["n"]
                for g in result["by_venue_distance"].values()
            )
            == expected
        )
    for row in result["observations"]:
        if row["history_eligibility"] != "supported":
            assert all(v is None for v in row["quantities"].values())
        assert row["structural_prior_support"]["count"] == 0
    assert result["historical_rank_pair_order"]["relative_time"] == {
        "same_order": 4381,
        "quantity_tie_only": 146,
        "missing_pair": 222,
    }
    assert result["fits"] == result["network_requests"] == 0
    assert result["future_target_coverage"] is result["future_dates_and_n"] is None
    assert result["accuracy"] is None
    for key in (
        "target_outcomes_loaded",
        "training_approved",
        "historical_prerace_verified",
        "counts_as_70_percent_evidence",
    ):
        assert result[key] is False
