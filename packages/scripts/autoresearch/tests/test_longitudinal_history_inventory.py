import json
import socket
import subprocess
from copy import deepcopy
from datetime import date, timedelta
from itertools import permutations
from pathlib import Path

import pytest

from autoresearch import longitudinal_history_inventory as inventory


def record(rid="20260501_1_1", horse="1", tier="dual_supported"):
    return {
        "race_id": rid,
        "horse_id": horse,
        "rank": 1,
        "observed_roster_size": 3,
        "tier": tier,
    }


def context(rid, distance=1200, grade="국6등급"):
    return {
        "race_id": rid,
        "status": "observed",
        "meet": int(rid.split("_")[1]),
        "distance_m": distance,
        "class_text": grade,
    }


def fixtures(rows):
    conditions = {r["race_id"]: context(r["race_id"]) for r in rows}
    sources = {
        r["race_id"]: {"layout": {"status": "recognized_literal_layout"}} for r in rows
    }
    return conditions, sources


def test_complete_population_and_mixed_tiers_are_retained():
    rows = [
        record(),
        record("20260601_1_1", tier="html_only"),
        record("20260701_1_1"),
        record("20260801_1_1"),
        record(horse="2"),
    ]
    c, s = fixtures(rows)
    result = inventory.profile(rows, c, s)
    assert result["rows"] == 5
    assert result["horses"] == 2
    assert result["counts"] == {
        "rows": 5,
        "with_any_prior": 3,
        "with_exact_prior": 3,
        "with_three_exact_priors": 1,
        "with_recognized_layout_pair": 3,
    }
    assert result["tiers"] == {"dual_supported": 4, "html_only": 1}
    assert sum(r["counts"]["rows"] for r in result["race_ledger"].values()) == 5


@pytest.mark.parametrize(
    "age,accepted", [(-1, False), (0, False), (1, True), (180, True), (181, False)]
)
def test_calendar_window_fixed_at_one_to_180_days(age, accepted):
    target = "20261011_1_1"
    previous = f"{date(2026, 10, 11) - timedelta(days=age):%Y%m%d}_1_2"
    rows = [record(target), record(previous)]
    c, s = fixtures(rows)
    result = inventory.profile(rows, c, s)
    assert bool(result["race_ledger"][target]["counts"]["with_exact_prior"]) is accepted


@pytest.mark.parametrize("change", ["venue", "distance", "horse", "class"])
def test_identity_venue_distance_filters_but_no_hidden_class_filter(change):
    rows = [record(), record("20260601_1_1")]
    if change == "venue":
        rows[0]["race_id"] = "20260501_3_1"
    if change == "horse":
        rows[0]["horse_id"] = "2"
    c, s = fixtures(rows)
    if change == "distance":
        c[rows[0]["race_id"]]["distance_m"] = 1400
    if change == "class":
        c[rows[0]["race_id"]]["class_text"] = "국5등급"
    result = inventory.profile(rows, c, s)
    assert result["counts"]["with_exact_prior"] == int(change == "class")
    assert result["rows"] == 2


def test_unrecognized_layout_keeps_structural_prior_and_population():
    rows = [record(), record("20260601_1_1")]
    c, s = fixtures(rows)
    s[rows[0]["race_id"]]["layout"]["status"] = "unrecognized_layout"
    result = inventory.profile(rows, c, s)
    assert result["counts"]["rows"] == 2
    assert result["counts"]["with_exact_prior"] == 1
    assert result["counts"]["with_recognized_layout_pair"] == 0


@pytest.mark.parametrize(
    "case",
    [
        "duplicate",
        "missing_horse",
        "condition",
        "wrong_venue",
        "tier",
        "october_target",
    ],
)
def test_invalid_selected_history_fails_closed(case):
    rows = [record()]
    c, s = fixtures(rows)
    if case == "duplicate":
        rows.append(deepcopy(rows[0]))
    elif case == "missing_horse":
        rows[0]["horse_id"] = ""
    elif case == "condition":
        c = {}
    elif case == "wrong_venue":
        c[rows[0]["race_id"]]["meet"] = 3
    elif case == "tier":
        rows[0]["tier"] = "newly_admitted"
    else:
        rows[0]["race_id"] = "20261016_1_1"
    with pytest.raises(ValueError):
        inventory.profile(rows, c, s)


def test_permutations_are_stable_without_input_mutations():
    rows = [record(), record("20260601_1_1"), record(horse="2")]
    c, s = fixtures(rows)
    before = deepcopy((rows, c, s))
    expected = inventory.profile(rows, c, s)
    for permuted in permutations(rows):
        assert inventory.profile(list(permuted), c, s) == expected
    assert before == (rows, c, s)


def test_yeongcheon_is_not_relabelled_busan():
    assert inventory.layout("", "20261011_4_1", 1200, {}) == {
        "status": "unsupported_physical_venue",
        "reason": "4",
    }


def test_layout_count_and_unseen_distance_are_explicit():
    assert inventory.layout("", "20260501_1_1", 1200, {}) == {
        "status": "unrecognized_layout",
        "reason": "timing_table_count",
    }
    source = inventory.sectional_source_audit
    with pytest.raises(ValueError, match="unobserved_busan_distance"):
        source.headers("busan_cumulative", 2000)


def source_fixture(tmp_path, monkeypatch):
    rid = "20260501_1_1"
    raw = b"<html>synthetic pinned source</html>"
    (tmp_path / "raw.html").write_bytes(raw)
    receipt = {
        "completed_at": "2026-10-15T00:00:00Z",
        "raw": {"path": "raw.html", "sha256": inventory.digest(raw)},
        "request": {"url": "https://race.kra.co.kr/test"},
        "encoding": "utf-8",
    }
    content = json.dumps(receipt).encode()
    (tmp_path / "receipt.json").write_bytes(content)
    c = context(rid)
    c["provenance"] = {
        "receipt": {"path": "receipt.json", "sha256": inventory.digest(content)}
    }
    parsed = {
        "event_support": "confirmed",
        "race_id": rid,
        "rows": [
            {"horse_id": str(i), "chul_no": i, "rank_text": str(i)} for i in range(1, 4)
        ],
    }
    monkeypatch.setattr(
        inventory.race_conditions, "from_capture", lambda *a: deepcopy(c)
    )
    monkeypatch.setattr(inventory, "parse_detail", lambda *a: parsed)
    return rid, c, parsed, receipt


def test_source_replay_checks_selected_roster_and_retains_layout_failure(
    tmp_path, monkeypatch
):
    rid, c, _, _ = source_fixture(tmp_path, monkeypatch)
    before = {p: p.read_bytes() for p in tmp_path.iterdir()}

    def forbidden(*a, **k):
        pytest.fail("unexpected network or training process")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    result = inventory.inspect_source(tmp_path, Path("."), rid, c, [record()])
    assert result["selected_rows"] == 1
    assert result["official_roster_size"] == 3
    assert result["layout"]["status"] == "unrecognized_layout"
    assert before == {p: p.read_bytes() for p in tmp_path.iterdir()}


@pytest.mark.parametrize(
    "case",
    ["raw_pin", "receipt_pin", "rank", "horse", "roster_size", "condition", "event"],
)
def test_changed_original_evidence_stops_inventory(tmp_path, monkeypatch, case):
    rid, c, parsed, _ = source_fixture(tmp_path, monkeypatch)
    rows = [record()]
    if case == "raw_pin":
        (tmp_path / "raw.html").write_bytes(b"changed")
    elif case == "receipt_pin":
        (tmp_path / "receipt.json").write_bytes(b"{}")
    elif case == "rank":
        parsed["rows"][0]["rank_text"] = "2"
    elif case == "horse":
        parsed["rows"][0]["horse_id"] = "99"
    elif case == "roster_size":
        rows[0]["observed_roster_size"] = 4
    elif case == "condition":
        monkeypatch.setattr(inventory.race_conditions, "from_capture", lambda *a: {})
    else:
        parsed["race_id"] = "20260501_3_1"
    with pytest.raises(ValueError):
        inventory.inspect_source(tmp_path, Path("."), rid, c, rows)


def test_unadmitted_condition_group_is_not_silently_deleted(tmp_path, monkeypatch):
    rid, c, _, _ = source_fixture(tmp_path, monkeypatch)
    result = inventory.inspect_source(tmp_path, Path("."), rid, c, [])
    assert result["selected_rows"] == 0
    assert result["layout"] == {"status": "not_in_supported_history"}


def test_equal_cutoff_receipt_is_not_timely(tmp_path, monkeypatch):
    rid, c, _, receipt = source_fixture(tmp_path, monkeypatch)
    receipt["completed_at"] = inventory.SOURCE_BOUND
    raw = json.dumps(receipt).encode()
    (tmp_path / "receipt.json").write_bytes(raw)
    c["provenance"]["receipt"]["sha256"] = inventory.digest(raw)
    with pytest.raises(ValueError, match="historical_source_after_bound"):
        inventory.inspect_source(tmp_path, Path("."), rid, c, [record()])


@pytest.mark.parametrize("rank,size", [(True, 3), (1, True), (0, 3), (4, 3), (1, 1)])
def test_invalid_rank_is_not_silently_counted(rank, size):
    rows = [record()]
    rows[0].update(rank=rank, observed_roster_size=size)
    c, s = fixtures(rows)
    with pytest.raises(ValueError, match="invalid_supported_rank"):
        inventory.profile(rows, c, s)


def test_published_inventory_keeps_full_declared_corpus_and_limits():
    root = Path(__file__).resolve().parents[4]
    raw = (
        root / "docs/research/experiments/2026-10-20-longitudinal-readiness/report.json"
    ).read_bytes()
    assert inventory.digest(raw) == (
        "a338c67f005c1ff56d3ab418f44073d7d76de0a2e3b879d7172a2a8f430e9701"
    )
    result = json.loads(raw)
    assert (result["rows"], result["races"], result["horses"]) == (11523, 1156, 3275)
    assert result["counts"] == {
        "rows": 11523,
        "with_any_prior": 8248,
        "with_exact_prior": 5173,
        "with_three_exact_priors": 1052,
        "with_recognized_layout_pair": 5123,
    }
    assert result["tiers"] == {"dual_supported": 9184, "html_only": 2339}
    assert len(result["race_ledger"]) == 1156
    assert len(result["sources"]) == result["condition_registry_groups"] == 1233
    assert sum(x["selected_rows"] for x in result["sources"].values()) == 11523
    assert sum(x["counts"]["rows"] for x in result["race_ledger"].values()) == 11523
    assert result["source_layout_status"] == {
        "recognized_literal_layout": 1113,
        "not_in_supported_history": 77,
        "unrecognized_layout": 19,
        "unsupported_physical_venue": 24,
    }
    assert result["condition_registry_status"] == {"observed": 1158, "unknown": 75}
    assert result["fits"] == result["network_requests"] == 0
    assert result["accuracy"] is result["future_target_coverage"] is None
    for key in (
        "october_16_18_outcomes_loaded",
        "new_sectional_api_crosscheck",
        "new_sectional_arithmetic_verified",
        "api_raw_replayed_this_audit",
        "historical_prerace_verified",
        "training_approved",
        "counts_as_70_percent_evidence",
    ):
        assert result[key] is False
