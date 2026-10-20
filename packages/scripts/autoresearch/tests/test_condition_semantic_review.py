"""Actual archived review binding is distinct from a claim's semantic truth."""

import socket
import subprocess
from copy import deepcopy

import pytest

from autoresearch import condition_forward
from autoresearch import condition_semantic_contract as contract
from autoresearch import condition_semantic_review as semantic
from autoresearch.restricted_cohort import parse_json
from autoresearch.tests.semantic_review_fixture import (
    actor,
    bundle,
    later_review,
    stamp,
)


def run(value):
    return semantic.audit(value.path, value.pin["sha256"])


def test_complete_attestation_is_not_population_or_machine_semantic_proof(
    tmp_path, monkeypatch
):
    value = bundle(tmp_path)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    def forbidden(*args, **kwargs):
        pytest.fail("unexpected side effect")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(condition_forward, "run", forbidden)
    result = run(value)
    assert result["status"] == "attestation_replayed"
    assert result["evidence_kind"] == "reviewer_attested_interpretation"
    assert result["authority_review"]["reviewer_id"] == contract.OWNER[0]
    assert result["decision_review"]["reviewer_id"] == 2002
    assert not result["source_semantics_fully_machine_verified"]
    assert not result["source_facts"][0]["claim_implication_machine_verified"]
    assert not result["usable_for_scoring"]
    assert not result["full_population_verified"]
    assert result["denominator"] is None
    assert result["actual_fit_count"] == 0
    assert not result["registration_performed"]
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


@pytest.mark.parametrize(
    "modify,reason",
    [
        (lambda v: v.owner.update(user=actor(999, "coyaSONG")), "authority_owner"),
        (lambda v: v.owner.update(state="DISMISSED"), "current_approval"),
        (lambda v: v.owner.update(body='{"reviewed":true}'), "commitment"),
        (
            lambda v: v.delegate.update(user=actor(999, "synthetic-reviewer")),
            "not_authorized",
        ),
        (lambda v: v.delegate.update(state="COMMENTED"), "current_approval"),
        (lambda v: v.delegate.update(state="PENDING"), "unsubmitted"),
        (lambda v: v.delegate.update(state="CHANGES_REQUESTED"), "current_approval"),
        (lambda v: v.delegate.update(body='{"approved":true}'), "commitment"),
        (lambda v: v.delegate.update(submitted_at=stamp(1)), "list_clock"),
        (lambda v: v.delegate.update(submitted_at=stamp(-0.5)), "current_approval"),
        (lambda v: v.delegate.update(commit_id="not-a-commit"), "review_commit"),
        (lambda v: v.delegate.update(submitted_at="2026-10-20"), "timezone"),
        (
            lambda v: v.registry["reviewers"][0].update(claim_types=["postponement"]),
            "not_authorized",
        ),
        (
            lambda v: v.registry["reviewers"][0].update(valid_until=stamp(-2)),
            "not_authorized",
        ),
        (
            lambda v: v.registry["reviewers"][0].update(claim_types=["complete"]),
            "authority_grant",
        ),
        (lambda v: v.decision.update(claim_type="complete"), "claim_type"),
        (lambda v: v.decision.update(complete=True), "decision_schema"),
        (lambda v: v.decision["claim"].update(complete=True), "typed_claim_fields"),
        (lambda v: v.decision.update(authored_at=stamp(-4)), "decision_binding"),
        (lambda v: v.decision.update(authored_at=stamp(-1.25)), "not_authorized"),
        (
            lambda v: v.decision["sources"][0].update(excerpt="not in source"),
            "excerpt_not",
        ),
        (
            lambda v: v.capture.update(url="https://example.com/notice"),
            "official_source",
        ),
        (
            lambda v: v.capture.update(url="http://race.kra.co.kr/notice"),
            "official_source",
        ),
        (lambda v: v.capture.update(status=403), "official_source"),
        (lambda v: v.capture.update(capture_completed_at=stamp(-1)), "source_clock"),
        (
            lambda v: v.decision.update(supersedes_decision_sha256="b" * 64),
            "correction_requires",
        ),
        (lambda v: later_review(v, "DISMISSED"), "current_approval"),
        (lambda v: later_review(v, "CHANGES_REQUESTED"), "current_approval"),
        (lambda v: later_review(v, "APPROVED"), "current_approval"),
    ],
)
def test_invalid_attestation_never_promoted(tmp_path, modify, reason):
    value = bundle(tmp_path, modify)
    with pytest.raises(ValueError, match=reason):
        run(value)


def test_same_author_cannot_supply_separate_review(tmp_path):
    def modify(value):
        value.decision_author = deepcopy(value.delegate["user"])

    with pytest.raises(ValueError, match="not_separate"):
        run(bundle(tmp_path, modify))


def test_approval_of_different_document_version_cannot_be_reused(tmp_path):
    def modify(value):
        value.reviewed_decision = {
            **deepcopy(value.decision),
            "justification": "old bytes",
        }

    with pytest.raises(ValueError, match="bytes_changed"):
        run(bundle(tmp_path, modify))


@pytest.mark.parametrize(
    "filename",
    [
        "owner-review/capture.json",
        "delegate-review/reviews.json",
        "delegate-review/content.json",
        "source/body.txt",
    ],
)
def test_missing_original_is_pending_not_approved(tmp_path, filename):
    value = bundle(tmp_path)
    (tmp_path / filename).unlink()
    result = run(value)
    assert result["status"] == "pending_evidence"
    assert result["evidence_kind"] == "unverified_interpretation"


@pytest.mark.parametrize(
    "filename",
    [
        "authority/pull.json",
        "decision/published-document.md",
        "delegate-review/reviews.json",
        "source/body.txt",
    ],
)
def test_corrupt_original_is_blocked_not_pending(tmp_path, filename):
    value = bundle(tmp_path)
    (tmp_path / filename).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="hash_mismatch"):
        run(value)


def test_symlink_original_is_blocked(tmp_path):
    value = bundle(tmp_path)
    path = tmp_path / "source/body.txt"
    other = tmp_path / "other.txt"
    path.rename(other)
    path.symlink_to(other)
    with pytest.raises(ValueError, match="symlink"):
        run(value)


def revise_review_capture(value, change):
    pin = value.manifest["decision_review"]
    record = parse_json((value.root / pin["path"]).read_bytes())
    change(record)
    value.manifest["decision_review"] = value.save(pin["path"], record)
    value.pin = value.save("manifest.json", value.manifest)


def test_wrong_review_commit_query_rejected(tmp_path):
    value = bundle(tmp_path)
    revise_review_capture(
        value,
        lambda r: r["reviewed_content"].update(
            url="https://api.github.com/repos/coyaSONG/kra-analysis/contents/current?ref=main"
        ),
    )
    with pytest.raises(ValueError, match="response_identity"):
        run(value)


def test_full_page_is_not_silently_treated_as_complete(tmp_path):
    value = bundle(tmp_path)
    page = value.save("delegate-review/full.json", [value.values.delegate] * 100)
    revise_review_capture(value, lambda r: r["reviews"].update(response=page))
    with pytest.raises(ValueError, match="page_not_complete"):
        run(value)


@pytest.mark.parametrize(
    "raw,reason",
    [
        (b'[{"id":1,"id":2}]', "duplicate_json_key"),
        (b'[{"id":NaN}]', "nonfinite_json_value"),
        (b'{"reviews":[]}', "page_not_complete"),
    ],
)
def test_review_response_uses_strict_json(tmp_path, raw, reason):
    value = bundle(tmp_path)
    page = value.save("delegate-review/invalid.json", raw)
    revise_review_capture(value, lambda r: r["reviews"].update(response=page))
    with pytest.raises(ValueError, match=reason):
        run(value)


@pytest.mark.parametrize(
    "scope",
    [
        {"race_dates": ["20261023"], "meets": [99]},
        {"race_dates": ["19991023"], "meets": [1]},
    ],
)
def test_empty_scope_claim_still_requires_valid_physical_scope(tmp_path, scope):
    def modify(value):
        value.decision.update(
            claim_type="no_enrollable_races",
            subjects={},
            claim={},
            scope=scope,
        )

    with pytest.raises(ValueError):
        run(bundle(tmp_path, modify))


def test_captured_future_reviews_rejected(tmp_path):
    value = bundle(tmp_path)
    revise_review_capture(value, lambda r: r.update(observed_at=stamp(2)))
    with pytest.raises(ValueError, match="observation_clock"):
        run(value)


def test_cli_invalid_manifest_does_not_create_authority(tmp_path, capsys):
    value = bundle(tmp_path)
    assert semantic.main(["--manifest", str(value.path), "--sha256", "b" * 64]) == 2
    result = parse_json(capsys.readouterr().out.encode())
    assert result["status"] == "blocked"
    assert not result["usable_for_scoring"]


@pytest.mark.parametrize(
    "kind,subjects,claim",
    [
        ("no_enrollable_races", {}, {}),
        ("exhaustive_scope_listing", {}, {"race_ids": ["20261023_1_1"]}),
        ("same_physical_event", {"a": "20261023_1_1", "b": "20261023_1_2"}, {}),
        ("different_replacement_event", {"a": "20261023_1_1", "b": "20261023_1_1"}, {}),
        (
            "postponement",
            {"a": "20261023_1_1"},
            {"new_race_id": "20261023_1_2", "effective_at": stamp(100)},
        ),
    ],
)
def test_claim_types_remain_attestation_not_automatic_semantic_truth(
    tmp_path, kind, subjects, claim
):
    # The common fixture excerpt does not imply each claim. Human semantic
    # error is deliberately not advertised as detectable by a hash/identity audit.
    def modify(value):
        value.decision.update(claim_type=kind, subjects=subjects, claim=claim)

    result = run(bundle(tmp_path, modify))
    assert result["evidence_kind"] == "reviewer_attested_interpretation"
    assert not result["source_semantics_fully_machine_verified"]
    assert result["denominator"] is None
