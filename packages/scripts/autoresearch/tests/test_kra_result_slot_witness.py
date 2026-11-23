"""Verify immutable, named result slots using fictional local archives only."""

import sys
from datetime import timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "docs/research/tools"))

import kra_result_slot_witness as slots

from autoresearch.observed_history_seed import save
from autoresearch.restricted_cohort import encoded, sha256
from autoresearch.tests import test_kra_walk_forward_enrollment as enrol
from autoresearch.tests import test_kra_walk_forward_fold as cases
from autoresearch.tests import test_kra_whole_card_learning as learning_cases

study = cases.study
RULES_PULL = 1100


@pytest.fixture
def appointment(study, monkeypatch):
    monkeypatch.setattr(slots.fold, "now", lambda: study.clock[0])
    policy = enrol._policy(study.root)
    before = study.training[0].cutoff - timedelta(seconds=10)
    enrol._archive(study, policy, before)
    windows = [
        {
            "week": week,
            "opens_at": (card.result_time - timedelta(minutes=1)).isoformat(),
            "closes_at": (card.result_time + timedelta(minutes=1)).isoformat(),
            "receipt_pull": RULES_PULL + i,
            "api_request_budget": 12,
        }
        for i, (week, card) in enumerate(
            zip(enrol.WEEKS[:2], study.training, strict=True), 1
        )
    ]
    rules = {
        "path": "observation-policy.json",
        "sha256": save(
            study.root / "observation-policy.json",
            {
                "format": slots.PLAN,
                "enrollment_sha256": policy["sha256"],
                "slots": windows,
            },
        ),
    }
    return study, policy, rules, windows


def _publish_rules(study, ref, *, at=None):
    digest = ref["sha256"]
    cases.source.archive_publication(
        study.root / f"result-slot-rules-publication-{digest}",
        slots.rule_marker(digest),
        RULES_PULL,
        slots.rule_document(digest),
        at or study.training[0].cutoff - timedelta(seconds=1),
        study.initial,
    )


def _close(appointment, card_index, *, failed=False, publish_at=None):
    study, _, rules, windows = appointment
    rule = windows[card_index]
    card = study.training[card_index]
    digest, week = rules["sha256"], rule["week"]
    relative = Path(f"result-observation-slots-{digest}") / week
    location = study.root / relative
    closed = slots.timestamp(rule["closes_at"]) + timedelta(seconds=1)
    if failed:
        location.mkdir(parents=True)
        plan_sha, inventory_sha = None, None
        selection = study.plan["training"][card_index]
    else:
        selection = cases._candidate(card, relative.as_posix(), card.result_time)
        ref = selection["result_plan"]
        plan_sha = ref["sha256"]
        inventory_sha = sha256(
            encoded(
                slots.custody.inventory(
                    study.root,
                    ref,
                    race_dates=card.protocol["race_dates"],
                    race_ids=sorted(card.races),
                    schedule_sha256=card.input_spec["schedule_sha256"],
                )
            )
        )
    terminal = save(
        location / "terminal.json",
        {
            "format": slots.TERMINAL,
            "policy_sha256": digest,
            "week": week,
            "schedule_sha256": card.input_spec["schedule_sha256"],
            "population_sha256": sha256(encoded(sorted(card.races))),
            "closed_at": closed.isoformat(),
            "state": "failed" if failed else "observed",
            "result_plan_sha256": plan_sha,
            "inventory_sha256": inventory_sha,
        },
    )
    at = publish_at or closed + timedelta(seconds=1)
    retrieved = max(study.initial, at + timedelta(seconds=1))
    study.clock[0] = retrieved
    cases.source.archive_publication(
        location / "terminal-publication",
        slots.terminal_marker(digest, week, terminal),
        rule["receipt_pull"],
        slots.slot_document(digest, week),
        at,
        retrieved,
    )
    return selection, location


def _verify(appointment, selections, monkeypatch):
    study, policy, rules, _ = appointment
    ref = cases._plan(study, study.plan | {"training": selections})
    learning_cases._guard(monkeypatch)
    return slots.verify(
        study.root,
        rules,
        policy,
        ref,
        rules_pull=RULES_PULL,
        enrollment_pull=enrol.PULL,
    )


def test_only_the_prebound_exact_whole_slot_vector_is_available(
    appointment, monkeypatch
):
    study, _, rules, _ = appointment
    _publish_rules(study, rules)
    a, _ = _close(appointment, 0)
    b, _ = _close(appointment, 1)
    report = _verify(appointment, [a, b], monkeypatch)
    assert report["state"] == "documented_slot_versions_bound"
    assert report["selected_result_plans"] == [a["result_plan"], b["result_plan"]]
    assert not report["result_targets_admitted"] and not report["training_approved"]
    assert not report["current_official_corrections_reviewed"]


def test_same_scope_cannot_substitute_different_result_plan(appointment, monkeypatch):
    study, _, rules, _ = appointment
    _publish_rules(study, rules)
    _close(appointment, 0)
    b, _ = _close(appointment, 1)
    with pytest.raises(ValueError, match="result_slot_fold_requests_another_version"):
        _verify(appointment, [study.plan["training"][0], b], monkeypatch)


def test_failed_terminal_record_withholds_the_whole_vector(appointment, monkeypatch):
    study, _, rules, _ = appointment
    _publish_rules(study, rules)
    a, _ = _close(appointment, 0, failed=True)
    b, _ = _close(appointment, 1)
    report = _verify(appointment, [a, b], monkeypatch)
    assert report["state"] == "result_slots_held"
    assert report["selected_result_plans"] is None
    assert all("result_plan" not in state for state in report["slots"])
    assert report["slots"][0]["holds"] == ["designated_slot_failed"]


def test_appended_request_cannot_replace_a_terminal_slot(appointment, monkeypatch):
    study, _, rules, _ = appointment
    _publish_rules(study, rules)
    a, folder = _close(appointment, 0)
    b, _ = _close(appointment, 1)
    journal = folder / "history" / "requests"
    ordinal = len(list(journal.glob("*.json"))) + 1
    save(journal / f"{ordinal:06d}.json", {"extra_record": True})
    report = _verify(appointment, [a, b], monkeypatch)
    assert report["slots"][0]["holds"] == ["designated_run_request_journal_changed"]
    assert report["selected_result_plans"] is None


def test_policy_or_terminal_at_a_cutoff_is_not_timely(appointment, monkeypatch):
    study, _, rules, _ = appointment
    _publish_rules(study, rules)
    a, _ = _close(appointment, 0)
    b, _ = _close(appointment, 1, publish_at=study.evaluation.cutoff)
    with pytest.raises(ValueError, match="result_slot_terminal_not_timely"):
        _verify(appointment, [a, b], monkeypatch)


def test_rules_must_be_fixed_before_the_first_original_cutoff(appointment, monkeypatch):
    study, _, rules, _ = appointment
    _publish_rules(study, rules, at=study.training[0].cutoff)
    with pytest.raises(ValueError, match="result_slot_rules_not_published_before"):
        _verify(appointment, study.plan["training"], monkeypatch)


def test_needed_sources_cannot_be_swapped_for_empty_or_failed_responses():
    view = {
        "api_units": [{"day": "20990103", "meet": 3, "status": "empty_unconfirmed"}],
        "official_captures": [{"kind": "detail", "status": "fetch_error"}],
    }
    assert slots._required_source_holds(view, ["20990103_3_2"]) == [
        "designated_api_scope_not_observed",
        "designated_official_detail_not_captured",
    ]
