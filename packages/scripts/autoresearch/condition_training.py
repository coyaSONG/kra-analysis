"""Read-only inspection or single-use, separately approved A24/B34 fitting."""

from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from autoresearch import condition_training_admission as admission
from autoresearch.condition_training_model import ARMS, fit_once, score, select
from autoresearch.restricted_cohort import encoded, parse_json, sha256


def now():
    return datetime.now(UTC).isoformat()


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def save(path, value):
    raw = encoded(value)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    sync_directory(path.parent)
    return sha256(raw)


def locations():
    common = Path(admission.git("rev-parse", "--git-common-dir").decode().strip())
    if not common.is_absolute():
        common = admission.ROOT / common
    # Cohort, not reviewer, output name or code hash, is the lifetime budget key.
    return (
        common.resolve() / "condition-training-attempts" / admission.COHORT_SHA,
        admission.ROOT
        / ".cache/autoresearch/condition-training-v1"
        / admission.COHORT_SHA,
    )


def safe_destination(path):
    if path.exists() or path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError("reused_or_symlink_destination")


def run():
    arrays, requirement = admission.load()
    registry, review = admission.approval(requirement)
    ledger, output = locations()
    safe_destination(ledger)
    safe_destination(output)
    admission.unchanged(requirement, registry)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    sync_directory(ledger.parent.parent)
    ledger.mkdir(exist_ok=False)
    sync_directory(ledger.parent)
    started = now()
    context = {
        "started_at": started,
        "review": review,
        "requirement": requirement,
        "registry_sha256": sha256(registry),
        "git_head": admission.git("rev-parse", "HEAD").decode().strip(),
        "output": str(output),
        "fit_budget": {"A24": 1, "B34": 1},
        "retry_allowed": False,
    }
    # Even interruption before an estimator call consumes the pair reservation.
    save(ledger / "reservation.json", context)
    attempts, completed = [], []
    try:
        output.mkdir(parents=True, exist_ok=False)
        sync_directory(output.parent)
        save(output / "admission.json", context)
        x, y, weights, identities = arrays
        models, evidence = {}, {}

        def before_estimator(arm):
            admission.unchanged(requirement, registry)
            if arm in attempts or arm not in ARMS:
                raise ValueError("fit_budget_exhausted")
            save(
                ledger / f"{arm}-attempt.json",
                {
                    "arm": arm,
                    "attempted_at": now(),
                    "review_id": review["review_id"],
                    "fit_attempt": 1,
                },
            )
            attempts.append(arm)

        for arm, columns in ARMS.items():
            admission.unchanged(requirement, registry)
            model, consumed = fit_once(
                x[:, : len(columns)].copy(),
                y.copy(),
                weights.copy(),
                identities,
                arm,
                before_estimator,
            )
            completed.append(arm)
            models[arm] = model
            evidence[arm] = {
                "model_sha256": save(output / f"{arm}-model.json", model),
                "consumed_sha256": save(output / f"{arm}-consumed.json", consumed),
            }
            reloaded = parse_json(admission.read(output / f"{arm}-model.json"))
            disk = parse_json(admission.read(output / f"{arm}-consumed.json"))
            scores = score(reloaded, x[:, : len(columns)])
            if (
                not np.allclose(scores, disk["scores"], rtol=0, atol=1e-12)
                or select(identities, scores) != disk["predictions"]
            ):
                raise ValueError("disk_replay_mismatch")
        for field in (
            "imputer_statistics",
            "scaler_mean",
            "scaler_var",
            "scaler_scale",
        ):
            if models["A24"][field] != models["B34"][field][:24]:
                raise ValueError("common24_preprocessing_mismatch")
        for arm, hashes in evidence.items():
            for artifact in ("model", "consumed"):
                if (
                    sha256(admission.read(output / f"{arm}-{artifact}.json"))
                    != hashes[f"{artifact}_sha256"]
                ):
                    raise ValueError("output_artifact_changed")
        admission.unchanged(requirement, registry)
        receipt = {
            "format_version": "condition-training-receipt-v1",
            "completed_at": now(),
            **context,
            "evidence": evidence,
            "attempted_arms": attempts,
            "completed_arms": completed,
            "actual_fit_count": len(completed),
            "development_only": True,
            "independent_validation_eligible": False,
            "model_promoted": False,
            "counts_as_70_percent_evidence": False,
            "common24_statistics_equal": True,
            "original_hashes_unchanged": True,
            "score_and_exact_set_replay_verified": True,
        }
        save(
            ledger / "complete.json",
            {"receipt_sha256": sha256(encoded(receipt)), "completed_at": now()},
        )
        save(output / "receipt.json", receipt)
        return receipt
    except BaseException as exc:
        save(
            ledger / "failure.json",
            {
                "failed_at": now(),
                "exception_type": type(exc).__name__,
                "error": str(exc),
                "attempted_arms": attempts,
                "completed_arms": completed,
                "retry_allowed": False,
                "pair_success": False,
            },
        )
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inspect", "run"))
    args = parser.parse_args()
    if args.command == "inspect":
        _, requirement = admission.load()
        result = {
            "requirement": requirement,
            "requirement_sha256": sha256(encoded(requirement)),
            "fit_count": 0,
            "approval_granted": False,
        }
    else:
        result = run()
    print(encoded(result).decode(), end="")


if __name__ == "__main__":
    main()
