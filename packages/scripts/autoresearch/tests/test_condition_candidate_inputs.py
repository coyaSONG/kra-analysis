from copy import deepcopy
from datetime import UTC, datetime

import pytest

from autoresearch import condition_candidate_inputs as candidate


@pytest.fixture
def data():
    identity = "20261016_2_1"
    roster = [{"horse_id": str(100 + n), "chul_no": n} for n in range(1, 4)]
    features = {
        k: False if k.endswith("_missing") or k == candidate.recency.FIELDS[-1] else 0
        for k in candidate.BASE_COLUMNS
    }
    packet = {
        "race_id": identity,
        "feature_cutoff_at": "2026-10-16T01:20:00+00:00",
        "materialized_at": "2026-10-14T06:28:11+00:00",
        "api_source": {"available_at": "2026-10-14T06:20:00+00:00"},
        "history_source": {
            "available_at": "2026-10-11T18:11:30+00:00",
            "public_existence_bound_at": "2026-10-11T20:17:47+00:00",
        },
        "feature_rows": [{**r, "features": deepcopy(features)} for r in roster],
    }
    memory_features = {
        **dict.fromkeys(candidate.COUNTS, 0),
        "condition_delta90": "0",
        "fallback90": "no_eligible_prior",
        "older_career_form": None,
    }
    memory = {
        "created_at": "2026-10-15T12:33:27+00:00",
        "training_approved": False,
        "target_outcomes_loaded": False,
        "rows": [
            {"race_id": identity, **r, "features": deepcopy(memory_features)}
            for r in roster
        ],
    }
    return [packet], memory, {identity: roster}, datetime(2026, 10, 15, 13, tzinfo=UTC)


def test_complete_matrix_preserves_base_and_excludes_diagnostics(data):
    before = deepcopy(data)
    data[1]["rows"][0]["deletion_diagnostic"] = {"not_a_feature": 999}
    result = candidate.build(*data)
    assert result["runner_count"] == 3 and result["race_count"] == 1
    assert len(result["columns"]) == 34
    assert result["training_approved"] is False and result["fit_count"] == 0
    assert result["accuracy"] is None and result["target_outcomes_loaded"] is False
    for row, old in zip(result["rows"], before[0][0]["feature_rows"], strict=True):
        assert {k: row["features"][k] for k in candidate.BASE_COLUMNS} == old[
            "features"
        ]
        assert set(row["features"]) == set(candidate.COLUMNS)
    assert data[0] == before[0]
    assert result["rows"][0]["features"]["memory_older_career_form"] is None


def test_observed_half_and_no_history_are_distinct(data):
    features = data[1]["rows"][0]["features"]
    features.update(older_count=1, older_career_form="1/2")
    rows = candidate.build(*data)["rows"]
    assert rows[0]["features"]["memory_older_career_form"] == 0.5
    assert rows[0]["features"]["memory_older_career_form_missing"] is False
    assert rows[1]["features"]["memory_older_career_form_missing"] is True


def test_zero_contrast_and_fallback_are_distinct(data):
    data[1]["rows"][0]["features"].update(
        prior90_count=1, similar90_count=1, fallback90=None
    )
    rows = candidate.build(*data)["rows"]
    assert rows[0]["features"]["memory_condition_delta90"] == 0
    assert rows[0]["features"]["memory_fallback90"] is False
    assert rows[1]["features"]["memory_fallback90"] is True


@pytest.mark.parametrize(
    "change",
    [
        {"prior90_count": True},
        {"older_count": -1},
        {"similar90_count": 1},
        {"older_same_venue_similar_count": 1},
        {"older_other_venue_count": 1},
        {"older_missing_condition_count": 1},
        {"fallback90": None},
        {"fallback90": "unknown"},
        {"older_career_form": "1/2"},
        {"older_count": 1},
        {"condition_delta90": "1/2"},
        {"condition_delta90": "nan"},
        {"condition_delta90": "2"},
        {"condition_delta90": True},
        {"condition_delta90": "1/0"},
        {"target_rank": 1},
    ],
)
def test_reject_invalid_memory_features(data, change):
    data[1]["rows"][0]["features"].update(change)
    with pytest.raises(ValueError):
        candidate.build(*data)


@pytest.mark.parametrize(
    "change",
    [
        {"age": float("nan")},
        {"rating": float("inf")},
        {"age": True},
        {"age_missing": 0},
        {"age_missing": True},
        {"age": None},
        {"target_rank": 1},
    ],
)
def test_reject_invalid_base_features(data, change):
    data[0][0]["feature_rows"][0]["features"].update(change)
    with pytest.raises(ValueError):
        candidate.build(*data)


@pytest.mark.parametrize("location", ["memory", "packets", "rows", "target"])
def test_reject_duplicate_or_missing_identity(data, location):
    packets, memory, targets, _ = data
    if location == "memory":
        memory["rows"].append(deepcopy(memory["rows"][0]))
    elif location == "packets":
        packets.append(deepcopy(packets[0]))
    elif location == "rows":
        packets[0]["feature_rows"].pop()
    else:
        targets[packets[0]["race_id"]][1]["horse_id"] = "101"
    with pytest.raises(ValueError):
        candidate.build(*data)


@pytest.mark.parametrize("field", ["training_approved", "target_outcomes_loaded"])
def test_reject_labelled_or_approved_memory(data, field):
    data[1][field] = True
    with pytest.raises(ValueError, match="label_free"):
        candidate.build(*data)


@pytest.mark.parametrize(
    "at",
    [
        datetime(2026, 10, 15, 12, tzinfo=UTC),
        datetime(2026, 10, 16, 1, 20, tzinfo=UTC),
        datetime(2026, 10, 16, 2, tzinfo=UTC),
        datetime(2026, 10, 15, 13),
    ],
)
def test_reject_bad_creation_clock(data, at):
    with pytest.raises(ValueError, match="cutoff"):
        candidate.build(*data[:3], at)


def test_reject_source_after_materialization(data):
    data[0][0]["api_source"]["available_at"] = "2026-10-15T14:00:00+00:00"
    with pytest.raises(ValueError, match="cutoff"):
        candidate.build(*data)


def test_reject_unknown_memory_member(data):
    data[1]["rows"][0]["horse_id"] = "999"
    with pytest.raises(ValueError, match="universe"):
        candidate.build(*data)
