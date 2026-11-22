"""Prove enrollment from fictional official cards, without consuming outcomes."""

import sys
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "docs/research/tools"))

import kra_walk_forward_enrollment as enrollment

from autoresearch.observed_history_seed import save
from autoresearch.restricted_cohort import parse_json
from autoresearch.tests import test_kra_walk_forward_fold as fixtures
from autoresearch.tests import test_kra_whole_card_learning as learning_fixtures

study = fixtures.study
PULL = 1000
WEEKS = ["2098-12-29", "2099-01-05", "2099-01-12"]


def _policy(root, **updates):
    path = root / "enrollment.json"
    data = {
        "format": enrollment.POLICY,
        "training_weeks": WEEKS[:2],
        "evaluation_week": WEEKS[2],
    }
    return {"path": path.name, "sha256": save(path, data | updates)}


def _archive(case, policy, merged, *, supplied_digest=None):
    digest = policy["sha256"]
    fixtures.source.archive_publication(
        case.root / f"{enrollment.ARCHIVE_NAME}-{digest}",
        enrollment.marker(supplied_digest or digest),
        PULL,
        enrollment.publication_document(digest),
        merged,
        case.initial,
    )


def _guard(case, monkeypatch):
    learning_fixtures._guard(monkeypatch)
    monkeypatch.setattr(enrollment.fold, "now", lambda: case.clock[0])

    def forbid(*_, **__):
        pytest.fail("enrollment cannot replay results")

    monkeypatch.setattr(enrollment.fold, "_training", forbid)
    monkeypatch.setattr(enrollment.fold.learning, "replay", forbid)
    read_pin = enrollment.fold._pinned
    outcome_pins = [
        item[key]
        for item in case.plan["training"]
        for key in ("result_plan", "candidate")
    ]

    def inputs_only(root, ref):
        assert ref not in outcome_pins
        return read_pin(root, ref)

    monkeypatch.setattr(enrollment.fold, "_pinned", inputs_only)


def test_cli_binds_plan_and_role_membership_without_reading_results(
    study, monkeypatch, capsys
):
    _guard(study, monkeypatch)
    policy, ref = _policy(study.root), fixtures._plan(study)
    before = study.training[0].cutoff - timedelta(seconds=1)
    _archive(study, policy, before)
    saved = learning_fixtures._snapshot(study.root)
    monkeypatch.chdir(study.root)
    args = ["--policy", policy["path"], "--policy-sha256", policy["sha256"]]
    assert enrollment.main(["marker", *args]) == 0
    assert capsys.readouterr().out.encode() == enrollment.marker(policy["sha256"])
    # A later readback proves the original merge, not contemporaneous local storage.
    study.clock[0] = study.evaluation.cutoff + timedelta(weeks=60)
    assert (
        enrollment.main(
            [
                "replay",
                *args,
                "--pull",
                str(PULL),
                "--plan",
                ref["path"],
                "--plan-sha256",
                ref["sha256"],
            ]
        )
        == 0
    )
    report = parse_json(capsys.readouterr().out.encode())
    assert report["state"] == "enrollment_membership_verified"
    assert report["training_weeks"] == WEEKS[:2]
    assert report["evaluation_week"] == WEEKS[2]
    assert report["plan_sha256"] == ref["sha256"]
    assert report["first_enrolled_cutoff"] == study.training[0].cutoff.isoformat()
    assert report["publication"]["merged_at"] == before.isoformat()
    assert report["publication"]["retrieved_at"] == study.initial.isoformat()
    assert not any(
        report[key]
        for key in (
            "study_registered",
            "training_approved",
            "cross_fold_selection_rule_verified",
            "result_version_selection_verified",
            "counts_as_70_percent_evidence",
        )
    )
    assert learning_fixtures._snapshot(study.root) == saved


@pytest.mark.parametrize("change", ["drop", "repeat", "reverse", "swap_roles"])
def test_no_omission_or_role_substitution(study, monkeypatch, change):
    _guard(study, monkeypatch)
    policy = _policy(study.root)
    _archive(study, policy, study.training[0].cutoff - timedelta(minutes=1))
    a, b = study.plan["training"]
    if change == "drop":
        plan = study.plan | {"training": [a]}
    elif change == "repeat":
        plan = study.plan | {"training": [a, a]}
    elif change == "reverse":
        plan = study.plan | {"training": [b, a]}
    else:
        plan = study.plan | {
            "training": [a, b | {"input": study.plan["evaluation"]}],
            "evaluation": b["input"],
        }
    reason = "card_count" if change == "drop" else "week"
    ref = fixtures._plan(study, plan)
    with pytest.raises(ValueError, match=f"enrollment_plan_{reason}_conflict"):
        enrollment.verify(study.root, policy, ref, pull=PULL)


@pytest.mark.parametrize("delay", [0, 1])
def test_cannot_enroll_at_or_after_the_first_original_cutoff(study, monkeypatch, delay):
    _guard(study, monkeypatch)
    policy, ref = _policy(study.root), fixtures._plan(study)
    cutoff = study.training[0].cutoff + timedelta(seconds=delay)
    _archive(study, policy, cutoff.astimezone(ZoneInfo("Asia/Seoul")))
    with pytest.raises(ValueError, match="enrollment_publication_not_before"):
        enrollment.verify(study.root, policy, ref, pull=PULL)


def test_requires_exact_archived_marker(study, monkeypatch):
    _guard(study, monkeypatch)
    policy, ref = _policy(study.root), fixtures._plan(study)
    with pytest.raises(ValueError, match="missing_or_oversized_evidence"):
        enrollment.verify(study.root, policy, ref, pull=PULL)
    _archive(
        study,
        policy,
        study.training[0].cutoff - timedelta(minutes=1),
        supplied_digest="0" * 64,
    )
    with pytest.raises(ValueError, match="forward_publication_evidence_conflict"):
        enrollment.verify(study.root, policy, ref, pull=PULL)


@pytest.mark.parametrize(
    ("training", "reason"),
    [
        ([], "invalid_policy"),
        (WEEKS[:2][::-1], "week_order_conflict"),
        ([WEEKS[0], WEEKS[0]], "week_order_conflict"),
        ([WEEKS[0], WEEKS[2]], "week_order_conflict"),
        ([WEEKS[0], "20990105"], "invalid_week"),
        ([WEEKS[0], "2099-01-06"], "invalid_week"),
        ([WEEKS[0], "invalid"], "invalid_week"),
    ],
)
def test_invalid_policy_cannot_emit_marker(tmp_path, monkeypatch, training, reason):
    monkeypatch.chdir(tmp_path)
    policy = _policy(tmp_path, training_weeks=training)
    with pytest.raises(ValueError, match=f"enrollment_{reason}"):
        enrollment.main(
            ["marker", "--policy", policy["path"], "--policy-sha256", policy["sha256"]]
        )
