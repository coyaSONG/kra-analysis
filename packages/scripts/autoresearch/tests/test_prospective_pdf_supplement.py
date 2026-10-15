"""Supplementary sources cannot replace a frozen population or drop failures."""

import asyncio
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from autoresearch import prospective_pdf_supplement as supplement


def inputs():
    roster = [{"horse_id": str(i), "chul_no": i} for i in range(1, 4)]
    targets = {"20261016_1_1": roster, "20261018_4_1": deepcopy(roster)}
    features = dict.fromkeys(supplement.NUMERIC_FIELDS)
    features.update({k + "_missing": True for k in supplement.NUMERIC_FIELDS})
    features["training_count"], features["training_count_missing"] = 0, False
    bundle = {
        "races": [
            {
                "race_id": "20261016_1_1",
                "eligible_for_prerace_features": True,
                "reasons": [],
            }
        ],
        "feature_rows": [
            {
                "race_id": "20261016_1_1",
                "chulNo": i,
                "hrNo": str(i),
                "features": dict(features),
            }
            for i in range(1, 4)
        ],
    }
    return targets, bundle


def test_full_population_missingness_and_zero_are_preserved():
    args = inputs()
    before = deepcopy(args)
    report = supplement.finalize(*args)
    assert report["race_count"] == 2 and report["expected_runner_rows"] == 6
    assert report["exported_runner_rows"] == 3
    assert report["status_counts"] == {"eligible": 1, "unsupported_venue": 1}
    assert report["field_coverage"]["training_count"] == {
        "observed": 3,
        "missing_of_full_population": 3,
        "missing_of_exported_rows": 0,
    }
    assert (
        report["field_coverage"]["training_minutes"]["missing_of_full_population"] == 6
    )
    assert args == before


def test_failed_source_retains_entire_race():
    targets, bundle = inputs()
    bundle["races"][0].update(eligible_for_prerace_features=False, reasons=["missing"])
    bundle["feature_rows"] = []
    report = supplement.finalize(targets, bundle)
    assert report["expected_runner_rows"] == 6
    assert report["status_counts"] == {"blocked": 1, "unsupported_venue": 1}


@pytest.mark.parametrize("mutation", ["missing", "extra", "duplicate"])
def test_bundle_membership_drift_rejected(mutation):
    targets, bundle = inputs()
    if mutation == "missing":
        bundle["races"] = []
    elif mutation == "extra":
        bundle["races"].append({"race_id": "20261016_1_2"})
    else:
        bundle["races"].append(bundle["races"][0])
    with pytest.raises(ValueError, match="population_mismatch"):
        supplement.finalize(targets, bundle)


@pytest.mark.parametrize("mutation", ["missing", "extra", "duplicate", "horse", "gate"])
def test_eligible_roster_must_equal_frozen_roster(mutation):
    targets, bundle = inputs()
    if mutation == "missing":
        bundle["feature_rows"].pop()
    elif mutation == "extra":
        bundle["feature_rows"].append(
            {**bundle["feature_rows"][0], "chulNo": 9, "hrNo": "9"}
        )
    elif mutation == "duplicate":
        bundle["feature_rows"].append(bundle["feature_rows"][0])
    elif mutation == "horse":
        bundle["feature_rows"][0]["hrNo"] = "99"
    else:
        bundle["feature_rows"][0]["chulNo"] = 99
    with pytest.raises(ValueError, match="frozen_roster_mismatch"):
        supplement.finalize(targets, bundle)


def test_blocked_rows_cannot_leak_into_export():
    targets, bundle = inputs()
    bundle["races"][0]["eligible_for_prerace_features"] = False
    with pytest.raises(ValueError, match="blocked_race_has_features"):
        supplement.finalize(targets, bundle)


def test_unsupported_feature_race_is_rejected():
    targets, bundle = inputs()
    bundle["feature_rows"][0]["race_id"] = "20261018_4_1"
    with pytest.raises(ValueError, match="unexpected_feature_race"):
        supplement.finalize(targets, bundle)


def test_missing_flag_must_agree_with_value():
    targets, bundle = inputs()
    bundle["feature_rows"][0]["features"]["training_count_missing"] = True
    with pytest.raises(ValueError, match="missing_flag_mismatch"):
        supplement.finalize(targets, bundle)


def test_empty_population_is_rejected():
    with pytest.raises(ValueError, match="empty_population"):
        supplement.finalize({}, {"races": [], "feature_rows": []})


def test_budget_caps_network_attempts(monkeypatch):
    async def no_sleep(_):
        pass

    monkeypatch.setattr(supplement.asyncio, "sleep", no_sleep)
    budget = supplement.RequestBudget(datetime.now(UTC) + timedelta(days=1), limit=2)

    async def run():
        await budget(None)
        await budget(None)
        with pytest.raises(ValueError, match="budget_exhausted"):
            await budget(None)

    asyncio.run(run())
    assert budget.count == 2


def test_late_capture_makes_no_request():
    budget = supplement.RequestBudget(datetime.now(UTC) - timedelta(seconds=1))
    with pytest.raises(ValueError, match="cutoff_reached"):
        asyncio.run(budget(None))
    assert budget.count == 0


def test_venue_extension_does_not_drop_previously_captured_population():
    targets, bundle = inputs()
    bundle["races"][0]["race_id"] = "20261018_4_1"
    for row in bundle["feature_rows"]:
        row["race_id"] = "20261018_4_1"
    report = supplement.finalize(targets, bundle, supported={4})
    assert report["race_count"] == 2 and report["expected_runner_rows"] == 6
    assert report["status_counts"] == {"not_requested": 1, "eligible": 1}


@pytest.mark.parametrize(
    "kwargs,reason",
    [
        ({"supported": set()}, "invalid_supported_venues"),
        ({"supported": {5}}, "invalid_supported_venues"),
        ({"max_requests": 61}, "invalid_request_limit"),
        ({"max_requests": True}, "invalid_request_limit"),
        ({"supported": {4}}, "original_archive_reserved"),
    ],
)
def test_invalid_capture_options_fail_before_io(kwargs, reason):
    with pytest.raises(ValueError, match=reason):
        asyncio.run(supplement.capture(**kwargs))
