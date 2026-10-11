"""Replay the original archive as unapproved API-only training candidates."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx
from shared.kra_entry_sheet import build_entry_snapshot

from autoresearch import local_m0_inference as inference
from autoresearch.local_m0_evaluation import OUTCOME_POLICY_SHA, OUTCOME_SOURCES_SHA
from autoresearch.observed_history_seed import save
from autoresearch.prerace_hash_witness import (
    DOCUMENT,
    audit_archive,
    collect_publication,
    timestamp,
)
from autoresearch.versioned_result_observations import replay_plan, value_hash

PLAN_SHA = "0ac4a309d07901d6f4da8c4503c937fee9529fb5e05871cfdcd5252116a52be0"
BUNDLE_SHA = "8061a185401bf72c4bfee2751529acb164b695eb2985dbf4d6a43e187a8ecdd6"
OUTCOME_PLAN_SHA = "314056646885d6112bbd392dcd7f8a20c2a934b03b6ab788090a270ee02be898"


def assess_race(projected, outcome, audit, cutoff, published):
    """Inputs are fresh raw-source replays, not user-supplied approval records."""
    reasons = []
    if not (
        audit["raw_chain_verified"] is True
        and audit["content_bound_before_cutoff"] is True
        and audit["feature_projection_matches_publication"] is True
    ):
        reasons.append("source_publication_chain_unverified")
    captured = timestamp(projected["source"]["available_at"])
    if not captured <= published < cutoff:
        reasons.append("capture_publication_cutoff_conflict")
    rows = projected["feature_rows"]
    expected = {(r["chul_no"], r["horse_id"]) for r in rows}
    records = outcome["api_records"] if outcome else []
    actual = {(r["chul_no"], r["horse_id"]) for r in records}
    exact = (
        outcome is not None
        and projected["race_id"] == outcome["race_id"] == audit["race_id"]
        and 3 <= len(rows) <= 20
        and len(expected) == len(rows) == len(actual) == len(records)
        and expected == actual
        and len({r["chul_no"] for r in rows}) == len(rows)
        and len({r["horse_id"] for r in rows}) == len(rows)
    )
    if not exact:
        reasons.append("whole_roster_label_join_conflict")
    top3 = outcome["observed_top3_horse_ids"] if outcome else None
    if not (
        outcome
        and outcome["status"] == "unique_top3_observed"
        and isinstance(top3, list)
        and len(top3) == len(set(top3)) == 3
        and set(top3) <= {r["horse_id"] for r in rows}
    ):
        reasons.append("unique_top3_not_observed")
    return {
        **projected,
        "cutoff": cutoff.isoformat(),
        "source_publication_bound": published.isoformat(),
        "whole_roster_label_join_exact": exact,
        "original_pdf_reasons": audit["reasons"],
        "result_status": outcome["status"] if outcome else "missing",
        "observed_top3": top3,
        "potential_unique_top3_training_candidate": not reasons,
        "reasons": reasons,
        "training_approved": False,
    }


def project_original(record, audit, root):
    entry = audit["evidence"]["entry"]
    path = inference.archive_path(entry["manifest_path"], archive_root=root)
    rows, manifest, _ = inference.replay_entry_pages(
        path,
        archive_root=root,
        meet=record["meet"],
        race_date=record["race_date"],
        expected_sha256=record["entry_manifest_sha256"],
    )
    snapshot = build_entry_snapshot(
        rows,
        **{k: record[k] for k in ("meet", "race_date", "race_no")},
        collected_at=timestamp(manifest["collected_at"]),
    )
    # Use the original captured schedule, never a later result-page start time.
    start = datetime.strptime(
        record["race_date"] + snapshot["scheduled_start_time"], "%Y%m%d%H%M"
    ).replace(tzinfo=ZoneInfo("Asia/Seoul"))
    projected = inference.project_capture(
        {
            **record,
            "runners": len(snapshot["entries"]),
            "scheduled_start_at": start.isoformat(),
        },
        path,
        root,
        expected_sha256=record["entry_manifest_sha256"],
    )
    return projected, start - timedelta(minutes=30)


def prepare(plan_path, bundle_path, outcome_path, root, directory):
    plan = inference.pinned_json(plan_path, PLAN_SHA)
    inference.pinned_json(bundle_path, BUNDLE_SHA)
    with httpx.Client(timeout=30, follow_redirects=False, trust_env=False) as client:
        document, witness = collect_publication(
            directory, number=61, document=DOCUMENT, client=client
        )
    audit = audit_archive(
        plan_bytes=inference.read_bytes(plan_path, limit=inference.MAX_MANIFEST_BYTES),
        bundle_bytes=inference.read_bytes(
            bundle_path, limit=inference.MAX_MANIFEST_BYTES
        ),
        document_bytes=document,
        witness=witness,
        archive_root=root,
    )
    if (
        audit["input_plan_sha256"] != PLAN_SHA
        or audit["feature_bundle_sha256"] != BUNDLE_SHA
    ):
        raise ValueError("opportunity_input_changed_during_replay")
    outcome = replay_plan(outcome_path, OUTCOME_PLAN_SHA)
    if (
        outcome["observation_policy_sha256"] != OUTCOME_POLICY_SHA
        or value_hash(outcome["observation_source_sha256"]) != OUTCOME_SOURCES_SHA
    ):
        raise ValueError("opportunity_outcome_policy_changed")
    evidence = {r["race_id"]: r for r in audit["ledger"]}
    results = {r["race_id"]: r for r in outcome["ledger"]}
    old = inference.pinned_json(inference.REVIEW_PATH, inference.REVIEW_SHA)
    published = timestamp(witness["merged_at"])
    ledger = []
    for record in sorted(plan["races"], key=lambda r: r["race_id"]):
        key = record["race_id"]
        projected, cutoff = project_original(record, evidence[key], root)
        ledger.append(
            assess_race(projected, results.get(key), evidence[key], cutoff, published)
            | {"original_training_selected": key in old["selected_race_ids"]}
        )
    candidates = [r for r in ledger if r["potential_unique_top3_training_candidate"]]
    return {
        "format_version": "kra-api-only-training-opportunity-v1",
        "scope": "original_28_race_capture_inventory_not_full_future_universe",
        "witness_audit": audit,
        "outcome_plan_sha256": OUTCOME_PLAN_SHA,
        "outcome_report_sha256": value_hash(outcome),
        "outcome_policy_sha256": OUTCOME_POLICY_SHA,
        "outcome_sources_sha256": OUTCOME_SOURCES_SHA,
        "implementation_sha256": inference.sha256(Path(__file__).read_bytes()),
        "inference_sha256": inference.sha256(Path(inference.__file__).read_bytes()),
        "old_review_sha256": inference.REVIEW_SHA,
        "race_count": len(ledger),
        "runner_count": sum(len(r["feature_rows"]) for r in ledger),
        "candidate_race_count": len(candidates),
        "candidate_runner_count": sum(len(r["feature_rows"]) for r in candidates),
        "additional_candidate_ids": [
            r["race_id"] for r in candidates if not r["original_training_selected"]
        ],
        "ledger": ledger,
        "training_approved": False,
        "model_fit_performed": False,
        "counts_as_70_percent_evidence": False,
        "official_finality_verified": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "bundle", "outcome-plan", "archive-root", "output-dir"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args(argv)
    directory = args.output_dir / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ") + "_" + uuid4().hex[:12]
    )
    directory.mkdir(parents=True)
    report = prepare(
        args.plan, args.bundle, args.outcome_plan, args.archive_root, directory
    )
    digest = save(directory / "report.json", report)
    print({"report_path": str(directory / "report.json"), "sha256": digest})
    print({k: v for k, v in report.items() if k.endswith("count")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
