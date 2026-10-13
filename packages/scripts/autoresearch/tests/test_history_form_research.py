"""Fixed predictors preserve dates, source tiers, outcome uncertainty and rosters."""

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import history_form_research as m
from autoresearch.tests.test_official_history_support import captured


def inputs():
    targets = {
        "20260901_1_1": [
            {"horse_id": str(100 + gate), "chul_no": gate} for gate in range(1, 5)
        ]
    }
    history = [
        {
            "race_id": "20260801_1_1",
            "horse_id": str(100 + gate),
            "rank": 5 - gate,
            "observed_roster_size": 4,
            "tier": "dual_supported",
        }
        for gate in range(1, 5)
    ]
    return targets, history


def outcomes(status="unique_top3_observed"):
    return {
        "20260901_1_1": {
            "status": status,
            "horse_ids": ["102", "103", "104"]
            if status == "unique_top3_observed"
            else None,
            "reasons": [],
        }
    }


def test_fixed_rank_score_predictions_and_source_lineage():
    targets, history = inputs()
    before = copy.deepcopy((targets, history))
    result = m.predict(targets, history)
    arms = result["ledger"][0]["arms"]
    assert arms["gate"]["horse_ids"] == ["101", "102", "103"]
    assert arms["dual90"]["horse_ids"] == ["104", "103", "102"]
    assert arms["dual90"]["rows"][0]["score_fraction"] == "1/3"
    assert arms["expanded90"]["rows"][0]["prior_tiers"] == ["dual_supported"]
    assert (targets, history) == before


@pytest.mark.parametrize(
    "day,in90,in180",
    [
        ("20260304", False, False),
        ("20260305", False, True),
        ("20260602", False, True),
        ("20260603", True, True),
        ("20260831", True, True),
        ("20260901", False, False),
        ("20260902", False, False),
    ],
)
def test_strict_dates(day, in90, in180):
    _, history = inputs()
    for row in history:
        row["race_id"] = f"{day}_1_9"
    assert bool(m.prior_rows(history, "20260901", "expanded90")) == in90
    assert bool(m.prior_rows(history, "20260901", "expanded180")) == in180


def test_source_ablation_and_june_october_window():
    targets, history = inputs()
    targets = {"20261016_1_1": next(iter(targets.values()))}
    for row in history:
        row.update(race_id="20260630_2_1", tier="html_only")
    arms = m.predict(targets, history)["ledger"][0]["arms"]
    assert (
        arms["dual90"]["horse_ids"]
        == arms["expanded90"]["horse_ids"]
        == ["101", "102", "103"]
    )
    assert arms["expanded180"]["horse_ids"] == ["104", "103", "102"]


def test_current_and_future_outcome_mutation_does_not_change_selection():
    targets, history = inputs()
    same_day = [{**r, "race_id": "20260901_1_1"} for r in history]
    future = [{**r, "race_id": "20260902_1_1"} for r in history]
    expected = m.predict(targets, history + same_day + future)
    for row in same_day + future:
        row["rank"] = 1
    assert m.predict(targets, history + same_day + future) == expected
    labels = outcomes()
    other = copy.deepcopy(labels)
    other["20260901_1_1"]["horse_ids"] = ["101", "102", "103"]
    assert (
        m.evaluate(expected, labels)["totals"] != m.evaluate(expected, other)["totals"]
    )
    assert m.predict(targets, history) == expected


def test_missing_history_keeps_every_runner_with_fixed_prior():
    targets, _ = inputs()
    arms = m.predict(targets, [])["ledger"][0]["arms"]
    for arm in m.ARMS:
        assert len(arms[arm]["rows"]) == 4
        assert arms[arm]["horse_ids"] == ["101", "102", "103"]
    assert {r["score_fraction"] for r in arms["expanded90"]["rows"]} == {"1/2"}
    assert {r["score_fraction"] for r in arms["top3_90"]["rows"]} == {"3/10"}


def test_shuffled_rosters_and_history_are_deterministic():
    targets, history = inputs()
    shuffled = {k: list(reversed(v)) for k, v in targets.items()}
    assert m.predict(targets, history) == m.predict(shuffled, list(reversed(history)))


@pytest.mark.parametrize("kind", ["horse", "gate", "history", "leak"])
def test_invalid_inputs_fail(kind):
    targets, history = inputs()
    roster = next(iter(targets.values()))
    if kind == "horse":
        roster[1]["horse_id"] = roster[0]["horse_id"]
    elif kind == "gate":
        roster[1]["chul_no"] = roster[0]["chul_no"]
    elif kind == "history":
        history.append({**history[0], "tier": "html_only"})
    else:
        roster[0]["raw_ord"] = 1
    with pytest.raises(ValueError):
        m.predict(targets, history)


def test_invalid_rank_size_is_withheld_not_clipped():
    targets, history = inputs()
    history[0]["rank"] = 20
    result = m.predict(targets, history)
    assert result["invalid_rank_size_history_withheld"] == 1
    assert result["ledger"][0]["arms"]["dual90"]["rows"][0]["prior_ids"] == []


@pytest.mark.parametrize(
    "status,expected",
    [
        ("source_missing", "pending"),
        ("source_conflict", "pending"),
        ("top3_unresolved", "pending"),
        ("no_top3_reason_unknown", "pending"),
        ("void_reported_no_top3", "undefined"),
    ],
)
def test_unresolved_outcomes_keep_complete_population(status, expected):
    predictions = m.predict(*inputs())
    report = m.evaluate(predictions, outcomes(status))
    for arm in m.ARMS:
        assert report["totals"]["all"][arm] == {"races": 1, expected: 1}
        assert report["paired_vs_dual90"]["all"][arm]["not_comparable"] == 1


def test_paired_matches_and_population_mismatch():
    predictions = m.predict(*inputs())
    report = m.evaluate(predictions, outcomes())
    assert report["totals"]["all"]["dual90"] == {"races": 1, "match": 1}
    assert report["paired_vs_dual90"]["all"]["gate"]["baseline_only"] == 1
    with pytest.raises(ValueError, match="population_mismatch"):
        m.evaluate(predictions, {})


def test_insufficient_roster_is_retained():
    targets, history = inputs()
    next(iter(targets.values())).pop()
    next(iter(targets.values())).pop()
    predictions = m.predict(targets, history)
    assert predictions["ledger"][0]["arms"]["gate"]["horse_ids"] is None
    assert (
        m.evaluate(predictions, outcomes())["totals"]["all"]["dual90"]["pending"] == 1
    )


def test_load_dual_replays_raw_and_rejects_tampering(tmp_path):
    root, path, sha, _, directory, receipt = captured(tmp_path)
    spec = {
        "root": root,
        "seed": path,
        "seed_sha256": sha,
        "archive": directory,
        "archive_sha256": receipt["sha256"],
    }
    targets, labels, history = m.load_dual(spec)
    assert targets and labels
    assert all(
        set(row) == {"horse_id", "chul_no"}
        for roster in targets.values()
        for row in roster
    )
    assert all(row["tier"] == "dual_supported" for row in history)
    raw = next(directory.glob("*.html"))
    raw.write_bytes(raw.read_bytes() + b" ")
    with pytest.raises(ValueError, match="pin_mismatch"):
        m.load_dual(spec)


def test_run_no_fit_no_approval_pinned_and_exclusive(tmp_path, monkeypatch):
    targets, history = inputs()
    monkeypatch.setattr(m, "load_sources", lambda plan: (targets, outcomes(), history))
    plan = {
        "format_version": "history-form-exploration-plan-v1",
        **m.RECIPE,
        "training_approved": False,
        "counts_as_70_percent_evidence": False,
    }
    path = tmp_path / "plan.json"
    sha = m.save(path, plan)
    result = m.run(path, sha, tmp_path / "run")
    report = json.loads((tmp_path / "run/report.json").read_bytes())
    assert report["prediction_success_rate"] is None
    assert report["training_approved"] is report["model_promoted"] is False
    assert result == m.run(path, sha, tmp_path / "rerun")
    assert (
        m.digest((tmp_path / "run/predictions.json").read_bytes())
        == report["prediction_sha256"]
    )
    with pytest.raises(FileExistsError):
        m.run(path, sha, tmp_path / "run")
    with pytest.raises(ValueError, match="pin_mismatch"):
        m.run(path, "0" * 64, tmp_path / "never")
    plan["training_approved"] = True
    other = tmp_path / "bad.json"
    bad_sha = m.save(other, plan)
    with pytest.raises(ValueError, match="unrecognized_protocol"):
        m.run(other, bad_sha, tmp_path / "never")
