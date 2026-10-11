from copy import deepcopy
from datetime import datetime, timedelta

import pytest

from autoresearch import api_training_opportunity as opportunity


@pytest.fixture
def inputs():
    rows = [
        {"chul_no": n, "horse_id": str(100 + n), "features": {"age": 3.0}}
        for n in range(1, 5)
    ]
    projected = {
        "race_id": "20261010_1_6",
        "feature_rows": rows,
        "source": {"available_at": "2026-10-09T16:00:00+00:00"},
    }
    outcome = {
        "race_id": projected["race_id"],
        "api_records": [{k: r[k] for k in ("chul_no", "horse_id")} for r in rows],
        "status": "unique_top3_observed",
        "observed_top3_horse_ids": ["101", "102", "103"],
    }
    audit = {
        "race_id": projected["race_id"],
        "raw_chain_verified": True,
        "content_bound_before_cutoff": True,
        "feature_projection_matches_publication": True,
        "reasons": ["pdf_api_name_join_conflict"],
    }
    published = datetime.fromisoformat("2026-10-09T17:08:16+00:00")
    cutoff = datetime.fromisoformat("2026-10-10T01:05:00+00:00")
    return projected, outcome, audit, cutoff, published


def test_pdf_ineligibility_does_not_remove_api_only_candidate(inputs):
    before = deepcopy(inputs)
    report = opportunity.assess_race(*inputs)
    assert report["potential_unique_top3_training_candidate"] is True
    assert report["training_approved"] is False
    assert report["original_pdf_reasons"] == ["pdf_api_name_join_conflict"]
    assert inputs == before
    assert report["feature_rows"] == inputs[0]["feature_rows"]


@pytest.mark.parametrize(
    "flag",
    [
        "raw_chain_verified",
        "content_bound_before_cutoff",
        "feature_projection_matches_publication",
    ],
)
def test_unproven_source_stays_in_ledger(inputs, flag):
    inputs[2][flag] = False
    report = opportunity.assess_race(*inputs)
    assert report["potential_unique_top3_training_candidate"] is False
    assert "source_publication_chain_unverified" in report["reasons"]
    assert len(report["feature_rows"]) == 4


@pytest.mark.parametrize(
    "status", ["void_reported_no_top3", "top3_unresolved", "source_conflict"]
)
def test_nonunique_outcome_preserved(inputs, status):
    inputs[1].update(status=status, observed_top3_horse_ids=None)
    report = opportunity.assess_race(*inputs)
    assert report["result_status"] == status
    assert report["whole_roster_label_join_exact"] is True
    assert report["potential_unique_top3_training_candidate"] is False


def test_missing_outcome_preserved(inputs):
    projected, _, audit, cutoff, published = inputs
    report = opportunity.assess_race(projected, None, audit, cutoff, published)
    assert report["result_status"] == "missing"
    assert report["potential_unique_top3_training_candidate"] is False


@pytest.mark.parametrize(
    "mutation", ["missing", "extra", "duplicate", "wrong_horse", "wrong_event"]
)
def test_entire_roster_required(inputs, mutation):
    outcome = inputs[1]
    records = outcome["api_records"]
    if mutation == "missing":
        records.pop()
    elif mutation == "extra":
        records.append({"chul_no": 5, "horse_id": "105"})
    elif mutation == "duplicate":
        records.append(records[0])
    elif mutation == "wrong_horse":
        records[-1]["horse_id"] = "999"
    else:
        outcome["race_id"] = "20261010_1_7"
    report = opportunity.assess_race(*inputs)
    assert report["whole_roster_label_join_exact"] is False
    assert report["potential_unique_top3_training_candidate"] is False


@pytest.mark.parametrize(
    "labels", [None, [], ["101", "102"], ["101", "101", "103"], ["101", "102", "999"]]
)
def test_unique_status_alone_cannot_admit_invalid_labels(inputs, labels):
    inputs[1]["observed_top3_horse_ids"] = labels
    assert (
        opportunity.assess_race(*inputs)["potential_unique_top3_training_candidate"]
        is False
    )


@pytest.mark.parametrize("at_cutoff", [True, False])
def test_publication_at_or_after_cutoff_is_rejected(inputs, at_cutoff):
    projected, outcome, audit, cutoff, _ = inputs
    published = cutoff if at_cutoff else cutoff + timedelta(seconds=1)
    report = opportunity.assess_race(projected, outcome, audit, cutoff, published)
    assert "capture_publication_cutoff_conflict" in report["reasons"]


def test_capture_after_publication_is_rejected(inputs):
    inputs[0]["source"]["available_at"] = "2026-10-09T17:08:17+00:00"
    assert (
        "capture_publication_cutoff_conflict"
        in opportunity.assess_race(*inputs)["reasons"]
    )


def test_original_hhmm_schedule_used(monkeypatch, tmp_path):
    record = {
        "race_id": "20261010_1_6",
        "meet": 1,
        "race_date": "20261010",
        "race_no": 6,
        "entry_manifest_sha256": "a" * 64,
    }
    audit = {"evidence": {"entry": {"manifest_path": str(tmp_path / "manifest.json")}}}
    monkeypatch.setattr(opportunity.inference, "archive_path", lambda path, **kw: path)
    monkeypatch.setattr(
        opportunity.inference,
        "replay_entry_pages",
        lambda *args, **kw: ([], {"collected_at": "2026-10-09T16:00:00+00:00"}, {}),
    )
    monkeypatch.setattr(
        opportunity,
        "build_entry_snapshot",
        lambda *args, **kw: {"scheduled_start_time": "1410", "entries": [1, 2, 3, 4]},
    )
    seen = {}

    def project(race, *args, **kwargs):
        seen.update(race)
        return {"race_id": race["race_id"]}

    monkeypatch.setattr(opportunity.inference, "project_capture", project)
    _, cutoff = opportunity.project_original(record, audit, tmp_path)
    assert cutoff.isoformat() == "2026-10-10T13:40:00+09:00"
    assert seen["scheduled_start_at"] == "2026-10-10T14:10:00+09:00"
    assert seen["runners"] == 4
