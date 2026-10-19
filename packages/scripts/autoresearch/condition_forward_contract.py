"""Exact stored models and separately merged prospective protocol admission."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from autoresearch import condition_training_admission as training
from autoresearch.condition_training_model import ARMS
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import ROOT, encoded, parse_json, sha256

REGISTRY = "data/contracts/condition_forward_reviews_v1.json"
MODELS = "docs/research/experiments/2026-10-19-condition-training-v1"
MODEL_HASHES = {
    "A24": "69f655fd005b59313d0a23dbf44759510c937ef403e8ac4fd844ea67494d635e",
    "B34": "c03972a447c2a36603717a7107b751f23d0fff08cb204565b68215f955ef16e0",
}
RECEIPT_SHA = "3587c948913c82cc9c0b8c5e64161ef29794ed22a80d08425300e924834aa96e"
POLICIES = {
    "population": "all_reconciled_national_races_on_registered_dates",
    "freeze": "whole_block_before_first_t30_cutoff",
    "within_block_outcome_updates": False,
    "selection": "one_unordered_three_per_arm_no_or_union",
    "prediction_failure": "retain_full_population_no_subset_replacement",
    "results": "versioned_unique_top3_pending_not_failure_undefined_reported",
    "schedule_changes": "retain_original_universe_flag_changes_no_silent_replacement",
    "promotion": "none_automatic",
    "refitting": "forbidden",
}


def local_path(value):
    path = ROOT / value
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError("forward_symlink_source")
    path = path.resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError("forward_source_outside_checkout")
    return path


def read_pin(pin):
    path = local_path(pin["path"])
    raw = training.read(path)
    if sha256(raw) != pin["sha256"]:
        raise ValueError("forward_source_hash_mismatch")
    return parse_json(raw)


def load_models():
    receipt = read_pin({"path": f"{MODELS}/receipt.json", "sha256": RECEIPT_SHA})
    models = {}
    for arm, digest in MODEL_HASHES.items():
        model = read_pin({"path": f"{MODELS}/{arm}-model.json", "sha256": digest})
        if (
            model["arm"] != arm
            or model["columns"] != list(ARMS[arm])
            or model["classes"] != [0, 1]
            or receipt["evidence"][arm]["model_sha256"] != digest
        ):
            raise ValueError("forward_model_contract_mismatch")
        models[arm] = model
    # Keep the reviewed numerical adapter, not a new scoring implementation.
    for name in (
        "condition_training_model.py",
        "condition_training_data.py",
        "condition_candidate_inputs.py",
    ):
        path = f"packages/scripts/autoresearch/{name}"
        if (
            sha256(training.read(ROOT / path))
            != receipt["requirement"]["implementation"][path]
        ):
            raise ValueError("forward_frozen_numerical_code_changed")
    return models, receipt


def runtime():
    return {
        "model_hashes": MODEL_HASHES,
        "training_receipt_sha256": RECEIPT_SHA,
        "implementation": training.implementation(),
        "environment": parse_json(encoded(training.environment())),
        "policies": POLICIES,
        "fit_count": 0,
    }


def validate_protocol(protocol, observed):
    dates = protocol["race_dates"]
    if (
        protocol["format_version"] != "condition-forward-protocol-v1"
        or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", protocol["study_id"])
        or not dates
        or dates != sorted(set(dates))
        or any(not re.fullmatch(r"\d{8}", d) or d <= "20261018" for d in dates)
    ):
        raise ValueError("forward_invalid_protocol_identity")
    for date in dates:
        datetime.strptime(date, "%Y%m%d")
    if encoded(protocol["policies"]) != encoded(POLICIES) or encoded(
        protocol["runtime"]
    ) != encoded(runtime()):
        raise ValueError("forward_runtime_or_policy_changed")
    for name in (
        "horizon",
        "sample_size_rationale",
        "uncertainty",
        "stopping",
        "prediction_failure_scoring",
        "prior_block_history_policy",
    ):
        if not isinstance(protocol.get(name), str) or not protocol[name].strip():
            raise ValueError("forward_missing_statistical_protocol")
    races = protocol["races"]
    ids = [r["race_id"] for r in races]
    if (
        not ids
        or ids != sorted(set(ids))
        or {rid[:8] for rid in ids} != set(dates)
        or any(not re.fullmatch(r"\d{8}_[1-4]_[1-9]\d*", rid) for rid in ids)
    ):
        raise ValueError("forward_invalid_population")
    cutoff = min(timestamp(r["feature_cutoff_at"]) for r in races)
    if (
        not timestamp(protocol["created_at"]) <= observed
        or not timestamp(protocol["created_at"]) < cutoff
    ):
        raise ValueError("forward_protocol_clock_invalid")
    return cutoff


def admit(study_id):
    raw = training.read(ROOT / REGISTRY)
    registry = parse_json(raw)
    if registry["format_version"] != "condition-forward-reviews-v1":
        raise ValueError("forward_invalid_registry")
    records = registry["approved_studies"]
    matches = [r for r in records if r["study_id"] == study_id]
    if len(matches) != 1:
        raise ValueError("forward_exact_registered_study_required")
    if raw != encoded(registry):
        raise ValueError("forward_registry_not_canonical")
    dates = [d for r in records for d in r["race_dates"]]
    if len(dates) != len(set(dates)):
        raise ValueError("forward_overlapping_registered_dates")
    review = matches[0]
    for flag in (
        "raw_source_closure_reviewed",
        "label_free_inputs_reviewed",
        "protocol_reviewed",
    ):
        if review.get(flag) is not True:
            raise ValueError("forward_incomplete_review")
    if (
        not isinstance(review.get("reviewer"), str)
        or not review["reviewer"].strip()
        or type(review.get("protocol_publication_pr")) is not int
        or review["protocol_publication_pr"] <= 0
    ):
        raise ValueError("forward_invalid_review")
    protocol = read_pin(review["protocol"])
    relative = str(local_path(review["protocol"]["path"]).relative_to(ROOT))
    if (
        not relative.startswith("docs/research/protocols/")
        or relative != review["protocol"]["path"]
        or sha256(encoded(protocol)) != review["protocol"]["sha256"]
    ):
        raise ValueError("forward_protocol_not_in_repository")
    observed = datetime.now(UTC)
    cutoff = validate_protocol(protocol, observed)
    _, fit_receipt = load_models()
    if timestamp(protocol["created_at"]) < timestamp(fit_receipt["completed_at"]):
        raise ValueError("forward_protocol_precedes_stored_models")
    if (
        protocol["study_id"] != study_id
        or protocol["race_dates"] != review["race_dates"]
        or not timestamp(protocol["created_at"])
        <= timestamp(review["reviewed_at"])
        <= observed
        or timestamp(review["reviewed_at"]) >= cutoff
    ):
        raise ValueError("forward_review_clock_or_identity_mismatch")
    for ref in ("HEAD", "origin/main"):
        if training.git("show", f"{ref}:{REGISTRY}") != raw or training.git(
            "show", f"{ref}:{relative}"
        ) != training.read(local_path(relative)):
            raise ValueError("forward_review_not_committed_on_main")
        for path, digest in protocol["runtime"]["implementation"].items():
            if sha256(training.git("show", f"{ref}:{path}")) != digest:
                raise ValueError("forward_code_not_committed_on_main")
    return protocol, review, raw
