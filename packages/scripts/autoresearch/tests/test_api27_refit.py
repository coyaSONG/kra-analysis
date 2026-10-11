import json
from copy import deepcopy

import numpy as np
import pytest

from autoresearch import api27_refit as refit
from autoresearch import restricted_ablation as numerical
from autoresearch import restricted_cohort as cohort


@pytest.fixture
def report():
    records = []
    for number in range(1, 4):
        rows = []
        for gate in range(1, 6):
            features = {
                "age": 3.0,
                "wgBudam": 53.0 + gate,
                "rating": float(30 + gate),
                "rcCntT": 10.0,
                "ord1CntT": float(gate % 3),
                "ord2CntT": 1.0,
                "ord3CntT": None,
            }
            features.update(
                {f"{k}_missing": v is None for k, v in list(features.items())}
            )
            rows.append(
                {"chul_no": gate, "horse_id": str(100 + gate), "features": features}
            )
        selected = number != 1
        records.append(
            {
                "race_id": f"20261010_1_{number}",
                "feature_rows": rows,
                "source": {"available_at": "2026-10-09T16:00:00+00:00"},
                "source_publication_bound": "2026-10-09T17:08:16+00:00",
                "cutoff": "2026-10-10T01:00:00+00:00",
                "reasons": [] if selected else ["unique_top3_not_observed"],
                "observed_top3": ["101", "102", "103"] if selected else None,
                "potential_unique_top3_training_candidate": selected,
                "whole_roster_label_join_exact": True,
                "result_status": "unique_top3_observed"
                if selected
                else "void_reported_no_top3",
            }
        )
    return {
        "format_version": "kra-api-only-training-opportunity-v1",
        "outcome_plan_sha256": refit.opportunity.OUTCOME_PLAN_SHA,
        "outcome_policy_sha256": refit.opportunity.OUTCOME_POLICY_SHA,
        "outcome_sources_sha256": refit.opportunity.OUTCOME_SOURCES_SHA,
        "training_approved": False,
        "model_fit_performed": False,
        "counts_as_70_percent_evidence": False,
        "candidate_race_count": 2,
        "candidate_runner_count": 10,
        "race_count": 3,
        "runner_count": 15,
        "ledger": records,
        "witness_audit": {"retrieved_at": "variable"},
    }


@pytest.fixture
def approved(report, monkeypatch, tmp_path):
    # Synthetic approval is test-only and cannot authorize a production corpus.
    monkeypatch.setattr(refit, "implementation", lambda: {"test": "fixed"})
    monkeypatch.setattr(refit, "REVIEW_PATH", tmp_path / "review.json")
    corpus = refit.corpus_from_report(report)
    selected = refit.validate_records(report["ledger"])
    review = {
        "format_version": "kra-api27-review-v1",
        "purpose": "research_fit_only",
        "arm": refit.ARM,
        "corpus_sha256": cohort.sha256(cohort.encoded(corpus)),
        "implementation_sha256": cohort.sha256(cohort.encoded(refit.implementation())),
        "recipe_sha256": cohort.sha256(cohort.encoded(refit.RECIPE)),
        "source_review_complete": True,
        "label_version_review_complete": True,
        "selected_race_ids": [r["race_id"] for r in selected],
        "selected_runner_count": 10,
        "inventory_race_ids": [r["race_id"] for r in report["ledger"]],
        "model_promoted": False,
    }
    refit.REVIEW_PATH.write_bytes(cohort.encoded(review))
    return corpus, review


def test_preparation_retains_void_and_is_not_approval(report):
    corpus = refit.corpus_from_report(report)
    assert corpus["training_approved"] is False
    assert len(corpus["evidence"]["ledger"]) == 3
    assert len(refit.validate_records(corpus["evidence"]["ledger"])) == 2
    changed = deepcopy(report)
    changed["witness_audit"] = {"retrieved_at": "new"}
    assert refit.corpus_from_report(changed) == corpus


@pytest.mark.parametrize(
    "field",
    [
        "corpus_sha256",
        "implementation_sha256",
        "recipe_sha256",
        "source_review_complete",
        "label_version_review_complete",
        "selected_race_ids",
        "selected_runner_count",
        "inventory_race_ids",
        "model_promoted",
        "purpose",
        "arm",
    ],
)
def test_review_mismatch_rejected(approved, field):
    corpus, review = approved
    review[field] = None
    refit.REVIEW_PATH.write_bytes(cohort.encoded(review))
    with pytest.raises(ValueError, match="unreviewed_api27"):
        refit.admit(corpus)


def test_no_review_no_fit(report, monkeypatch, tmp_path):
    monkeypatch.setattr(refit, "REVIEW_PATH", tmp_path / "absent.json")
    with pytest.raises((FileNotFoundError, ValueError)):
        refit.admit(refit.corpus_from_report(report))


@pytest.mark.parametrize("kind", ["feature", "label", "membership", "source"])
def test_changed_corpus_cannot_use_old_review(approved, kind):
    corpus, _ = approved
    race = corpus["evidence"]["ledger"][1]
    if kind == "feature":
        race["feature_rows"][0]["features"]["rating"] += 1
    elif kind == "label":
        race["observed_top3"][-1] = "104"
    elif kind == "source":
        race["source"]["available_at"] = "2026-10-09T15:00:00+00:00"
    else:
        corpus["evidence"]["ledger"].pop()
    with pytest.raises(ValueError):
        refit.admit(corpus)


@pytest.mark.parametrize(
    "kind",
    [
        "extra_label_feature",
        "duplicate_horse",
        "duplicate_gate",
        "bad_missing",
        "late",
        "label_outside",
        "duplicate_labels",
        "negative",
        "count_exceeds",
        "false_join",
        "conflict",
        "drop_candidate",
        "duplicate_race",
        "nan",
    ],
)
def test_bad_evidence_rejected(report, kind):
    records = report["ledger"]
    race = records[1]
    row = race["feature_rows"][0]
    if kind == "extra_label_feature":
        row["features"]["rank"] = 1
    elif kind == "duplicate_horse":
        row["horse_id"] = "102"
    elif kind == "duplicate_gate":
        row["chul_no"] = 2
    elif kind == "bad_missing":
        row["features"]["rating_missing"] = True
    elif kind == "late":
        race["source_publication_bound"] = race["cutoff"]
    elif kind == "label_outside":
        race["observed_top3"][-1] = "999"
    elif kind == "duplicate_labels":
        race["observed_top3"][-1] = "101"
    elif kind == "negative":
        row["features"]["rating"] = -1
    elif kind == "count_exceeds":
        row["features"]["ord1CntT"] = 11
    elif kind == "false_join":
        race["whole_roster_label_join_exact"] = False
    elif kind == "conflict":
        race["result_status"] = "source_conflict"
    elif kind == "drop_candidate":
        race["potential_unique_top3_training_candidate"] = False
    elif kind == "duplicate_race":
        records.append(records[-1])
    else:
        row["features"]["rating"] = float("nan")
    with pytest.raises(ValueError):
        refit.corpus_from_report(report)


def test_fixed_refit_deterministic_and_unpromoted(approved, tmp_path):
    corpus, _ = approved
    admitted = refit.admit(corpus)
    first = refit.run(admitted, tmp_path / "first")
    second = refit.run(admitted, tmp_path / "second")
    assert first["artifacts"] == second["artifacts"]
    assert first["selected_races"] == 2
    assert first["selected_rows"] == 10
    assert first["positive_labels"] == 6
    assert first["model_promoted"] is False
    assert first["counts_as_70_percent_evidence"] is False
    matrix = cohort.parse_json((tmp_path / "first/matrix.json").read_bytes())
    assert np.asarray(matrix["X"]).shape == (10, 14)
    assert sum(matrix["sample_weight"]) == pytest.approx(2)
    assert matrix["columns"] == list(cohort.API_COLUMNS)
    model = cohort.parse_json((tmp_path / "first/model.json").read_bytes())
    assert model["arm"] == refit.ARM
    assert model["format_version"] != "kra-restricted-logistic-v1"
    assert "train_date" not in model["estimator"]["recipe"]
    assert "development_date" not in model["estimator"]["recipe"]
    assert "train_date" in numerical.RECIPE
    assert numerical.RECIPE != refit.RECIPE
    with pytest.raises(FileExistsError):
        refit.run(admitted, tmp_path / "first")


@pytest.mark.parametrize("stage", ["before", "during"])
def test_implementation_drift_never_completes(approved, monkeypatch, tmp_path, stage):
    corpus, _ = approved
    admitted = refit.admit(corpus)
    if stage == "before":
        monkeypatch.setattr(refit, "implementation", lambda: {"test": "changed"})
    else:
        original_fit = numerical.fit

        def drifting(*args):
            result = original_fit(*args)
            monkeypatch.setattr(refit, "implementation", lambda: {"test": "changed"})
            return result

        monkeypatch.setattr(numerical, "fit", drifting)
    with pytest.raises(ValueError, match="changed_after_admission"):
        refit.run(admitted, tmp_path / "failed")
    assert not (tmp_path / "failed/receipt.json").exists()


def test_review_drift_after_admission_rejected(approved, tmp_path):
    corpus, review = approved
    admitted = refit.admit(corpus)
    review["source_review_complete"] = False
    refit.REVIEW_PATH.write_bytes(cohort.encoded(review))
    with pytest.raises(ValueError, match="changed_after_admission"):
        refit.run(admitted, tmp_path / "failed")
    assert not (tmp_path / "failed/receipt.json").exists()


def test_cli_replays_before_admission(approved, monkeypatch, tmp_path):
    corpus, _ = approved
    seen = []

    def replay(*args):
        seen.append(args)
        changed = deepcopy(corpus["evidence"])
        changed["ledger"][1]["feature_rows"][0]["features"]["rating"] += 1
        return changed

    monkeypatch.setattr(refit.opportunity, "prepare", replay)
    args = ["fit"]
    for name in ("plan", "bundle", "outcome-plan", "archive-root", "output-dir"):
        args += [f"--{name}", str(tmp_path / name)]
    with pytest.raises(ValueError, match="unreviewed_api27"):
        refit.main(args)
    assert len(seen) == 1
    assert not list((tmp_path / "output-dir").rglob("receipt.json"))


def test_fit_failure_never_completes(approved, monkeypatch, tmp_path):
    corpus, _ = approved

    def failed(*args):
        raise ValueError("solver_failed")

    monkeypatch.setattr(numerical, "fit", failed)
    with pytest.raises(ValueError, match="solver_failed"):
        refit.run(refit.admit(corpus), tmp_path / "failed")
    assert not (tmp_path / "failed/receipt.json").exists()


def test_corrupt_matrix_never_completes(approved, monkeypatch, tmp_path):
    corpus, _ = approved
    original_save = refit.save

    def corrupted(path, value):
        digest = original_save(path, value)
        if path.name == "matrix.json":
            path.write_bytes(b"{}\n")
        return digest

    monkeypatch.setattr(refit, "save", corrupted)
    with pytest.raises(ValueError, match="saved_artifact_changed"):
        refit.run(refit.admit(corpus), tmp_path / "failed")
    assert not (tmp_path / "failed/receipt.json").exists()


@pytest.mark.parametrize("command", ["prepare", "fit"])
def test_cli_manifest_binds_replay_and_fit(approved, monkeypatch, tmp_path, command):
    corpus, _ = approved
    monkeypatch.setattr(
        refit.opportunity, "prepare", lambda *args: deepcopy(corpus["evidence"])
    )
    args = [command]
    for name in ("plan", "bundle", "outcome-plan", "archive-root", "output-dir"):
        args += [f"--{name}", str(tmp_path / name)]
    assert refit.main(args) == 0
    (directory,) = (tmp_path / "output-dir").iterdir()
    if command == "prepare":
        assert not (directory / "fit").exists()
        assert not (directory / "run-manifest.json").exists()
        return
    manifest = cohort.parse_json((directory / "run-manifest.json").read_bytes())
    for name, key in (
        ("replay-report.json", "replay_report_sha256"),
        ("corpus.json", "corpus_sha256"),
        ("fit/receipt.json", "fit_receipt_sha256"),
    ):
        assert cohort.sha256((directory / name).read_bytes()) == manifest[key]
    assert manifest["fit"]["status"] == "completed"


def test_noncanonical_review_hashes_have_explicit_meaning(approved, tmp_path):
    corpus, review = approved
    raw = json.dumps(review, indent=4).encode()
    refit.REVIEW_PATH.write_bytes(raw)
    receipt = refit.run(refit.admit(corpus), tmp_path / "fit")
    model = cohort.parse_json((tmp_path / "fit/model.json").read_bytes())
    assert model["review_sha256"] == receipt["artifacts"]["review.json"]
    assert model["repository_review_sha256"] == cohort.sha256(raw)
    assert model["review_sha256"] != model["repository_review_sha256"]
