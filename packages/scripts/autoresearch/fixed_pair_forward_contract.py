"""Bind a new complete card, unchanged models and two independent public reviews."""

import re
import subprocess

from autoresearch import api27_forward as api27
from autoresearch import condition_forward_publication as publication
from autoresearch import condition_training_admission as training
from autoresearch import kra_entry_scope_inputs as inputs
from autoresearch import kra_entry_scope_witness as input_witness
from autoresearch import local_m0_inference as m0
from autoresearch.kra_entry_scope_intake import now
from autoresearch.local_m0_evaluation import OUTCOME_POLICY_SHA
from autoresearch.prerace_hash_witness import REPOSITORY, timestamp
from autoresearch.restricted_cohort import encoded, parse_json, sha256

OWNER = REPOSITORY.split("/")[0]
PROTOCOL = "kra-fixed-pair-prospective-protocol-v1"
APPROVAL = "kra-fixed-pair-prospective-approval-v1"
MODELS = {
    "M0": {"model_sha256": m0.MODEL_SHA, "fit_receipt_sha256": m0.RECEIPT_SHA},
    "API27": {"model_sha256": api27.MODEL_SHA, "fit_receipt_sha256": api27.RECEIPT_SHA},
}
POLICY = {
    "population": "all_races_and_declarations_of_the_original_complete_card",
    "freeze": "strictly_before_the_first_original_t30",
    "selection": "one_unordered_triple_per_race_and_arm_no_fallback",
    "failure": "preserve_full_population_pending_until_proven",
    "outcome_policy_sha256": OUTCOME_POLICY_SHA,
    "promotion_or_refit_authorized": False,
}
ANALYSIS_FIELDS = {"horizon", "uncertainty", "sample_size_rationale", "stopping"}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def canonical(raw):
    value = parse_json(raw)
    require(encoded(value) == raw, "fixed_pair_noncanonical_bytes")
    return value


def git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root), *args], stderr=subprocess.PIPE, timeout=15
    )


def path_for(study, role):
    require(
        type(study) is str and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", study),
        "fixed_pair_invalid_study",
    )
    if role == "prediction":
        return f"docs/research/commitments/fixed-pair-v1/{study}/paired.json"
    parent = {"protocol": "protocols", "approval": "approvals"}[role]
    return f"docs/research/{parent}/fixed-pair-v1/{study}.json"


def pull_number(number):
    require(type(number) is int and number > 0, "fixed_pair_invalid_pull")
    return number


def reviewer_login(login):
    require(
        isinstance(login, str)
        and re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,38})", login)
        and login != OWNER.lower(),
        "fixed_pair_independent_reviewer_required",
    )
    return login


def runtime_sha():
    return sha256(
        encoded(
            {
                "implementation": training.implementation(),
                "environment": training.environment(),
            }
        )
    )


def committed(root, path):
    document = root / path
    require(
        not document.is_symlink() and document.resolve() == document,
        "fixed_pair_document_path_conflict",
    )
    raw = training.read(document)
    for ref in ("HEAD", "refs/remotes/origin/main"):
        require(git(root, "show", f"{ref}:{path}") == raw, "fixed_pair_not_on_main")
    return raw


def source(root, receipt, *, schedule_sha256, first_cutoff, packet_sha256, input_pr):
    report = input_witness.verify(
        root,
        receipt,
        schedule_sha256=schedule_sha256,
        first_cutoff=first_cutoff,
        packet_sha256=packet_sha256,
        pull=pull_number(input_pr),
    )
    require(report["before_cutoff"], "fixed_pair_input_publication_late")
    replay_at = timestamp(report["local_readback_at"])
    verified = inputs.preflight(
        root,
        receipt,
        schedule_sha256=schedule_sha256,
        first_cutoff=first_cutoff,
        clock=lambda: replay_at,
    )
    require(
        sha256(encoded(input_witness._packet(verified))) == packet_sha256,
        "fixed_pair_input_projection_changed",
    )
    observed = report["publication"]
    return verified, {
        "intake_receipt_sha256": receipt["sha256"],
        "schedule_sha256": schedule_sha256,
        "input_packet_sha256": packet_sha256,
        "input_publication": {
            key: observed[key]
            for key in (
                "pull_number",
                "merge_commit_sha",
                "merged_at",
                "document_sha256",
            )
        },
    }


def protocol_for(study, login, pair_pr, analysis, verified, source_binding, created):
    require(
        type(analysis) is dict
        and analysis.keys() == ANALYSIS_FIELDS
        and all(isinstance(v, str) and v.strip() for v in analysis.values()),
        "fixed_pair_missing_analysis_protocol",
    )
    dates = verified["race_dates"]
    cutoff = timestamp(verified["first_block_cutoff"])
    require(
        all(day > "20261018" for day in dates)
        and timestamp(source_binding["input_publication"]["merged_at"])
        <= created
        < cutoff,
        "fixed_pair_protocol_outside_original_window",
    )
    return {
        "format_version": PROTOCOL,
        "study_id": study,
        "created_at": created.isoformat(),
        "reviewer": reviewer_login(login),
        "analysis": analysis,
        "models": MODELS,
        "policy": POLICY,
        "runtime_sha256": runtime_sha(),
        "source": source_binding,
        "race_dates": dates,
        "first_block_cutoff": verified["first_block_cutoff"],
        "race_ids": sorted(b["race"]["race_id"] for b in verified["bindings"]),
        "prediction_slot": {
            "repository": REPOSITORY,
            "pull_number": pull_number(pair_pr),
            "document": path_for(study, "prediction"),
        },
    }


def approval_for(study, protocol_raw, protocol_pr, login, reviewed):
    return {
        "format_version": APPROVAL,
        "study_id": study,
        "protocol_sha256": sha256(protocol_raw),
        "protocol_pr": pull_number(protocol_pr),
        "reviewer": reviewer_login(login),
        "reviewed_at": reviewed.isoformat(),
        "source_closure_reviewed": True,
        "population_and_statistics_reviewed": True,
        "release_checks_reviewed": True,
    }


def documents(root, study, protocol_pr, approval_pr):
    require(
        pull_number(protocol_pr) != pull_number(approval_pr),
        "fixed_pair_reused_publication_slot",
    )
    protocol_path = path_for(study, "protocol")
    approval_path = path_for(study, "approval")
    protocol_raw = committed(root, protocol_path)
    approval_raw = committed(root, approval_path)
    protocol = canonical(protocol_raw)
    approval = canonical(approval_raw)
    return protocol, approval, protocol_raw, approval_raw


def unused_scope(root, protocol):
    directory = "docs/research/protocols/fixed-pair-v1"
    selected = path_for(protocol["study_id"], "protocol")
    paths = (
        git(
            root,
            "ls-tree",
            "-r",
            "--name-only",
            "-z",
            "refs/remotes/origin/main",
            "--",
            directory,
        )
        .decode()
        .split("\0")
    )
    numbers = {
        protocol["prediction_slot"]["pull_number"],
        protocol["source"]["input_publication"]["pull_number"],
    }
    for path in paths:
        if not path or path == selected:
            continue
        other = canonical(git(root, "show", f"refs/remotes/origin/main:{path}"))
        require(
            other["format_version"] == PROTOCOL
            and path == path_for(other["study_id"], "protocol")
            and not set(other["race_dates"]).intersection(protocol["race_dates"])
            and not numbers.intersection(
                (
                    other["prediction_slot"]["pull_number"],
                    other["source"]["input_publication"]["pull_number"],
                )
            ),
            "fixed_pair_scope_already_registered",
        )


def local_review(study, proof_ids, protocol, protocol_raw, approval_raw):
    protocol_pr, approval_pr = proof_ids
    approval = canonical(approval_raw)
    numbers = [
        protocol_pr,
        approval_pr,
        protocol["prediction_slot"]["pull_number"],
        protocol["source"]["input_publication"]["pull_number"],
    ]
    require(
        len({pull_number(n) for n in numbers}) == len(numbers),
        "fixed_pair_reused_publication_slot",
    )
    reviewer = reviewer_login(protocol["reviewer"])
    reviewed_at = timestamp(approval["reviewed_at"])
    require(
        approval_raw
        == encoded(
            approval_for(study, protocol_raw, protocol_pr, reviewer, reviewed_at)
        ),
        "fixed_pair_approval_does_not_bind_exact_protocol",
    )
    return reviewer, reviewed_at


def verify_documents(ledger, study, proof_ids, protocol_raw, approval_raw, *, collect):
    protocol_pr, approval_pr = proof_ids
    protocol = canonical(protocol_raw)
    reviewer, reviewed_at = local_review(
        study, proof_ids, protocol, protocol_raw, approval_raw
    )
    evidence = {}
    operation = publication.capture if collect else publication.replay
    for role, pr, raw, author in (
        ("protocol", protocol_pr, protocol_raw, OWNER.lower()),
        ("approval", approval_pr, approval_raw, reviewer),
    ):
        directory = ledger / (role + "-publication")
        public, observation = operation(
            directory, pr, path_for(study, role), sha256(raw)
        )
        pull = parse_json(training.read(directory / "pull.json"))
        require(
            public == raw and pull.get("user", {}).get("login", "").lower() == author,
            "fixed_pair_public_review_author_conflict",
        )
        evidence[role] = observation
    cutoff = timestamp(protocol["first_block_cutoff"])
    first, second = (
        timestamp(evidence[name]["merged_at"]) for name in ("protocol", "approval")
    )
    require(
        timestamp(protocol["created_at"]) <= first <= reviewed_at <= second < cutoff
        and first < second
        and all(timestamp(item["retrieved_at"]) <= now() for item in evidence.values()),
        "fixed_pair_review_not_before_cutoff",
    )
    return evidence
