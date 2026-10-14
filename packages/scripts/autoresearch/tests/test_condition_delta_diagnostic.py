"""The condition contrast is a covariate diagnostic, never a new prediction."""

from copy import deepcopy
from fractions import Fraction

import pytest

from autoresearch import condition_delta_diagnostic as delta
from autoresearch import condition_form_research as condition


def inputs():
    targets = {
        "20261016_1_1": [{"horse_id": str(n), "chul_no": n} for n in range(1, 4)]
    }
    history = [
        {
            "race_id": day + "_1_1",
            "horse_id": "1",
            "rank": rank,
            "observed_roster_size": 3,
            "tier": "dual_supported",
        }
        for day, rank in [("20261001", 1), ("20261002", 3)]
    ] + [
        {
            "race_id": "20261001_1_1",
            "horse_id": "2",
            "rank": 2,
            "observed_roster_size": 3,
            "tier": "dual_supported",
        }
    ]
    context = {
        "status": "observed",
        "meet": 1,
        "distance_m": 1200,
        "class_text": "classA",
    }
    contexts = {
        key: dict(context) for key in ("20261016_1_1", "20261001_1_1", "20261002_1_1")
    }
    contexts["20261002_1_1"]["distance_m"] = 1600
    return targets, history, contexts


def test_fixed_delta_and_three_distinct_zero_states():
    args = inputs()
    before = deepcopy(args)
    result = delta.project(*args)
    rows = result["ledger"][0]["rows"]
    assert rows[0]["delta"] == "1/6"
    assert rows[1]["delta"] == "0" and rows[1]["fallback"] is None
    assert rows[2]["delta"] == "0" and rows[2]["fallback"] == "no_eligible_prior"
    assert delta.summarize(result["ledger"]) == {
        "races": 1,
        "runner_rows": 3,
        "varying_races": 1,
        "all_fallback_races": 0,
        "fallback_rows": 1,
        "observed_zero_rows": 1,
        "nonzero_rows": 1,
        "no_history_rows": 1,
        "missing_history_condition_links": 0,
    }
    reference = condition.predict(*args)["ledger"][0]["arms"]
    for row, base, joint in zip(
        rows, reference["expanded90"]["rows"], reference["joint90"]["rows"], strict=True
    ):
        assert Fraction(row["delta"]) == Fraction(joint["score_fraction"]) - Fraction(
            base["score_fraction"]
        )
        assert row["fallback"] == joint["fallback"]
    assert args == before


def test_strict_window_and_same_day_exclusion():
    targets, history, contexts = inputs()
    history = [
        {**history[0], "race_id": day + "_1_1"}
        for day in ("20260717", "20260718", "20261015", "20261016", "20261017")
    ]
    actual = delta.project(targets, history, contexts)["ledger"][0]["rows"][0]
    assert actual["baseline_prior_ids"] == ["20260718_1_1", "20261015_1_1"]
    assert actual["missing_history_conditions"] == 2
    assert actual["fallback"] == "no_eligible_prior"


@pytest.mark.parametrize(
    "field,value",
    [
        ("meet", 2),
        ("class_text", "classB"),
        ("distance_m", 1401),
        ("status", "unknown"),
    ],
)
def test_ineligible_history_never_becomes_observed_zero(field, value):
    targets, history, contexts = inputs()
    contexts["20261001_1_1"][field] = value
    result = delta.project(targets, history, contexts)
    assert result["ledger"][0]["all_fallback"]
    assert delta.summarize(result["ledger"])["observed_zero_rows"] == 0


def test_missing_target_is_retained():
    targets, history, contexts = inputs()
    del contexts["20261016_1_1"]
    rows = delta.project(targets, history, contexts)["ledger"][0]["rows"]
    assert len(rows) == 3
    assert all(r["fallback"] == "missing_target_conditions" for r in rows)


def test_reject_duplicate_and_outcome_bearing_targets():
    targets, history, contexts = inputs()
    targets["20261016_1_1"].append(targets["20261016_1_1"][0])
    with pytest.raises(ValueError, match="duplicate"):
        delta.project(targets, history, contexts)
    targets, history, contexts = inputs()
    targets["20261016_1_1"][0]["rank"] = 1
    with pytest.raises(ValueError, match="identity_only"):
        delta.project(targets, history, contexts)


def test_all_equal_deltas_cannot_rank_within_race():
    targets, history, contexts = inputs()
    result = delta.project(targets, [], contexts)
    assert not result["ledger"][0]["within_race_delta_varies"]
    assert delta.summarize(result["ledger"])["all_fallback_races"] == 1


def test_exclusive_output_never_overwrites(tmp_path):
    path = tmp_path / "report.json"
    delta.save(path, {"sentinel": 1})
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        delta.save(path, {"sentinel": 2})
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "mutation,error",
    [
        ("valid_but_incomplete", "incomplete_frozen_population"),
        ("identity", "packet_identity_mismatch"),
        ("roster", "roster_mismatch"),
        ("late", "capture_not_timely"),
    ],
)
def test_published_input_guards(monkeypatch, mutation, error):
    packet = {
        "feature_cutoff_at": "2026-10-16T01:20:00+00:00",
        "prediction": {
            "race_id": "20261016_1_1",
            "source": {
                "manifest_path": "/unused/capture.json",
                "manifest_sha256": "pin",
            },
            "feature_rows": [{"horse_id": "1", "chul_no": 1}],
        },
    }
    projected = {
        "captured_at": "2026-10-14T06:00:00+00:00",
        "cutoff": packet["feature_cutoff_at"],
        "roster": [{"hrNo": "0000001", "chulNo": 1}],
        "distance_m": {"status": "observed", "value": 1200},
        "class_text": {"status": "observed", "value": "classA"},
    }
    if mutation == "identity":
        packet["prediction"]["race_id"] = "20261016_2_1"
    if mutation == "roster":
        projected["roster"][0]["hrNo"] = "0000002"
    if mutation == "late":
        projected["captured_at"] = packet["feature_cutoff_at"]
    monkeypatch.setattr(delta, "read_pin", lambda *a: packet)
    monkeypatch.setattr(
        delta,
        "replay_entry_pages",
        lambda *a, **kw: ([], {"collected_at": projected["captured_at"]}, {}),
    )
    monkeypatch.setattr(delta, "project_conditions", lambda *a, **kw: projected)
    commitment = {
        "days": [
            {
                "race_date": "20261016",
                "races": [{"race_id": "20261016_1_1", "packet_sha256": "pin"}],
            }
        ]
    }
    with pytest.raises(ValueError, match=error):
        delta.load_targets(commitment)
