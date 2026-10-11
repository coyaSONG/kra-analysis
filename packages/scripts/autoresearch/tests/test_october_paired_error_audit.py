"""Stored-prediction audits must preserve the whole paired population."""

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch.october_paired_error_audit import (
    FILES,
    audit_stored_files,
    build_ledger,
)


def inputs():
    baseline, predictions, answers, validation = {}, [], {}, []
    for i, (left, right) in enumerate(
        ((True, True), (True, False), (False, True), (False, False)), 1
    ):
        key = f"20251002_3_{i}"
        baseline[key] = [1, 2, 3] if left else [1, 2, 4]
        answers[key] = [3, 2, 1]
        predictions.append(
            {
                "race_id": key,
                "predicted_description": "1,2,3|x" if right else "1,2,4|x",
                "expected_description": "1,2,3|x",
                "top3_correct": right,
            }
        )
        validation.append(
            {
                "state": {
                    "race_id": key,
                    "date": "20251002",
                    "field_size": 4,
                    "runner_fields": ["number", "rest"],
                    "runner_values": [[n, None] for n in range(1, 5)],
                }
            }
        )
    return baseline, predictions, answers, validation


def test_recompute_all_four_categories_and_preserve_missingness():
    result = build_ledger(*inputs())
    assert result["paired_counts"] == {
        "both_hit": 1,
        "baseline_only": 1,
        "ranker_only": 1,
        "both_miss": 1,
    }
    assert result["baseline_exact"] == result["ranker_exact"] == 2
    assert result["race_count"] == len(result["ledger"]) == 4
    assert result["feature_profile"]["rest"]["null_rows"] == 16
    assert result["counts_as_70_percent_evidence"] is False


def test_none_is_not_an_exact_hit_or_a_reconstructed_fallback():
    args = inputs()
    args[1][1].update(predicted_description="NONE", expected_description="NONE")
    result = build_ledger(*args)
    assert result["ranker_abstentions"] == 1
    assert result["ledger"][1]["ranker"] == ()
    assert result["ranker_exact"] == 2


@pytest.mark.parametrize("side", range(4))
def test_missing_race_on_any_side_does_not_shrink_universe(side):
    args = inputs()
    if isinstance(args[side], dict):
        args[side].pop("20251002_3_1")
    else:
        args[side].pop()
    with pytest.raises(ValueError, match="universe_mismatch"):
        build_ledger(*args)


@pytest.mark.parametrize("side", [1, 3])
def test_duplicate_race_rejected(side):
    args = inputs()
    args[side].append(copy.deepcopy(args[side][0]))
    with pytest.raises(ValueError, match="duplicate_race"):
        build_ledger(*args)


def test_wrong_saved_boolean_and_answer_are_detected():
    args = inputs()
    args[1][0]["top3_correct"] = False
    with pytest.raises(ValueError, match="saved_hit_disagreement"):
        build_ledger(*args)
    args = inputs()
    args[1][0]["expected_description"] = "1,2,4|x"
    with pytest.raises(ValueError, match="saved_answer_disagreement"):
        build_ledger(*args)


def test_duplicate_horse_and_outside_roster_rejected():
    args = inputs()
    args[0]["20251002_3_1"] = [1, 1, 2]
    with pytest.raises(ValueError, match="invalid_three_horse"):
        build_ledger(*args)
    args[0]["20251002_3_1"] = [1, 2, 5]
    with pytest.raises(ValueError, match="outside_saved_roster"):
        build_ledger(*args)


def test_input_row_order_does_not_change_ledger():
    args = inputs()
    expected = build_ledger(*args)
    args[1].reverse()
    args[3].reverse()
    for row in args[3]:
        row["state"]["runner_values"].reverse()
    assert build_ledger(*args) == expected


@pytest.mark.parametrize("bad_pin", ["candidate_cache", "validation"])
def test_bad_pin_rejected_before_trusted_cache_deserialization(
    tmp_path, monkeypatch, bad_pin
):
    import joblib

    for path in FILES.values():
        file = tmp_path / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(b"{}")
    digest = hashlib.sha256(b"{}").hexdigest()
    manifest = {
        "candidate_cache_sha256": digest,
        "dataset_sha256": {"validation": digest},
    }
    if bad_pin == "candidate_cache":
        manifest["candidate_cache_sha256"] = "0" * 64
    else:
        manifest["dataset_sha256"]["validation"] = "0" * 64
    (tmp_path / FILES["manifest"]).write_text(json.dumps(manifest))
    (tmp_path / FILES["ranker_report"]).write_text(
        json.dumps({"validation_sha256": digest})
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("unverified cache was deserialized")

    monkeypatch.setattr(joblib, "load", forbidden)
    with pytest.raises(ValueError, match="pin_mismatch"):
        audit_stored_files(tmp_path)


def test_other_month_and_malformed_roster_do_not_enter_diagnostic():
    args = inputs()
    args[3][0]["state"]["date"] = "20251202"
    with pytest.raises(ValueError, match="only_october"):
        build_ledger(*args)
    args = inputs()
    args[3][0]["state"]["runner_values"][0].pop()
    with pytest.raises(ValueError, match="roster_shape"):
        build_ledger(*args)
