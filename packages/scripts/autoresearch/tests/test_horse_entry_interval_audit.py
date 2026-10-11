"""Observed-entry gaps are diagnostics, not certified last-start intervals."""

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch.horse_entry_interval_audit import build_audit, main


def race(day, horses, meet=1, number=1):
    return {
        "race_id": f"{day}_{meet}_{number}",
        "race_date": day,
        "horses": [
            {"chulNo": gate, "hrNo": horse, "ilsu": 75}
            for gate, horse in enumerate(horses, 1)
        ],
    }


def inputs():
    dataset = [
        race("20250901", [100]),
        race("20250920", [200], meet=3),
        race("20251001", [100, 200, 300, None]),
        race("20251001", [100], meet=4),
        race("20251002", [100, 200]),
    ]
    validation = [
        {
            "state": {
                "race_id": "20251001_1_1",
                "date": "20251001",
                "field_size": 4,
                "runner_fields": ["number", "rest"],
                "runner_values": [[i, 75] for i in range(1, 5)],
            }
        }
    ]
    return dataset, validation


def test_different_horse_gaps_and_nulls_preserve_entire_roster():
    result = build_audit(*inputs())
    assert [row["days_since_prior_observed_entry"] for row in result["ledger"]] == [
        30,
        11,
        None,
        None,
    ]
    assert result["ledger"][1]["prior_observed_race_ids"] == ["20250920_3_1"]
    assert result["target_runner_count"] == 4
    assert result["counts"] == {
        "missing_stable_id": 1,
        "no_prior_observed_entry": 1,
        "prior_entry_observed": 2,
        "comparable_rows": 2,
        "proxy_equals_observed_gap": 0,
        "races_with_varying_observed_gaps": 1,
        "races_with_complete_observed_gaps": 0,
        "races_with_constant_complete_proxy": 1,
    }
    assert not result["promotion_safe"]
    assert not result["counts_as_70_percent_evidence"]
    assert not result["production_feature_changed"]
    assert result["historical_source_availability"] == "unproven"
    assert result["actual_start_and_history_completeness"] == "unproven"


def test_order_and_same_day_future_observations_do_not_change_gaps():
    data, states = inputs()
    first = build_audit(data, states)
    assert build_audit(list(reversed(data)), states) == first
    assert build_audit(data[:3], states)["ledger"] == first["ledger"]


def test_latest_prior_date_is_selected_and_duplicate_dates_are_preserved():
    data, states = inputs()
    data.extend([race("20250930", [100], meet=4), race("20250930", [100], meet=3)])
    row = build_audit(data, states)["ledger"][0]
    assert row["days_since_prior_observed_entry"] == 1
    assert row["prior_observed_race_ids"] == ["20250930_3_1", "20250930_4_1"]


def test_numeric_string_ids_normalize_without_name_matching():
    data, states = inputs()
    data[0]["horses"][0]["hrNo"] = "000100"
    assert (
        build_audit(data, states)["ledger"][0]["days_since_prior_observed_entry"] == 30
    )


def test_calendar_gap_includes_leap_day_and_year_boundary():
    data, states = inputs()
    data[0] = race("20240228", [100])
    assert (
        build_audit(data, states)["ledger"][0]["days_since_prior_observed_entry"] == 581
    )


@pytest.mark.parametrize(
    "value", [True, False, 0, -1, 1.2, "12.0", " 100", "unknown", "\u0661"]
)
def test_invalid_ids_fail_instead_of_becoming_missing(value):
    data, states = inputs()
    data[0]["horses"][0]["hrNo"] = value
    with pytest.raises(ValueError, match="invalid_stable_horse_id"):
        build_audit(data, states)


@pytest.mark.parametrize(
    "case, message",
    [
        ("source_duplicate", "duplicate_source_race"),
        ("source_gate", "duplicate_source_runner_or_horse"),
        ("source_id", "duplicate_source_runner_or_horse"),
        ("missing_target", "missing_target_race"),
        ("missing_runner", "target_roster_mismatch"),
        ("target_duplicate", "duplicate_or_non_october_target"),
        ("target_gate", "duplicate_target_runner"),
        ("target_shape", "invalid_target_roster_shape"),
        ("rest_disagrees", "saved_rest_source_disagreement"),
        ("horse_date", "horse_race_identity_mismatch"),
        ("invalid_date", "day is out of range"),
        ("empty_roster", "empty_source_roster"),
    ],
)
def test_fail_closed_instead_of_silent_denominator_loss(case, message):
    data, states = copy.deepcopy(inputs())
    if case == "source_duplicate":
        data.append(data[0])
    elif case == "source_gate":
        data[2]["horses"][1]["chulNo"] = 1
    elif case == "source_id":
        data[2]["horses"][1]["hrNo"] = "000100"
    elif case == "missing_target":
        data.pop(2)
    elif case == "missing_runner":
        data[2]["horses"].pop()
    elif case == "target_duplicate":
        states.append(states[0])
    elif case == "target_gate":
        states[0]["state"]["runner_values"][1][0] = 1
    elif case == "target_shape":
        states[0]["state"]["field_size"] = 5
    elif case == "rest_disagrees":
        data[2]["horses"][0]["ilsu"] = 74
    elif case == "horse_date":
        data[0]["horses"][0]["rcDate"] = 20250902
    elif case == "invalid_date":
        data[0] = race("20250230", [100])
    elif case == "empty_roster":
        data[0]["horses"] = []
    with pytest.raises(ValueError, match=message):
        build_audit(data, states)


def test_missing_proxy_remains_missing_and_not_comparable():
    data, states = inputs()
    data[2]["horses"][0]["ilsu"] = None
    states[0]["state"]["runner_values"][0][1] = None
    result = build_audit(data, states)
    assert result["counts"]["comparable_rows"] == 1
    assert result["ledger"][0]["saved_rest_proxy"] is None


def test_empty_and_non_october_targets_fail():
    data, states = inputs()
    with pytest.raises(ValueError, match="empty_target_universe"):
        build_audit(data, [])
    states[0]["state"].update(race_id="20251201_1_1", date="20251201")
    with pytest.raises(ValueError, match="duplicate_or_non_october_target"):
        build_audit(data, states)


@pytest.mark.parametrize("level", ["race", "horse"])
def test_source_venue_must_agree_with_physical_key(level):
    data, states = inputs()
    obj = data[0] if level == "race" else data[0]["horses"][0]
    obj["meet"] = 3
    with pytest.raises(ValueError, match="source_meet_identity_mismatch"):
        build_audit(data, states)


@pytest.mark.parametrize("bad", [True, 1.0, -1, "75"])
def test_proxy_must_be_nullable_nonnegative_integer(bad):
    data, states = inputs()
    states[0]["state"]["runner_values"][0][1] = bad
    with pytest.raises(ValueError, match="invalid_rest_proxy"):
        build_audit(data, states)


def test_input_objects_are_not_modified():
    args = inputs()
    original = copy.deepcopy(args)
    build_audit(*args)
    assert args == original


def test_cli_pins_exact_bytes_and_refuses_overwrite(tmp_path):
    data, states = inputs()
    source, validation, output = (tmp_path / name for name in ("data", "states", "out"))
    source.write_text(json.dumps(data))
    validation.write_text("\n".join(json.dumps(row) for row in states))
    args = [
        "--dataset",
        str(source),
        "--validation",
        str(validation),
        "--output",
        str(output),
    ]
    assert main(args) == 0
    original = output.read_bytes()
    result = json.loads(original)
    assert (
        result["input_pins"]["dataset"]["sha256"]
        == hashlib.sha256(source.read_bytes()).hexdigest()
    )
    assert (
        result["input_pins"]["validation"]["sha256"]
        == hashlib.sha256(validation.read_bytes()).hexdigest()
    )
    with pytest.raises(FileExistsError):
        main(args)
    assert output.read_bytes() == original
