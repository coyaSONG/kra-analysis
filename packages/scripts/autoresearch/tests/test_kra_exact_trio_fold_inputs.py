"""The exact-role adapter uses the existing three fictional complete cards."""

import json
import sys
from datetime import timedelta
from math import comb
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "docs/research/tools"))

import kra_exact_trio_fold_design as design
import kra_exact_trio_fold_inputs as bridge

from autoresearch import kra_whole_card_learning as learning
from autoresearch.exact_trio_distribution import ExactTrioDistribution, partition_trios
from autoresearch.restricted_cohort import API_FIELDS, encoded, parse_json, sha256
from autoresearch.tests import test_fixed_pair_evaluation as results
from autoresearch.tests import test_kra_walk_forward_fold as fixtures
from autoresearch.tests import test_kra_whole_card_learning as learning_fixtures

study = fixtures.study


def ready(study, monkeypatch, *, merge=None):
    monkeypatch.setattr(bridge, "now", lambda: study.clock[0])
    monkeypatch.setattr(bridge.fold, "now", lambda: study.clock[0])
    plan = fixtures._plan(study)
    mark = bridge.fold.stage(study.root, plan)
    digest = fixtures._publication(
        study, mark, merge or study.initial + timedelta(seconds=30)
    )
    return {
        "plan_ref": plan,
        "packet_sha256": digest,
        "pull": fixtures.FOLD_PR,
    }


def test_all_earlier_targets_and_input_only_future(study, monkeypatch):
    args = ready(study, monkeypatch)
    sealed_roles = [x["candidate"] for x in study.plan["training"]]
    original_clock = study.clock[0]
    held_out_plan, _ = results.seal_results(
        study.evaluation,
        "forbidden-held-out-result",
        choice="API27",
        captured_at=study.evaluation.result_time,
    )
    study.clock[0] = original_clock
    original_replay = learning.replay
    accessed = []

    def old_only(root, **selected):
        assert selected["receipt"] != study.evaluation.input_spec["receipt"]
        accessed.append(selected["result_plan"][0])
        return original_replay(root, **selected)

    monkeypatch.setattr(learning, "replay", old_only)
    learning_fixtures._guard(monkeypatch)

    # A valid version exists in the fixture but no replay may open its archive.
    forbidden = held_out_plan.parent
    original_open = Path.open

    def no_future_reads(path, *args, **kwargs):
        assert not path.resolve().is_relative_to(forbidden)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", no_future_reads)
    result = bridge.read_verified(study.root, **args)
    assert len(accessed) == 2
    assert [c["candidate"] for c in result.training["cards"]] == sealed_roles
    assert result.chronology["training_races"] == 28
    assert result.chronology["evaluation_races"] == 14
    assert not result.chronology["training_approved"]
    assert not result.chronology["predictions_generated"]
    h = []
    for card, selection in zip(
        result.training["cards"], study.plan["training"], strict=True
    ):
        source = parse_json((study.root / selection["candidate"]["path"]).read_bytes())
        assert card["targets"] == source["target_races"]
        assert len(card["fields"]) == len(card["targets"]) == 14
        h.extend(f["race_id"] for f in card["fields"])
    card = result.evaluation["card"]
    assert set(card) == {"fields", "population_sha256", "source"}
    assert {r["race_id"] for r in card["fields"]} == set(study.evaluation.races)
    assert not set(h) & set(study.evaluation.races)
    assert b"target" not in encoded(result.evaluation)
    for field in card["fields"]:
        assert field["feature_rows"] == sorted(
            study.evaluation.races[field["race_id"]]["shared_input"]["feature_rows"],
            key=lambda r: r["chul_no"],
        )
    prepared = bridge.stage(study.root, **args)
    assert len(accessed) == 4 and prepared["state"] == "local_views_prepared"
    assert not prepared["predictions_generated"]


def test_unknown_or_conflicting_missing_value_rejected(study):
    field = next(iter(study.evaluation.races.values()))
    values = field["shared_input"]["feature_rows"][0]["features"]
    value = API_FIELDS[0]
    flag = f"{value}_missing"
    values[flag] = not values[flag]
    with pytest.raises(ValueError, match="missingness_or_type_conflict"):
        bridge._project_field(field)
    values[flag] = not values[flag]
    values["actual_top3"] = False
    with pytest.raises(ValueError, match="unexpected_entry_features"):
        bridge._project_field(field)


def test_lost_duplicate_or_extra_declared_rows_rejected(study):
    field = next(iter(study.evaluation.races.values()))
    rows = field["shared_input"]["feature_rows"]
    original = rows.pop()
    with pytest.raises(ValueError, match="incomplete_declared_field"):
        bridge._project_field(field)
    rows.append(rows[0])
    with pytest.raises(ValueError, match="ambiguous_declared_identity"):
        bridge._project_field(field)
    rows[-1] = original | {"rank": 1}
    with pytest.raises(ValueError, match="unexpected_declared_row_fields"):
        bridge._project_field(field)


def test_exact_prior_version_survives_newer_result(study, monkeypatch):
    args = ready(study, monkeypatch)
    original = bridge.read_verified(study.root, **args)
    original_clock = study.clock[0]
    candidate = study.training[0]
    # Add and seal a different old observation without changing the fold plan.
    new_result = fixtures._candidate(
        candidate,
        "newer-result-version",
        study.evaluation.cutoff + timedelta(days=3),
        choice="API27",
    )
    assert new_result["result_plan"] != study.plan["training"][0]["result_plan"]
    study.clock[0] = original_clock
    assert bridge.read_verified(study.root, **args) == original


def test_evaluation_cutoff_equality_fails(study, monkeypatch):
    args = ready(study, monkeypatch)
    study.clock[0] = study.evaluation.cutoff
    with pytest.raises(ValueError, match="not_ready_before_original_cutoff"):
        bridge.read_verified(study.root, **args)


def test_publication_at_cutoff_cannot_prepare(study, monkeypatch):
    args = ready(study, monkeypatch, merge=study.evaluation.cutoff)
    with pytest.raises(ValueError, match="not_ready_before_original_cutoff"):
        bridge.read_verified(study.root, **args)


def test_plan_with_future_result_ref_is_rejected_before_open(study, monkeypatch):
    args = ready(study, monkeypatch)
    alternate = json.loads(encoded(study.plan))
    alternate["evaluation"]["result_plan"] = study.plan["training"][0]["result_plan"]
    args["plan_ref"] = fixtures._plan(study, alternate, "mixed-role-plan.json")

    def never_replay(*args, **kwargs):
        pytest.fail("invalid role reached result replay")

    monkeypatch.setattr(learning, "replay", never_replay)
    with pytest.raises(ValueError, match="fold_invalid_input"):
        bridge.read_verified(study.root, **args)


def test_role_file_hashes_replay_after_cutoff_without_replacing(study, monkeypatch):
    args = ready(study, monkeypatch)
    monkeypatch.chdir(study.root)
    report = bridge.stage(study.root, **args)
    assert report["state"] == "local_views_prepared"
    assert not report["materialization_independent_clock_verified"]
    assert not report["counts_as_70_percent_evidence"]
    assert set(report["source_roles"]) == {"training", "labels", "evaluation"}
    saved = learning_fixtures._snapshot(study.root)
    with pytest.raises(FileExistsError, match="already_reserved"):
        bridge.stage(study.root, **args)
    study.clock[0] = study.evaluation.cutoff + timedelta(days=2)
    assert (
        bridge.replay(study.root, **args, receipt_sha256=report["receipt"]["sha256"])
        == report
    )
    assert learning_fixtures._snapshot(study.root) == saved
    path = study.root / report["source_roles"]["evaluation"]["path"]
    path.write_bytes(path.read_bytes()[:-1] + b" ")
    with pytest.raises(ValueError, match="role_does_not_replay"):
        bridge.replay(study.root, **args, receipt_sha256=report["receipt"]["sha256"])


def test_derived_view_read_is_bounded_by_verified_bytes_not_one_manifest(tmp_path):
    data = {"fictional": "x" * bridge.fold.MAX_MANIFEST_BYTES}
    raw = encoded(data)
    ref = {"path": "training.json", "sha256": sha256(raw)}
    path = tmp_path / ref["path"]
    path.write_bytes(raw)
    bridge._verify_role_file(tmp_path, ref, data)
    path.write_bytes(raw + b"x")
    with pytest.raises(ValueError, match="archive_file_too_large"):
        bridge._verify_role_file(tmp_path, ref, data)


def test_only_after_original_proof_is_read_back(study, monkeypatch):
    args = ready(
        study, monkeypatch, merge=study.evaluation.cutoff - timedelta(seconds=1)
    )
    # The receipt is visible by the end of the call, but was not available
    # at the preparation start recorded here.
    start = study.evaluation.cutoff - timedelta(microseconds=1)
    monkeypatch.setattr(bridge, "now", lambda: start)
    with pytest.raises(ValueError, match="not_ready_before_original_cutoff"):
        bridge.stage(study.root, **args)
    assert not (study.parent / bridge.DIRECTORY).exists()


def test_write_crossing_cutoff_preserves_late_receipt(study, monkeypatch):
    args = ready(study, monkeypatch)
    real_save = bridge.save

    def crossing(path, value):
        digest = real_save(path, value)
        if path.name == bridge.FILES["evaluation"]:
            study.clock[0] = study.evaluation.cutoff
        return digest

    monkeypatch.setattr(bridge, "save", crossing)
    report = bridge.stage(study.root, **args)
    assert report["state"] == "local_views_late"
    assert not report["training_approved"]
    assert (
        bridge.replay(study.root, **args, receipt_sha256=report["receipt"]["sha256"])
        == report
    )
    with pytest.raises(ValueError, match="not_ready_before_original_cutoff"):
        bridge.read_verified(study.root, **args)


def test_exact_fit_arguments_stop_before_any_optimizer_or_choice(study, monkeypatch):
    import kra_exact_trio_ridge_fit as fitter

    def forbid(*args, **kwargs):
        pytest.fail("a preparation path cannot fit or choose a trio")

    monkeypatch.setattr(fitter, "fit_exact_trios", forbid)
    monkeypatch.setattr(fitter, "minimize", forbid)
    monkeypatch.setattr(ExactTrioDistribution, "mode", forbid)

    args = ready(study, monkeypatch)
    report = bridge.stage(study.root, **args)

    def read(role):
        path = study.root / report["source_roles"][role]["path"]
        return parse_json(path.read_bytes())

    earlier = read("training")
    labels = read("labels")
    assert earlier["format"] == design.TRAIN and not earlier["training_approved"]
    assert b'"targets"' not in encoded(earlier) and labels["equal_race_weight"] == [
        1,
        28,
    ]
    a, b = [design.fit_arguments(earlier, labels, arm=arm) for arm in ("A", "B")]
    assert (
        a["expected_rosters"] == b["expected_rosters"] and a["targets"] == b["targets"]
    )
    assert a["feature_columns"] == b["feature_columns"][:-1]
    assert len(a["targets"]) == 28 and a["ridge"] == b["ridge"] == design.RIDGE
    for rid, roster in a["expected_rosters"].items():
        left, right = a["distributions"][rid], b["distributions"][rid]
        assert len(left.trios) == comb(len(roster), 3) and left.trios == right.trios
        # A zero added coefficient means both arms have the same score function.
        theta = (0.125,) * len(a["feature_columns"])
        assert left.log_probabilities(theta) == right.log_probabilities((*theta, 0))
    future = read("evaluation")
    assert future["format"] == design.EVAL and b'"targets"' not in encoded(future)
    fields = future["card"]["fields"]
    assert {f["race_id"] for f in fields} == study.evaluation.races.keys()
    assert all(
        len(f["candidate_horse_ids"]) == comb(len(f["roster"]), 3) for f in fields
    )
    with pytest.raises(ValueError, match="invalid_training_role"):
        design.fit_arguments(future, labels, arm="A")
    changed = parse_json(encoded(labels))
    changed["cards"][0]["targets"][0]["candidate_index"] = -1
    with pytest.raises(ValueError, match="population_or_index_mismatch"):
        design.fit_arguments(earlier, changed, arm="A")
    assert not report["model_fit_performed"] and not report["predictions_generated"]


def test_valid_old_result_change_leaves_exact_feature_bytes_unchanged(
    study, monkeypatch
):
    args = ready(study, monkeypatch)
    original = bridge.read_verified(study.root, **args)
    first = design.prepare_roles(study.root, original.training, original.evaluation)

    card = study.training[0]
    corrected = fixtures._candidate(
        card,
        "alternate-valid-official-version",
        study.evaluation.cutoff + timedelta(days=3),
        choice="API27",
    )
    raw = parse_json((study.root / corrected["candidate"]["path"]).read_bytes())
    previous, second = original.training["cards"]
    assert raw["target_races"] != previous["targets"]
    assert [bridge._project_field(item) for item in raw["input_races"]] == previous[
        "fields"
    ]
    replacement = previous | {
        "targets": raw["target_races"],
        "candidate": corrected["candidate"],
        "result_version": raw["report"]["result_version"],
    }
    changed = design.prepare_roles(
        study.root,
        original.training | {"cards": [replacement, second]},
        original.evaluation,
    )
    assert encoded(changed["training"]) == encoded(first["training"])
    assert encoded(changed["evaluation"]) == encoded(first["evaluation"])
    assert encoded(changed["labels"]) != encoded(first["labels"])
    # This compares transformations only; the newer version was never admitted.


@pytest.mark.parametrize("count", [3, 4, 5, 11])
def test_centered_trainer_term_has_zero_additive_runner_projection(count):
    horses = tuple(str(i) for i in range(1, count + 1))
    trios, _ = partition_trios(horses, ())
    raw = {s: int({"1", "2"} <= set(s)) for s in trios}
    extra = design.centered_trainer_counts(raw, horses)
    assert any(extra.values()) == (count >= 5)
    for horse in horses:
        assert sum(value for trio, value in extra.items() if horse in trio) == 0


def test_midrank_preserves_ties_and_does_not_rank_missing_as_last():
    fields = [
        {"horse_id": str(i), "features": {"rating": r}}
        for i, r in enumerate((49, 49, None, 51, 53), 1)
    ]
    got = design.centered_midranks(fields, "rating")
    assert got == pytest.approx({"1": -2 / 3, "2": -2 / 3, "3": 0, "4": 1 / 3, "5": 1})
    assert design.centered_midranks(list(reversed(fields)), "rating") == got
