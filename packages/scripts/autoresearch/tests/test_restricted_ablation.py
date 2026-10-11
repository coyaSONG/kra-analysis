"""Fixed fitting, train-only transforms, admission and completed artifact tests."""

import copy
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import restricted_ablation as m
from autoresearch import restricted_cohort as c
from autoresearch.tests.test_restricted_cohort import corpus_fixture


@pytest.fixture
def reviewed(tmp_path, monkeypatch):
    corpus = corpus_fixture()
    corpus["implementation"] = c.implementation()
    raw = c.encoded(corpus)
    path = tmp_path / "corpus.json"
    path.write_bytes(raw)
    review = {
        "format_version": "kra-restricted-review-v1",
        "purpose": "research_fit_only",
        "review_id": "synthetic-test-only",
        "corpus_sha256": c.sha256(raw),
        "implementation_sha256": c.sha256(c.encoded(corpus["implementation"])),
        "recipe_sha256": c.sha256(c.encoded(m.RECIPE)),
        "source_review_complete": True,
        "label_version_review_complete": True,
        "selected_race_ids": [r["race_id"] for r in corpus["ledger"]],
        "selected_runner_count": 8,
    }
    review_path = tmp_path / "review.json"
    review_path.write_bytes(c.encoded(review))
    monkeypatch.setattr(m, "REVIEW_PATH", review_path)
    return path, review_path, corpus


def test_paired_matrix_membership_and_weight_meaning():
    races = c.validate_corpus(corpus_fixture())
    a, b = m.matrix(races, "M0"), m.matrix(races, "M1")
    assert a[3] == b[3]
    np.testing.assert_array_equal(a[1], b[1])
    np.testing.assert_array_equal(a[2], b[2])
    np.testing.assert_allclose(a[2].sum(), len(races))
    assert a[0].shape == (8, 14) and b[0].shape == (8, 33)


def test_train_only_preprocessing_and_label_free_inference():
    races = c.validate_corpus(corpus_fixture())
    model, consumed = m.fit(races[:1], "M1")
    assert model["C"] == 1.0
    assert model["imputer_statistics"][14] == 0
    assert len(consumed["X"][0]) == 33
    original = copy.deepcopy(model)
    expected = m.predict(model, races[1:])
    del races[1]["label_top3"]
    del races[1]["results"]
    assert m.predict(model, races[1:]) == expected
    races[1]["feature_rows"][0]["features"]["age"] = 999
    m.predict(model, races[1:])
    assert model == original


def test_deterministic_reload_and_ties():
    races = c.validate_corpus(corpus_fixture())
    model, _ = m.fit(races, "M0")
    assert model["C"] == 0.5
    assert m.predict(model, races) == m.predict(c.parse_json(c.encoded(model)), races)
    model["coefficients"] = [0] * len(model["columns"])
    assert all(r["horse_ids"] == ["1", "2", "3"] for r in m.predict(model, races))


def test_fitted_objective_has_fixed_unit_l2_penalty():
    races = c.validate_corpus(corpus_fixture())
    model, consumed = m.fit(races, "M0")
    x = np.asarray(consumed["X"])
    y = np.asarray(consumed["y"])
    weights = np.asarray(consumed["sample_weight"])
    beta = np.asarray(model["coefficients"])
    probabilities = 1 / (1 + np.exp(-(x @ beta + model["intercept"])))
    residual = weights * (probabilities - y) / weights.sum()
    assert np.max(np.abs(x.T @ residual + beta)) < 1e-6
    assert abs(residual.sum()) < 1e-6


@pytest.mark.parametrize(
    "change",
    ["corpus", "implementation", "recipe", "source", "label", "membership", "count"],
)
def test_admission_rejects_changed_reviewed_recipe(reviewed, change):
    path, review_path, _ = reviewed
    if change == "corpus":
        path.write_bytes(path.read_bytes() + b" ")
    else:
        review = c.parse_json(review_path.read_bytes())
        key = {
            "implementation": "implementation_sha256",
            "recipe": "recipe_sha256",
            "source": "source_review_complete",
            "label": "label_version_review_complete",
            "membership": "selected_race_ids",
            "count": "selected_runner_count",
        }[change]
        review[key] = None
        review_path.write_bytes(c.encoded(review))
    with pytest.raises(ValueError):
        m.admit(path)


def test_frozen_bytes_are_consumed_and_completion_binds_artifacts(reviewed, tmp_path):
    path, _, _ = reviewed
    admitted = m.admit(path)
    path.write_bytes(b"changed after admission")
    output = tmp_path / "run"
    result = m.run(admitted, output)
    receipt = c.parse_json((output / "receipt.json").read_bytes())
    assert receipt["status"] == "completed" and receipt["selected_races"] == 2
    assert (
        not receipt["counts_as_70_percent_evidence"] and not receipt["model_promoted"]
    )
    assert len(receipt["artifacts"]) == 9
    for name, digest in receipt["artifacts"].items():
        assert c.sha256((output / name).read_bytes()) == digest
    assert result["development"]["denominator"] == 1
    assert sum(result["development"]["paired"].values()) == 1
    with pytest.raises(FileExistsError):
        m.run(admitted, output)


def test_changed_implementation_fails_before_output(reviewed, tmp_path, monkeypatch):
    admitted = m.admit(reviewed[0])
    monkeypatch.setattr(m, "implementation", lambda: {"changed": True})
    with pytest.raises(ValueError, match="implementation_changed"):
        m.run(admitted, tmp_path / "not-created")
    assert not (tmp_path / "not-created").exists()


def test_nonconvergence_does_not_emit_receipt(reviewed, tmp_path, monkeypatch):
    admitted = m.admit(reviewed[0])

    def fail(*args, **kwargs):
        import warnings

        warnings.warn("synthetic", m.ConvergenceWarning, stacklevel=2)

    monkeypatch.setattr(m.LogisticRegression, "fit", fail)
    with pytest.raises(m.ConvergenceWarning):
        m.run(admitted, tmp_path / "incomplete")
    assert not (tmp_path / "incomplete/receipt.json").exists()


def test_synthetic_data_does_not_match_canonical_review(tmp_path):
    path = tmp_path / "synthetic.json"
    path.write_bytes(c.encoded(corpus_fixture()))
    with pytest.raises((OSError, ValueError)):
        m.admit(path)
