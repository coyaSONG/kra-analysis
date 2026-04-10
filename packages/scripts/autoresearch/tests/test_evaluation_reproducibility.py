from __future__ import annotations

import copy
import json
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.autoresearch_config_schema import (  # noqa: E402
    AUTORESEARCH_CONFIG_VERSION,
    default_experiment_payload,
)
from shared.read_contract import RaceSnapshot  # noqa: E402
from shared.reproducibility_manifest_schema import (  # noqa: E402
    validate_reproducibility_manifest,
)

from autoresearch import research_clean  # noqa: E402
from autoresearch.dataset_artifacts import (  # noqa: E402
    load_offline_evaluation_dataset,
    resolve_offline_evaluation_dataset_artifacts,
)
from autoresearch.holdout_dataset import build_dataset_manifest  # noqa: E402
from autoresearch.holdout_split import serialize_split_manifest  # noqa: E402
from autoresearch.reproducibility import (  # noqa: E402
    REPRODUCIBILITY_CHECK_REPORT_JSON_FILENAME,
    REPRODUCIBILITY_CHECK_REPORT_MARKDOWN_FILENAME,
    build_research_evaluation_reproducibility_report,
    metrics_artifact_path_for_output,
    prediction_artifact_path_for_output,
    render_research_evaluation_reproducibility_markdown,
    sync_research_evaluation_reproducibility_report,
    write_research_evaluation_bundle,
)
from autoresearch.split_plan import (  # noqa: E402
    build_temporal_split_plan,
    plan_recent_holdout_manifests_from_config,
)

_FIXTURE_DIR = Path(__file__).with_name("fixtures")
_EVALUATION_FIXTURE_DATASET = "evaluation_repro_fixture"
_FIXTURE_CREATED_AT = "2026-04-10T12:00:00+09:00"


def _load_evaluation_case() -> dict[str, Any]:
    return json.loads(
        (_FIXTURE_DIR / "evaluation_repro_case.json").read_text(encoding="utf-8")
    )


def _load_holdout_split_fixture_snapshots() -> list[RaceSnapshot]:
    rows = json.loads(
        (_FIXTURE_DIR / "recent_holdout_split_snapshots.json").read_text(
            encoding="utf-8"
        )
    )
    return [RaceSnapshot.from_row(row) for row in rows]


def _iso_date(compact: str) -> str:
    return f"{compact[0:4]}-{compact[4:6]}-{compact[6:8]}"


def _build_snapshot_meta(
    *, race_id: str, race_date: str, race_number: int
) -> dict[str, Any]:
    entry_finalized_at = f"{_iso_date(race_date)}T10:{30 + race_number:02d}:00+09:00"
    scheduled_start_at = f"{_iso_date(race_date)}T11:00:00+09:00"
    return {
        "race_id": race_id,
        "format_version": "holdout-snapshot-v1",
        "rule_version": "holdout-entry-finalization-rule-v1",
        "source_filter_basis": "entry_finalized_at",
        "scheduled_start_at": scheduled_start_at,
        "operational_cutoff_at": f"{_iso_date(race_date)}T10:50:00+09:00",
        "snapshot_ready_at": entry_finalized_at,
        "entry_finalized_at": entry_finalized_at,
        "selected_timestamp_field": "basic_data.collected_at",
        "selected_timestamp_value": entry_finalized_at,
        "timestamp_source": "snapshot_collected_at",
        "timestamp_confidence": "medium",
        "revision_id": None,
        "late_reissue_after_cutoff": False,
        "cutoff_unbounded": False,
        "replay_status": "strict",
        "include_in_strict_dataset": True,
        "hard_required_sources_present": True,
        "hard_required_source_status": {
            "API214_1": "present",
            "API72_2": "present",
            "API189_1": "present",
            "API9_1": "present",
        },
        "source_lookup": {
            "race_id": race_id,
            "race_date": race_date,
            "entry_snapshot_at": entry_finalized_at,
        },
    }


def _materialize_races(case: dict[str, Any]) -> list[dict[str, Any]]:
    races: list[dict[str, Any]] = []
    for race in case["races"]:
        race_id = str(race["race_id"])
        race_date = str(race["race_date"])
        race_number = int(race["race_number"])
        horses = []
        for horse in race["horses"]:
            chul_no = int(horse["chulNo"])
            horses.append(
                {
                    "chulNo": chul_no,
                    "hrNo": f"HR{race_date}{chul_no:02d}",
                    "hrName": f"Horse-{race_date}-{chul_no}",
                    "age": int(horse["age"]),
                    "sex": horse["sex"],
                    "rating": int(horse["rating"]),
                    "wgBudam": int(horse["wgBudam"]),
                    "wgHr": f"{470 + chul_no}(+0)",
                    "hrDetail": {
                        "rcCntY": int(horse["rcCntY"]),
                        "ord1CntY": int(horse["ord1CntY"]),
                        "ord2CntY": int(horse["ord2CntY"]),
                        "ord3CntY": int(horse["ord3CntY"]),
                    },
                    "computed_features": {
                        "horse_win_rate": float(horse["horse_win_rate"]),
                        "horse_place_rate": float(horse["horse_place_rate"]),
                    },
                }
            )
        races.append(
            {
                "race_id": race_id,
                "race_date": race_date,
                "meet": "seoul",
                "race_info": {
                    "rcDate": race_date,
                    "rcNo": race_number,
                    "rcDist": 1200,
                    "weather": "clear",
                    "track": "dry",
                    "budam": "allowance",
                    "meet": "seoul",
                },
                "horses": horses,
                "snapshot_meta": _build_snapshot_meta(
                    race_id=race_id,
                    race_date=race_date,
                    race_number=race_number,
                ),
            }
        )
    return races


def _build_config(*, dataset_name: str) -> dict[str, Any]:
    return {
        "format_version": AUTORESEARCH_CONFIG_VERSION,
        "dataset": dataset_name,
        "split": {
            "train_end": "20250103",
            "dev_end": "20250105",
            "test_start": "20250106",
        },
        "rolling_windows": [
            {
                "name": "fold_a",
                "train_end": "20250102",
                "eval_start": "20250103",
                "eval_end": "20250104",
            },
            {
                "name": "fold_b",
                "train_end": "20250103",
                "eval_start": "20250104",
                "eval_end": "20250105",
            },
        ],
        "evaluation_contract": {
            "same_source_data_required": True,
            "selection_method": "time_ordered_complete_date_accumulation",
            "boundary_unit": "race_date",
            "minimum_holdout_race_count": 4,
            "minimum_mini_val_race_count": 4,
            "require_complete_race_dates": True,
            "allow_intra_day_cut": False,
            "selection_seed_invariant": True,
            "active_runner_rule": "candidate_filter_minimum_info_fallback_v1",
            "target_label": "unordered_top3",
            "holdout_rule_version": "recent-holdout-split-rule-v1",
            "entry_finalization_rule_version": "holdout-entry-finalization-rule-v1",
            "strict_dataset_selector": "include_in_strict_dataset_true",
            "excluded_replay_statuses": [
                "late_snapshot_unusable",
                "missing_timestamp",
                "partial_snapshot",
            ],
            "excluded_race_reasons": [
                "insufficient_active_runners",
                "invalid_top3_result",
                "late_snapshot_unusable",
                "leakage_violation",
                "missing_basic_data",
                "missing_result_data",
                "partial_snapshot",
                "payload_conversion_failed",
                "top3_not_in_active_runners",
            ],
        },
        "model": {
            "kind": "logreg",
            "positive_class_weight": 1.0,
            "params": {
                "max_iter": 2000,
                "C": 0.75,
            },
        },
        "experiment": default_experiment_payload(dataset=dataset_name),
        "features": [
            "rating",
            "age",
            "wgBudam",
            "horse_win_rate",
            "horse_place_rate",
        ],
        "notes": {"goal": "evaluation reproducibility fixture"},
    }


def _write_evaluation_fixture_bundle(tmp_path: Path) -> Path:
    case = _load_evaluation_case()
    races = _materialize_races(case)
    answers = case["answer_key"]
    (tmp_path / f"{_EVALUATION_FIXTURE_DATASET}.json").write_text(
        json.dumps(races, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (tmp_path / f"{_EVALUATION_FIXTURE_DATASET}_answer_key.json").write_text(
        json.dumps(answers, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    manifest = build_dataset_manifest(
        mode=_EVALUATION_FIXTURE_DATASET,
        created_at=_FIXTURE_CREATED_AT,
        races=[race["snapshot_meta"] for race in races],
    )
    (tmp_path / f"{_EVALUATION_FIXTURE_DATASET}_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    config_path = tmp_path / "evaluation_repro_config.json"
    config_path.write_text(
        json.dumps(
            _build_config(dataset_name=_EVALUATION_FIXTURE_DATASET),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return config_path


def _build_temporal_split_signature(
    *,
    config_path: Path,
    artifact_root: Path,
) -> tuple[object, tuple[str, ...]]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    artifacts = resolve_offline_evaluation_dataset_artifacts(
        _EVALUATION_FIXTURE_DATASET,
        artifact_root=artifact_root,
    )
    races, answers = load_offline_evaluation_dataset(artifacts)
    races, answers, _ = research_clean._normalize_dataset_before_split(races, answers)
    rows = research_clean._build_feature_rows(races, answers)
    rows, _ = research_clean._normalize_feature_rows_before_split(rows)
    _, _, _, dates, _ = research_clean._build_arrays(rows, config["features"])
    plan = build_temporal_split_plan(dates=dates, config=config)
    return plan, tuple(dates)


def _sha256_path(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def test_fixed_fixture_rerun_keeps_train_validation_holdout_splits_identical(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = _write_evaluation_fixture_bundle(tmp_path)
    monkeypatch.setattr(research_clean, "SNAPSHOT_DIR", tmp_path)

    first_result = research_clean.evaluate(
        config_path,
        seed_index=1,
        run_id="seed_01_rs11",
    )
    second_result = research_clean.evaluate(
        config_path,
        seed_index=1,
        run_id="seed_01_rs11",
    )

    assert first_result == second_result

    first_plan, first_dates = _build_temporal_split_signature(
        config_path=config_path,
        artifact_root=tmp_path,
    )
    second_plan, second_dates = _build_temporal_split_signature(
        config_path=config_path,
        artifact_root=tmp_path,
    )

    assert first_dates == second_dates
    assert first_plan == second_plan

    holdout_snapshots = _load_holdout_split_fixture_snapshots()
    holdout_config = json.loads(config_path.read_text(encoding="utf-8"))
    first_manifests = plan_recent_holdout_manifests_from_config(
        holdout_snapshots,
        config=holdout_config,
        manifest_created_at=_FIXTURE_CREATED_AT,
    )
    second_manifests = plan_recent_holdout_manifests_from_config(
        holdout_snapshots,
        config=holdout_config,
        manifest_created_at=_FIXTURE_CREATED_AT,
    )

    for dataset in ("holdout", "mini_val"):
        assert serialize_split_manifest(
            first_manifests[dataset]
        ) == serialize_split_manifest(second_manifests[dataset])
        assert (
            first_manifests[dataset].manifest_sha256
            == second_manifests[dataset].manifest_sha256
        )
        assert (
            first_manifests[dataset].included_race_ids
            == second_manifests[dataset].included_race_ids
        )


def test_fixed_fixture_rerun_keeps_saved_artifacts_and_hashes_identical(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = _write_evaluation_fixture_bundle(tmp_path)
    monkeypatch.setattr(research_clean, "SNAPSHOT_DIR", tmp_path)

    output_path = tmp_path / "runs" / "seed_01_rs11" / "research_clean.json"
    dataset_artifacts = resolve_offline_evaluation_dataset_artifacts(
        _EVALUATION_FIXTURE_DATASET,
        artifact_root=tmp_path,
    )

    first_result = research_clean.evaluate(
        config_path,
        seed_index=1,
        run_id="seed_01_rs11",
    )
    write_research_evaluation_bundle(
        result=first_result,
        config_path=config_path,
        output_path=output_path,
        created_at=_FIXTURE_CREATED_AT,
        dataset_artifacts=dataset_artifacts,
        runtime_params=first_result["runtime_params"],
    )

    prediction_artifact_path = prediction_artifact_path_for_output(output_path)
    metrics_artifact_path = metrics_artifact_path_for_output(output_path)
    manifest_path = output_path.with_name(f"{output_path.stem}_manifest.json")

    first_output_text = output_path.read_text(encoding="utf-8")
    first_prediction_text = prediction_artifact_path.read_text(encoding="utf-8")
    first_metrics_text = metrics_artifact_path.read_text(encoding="utf-8")
    first_manifest_text = manifest_path.read_text(encoding="utf-8")
    first_hashes = {
        "evaluation_result": _sha256_path(output_path),
        "evaluation_prediction_rows": _sha256_path(prediction_artifact_path),
        "evaluation_metrics_summary": _sha256_path(metrics_artifact_path),
        "evaluation_manifest": _sha256_path(manifest_path),
    }
    first_manifest_payload = json.loads(first_manifest_text)
    first_manifest_ok, first_manifest_errors = validate_reproducibility_manifest(
        first_manifest_payload
    )

    second_result = research_clean.evaluate(
        config_path,
        seed_index=1,
        run_id="seed_01_rs11",
    )
    write_research_evaluation_bundle(
        result=second_result,
        config_path=config_path,
        output_path=output_path,
        created_at=_FIXTURE_CREATED_AT,
        dataset_artifacts=dataset_artifacts,
        runtime_params=second_result["runtime_params"],
    )

    second_output_text = output_path.read_text(encoding="utf-8")
    second_prediction_text = prediction_artifact_path.read_text(encoding="utf-8")
    second_metrics_text = metrics_artifact_path.read_text(encoding="utf-8")
    second_manifest_text = manifest_path.read_text(encoding="utf-8")
    second_hashes = {
        "evaluation_result": _sha256_path(output_path),
        "evaluation_prediction_rows": _sha256_path(prediction_artifact_path),
        "evaluation_metrics_summary": _sha256_path(metrics_artifact_path),
        "evaluation_manifest": _sha256_path(manifest_path),
    }
    second_manifest_payload = json.loads(second_manifest_text)
    second_manifest_ok, second_manifest_errors = validate_reproducibility_manifest(
        second_manifest_payload
    )

    assert (
        first_result["_reproducibility_artifacts"]["prediction_rows"]
        == second_result["_reproducibility_artifacts"]["prediction_rows"]
    )
    assert first_result["summary"] == second_result["summary"]
    assert first_result["dev"] == second_result["dev"]
    assert first_result["test"] == second_result["test"]
    assert first_result["rolling"] == second_result["rolling"]

    assert first_output_text == second_output_text
    assert first_prediction_text == second_prediction_text
    assert first_metrics_text == second_metrics_text
    assert first_manifest_text == second_manifest_text
    assert first_hashes == second_hashes

    assert first_manifest_ok is True, first_manifest_errors
    assert second_manifest_ok is True, second_manifest_errors
    assert {
        artifact["artifact_id"]: artifact["sha256"]
        for artifact in first_manifest_payload["artifacts"]
    } == {
        artifact["artifact_id"]: artifact["sha256"]
        for artifact in second_manifest_payload["artifacts"]
    }


def test_reproducibility_report_marks_identical_rerun_as_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = _write_evaluation_fixture_bundle(tmp_path)
    monkeypatch.setattr(research_clean, "SNAPSHOT_DIR", tmp_path)
    dataset_artifacts = resolve_offline_evaluation_dataset_artifacts(
        _EVALUATION_FIXTURE_DATASET,
        artifact_root=tmp_path,
    )

    first_result = research_clean.evaluate(
        config_path,
        seed_index=1,
        run_id="seed_01_rs11",
    )
    second_result = research_clean.evaluate(
        config_path,
        seed_index=1,
        run_id="seed_01_rs11",
    )

    run_a_output = tmp_path / "repro-check" / "run_a" / "research_clean.json"
    run_b_output = tmp_path / "repro-check" / "run_b" / "research_clean.json"
    write_research_evaluation_bundle(
        result=first_result,
        config_path=config_path,
        output_path=run_a_output,
        created_at=_FIXTURE_CREATED_AT,
        dataset_artifacts=dataset_artifacts,
        runtime_params=first_result["runtime_params"],
    )
    write_research_evaluation_bundle(
        result=second_result,
        config_path=config_path,
        output_path=run_b_output,
        created_at=_FIXTURE_CREATED_AT,
        dataset_artifacts=dataset_artifacts,
        runtime_params=second_result["runtime_params"],
    )

    report = build_research_evaluation_reproducibility_report(
        reference_output_path=run_a_output,
        regenerated_output_path=run_b_output,
        generated_at=_FIXTURE_CREATED_AT,
    )
    markdown = render_research_evaluation_reproducibility_markdown(report)
    written = sync_research_evaluation_reproducibility_report(
        reference_output_path=run_a_output,
        regenerated_output_path=run_b_output,
        report_dir=tmp_path / "repro-check",
        generated_at=_FIXTURE_CREATED_AT,
    )

    assert report["passed"] is True
    assert report["mismatched_items"]["required"] == []
    assert report["difference_summary"] == []
    assert report["manifest_validation"]["reference_ok"] is True
    assert report["manifest_validation"]["regenerated_ok"] is True
    required_by_label = {row["label"]: row for row in report["required_checks"]}
    informational_by_label = {
        row["label"]: row for row in report["informational_checks"]
    }
    assert required_by_label["evaluation_result_payload"]["matched"] is True
    assert required_by_label["configuration.settings"]["matched"] is True
    assert required_by_label["seeds"]["matched"] is True
    assert informational_by_label["evaluation_result"]["matched"] is True
    assert "status: `PASS`" in markdown
    assert "## Required Checks" in markdown
    assert Path(written["json_path"]).name == REPRODUCIBILITY_CHECK_REPORT_JSON_FILENAME
    assert (
        Path(written["markdown_path"]).name
        == REPRODUCIBILITY_CHECK_REPORT_MARKDOWN_FILENAME
    )
    assert (
        json.loads(Path(written["json_path"]).read_text(encoding="utf-8"))["passed"]
        is True
    )


def test_reproducibility_report_summarizes_mismatch_items_and_hash_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = _write_evaluation_fixture_bundle(tmp_path)
    monkeypatch.setattr(research_clean, "SNAPSHOT_DIR", tmp_path)
    dataset_artifacts = resolve_offline_evaluation_dataset_artifacts(
        _EVALUATION_FIXTURE_DATASET,
        artifact_root=tmp_path,
    )

    first_result = research_clean.evaluate(
        config_path,
        seed_index=1,
        run_id="seed_01_rs11",
    )
    second_result = copy.deepcopy(first_result)
    second_result["summary"]["robust_exact_rate"] = 0.61
    second_result["summary"]["overfit_safe_exact_rate"] = 0.6
    second_result["test"]["exact_3of3_rate"] = 0.62
    second_result["runtime_params"]["model_random_state"] = 23
    second_result["seeds"]["model_random_state"] = 23
    second_result["_reproducibility_artifacts"]["metrics_summary"]["summary"][
        "robust_exact_rate"
    ] = 0.61
    second_result["_reproducibility_artifacts"]["metrics_summary"]["test"][
        "exact_3of3_rate"
    ] = 0.62
    second_result["_reproducibility_artifacts"]["metrics_summary"][
        "model_random_state"
    ] = 23

    run_a_output = tmp_path / "repro-check" / "run_a" / "research_clean.json"
    run_b_output = tmp_path / "repro-check" / "run_b" / "research_clean.json"
    write_research_evaluation_bundle(
        result=first_result,
        config_path=config_path,
        output_path=run_a_output,
        created_at=_FIXTURE_CREATED_AT,
        dataset_artifacts=dataset_artifacts,
        runtime_params=first_result["runtime_params"],
    )
    write_research_evaluation_bundle(
        result=second_result,
        config_path=config_path,
        output_path=run_b_output,
        created_at=_FIXTURE_CREATED_AT,
        dataset_artifacts=dataset_artifacts,
        runtime_params=second_result["runtime_params"],
    )

    report = build_research_evaluation_reproducibility_report(
        reference_output_path=run_a_output,
        regenerated_output_path=run_b_output,
        generated_at=_FIXTURE_CREATED_AT,
    )
    markdown = render_research_evaluation_reproducibility_markdown(report)

    assert report["passed"] is False
    assert "evaluation_result_payload" in report["mismatched_items"]["required"]
    assert "evaluation_metrics_summary" in report["mismatched_items"]["required"]
    assert "seeds" in report["mismatched_items"]["required"]
    summaries = {
        item["label"]: item["summary"] for item in report["difference_summary"]
    }
    assert "해시 불일치" in summaries["evaluation_metrics_summary"]
    assert "$.model_random_state" in summaries["seeds"]
    assert "status: `FAIL`" in markdown
    assert "[required] `seeds`" in markdown
