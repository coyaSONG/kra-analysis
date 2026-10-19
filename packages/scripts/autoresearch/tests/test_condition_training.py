import warnings
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime
from itertools import permutations

import numpy as np
import pytest
from sklearn.exceptions import ConvergenceWarning

from autoresearch import condition_candidate_inputs as candidate
from autoresearch import condition_training as runner
from autoresearch import condition_training_admission as admission
from autoresearch import condition_training_data as data
from autoresearch import condition_training_model as model
from autoresearch.restricted_cohort import encoded, parse_json, sha256


@pytest.fixture
def corpus():
    packets, memory_rows, rosters = [], [], {}
    base = {
        c: False if c.endswith("_missing") or c == candidate.recency.FIELDS[-1] else 0
        for c in candidate.BASE_COLUMNS
    }
    for race in (1, 2):
        rid = f"20261016_2_{race}"
        roster = [{"horse_id": str(100 + n), "chul_no": n} for n in range(1, 6)]
        rosters[rid] = roster
        rows = []
        for n, row in enumerate(roster):
            features = {**base, "age": n, "rating": None, "rating_missing": True}
            rows.append({**row, "features": features})
            memory_rows.append(
                {
                    "race_id": rid,
                    **row,
                    "features": {
                        **dict.fromkeys(candidate.COUNTS, 0),
                        "condition_delta90": "0",
                        "fallback90": "no_eligible_prior",
                        "older_career_form": None,
                    },
                }
            )
        packets.append(
            {
                "race_id": rid,
                "feature_cutoff_at": "2026-10-16T01:20:00+00:00",
                "materialized_at": "2026-10-14T06:28:11+00:00",
                "api_source": {"available_at": "2026-10-14T06:20:00+00:00"},
                "history_source": {
                    "available_at": "2026-10-11T18:11:30+00:00",
                    "public_existence_bound_at": "2026-10-11T20:17:47+00:00",
                },
                "feature_rows": rows,
            }
        )
    memory = {
        "created_at": "2026-10-15T12:33:27+00:00",
        "training_approved": False,
        "target_outcomes_loaded": False,
        "rows": memory_rows,
    }
    matrix = candidate.build(
        packets, memory, rosters, datetime(2026, 10, 15, 13, tzinfo=UTC)
    )
    ledger, targets, observations = [], [], []
    for rid, roster in rosters.items():
        obs = [
            {
                "race_id": rid,
                **r,
                "evidence": "unresolved"
                if r["chul_no"] == 5
                else "ranked_finish_observed",
                "raw_ord_bigo": "exception" if r["chul_no"] == 5 else "",
                "raw_ord": None if r["chul_no"] == 5 else r["chul_no"],
            }
            for r in roster
        ]
        notes = {"unresolved": 1}
        ledger.append(
            {
                "race_id": rid,
                "api_records": obs,
                "observed_top3_horse_ids": ["101", "102", "103"],
                "observed_runner_count": 5,
                "exception_notes": notes,
                "status": "unique_top3_observed",
            }
        )
        targets.append(
            {
                "race_id": rid,
                "unordered_top3_horse_ids": ["101", "102", "103"],
                "exception_notes": notes,
            }
        )
        observations.extend(deepcopy(obs))
    cohort = {
        "format_version": "development-cohort-link-v1",
        "columns": list(candidate.COLUMNS),
        "training_approved": False,
        "training_label_policy_approved": False,
        "fit_count": 0,
        "feature_rows": deepcopy(matrix["rows"]),
        "race_targets": targets,
        "race_cutoffs": deepcopy(matrix["races"]),
        "result_observations_not_features": observations,
    }
    return cohort, matrix, {"ledger": ledger}, packets, list(rosters)


def test_complete_membership_weights_and_unchanged_originals(corpus):
    before = deepcopy(corpus)
    x, y, w, identities, summary = data.prepare(*corpus)
    assert x.shape == (10, 34) and summary["positive"] == 6
    assert summary["negative"] == 4 and len(summary["exceptions"]) == 2
    assert y.tolist() == [1, 1, 1, 0, 0] * 2
    assert w.tolist() == [0.2] * 10 and w.sum() == 2
    assert len(identities) == 10 and corpus == before
    assert np.isnan(x[:, candidate.COLUMNS.index("rating")]).all()


@pytest.mark.parametrize(
    "case",
    [
        "drop_race",
        "duplicate_race",
        "duplicate_identity",
        "gate",
        "feature",
        "type",
        "column",
        "label",
        "pending",
        "tie",
        "outside",
        "observation",
        "cutoff",
        "missing_flag",
        "infinite",
        "approved",
        "extra_feature",
    ],
)
def test_data_rejects_invalid_whole_population(corpus, case):
    c, m, o, p, ids = corpus
    if case == "drop_race":
        ids.pop()
    elif case == "duplicate_race":
        o["ledger"].append(deepcopy(o["ledger"][0]))
    elif case == "duplicate_identity":
        c["feature_rows"].append(deepcopy(c["feature_rows"][0]))
    elif case == "gate":
        p[0]["feature_rows"][0]["chul_no"] = 2
    elif case == "feature":
        c["feature_rows"][0]["features"]["age"] += 1
    elif case == "type":
        c["feature_rows"][0]["features"]["age"] = 0.0
    elif case == "column":
        c["columns"].reverse()
    elif case == "label":
        c["race_targets"][0]["unordered_top3_horse_ids"] = ["101", "102", "104"]
    elif case == "pending":
        o["ledger"][0]["status"] = "pending"
    elif case == "tie":
        o["ledger"][0]["observed_top3_horse_ids"] = None
    elif case == "outside":
        o["ledger"][0]["observed_top3_horse_ids"] = ["101", "102", "999"]
    elif case == "observation":
        o["ledger"][0]["api_records"].pop()
    elif case == "cutoff":
        m["created_at"] = "2026-10-17T00:00:00+00:00"
    elif case == "approved":
        c["training_approved"] = True
    else:
        for rows in (c["feature_rows"], m["rows"]):
            f = rows[0]["features"]
            if case == "missing_flag":
                f["memory_older_career_form_missing"] = False
            elif case == "infinite":
                f["memory_condition_delta90"] = float("inf")
            else:
                f["outcome_rank"] = 1
    with pytest.raises(ValueError):
        data.prepare(*corpus)


def test_exception_notes_never_change_features_or_weights(corpus):
    a = data.prepare(*corpus)
    c, _, o, _, _ = corpus
    for obs in (
        c["result_observations_not_features"],
        [r for row in o["ledger"] for r in row["api_records"]],
    ):
        for row in obs:
            row["raw_ord_bigo"] = "different diagnostic note"
    b = data.prepare(*corpus)
    for i in (0, 1, 2):
        np.testing.assert_array_equal(a[i], b[i])


@pytest.mark.parametrize(
    "ids", list(permutations(["2", "10", "900719925474099300001"]))
)
def test_canonical_all_six_permutations(ids):
    assert data.canonical(list(ids)) == ["2", "10", "900719925474099300001"]


@pytest.mark.parametrize(
    "scores,expected",
    [
        ([1, 1, 1, 1], ["2", "10", "900719925474099300001"]),
        ([0, 0, 0, np.nextafter(0.0, 1.0)], ["2", "4", "10"]),
        ([1, 2, 3, 4], ["4", "10", "900719925474099300001"]),
    ],
)
def test_ties_near_ties_large_numeric_ids(scores, expected):
    rows = [
        {"race_id": "r", "chul_no": n, "horse_id": h}
        for n, h in enumerate(["2", "10", "900719925474099300001", "4"], 1)
    ]
    assert model.select(rows, scores)[0]["horse_ids"] == expected


def test_selection_rejects_duplicate_horses_and_nonfinite():
    rows = [{"race_id": "r", "chul_no": n, "horse_id": "1"} for n in (1, 2, 3)]
    with pytest.raises(ValueError):
        model.select(rows, [0, 0, 0])
    with pytest.raises(ValueError):
        model.select(rows, [0, float("nan"), 0])


@pytest.fixture
def admitted(tmp_path, monkeypatch, corpus):
    x, y, w, ids, summary = data.prepare(*corpus)
    original = tmp_path / "original.json"
    original.write_bytes(encoded({"unchanged": True}))
    requirement = parse_json(
        encoded(
            {
                "inputs": {str(original): sha256(original.read_bytes())},
                "implementation": {},
                "environment": {},
                "recipe": model.RECIPE,
                "summary": summary,
            }
        )
    )
    review = {
        "requirement_sha256": sha256(encoded(requirement)),
        "review_id": "synthetic-only",
        "reviewer": "synthetic fixture",
        "reviewed_at": "2026-01-01T00:00:00+00:00",
        "purpose": "research_fit_only",
        "fit_budget": {"A24": 1, "B34": 1},
        "source_review_complete": True,
        "label_version_review_complete": True,
        "implementation_review_complete": True,
    }
    registry = tmp_path / admission.REGISTRY
    registry.parent.mkdir(parents=True)
    registry.write_bytes(
        encoded(
            {
                "format_version": "condition-training-reviews-v1",
                "approved_recipes": [review],
            }
        )
    )
    monkeypatch.setattr(admission, "ROOT", tmp_path)
    monkeypatch.setattr(
        admission, "load", lambda: ((x, y, w, ids), deepcopy(requirement))
    )
    monkeypatch.setattr(admission, "implementation", lambda: {})
    monkeypatch.setattr(admission, "environment", lambda: {})

    def git(*args):
        if args[0] == "show":
            return registry.read_bytes()
        return (
            b"synthetic-head"
            if args[-1] == "HEAD"
            else str(tmp_path / "common-git").encode()
        )

    monkeypatch.setattr(admission, "git", git)
    return requirement, registry, original


def test_pair_fits_once_each_and_replays_disk(admitted, monkeypatch):
    calls = []
    original_fit = model.LogisticRegression.fit

    def fit(self, *args, **kwargs):
        calls.append(self.get_params())
        return original_fit(self, *args, **kwargs)

    monkeypatch.setattr(model.LogisticRegression, "fit", fit)
    receipt = runner.run()
    assert len(calls) == receipt["actual_fit_count"] == 2
    assert receipt["completed_arms"] == ["A24", "B34"]
    assert receipt["common24_statistics_equal"]
    assert not receipt["independent_validation_eligible"]
    assert not receipt["model_promoted"]
    ledger, output = runner.locations()
    assert (output / "receipt.json").is_file()
    for arm in model.ARMS:
        saved = parse_json((output / f"{arm}-model.json").read_bytes())
        consumed = parse_json((output / f"{arm}-consumed.json").read_bytes())
        assert saved["classes"] == [0, 1]
        assert saved["actual_parameters"]["C"] == 0.02
        assert saved["imputer_statistics"][2] == 0  # Entirely missing rating.
        assert consumed["sample_weight"] == [0.2] * 10
        assert (ledger / f"{arm}-attempt.json").exists()
    with pytest.raises(ValueError, match="reused"):
        runner.run()
    assert len(calls) == 2


@pytest.mark.parametrize(
    "case",
    [
        "absent",
        "budget",
        "source",
        "label",
        "implementation",
        "future",
        "uncommitted",
        "unmerged",
        "code_changed",
        "env_changed",
        "input_changed",
        "output_exists",
        "output_symlink",
    ],
)
def test_gate_rejects_before_any_preprocessing(admitted, monkeypatch, case):
    requirement, registry, original = admitted
    document = parse_json(registry.read_bytes())
    review = document["approved_recipes"][0]
    if case == "absent":
        document["approved_recipes"] = []
    elif case == "budget":
        review["fit_budget"]["A24"] = 2
    elif case in ("source", "label", "implementation"):
        review[
            {
                "source": "source_review_complete",
                "label": "label_version_review_complete",
                "implementation": "implementation_review_complete",
            }[case]
        ] = False
    elif case == "future":
        review["reviewed_at"] = "2999-01-01T00:00:00+00:00"
    elif case in ("uncommitted", "unmerged"):
        old = admission.git
        monkeypatch.setattr(
            admission,
            "git",
            lambda *args: (
                b"changed"
                if args
                == (
                    "show",
                    f"{'HEAD' if case == 'uncommitted' else 'origin/main'}:{admission.REGISTRY}",
                )
                else old(*args)
            ),
        )
    elif case == "code_changed":
        monkeypatch.setattr(admission, "implementation", lambda: {"changed": "hash"})
    elif case == "env_changed":
        monkeypatch.setattr(admission, "environment", lambda: {"changed": True})
    elif case == "input_changed":
        original.write_text("changed")
    else:
        _, output = runner.locations()
        output.parent.mkdir(parents=True)
        if case == "output_exists":
            output.mkdir()
        else:
            output.symlink_to(original)
    registry.write_bytes(encoded(document))

    def no_preprocessing(*args, **kwargs):
        pytest.fail("preprocessing before admission")

    monkeypatch.setattr(model.SimpleImputer, "fit_transform", no_preprocessing)
    with pytest.raises(ValueError):
        runner.run()
    assert not runner.locations()[0].exists()


@pytest.mark.parametrize(
    "failure",
    [
        "preprocessing",
        "warning",
        "iterations",
        "nonfinite",
        "changed_before_fit",
        "replay",
    ],
)
def test_failure_consumes_reservation_no_new_directory_retry(
    admitted, monkeypatch, failure
):
    original_fit = model.LogisticRegression.fit
    calls = []

    def fit(self, *args, **kwargs):
        calls.append(1)
        if failure == "warning":
            warnings.warn("did not converge", ConvergenceWarning, stacklevel=2)
        result = original_fit(self, *args, **kwargs)
        if failure == "iterations":
            self.n_iter_[:] = 2000
        if failure == "nonfinite":
            self.coef_[0, 0] = float("nan")
        if failure == "replay":
            self.decision_function = lambda x: np.ones(len(x)) * 100
        return result

    monkeypatch.setattr(model.LogisticRegression, "fit", fit)
    old_preprocess = model.SimpleImputer.fit_transform

    def preprocess(self, *args, **kwargs):
        if failure == "preprocessing":
            raise ValueError("preprocessing failure")
        result = old_preprocess(self, *args, **kwargs)
        if failure == "changed_before_fit":
            admitted[2].write_text("changed")
        return result

    monkeypatch.setattr(model.SimpleImputer, "fit_transform", preprocess)
    with pytest.raises((ValueError, ConvergenceWarning)):
        runner.run()
    ledger, output = runner.locations()
    assert (ledger / "failure.json").exists() and not (output / "receipt.json").exists()
    assert len(calls) == (
        0 if failure in ("preprocessing", "changed_before_fit") else 1
    )
    # Different output and review ID cannot reset the common-Git cohort budget.
    registry = parse_json(admitted[1].read_bytes())
    registry["approved_recipes"][0]["review_id"] = "renamed"
    admitted[1].write_bytes(encoded(registry))
    monkeypatch.setattr(
        runner, "locations", lambda: (ledger, output.parent / "different")
    )
    with pytest.raises(ValueError, match="reused"):
        runner.run()


def test_exclusive_claim_and_shared_worktree_budget(admitted):
    ledger, _ = runner.locations()
    ledger.parent.mkdir(parents=True)
    ledger.mkdir()
    with pytest.raises(ValueError, match="reused"):
        runner.run()


def test_pin_hash_and_registry_are_not_interchangeable(tmp_path):
    path = tmp_path / "input.json"
    path.write_bytes(encoded({"v": 1}))
    assert admission.pinned(path, sha256(path.read_bytes())) == {"v": 1}
    with pytest.raises(ValueError, match="hash_mismatch"):
        admission.pinned(path, "0" * 64)


def test_concurrent_invocations_only_one_pair(admitted):
    def attempt():
        try:
            return runner.run()["actual_fit_count"]
        except (FileExistsError, ValueError):
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert results.count(2) == results.count("rejected") == 1


def test_attempt_is_durable_before_estimator_and_no_b_after_revocation(
    admitted, monkeypatch
):
    old_fit = model.LogisticRegression.fit
    calls = []

    def fit(self, *args, **kwargs):
        ledger, _ = runner.locations()
        assert (ledger / "reservation.json").is_file()
        assert (ledger / "A24-attempt.json").is_file()
        calls.append(1)
        result = old_fit(self, *args, **kwargs)
        admitted[1].write_bytes(encoded({"revoked": True}))
        return result

    monkeypatch.setattr(model.LogisticRegression, "fit", fit)
    with pytest.raises(ValueError, match="approval_changed"):
        runner.run()
    assert len(calls) == 1
    ledger, output = runner.locations()
    assert not (ledger / "B34-attempt.json").exists()
    assert not (output / "receipt.json").exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("memory_prior90_count", None),
        ("memory_prior90_count", 1.0),
        ("memory_similar90_count", 1),
        ("memory_older_count", -1),
        ("memory_condition_delta90", None),
        ("memory_fallback90", 1),
        ("memory_older_career_form", 0.5),
    ],
)
def test_only_permitted_memory_nulls_and_types(corpus, field, value):
    features = deepcopy(corpus[0]["feature_rows"][0]["features"])
    features[field] = value
    with pytest.raises(ValueError):
        data.feature_values(features)


def test_numeric_id_breaks_equal_gate_score_ties():
    rows = [
        {"race_id": "r", "chul_no": 1, "horse_id": h} for h in ("100", "10", "2", "1")
    ]
    assert model.select(rows, [0, 0, 0, 0])[0]["horse_ids"] == ["1", "2", "10"]


def test_variable_extra_columns_do_not_change_shared_preprocessing():
    rng = np.random.default_rng(110)
    x = rng.normal(size=(35, 34))
    x[rng.random(x.shape) < 0.2] = np.nan
    x[:, 2] = np.nan
    identities = [
        {"race_id": f"synthetic-{n // 7}", "chul_no": n % 7 + 1, "horse_id": str(n + 1)}
        for n in range(35)
    ]
    y = np.asarray([int(n % 7 < 3) for n in range(35)])
    weights = np.full(35, 1 / 7)
    attempts, models = [], {}
    for arm, columns in model.ARMS.items():
        models[arm], consumed = model.fit_once(
            x[:, : len(columns)].copy(), y, weights, identities, arm, attempts.append
        )
        assert consumed["score_and_exact_set_replay_verified"]
        assert len(consumed["predictions"]) == 5
    assert attempts == ["A24", "B34"]
    for name in ("imputer_statistics", "scaler_mean", "scaler_var", "scaler_scale"):
        assert models["A24"][name] == models["B34"][name][:24]
