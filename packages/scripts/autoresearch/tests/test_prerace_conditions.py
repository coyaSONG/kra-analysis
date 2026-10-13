import json
from copy import deepcopy
from datetime import UTC, datetime

import pytest

from autoresearch import prerace_conditions as conditions


@pytest.fixture
def rows():
    return [
        {
            "meet": 1,
            "rcDate": 20261010,
            "rcNo": 1,
            "chulNo": n,
            "hrNo": str(100 + n),
            "hrName": f"Horse {n}",
            "dusu": 3,
            "stTime": "10:35",
            "rcDist": 1200,
            "rank": "\uad6d6\ub4f1\uae09",
        }
        for n in range(1, 4)
    ]


def project(rows):
    return conditions.project_conditions(
        rows,
        meet=1,
        race_date="20261010",
        race_no=1,
        collected_at=datetime(2026, 10, 9, 16, tzinfo=UTC),
    )


def test_exact_values_roster_and_original_schedule(rows):
    original = deepcopy(rows)
    result = project(rows)
    assert result["distance_m"]["value"] == 1200
    assert result["class_text"]["value"] == "\uad6d6\ub4f1\uae09"
    assert result["runner_count"] == len(result["roster"]) == 3
    assert result["cutoff"] == "2026-10-10T10:05:00+09:00"
    assert result["captured_at"] == "2026-10-09T16:00:00+00:00"
    assert rows == original


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        True,
        1200.0,
        "1200M",
        "1200.0",
        " 1200",
        "1e3",
        "\uff11\uff12\uff10\uff10",
        499,
        5001,
        -1200,
        {},
        [],
    ],
)
def test_invalid_distance_never_imputed_and_class_retained(rows, value):
    rows[1]["rcDist"] = value
    result = project(rows)
    assert result["distance_m"]["status"] == "unknown"
    assert result["distance_m"]["value"] is None
    assert result["distance_m"]["reason"] == "missing_or_invalid_runner_value"
    assert result["class_text"]["status"] == "observed"
    assert result["runner_count"] == 3


@pytest.mark.parametrize("value", [500, 1110, "1610", 5000])
def test_exact_distances_preserved(rows, value):
    for row in rows:
        row["rcDist"] = value
    assert project(rows)["distance_m"]["value"] == int(value)


@pytest.mark.parametrize(
    "value", [None, "", 6, "6", "OPEN", "\uad6d7\ub4f1\uae09", "\uad6d6\ub4f1\uae09 "]
)
def test_class_not_ordinal_or_inferred(rows, value):
    rows[0]["rank"] = value
    result = project(rows)
    assert result["class_text"]["status"] == "unknown"
    assert result["distance_m"]["value"] == 1200


@pytest.mark.parametrize(
    "value",
    ["\uad6dOPEN", "\ud63cOPEN", "\uc81cOPEN", "1\ub4f1\uae09", "\uc81c5\ub4f1\uae09"],
)
def test_exact_class_labels_preserved(rows, value):
    for row in rows:
        row["rank"] = value
    assert project(rows)["class_text"]["value"] == value


@pytest.mark.parametrize(
    "key,value,field",
    [("rcDist", 1300, "distance_m"), ("rank", "\uad6d5\ub4f1\uae09", "class_text")],
)
def test_disagreement_never_resolved_by_majority(rows, key, value, field):
    rows[1][key] = value
    result = project(rows)
    assert result[field]["reason"] == "conflicting_runner_values"
    assert result[field]["value"] is None
    assert len(result[field]["raw_values"]) == 3


def test_full_day_rows_filtered_without_result_fields(rows):
    expected = project(rows)
    extra = {**rows[0], "rcNo": 2, "rank": None, "rcDist": "invalid"}
    for row in rows:
        row.update(ord=99, rcTime=1000, winOdds=0.1)
    assert project([extra, *reversed(rows)]) == expected


@pytest.mark.parametrize(
    "mutation",
    [
        "date",
        "meet",
        "duplicate_gate",
        "duplicate_horse",
        "incomplete",
        "start",
        "no_race",
    ],
)
def test_roster_integrity_is_not_relaxed(rows, mutation):
    if mutation == "date":
        rows[0]["rcDate"] = 20261011
    elif mutation == "meet":
        rows[0]["meet"] = 2
    elif mutation == "duplicate_gate":
        rows[0]["chulNo"] = 2
    elif mutation == "duplicate_horse":
        rows[0]["hrNo"] = "102"
    elif mutation == "incomplete":
        rows.pop()
    elif mutation == "start":
        rows[0]["stTime"] = "10:40"
    else:
        for row in rows:
            row["rcNo"] = 2
    with pytest.raises(ValueError):
        project(rows)


def proof(projected):
    return {
        "race_id": projected["race_id"],
        "raw_chain_verified": True,
        "content_bound_before_cutoff": True,
        "feature_projection_matches_publication": True,
        "reasons": [],
    }


@pytest.mark.parametrize(
    "publication,expected",
    [
        ("2026-10-09T17:08:16Z", True),
        ("2026-10-09T15:59:59Z", False),
        ("2026-10-10T01:05:00Z", False),
        ("2026-10-10T01:05:01Z", False),
    ],
)
def test_availability_requires_capture_publication_cutoff_order(
    rows, publication, expected
):
    projected = project(rows)
    assert (
        conditions.source_available(
            projected, proof(projected), {"merged_at": publication}
        )
        is expected
    )


@pytest.mark.parametrize(
    "flag",
    [
        "raw_chain_verified",
        "content_bound_before_cutoff",
        "feature_projection_matches_publication",
    ],
)
def test_unverified_publication_flag(rows, flag):
    projected = project(rows)
    audit = proof(projected)
    audit[flag] = False
    assert not conditions.source_available(
        projected, audit, {"merged_at": "2026-10-09T17:08:16Z"}
    )


def test_identity_bound_to_publication_and_comparison(rows):
    projected = project(rows)
    audit = proof(projected) | {"race_id": "20261010_1_2"}
    with pytest.raises(ValueError, match="audit_identity"):
        conditions.source_available(projected, audit, {})
    with pytest.raises(ValueError, match="comparison_identity"):
        conditions.compare_conditions(projected, audit)


def test_retrospective_comparison_cannot_fill_or_replace_inputs(rows):
    rows[0]["rank"] = None
    projected = project(rows)
    before = deepcopy(projected)
    historical = {
        "race_id": projected["race_id"],
        "status": "observed",
        "distance_m": 1400,
        "class_text": "\uad6d6\ub4f1\uae09",
    }
    compared = conditions.compare_conditions(projected, historical)
    assert compared["distance_m"]["state"] == "conflict"
    assert compared["class_text"]["state"] == "not_comparable"
    assert projected == before
    assert all(
        r["state"] == "not_comparable"
        for r in conditions.compare_conditions(projected, None).values()
    )


def test_cli_audit_replays_pins_and_retains_unknown_fields(rows, monkeypatch, tmp_path):
    rows[0]["rank"] = None
    projected = project(rows)
    record = {
        "race_id": projected["race_id"],
        "meet": 1,
        "race_date": "20261010",
        "race_no": 1,
        "entry_manifest_sha256": "a" * 64,
    }
    paths = []
    for name, payload, pin in (
        ("plan", {"races": [record]}, "PLAN_SHA"),
        ("bundle", {}, "BUNDLE_SHA"),
        ("comparison", {"records": {}}, "COMPARISON_SHA"),
    ):
        raw = json.dumps(payload).encode()
        path = tmp_path / f"{name}.json"
        path.write_bytes(raw)
        paths.append(path)
        monkeypatch.setattr(conditions, pin, conditions.sha256(raw))
    monkeypatch.setattr(
        conditions,
        "collect_publication",
        lambda *a, **kw: (b"document", {"merged_at": "2026-10-09T17:08:16Z"}),
    )
    audit = proof(projected) | {
        "evidence": {"entry": {"manifest_path": "entry_capture.json"}}
    }
    monkeypatch.setattr(conditions, "audit_archive", lambda **kw: {"ledger": [audit]})
    seen = {}

    def replay(path, **kw):
        seen.update(kw)
        return (
            rows,
            {"collected_at": projected["captured_at"]},
            {"manifest_path": str(path)},
        )

    monkeypatch.setattr(conditions, "replay_entry_pages", replay)
    output = tmp_path / "run"
    result = conditions.run(paths[0], paths[1], tmp_path, paths[2], output)
    report = json.loads((output / "report.json").read_text())
    assert result["race_count"] == 1
    assert result["runner_count"] == 3
    assert result["source_available_race_count"] == 1
    assert result["field_status_counts"]["class_text"] == {"unknown": 1}
    assert seen["expected_sha256"] == "a" * 64
    assert (
        report["training_approved"] is report["counts_as_70_percent_evidence"] is False
    )
    assert report["model_fit_performed"] is report["model_promoted"] is False
    with pytest.raises(FileExistsError):
        conditions.run(paths[0], paths[1], tmp_path, paths[2], output)
    paths[0].write_text("{}")
    with pytest.raises(ValueError, match="input_hash_mismatch"):
        conditions.run(paths[0], paths[1], tmp_path, paths[2], tmp_path / "run2")
