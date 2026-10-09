"""Fixed inventory, whitelisted features, pinned plans, and immutable exports."""

import asyncio
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.kra_race_card_pdf import NUMERIC_FIELDS

from autoresearch import kra_race_card_pdf_bundle as bundle
from autoresearch.kra_race_card_pdf_replay import ReplayError, sha256
from autoresearch.tests.race_card_pdf_capture_fixture import (
    IDENTITY,
    capture_chain,
    save_json,
)


@pytest.fixture
def chain(tmp_path):
    pytest.importorskip("pdfplumber")
    return asyncio.run(capture_chain(tmp_path))


def plan_for(chain):
    pdf, entries = chain["pdf"], chain["entries"]
    return {
        "format_version": bundle.PLAN_VERSION,
        "scope_basis": bundle.SCOPE_BASIS,
        "pinned_at": "2026-06-27T01:01:00+00:00",
        "cohort_sha256": None,
        "implementation": bundle.implementation_fingerprint(),
        "races": [
            {
                **IDENTITY,
                "race_id": pdf["race_id"],
                "manifest_path": pdf["manifest_path"],
                "manifest_sha256": sha256(Path(pdf["manifest_path"]).read_bytes()),
                "pdf_sha256": pdf["sha256"],
                "entry_manifest_sha256": sha256(
                    Path(entries["manifest_path"]).read_bytes()
                ),
            }
        ],
        "unresolved_scope": [],
    }


def add_missing_race(plan):
    plan["races"].append(
        {
            **IDENTITY,
            "race_no": 2,
            "race_id": "20260627_1_2",
            "manifest_path": None,
            "manifest_sha256": None,
            "pdf_sha256": None,
            "entry_manifest_sha256": None,
        }
    )


def test_numeric_whitelist_preserves_null_and_zero_and_excludes_history(
    chain, tmp_path
):
    result = bundle.build_bundle(plan_for(chain), archive_root=tmp_path)
    assert result["race_count"] == result["eligible_race_count"] == 1
    assert result["feature_row_count"] == 2
    assert result["status"] == "verified_feature_archive"
    assert not result["counts_as_70_percent_evidence"]
    assert not result["model_promoted"]
    assert not result["prediction_accuracy_evaluated"]
    for row in result["feature_rows"]:
        features = row["features"]
        assert set(features) == set(NUMERIC_FIELDS) | {
            f"{field}_missing" for field in NUMERIC_FIELDS
        } | {"training_summary_truncated"}
        assert features["swimming_count"] == 0
        assert features["swimming_count_missing"] is False
        assert features["training_window_days"] is None
        assert features["training_window_days_missing"] is True
        assert features["training_count"] == 16
        assert "rank" not in row and "rank" not in features
        assert "recent_listed_treatments" not in row
        assert "evidence_lines" not in row
        assert "hrNo" not in features


def test_absent_race_is_retained_with_fallback_marker(chain, tmp_path):
    plan = plan_for(chain)
    add_missing_race(plan)
    result = bundle.build_bundle(plan, archive_root=tmp_path)
    assert result["race_count"] == 2
    assert result["eligible_race_count"] == result["blocked_race_count"] == 1
    assert result["feature_row_count"] == 2
    assert [row["race_id"] for row in result["races"]] == [
        "20260627_1_1",
        "20260627_1_2",
    ]
    assert result["races"][1]["fallback_required"]
    assert result["races"][1]["feature_row_count"] == 0


def test_corrupt_source_does_not_remove_declared_race(chain, tmp_path):
    plan = plan_for(chain)
    Path(chain["pdf"]["raw_path"]).write_bytes(b"changed")
    result = bundle.build_bundle(plan, archive_root=tmp_path)
    assert result["race_count"] == result["blocked_race_count"] == 1
    assert result["feature_rows"] == []
    assert result["races"][0]["reasons"] == ["raw_sha256_mismatch"]


def test_unpinned_entry_manifest_cannot_emit_features(chain, tmp_path):
    plan = plan_for(chain)
    plan["races"][0]["entry_manifest_sha256"] = None
    result = bundle.build_bundle(plan, archive_root=tmp_path)
    assert result["feature_rows"] == []
    assert result["races"][0]["reasons"] == ["entry_manifest_not_pinned"]


def test_source_cannot_postdate_the_pinned_plan(chain, tmp_path):
    plan = plan_for(chain)
    plan["pinned_at"] = "2026-06-27T00:29:00+00:00"
    result = bundle.build_bundle(plan, archive_root=tmp_path)
    assert result["feature_rows"] == []
    assert result["races"][0]["reasons"] == ["source_after_plan_pin"]


def test_future_plan_pin_is_rejected(chain, tmp_path):
    plan = plan_for(chain)
    plan["pinned_at"] = "2099-01-01T00:00:00+00:00"
    with pytest.raises(ReplayError, match="plan_pin_timestamp_in_future"):
        bundle.build_bundle(plan, archive_root=tmp_path)


@pytest.mark.parametrize(
    "change,code",
    [
        ("duplicate", "duplicate_planned_race"),
        ("race_id", "planned_race_identity_mismatch"),
        ("unknown_feature", "unexpected_planned_race_fields"),
        ("digest", "invalid_expected_sha256"),
        ("implementation", "plan_implementation_changed"),
        ("scope", "unsupported_plan_contract"),
        ("outcome", "unexpected_plan_fields"),
        ("naive_pin", "invalid_plan_pin_timestamp"),
    ],
)
def test_invalid_plan_never_silently_changes_inventory(chain, tmp_path, change, code):
    plan = plan_for(chain)
    if change == "duplicate":
        plan["races"].append(copy.deepcopy(plan["races"][0]))
    elif change == "race_id":
        plan["races"][0]["race_no"] = 2
    elif change == "unknown_feature":
        plan["races"][0]["actual_top3"] = [1, 2, 3]
    elif change == "digest":
        plan["races"][0]["manifest_sha256"] = "bad"
    elif change == "implementation":
        plan["implementation"]["dependency_versions"]["pdfplumber"] = "different"
    elif change == "scope":
        plan["scope_basis"] = "complete_national_race_universe"
    elif change == "outcome":
        plan["answer_key"] = {}
    else:
        plan["pinned_at"] = "2026-06-27T01:01:00"
    with pytest.raises(ReplayError, match=code):
        bundle.build_bundle(plan, archive_root=tmp_path)


def test_cohort_pin_keeps_unknown_requested_scope(chain, tmp_path):
    path = tmp_path / "cohort.json"
    save_json(
        path,
        {
            "planned_meet_dates": [[1, "20260627"], [3, "20260628"]],
            "observations": [
                {
                    "race_id": chain["pdf"]["race_id"],
                    "manifest_path": chain["pdf"]["manifest_path"],
                    "sha256": chain["pdf"]["sha256"],
                }
            ],
        },
    )
    plan = bundle.plan_from_cohort(path, archive_root=tmp_path)
    assert plan["cohort_sha256"] == sha256(path.read_bytes())
    assert plan["races"][0]["manifest_sha256"]
    result = bundle.build_bundle(plan, archive_root=tmp_path)
    assert result["feature_row_count"] == 2
    assert result["unresolved_scope"] == [
        {"meet": 3, "race_date": "20260628", "reason": "race_universe_unknown"}
    ]
    assert not result["all_declared_sources_eligible"]
    assert result["status"] == "partial_feature_archive"


def test_missing_cohort_manifest_remains_a_blocked_record(tmp_path):
    path = tmp_path / "cohort.json"
    save_json(
        path,
        {
            "planned_meet_dates": [[1, "20260627"]],
            "observations": [
                {
                    "race_id": "20260627_1_1",
                    "manifest_path": "missing.json",
                    "sha256": None,
                }
            ],
        },
    )
    plan = bundle.plan_from_cohort(path, archive_root=tmp_path)
    result = bundle.build_bundle(plan, archive_root=tmp_path)
    assert result["race_count"] == result["blocked_race_count"] == 1
    assert result["feature_rows"] == []


@pytest.mark.parametrize("value", [-1, float("nan"), True, 101])
def test_invalid_projection_blocks_whole_race(chain, tmp_path, monkeypatch, value):
    replayed = bundle.replay_race_card_snapshot(
        chain["pdf"]["manifest_path"],
        archive_root=tmp_path,
        expected_sha256=sha256(Path(chain["pdf"]["manifest_path"]).read_bytes()),
        expected_identity=IDENTITY,
    )
    replayed["feature_rows"][0]["trainer_win_rate"] = value
    monkeypatch.setattr(
        bundle, "replay_race_card_snapshot", lambda *args, **kwargs: replayed
    )
    result = bundle.build_bundle(plan_for(chain), archive_root=tmp_path)
    assert result["feature_rows"] == []
    assert result["races"][0]["reasons"] == ["invalid_numeric_pdf_feature"]


def cli_args(monkeypatch, plan_path, tmp_path):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "bundle",
            "--plan",
            str(plan_path),
            "--archive-root",
            str(tmp_path),
            "--output-dir",
            str(tmp_path / "exports"),
            "--require-complete",
        ],
    )


def test_cli_exports_checksums_and_never_overwrites_previous_bundle(
    chain, tmp_path, monkeypatch, capsys
):
    plan_path = tmp_path / "plan.json"
    save_json(plan_path, plan_for(chain))
    cli_args(monkeypatch, plan_path, tmp_path)
    summaries = []
    for _ in range(2):
        assert bundle.main() == 0
        summaries.append(json.loads(capsys.readouterr().out))
    assert summaries[0]["manifest_path"] != summaries[1]["manifest_path"]
    outputs = []
    for summary in summaries:
        raw = Path(summary["manifest_path"]).read_bytes()
        assert sha256(raw) == summary["bundle_sha256"]
        output = json.loads(raw)
        assert output["input_plan_sha256"] == sha256(
            Path(summary["input_plan_path"]).read_bytes()
        )
        output.pop("exported_at")
        outputs.append(output)
    assert outputs[0] == outputs[1]


def test_cli_partial_archive_exit_two_still_preserves_inventory(
    chain, tmp_path, monkeypatch, capsys
):
    plan = plan_for(chain)
    add_missing_race(plan)
    plan_path = tmp_path / "plan.json"
    save_json(plan_path, plan)
    cli_args(monkeypatch, plan_path, tmp_path)
    assert bundle.main() == 2
    summary = json.loads(capsys.readouterr().out)
    assert summary["race_count"] == 2
    assert summary["blocked_races"][0]["race_id"] == "20260627_1_2"
    assert Path(summary["manifest_path"]).is_file()


def test_cli_invalid_plan_exit_one_without_export(tmp_path, monkeypatch, capsys):
    path = tmp_path / "bad.json"
    path.write_bytes(b'{"format_version":"bad"}')
    cli_args(monkeypatch, path, tmp_path)
    assert bundle.main() == 1
    assert json.loads(capsys.readouterr().out)["reason"] == "unexpected_plan_fields"
    assert not (tmp_path / "exports").exists()
