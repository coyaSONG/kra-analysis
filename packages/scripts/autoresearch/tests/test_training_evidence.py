"""Production admission tests; all source review fixtures are synthetic."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import numpy as np
import pytest

SCRIPT_ROOT = Path(__file__).resolve().parents[2]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from ml import train_clean  # noqa: E402

from autoresearch import training_evidence  # noqa: E402
from autoresearch.dataset_artifacts import (  # noqa: E402
    load_offline_evaluation_dataset,
    resolve_offline_evaluation_dataset_artifacts,
)
from autoresearch.holdout_dataset import audit_snapshot_manifest_races  # noqa: E402
from autoresearch.parameter_context import (  # noqa: E402
    load_evaluation_parameter_context,
    load_seed_matrix_parameter_context,
)
from autoresearch.training_evidence import (  # noqa: E402
    load_reviewed_training_inputs,
    validate_minimum_training_timing,
)


def _config() -> dict:
    return {
        "dataset": "synthetic_training",
        "features": ["age"],
        "model": {"kind": "logreg", "params": {"C": 0.75, "max_iter": 50}},
        "split": {"train_end": "20260101"},
    }


def _write_json(path: Path, payload: object) -> bytes:
    raw = json.dumps(payload, sort_keys=True).encode()
    path.write_bytes(raw)
    return raw


def _legacy_artifacts(root: Path) -> Path:
    config_path = root / "config.json"
    _write_json(config_path, _config())
    _write_json(
        root / "synthetic_training.json",
        [
            {
                "race_id": "20260101_1_1",
                "race_date": "20260101",
                "race_info": {"meet": "서울", "rcDate": "20260101", "rcNo": 1},
                "horses": [{"chulNo": n, "age": n + 2} for n in range(1, 5)],
            }
        ],
    )
    _write_json(
        root / "synthetic_training_answer_key.json", {"20260101_1_1": [1, 2, 3]}
    )
    _write_json(
        root / "synthetic_training_manifest.json",
        {
            "dataset": "synthetic_training",
            "audit": {"legacy_bootstrap": True},
            "races": [{"race_id": "20260101_1_1"}],
        },
    )
    return config_path


def _forbid_fit(monkeypatch: pytest.MonkeyPatch) -> list[bool]:
    calls: list[bool] = []

    def forbidden_model(*_args, **_kwargs):
        calls.append(True)
        raise AssertionError("production admission reached model fitting")

    monkeypatch.setattr(train_clean, "_make_model", forbidden_model)
    monkeypatch.setattr(train_clean, "_build_feature_rows", lambda *_args: [])
    monkeypatch.setattr(
        train_clean,
        "_build_arrays",
        lambda *_args: (
            np.array([[3.0], [4.0], [5.0], [6.0]]),
            np.array([1, 1, 1, 0]),
            np.array(["20260101_1_1"] * 4),
            np.array(["20260101"] * 4),
            np.array([1, 2, 3, 4]),
        ),
    )
    return calls


def test_trainer_rejects_legacy_before_fit_or_output(tmp_path, monkeypatch):
    config_path = _legacy_artifacts(tmp_path)
    output = tmp_path / "not_created" / "candidate.joblib"
    monkeypatch.setattr(train_clean, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["train_clean.py", "--config", str(config_path), "--output", str(output)],
    )
    calls = _forbid_fit(monkeypatch)

    with pytest.raises(ValueError, match="legacy"):
        train_clean.main()

    assert calls == []
    assert not output.parent.exists()


@pytest.mark.parametrize(
    "loader", [load_evaluation_parameter_context, load_seed_matrix_parameter_context]
)
def test_parameter_context_parses_the_bytes_it_hashes(tmp_path, monkeypatch, loader):
    path = tmp_path / "config.json"
    original = _write_json(path, _config())
    changed = _config()
    changed["model"]["params"]["C"] = 2.0
    read_bytes = Path.read_bytes

    def read_then_change(self):
        raw = read_bytes(self)
        if self == path:
            _write_json(path, changed)
        return raw

    monkeypatch.setattr(Path, "read_bytes", read_then_change)
    context = loader(config_path=path)

    assert context.config_sha256 == sha256(original).hexdigest()
    assert context.config["model"]["params"]["C"] == 0.75


def _timing() -> dict:
    return {
        "race_id": "20260101_1_1",
        "source_filter_basis": "entry_finalized_at",
        "timestamp_source": "snapshot_collected_at",
        "timestamp_confidence": "medium",
        "replay_status": "strict",
        "include_in_strict_dataset": True,
        "hard_required_sources_present": True,
        "hard_required_source_status": dict.fromkeys(
            ("API214_1", "API72_2", "API189_1", "API9_1"), "present"
        ),
        "late_reissue_after_cutoff": False,
        "cutoff_unbounded": False,
        "entry_finalized_at": "2026-01-01T11:15:00+09:00",
        "snapshot_ready_at": "2026-01-01T11:15:00+09:00",
        "operational_cutoff_at": "2026-01-01T11:30:00+09:00",
        "scheduled_start_at": "2026-01-01T12:00:00+09:00",
        "source_lookup": {
            "entry_snapshot_at": "2026-01-01T11:15:00+09:00",
            "capture_completed_at": "2026-01-01T11:15:00+09:00",
        },
    }


@pytest.mark.parametrize(
    "mutation,expected",
    [
        (
            {
                "cutoff_unbounded": True,
                "operational_cutoff_at": None,
                "scheduled_start_at": None,
            },
            "cutoff_unbounded",
        ),
        (
            {
                "timestamp_source": "unverified_source",
                "timestamp_confidence": "unverified",
            },
            "timestamp_source",
        ),
        (
            {
                "timestamp_source": "derived_from_schedule",
                "timestamp_confidence": "low",
                "snapshot_ready_at": None,
            },
            "timestamp_source",
        ),
        ({"include_in_strict_dataset": False}, "include_in_strict_dataset"),
        (
            {
                "entry_finalized_at": "2026-01-01T02:15:00",
                "snapshot_ready_at": "2026-01-01T02:15:00",
            },
            "timezone",
        ),
    ],
    ids=["unbounded", "unknown_source", "schedule_only", "excluded_race", "naive_time"],
)
def test_old_audit_bypasses_fail_minimum_training_conditions(mutation, expected):
    row = {**_timing(), **mutation}
    assert audit_snapshot_manifest_races([row])["passed"] is True
    with pytest.raises(ValueError, match=expected):
        validate_minimum_training_timing(row)


def test_old_revision_does_not_excuse_late_acquisition():
    row = _timing()
    row.update(timestamp_source="source_revision", timestamp_confidence="high")
    row["snapshot_ready_at"] = "2026-01-01T11:35:00+09:00"
    row["source_lookup"]["capture_completed_at"] = row["snapshot_ready_at"]
    assert audit_snapshot_manifest_races([row])["passed"] is True
    with pytest.raises(ValueError, match="capture/ready/entry"):
        validate_minimum_training_timing(row)


@pytest.mark.parametrize(
    "mutation,expected",
    [
        ({"include_in_strict_dataset": 1}, "include_in_strict_dataset"),
        ({"cutoff_unbounded": 0}, "cutoff_unbounded"),
        ({"hard_required_source_status": {}}, "hard-required"),
        ({"replay_status": "degraded"}, "replay_status"),
        ({"operational_cutoff_at": "2026-01-01T12:00:00+09:00"}, "capture/ready/entry"),
        (
            {"source_lookup": {"entry_snapshot_at": "2026-01-01T11:15:00+09:00"}},
            "capture_completed_at",
        ),
    ],
)
def test_strict_timing_rejects_other_unknown_conditions(mutation, expected):
    with pytest.raises(ValueError, match=expected):
        validate_minimum_training_timing({**_timing(), **mutation})


def _strict_artifacts(root: Path) -> Path:
    path = _legacy_artifacts(root)
    race_path = root / "synthetic_training.json"
    races = json.loads(race_path.read_bytes())
    race = races[0]
    race["race_info"].update(dusu=4, rcDist=1200, track="건조", weather="맑음")
    for horse in race["horses"]:
        horse["hrNo"] = f"SYNTHETIC-{horse['chulNo']}"
    race["snapshot_meta"] = _timing()
    _write_json(race_path, races)
    _write_json(
        root / "synthetic_training_manifest.json",
        {"dataset": "synthetic_training", "races": [deepcopy(race["snapshot_meta"])]},
    )
    return path


def _synthetic_review(root: Path, monkeypatch) -> Path:
    """Inject a test trust root, never a real source approval or canonical registry."""
    repo = root / "test_review_repository"
    review = repo / "docs/research/synthetic_review.md"
    review.parent.mkdir(parents=True)
    review_bytes = (
        b"Synthetic trust-boundary fixture, not evidence about actual races.\n"
    )
    review.write_bytes(review_bytes)
    artifacts = {
        role: {"sha256": sha256(raw).hexdigest(), "byte_size": len(raw)}
        for role, filename in (
            ("config", "config.json"),
            ("dataset", "synthetic_training.json"),
            ("answer_key", "synthetic_training_answer_key.json"),
            ("manifest", "synthetic_training_manifest.json"),
        )
        for raw in [(root / filename).read_bytes()]
    }
    registry = repo / "registry.json"
    implementation = training_evidence._implementation_bytes()
    artifacts["implementation"] = {
        "sha256": sha256(implementation).hexdigest(),
        "byte_size": len(implementation),
    }
    _write_json(
        registry,
        {
            "format_version": "production-training-reviews-v1",
            "approved_recipes": [
                {
                    "dataset": "synthetic_training",
                    "artifacts": artifacts,
                    "review_id": "synthetic-review-only",
                    "source_review_path": "docs/research/synthetic_review.md",
                    "source_review_sha256": sha256(review_bytes).hexdigest(),
                }
            ],
        },
    )
    monkeypatch.setattr(training_evidence, "REPO_ROOT", repo)
    monkeypatch.setattr(training_evidence, "APPROVAL_REGISTRY_PATH", registry)
    return registry


def test_correct_timestamps_are_not_source_lineage_proof(tmp_path):
    config_path = _strict_artifacts(tmp_path)
    validate_minimum_training_timing(_timing())
    with pytest.raises(ValueError, match="source lineage is unreviewed"):
        load_reviewed_training_inputs(config_path=config_path, artifact_root=tmp_path)


def test_missing_manifest_is_not_bootstrapped(tmp_path):
    path = _legacy_artifacts(tmp_path)
    manifest = tmp_path / "synthetic_training_manifest.json"
    manifest.unlink()
    with pytest.raises(FileNotFoundError):
        load_reviewed_training_inputs(config_path=path, artifact_root=tmp_path)
    assert not manifest.exists()


def test_legacy_offline_diagnostics_remain_available(tmp_path):
    _legacy_artifacts(tmp_path)
    artifacts = resolve_offline_evaluation_dataset_artifacts(
        "synthetic_training", artifact_root=tmp_path
    )
    races, answers = load_offline_evaluation_dataset(artifacts)
    assert len(races) == 1
    assert answers == {"20260101_1_1": [1, 2, 3]}


def test_frozen_training_inputs_read_once_and_survive_file_changes(
    tmp_path, monkeypatch
):
    path = _strict_artifacts(tmp_path)
    _synthetic_review(tmp_path, monkeypatch)
    reads: dict[Path, int] = {}
    read_bytes = Path.read_bytes

    def counted(self):
        reads[self] = reads.get(self, 0) + 1
        return read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", counted)
    frozen = load_reviewed_training_inputs(config_path=path, artifact_root=tmp_path)
    receipt = frozen.receipt()
    assert len(reads) == 6 + len(training_evidence._IMPLEMENTATION_FILES)
    assert all(count == 1 for count in reads.values())
    for file in (
        path,
        tmp_path / "synthetic_training.json",
        tmp_path / "synthetic_training_answer_key.json",
        tmp_path / "synthetic_training_manifest.json",
    ):
        file.write_bytes(b"changed after admission")
    races, answers = frozen.load_dataset()
    context = load_evaluation_parameter_context(
        config_path=path, config_bytes=frozen.config_bytes, seed_index=0
    )
    assert len(races[0]["horses"]) == 4
    assert answers == {"20260101_1_1": [1, 2, 3]}
    assert context.model_parameters.params["C"] == 0.75
    assert receipt == frozen.receipt()
    races[0]["horses"].clear()
    assert len(frozen.load_dataset()[0][0]["horses"]) == 4


@pytest.mark.parametrize(
    "artifact",
    [
        "config.json",
        "synthetic_training.json",
        "synthetic_training_answer_key.json",
        "synthetic_training_manifest.json",
    ],
)
def test_review_pins_reject_byte_changes(tmp_path, monkeypatch, artifact):
    path = _strict_artifacts(tmp_path)
    _synthetic_review(tmp_path, monkeypatch)
    with (tmp_path / artifact).open("ab") as stream:
        stream.write(b"\n")
    with pytest.raises(ValueError, match="source lineage is unreviewed"):
        load_reviewed_training_inputs(config_path=path, artifact_root=tmp_path)


@pytest.mark.parametrize(
    "failure",
    [
        "missing_runner",
        "duplicate_runner",
        "duplicate_horse",
        "target_duplicate",
        "target_extra",
        "target_boolean",
        "float_venue",
    ],
)
def test_complete_field_and_target_validation(tmp_path, failure):
    path = _strict_artifacts(tmp_path)
    race_path = tmp_path / "synthetic_training.json"
    races = json.loads(race_path.read_bytes())
    answers_path = tmp_path / "synthetic_training_answer_key.json"
    answers = json.loads(answers_path.read_bytes())
    if failure == "missing_runner":
        races[0]["horses"].pop()
    elif failure == "duplicate_runner":
        races[0]["horses"][1]["chulNo"] = 1
    elif failure == "duplicate_horse":
        races[0]["horses"][1]["hrNo"] = races[0]["horses"][0]["hrNo"]
    elif failure == "float_venue":
        races[0]["race_info"]["meet"] = 1.0
    else:
        answers["20260101_1_1"] = {
            "target_duplicate": [1, 1, 3],
            "target_extra": [1, 2, 5],
            "target_boolean": [True, 2, 3],
        }[failure]
    _write_json(race_path, races)
    _write_json(answers_path, answers)
    with pytest.raises(ValueError, match="field|identity|target"):
        load_reviewed_training_inputs(config_path=path, artifact_root=tmp_path)


def test_one_ineligible_race_rejects_entire_input(tmp_path, monkeypatch):
    path = _strict_artifacts(tmp_path)
    registry = _synthetic_review(tmp_path, monkeypatch)
    manifest_path = tmp_path / "synthetic_training_manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    second = deepcopy(_timing())
    second.update(race_id="20260101_1_2", include_in_strict_dataset=False)
    manifest["races"].append(second)
    _write_json(manifest_path, manifest)
    before = registry.read_bytes()
    with pytest.raises(ValueError, match="include_in_strict_dataset"):
        load_reviewed_training_inputs(config_path=path, artifact_root=tmp_path)
    assert registry.read_bytes() == before


def test_atomic_candidate_writer_does_not_replace_existing_file(tmp_path):
    output = tmp_path / "existing.joblib"
    output.write_bytes(b"owner model bytes")
    with pytest.raises(FileExistsError):
        train_clean._save_new_bundle({"synthetic": True}, output)
    assert output.read_bytes() == b"owner model bytes"
    assert list(tmp_path.iterdir()) == [output]


def test_atomic_candidate_writer_cleans_up_failed_serialization(tmp_path, monkeypatch):
    output = tmp_path / "candidate.joblib"

    def failed_dump(*_args):
        raise RuntimeError("synthetic serialization failure")

    monkeypatch.setattr(train_clean.joblib, "dump", failed_dump)
    with pytest.raises(RuntimeError, match="serialization failure"):
        train_clean._save_new_bundle({}, output)
    assert not output.exists()
    assert list(tmp_path.iterdir()) == []


def test_real_approval_registry_contains_no_synthetic_or_unreviewed_recipes():
    registry = json.loads(
        (
            SCRIPT_ROOT.parents[1]
            / "data/contracts/production_training_reviews_v1.json"
        ).read_bytes()
    )
    assert registry["approved_recipes"] == []


def test_synthetic_reviewed_trainer_writes_candidate_and_pinned_receipt(
    tmp_path, monkeypatch
):
    """Exercises the pipeline; no fixture is evidence of real pre-race availability."""
    config_path = _strict_artifacts(tmp_path)
    _synthetic_review(tmp_path, monkeypatch)
    output = tmp_path / "new_candidate" / "candidate.joblib"
    monkeypatch.setattr(train_clean, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["train_clean.py", "--config", str(config_path), "--output", str(output)],
    )

    assert train_clean.main() == 0
    bundle = train_clean.joblib.load(output)
    assert bundle["n_train_races"] == 1
    assert bundle["n_train_rows"] == 4
    assert bundle["model_promoted"] is False
    assert bundle["training_receipt"]["target_accuracy_verified"] is False
    assert bundle["training_receipt"]["source_review_id"] == "synthetic-review-only"
    assert (
        bundle["training_receipt"]["artifacts"]["config"]["sha256"]
        == sha256(config_path.read_bytes()).hexdigest()
    )
    assert set(bundle["training_receipt"]["implementation"]["packages"]) == {
        "numpy",
        "scikit-learn",
        "joblib",
        "pydantic",
    }
    assert [p.name for p in output.parent.iterdir()] == ["candidate.joblib"]


def test_training_implementation_drift_is_rejected(tmp_path, monkeypatch):
    path = _strict_artifacts(tmp_path)
    _synthetic_review(tmp_path, monkeypatch)
    frozen = load_reviewed_training_inputs(config_path=path, artifact_root=tmp_path)
    monkeypatch.setattr(training_evidence, "_implementation_bytes", lambda: b"changed")
    with pytest.raises(ValueError, match="implementation or environment changed"):
        frozen.require_unchanged_implementation()


def test_synthetic_reviewed_trainer_refuses_owner_output_before_fit(
    tmp_path, monkeypatch
):
    config_path = _strict_artifacts(tmp_path)
    _synthetic_review(tmp_path, monkeypatch)
    output = tmp_path / "owner.joblib"
    output.write_bytes(b"owner model bytes")
    monkeypatch.setattr(train_clean, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["train_clean.py", "--config", str(config_path), "--output", str(output)],
    )
    calls = _forbid_fit(monkeypatch)
    with pytest.raises(FileExistsError, match="Refusing to replace"):
        train_clean.main()
    assert calls == []
    assert output.read_bytes() == b"owner model bytes"


def test_atomic_candidate_writer_refuses_broken_symlink(tmp_path):
    output = tmp_path / "owner.joblib"
    output.symlink_to(tmp_path / "nonexistent_model")
    with pytest.raises(FileExistsError):
        train_clean._save_new_bundle({}, output)
    assert output.is_symlink()
    assert list(tmp_path.iterdir()) == [output]


def test_review_note_changes_invalidate_admission(tmp_path, monkeypatch):
    path = _strict_artifacts(tmp_path)
    registry = _synthetic_review(tmp_path, monkeypatch)
    review = registry.parent / "docs/research/synthetic_review.md"
    review.write_bytes(b"different synthetic review")
    with pytest.raises(ValueError, match="source review content changed"):
        load_reviewed_training_inputs(config_path=path, artifact_root=tmp_path)


def test_duplicate_review_does_not_create_ambiguous_approval(tmp_path, monkeypatch):
    path = _strict_artifacts(tmp_path)
    registry_path = _synthetic_review(tmp_path, monkeypatch)
    registry = json.loads(registry_path.read_bytes())
    registry["approved_recipes"] *= 2
    _write_json(registry_path, registry)
    with pytest.raises(ValueError, match="no unique approved exact recipe"):
        load_reviewed_training_inputs(config_path=path, artifact_root=tmp_path)


def test_candidate_field_loss_is_not_silently_normalized(tmp_path, monkeypatch):
    path = _strict_artifacts(tmp_path)
    _synthetic_review(tmp_path, monkeypatch)
    output = tmp_path / "not_created" / "candidate.joblib"
    monkeypatch.setattr(train_clean, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.setattr(
        sys, "argv", ["train_clean.py", "--config", str(path), "--output", str(output)]
    )
    calls = _forbid_fit(monkeypatch)
    with pytest.raises(ValueError, match="complete runner field"):
        train_clean.main()
    assert calls == []
    assert not output.parent.exists()
