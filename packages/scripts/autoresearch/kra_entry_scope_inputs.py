"""Read-only whole-card input preflight for the two frozen API26-based arms."""

import argparse
import json
from datetime import timedelta
from pathlib import Path

from autoresearch import local_m0_inference as inference
from autoresearch.kra_entry_scope_intake import FORMAT as INTAKE_FORMAT
from autoresearch.kra_entry_scope_intake import (
    _pinned,
    _scope_evidence,
    _utc,
    now,
    plan_intake,
)
from autoresearch.kra_schedule_snapshot import FEATURE_CUTOFF_MINUTES
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import encoded, parse_json

FORMAT = "kra-api26-scope-input-preflight-v1"


def _source(root, planned, result, *, window, reserved_at, completed, cutoff):
    if encoded({key: result.get(key) for key in planned}) != encoded(planned):
        raise ValueError("scope_inputs_unexpected_scope")
    reuse = planned.get("reused_source")
    if reuse is not None:
        if (
            result["state"] != "reused"
            or result["requests"] != []
            or "capture" in result
        ):
            raise ValueError("scope_inputs_reuse_conflict")
        source = reuse
    else:
        if result["state"] != "captured":
            raise ValueError("scope_inputs_incomplete_scope")
        path, _ = _pinned(root, result["capture"])
        if not path.is_relative_to(window / "entries"):
            raise ValueError("scope_inputs_capture_outside_reservation")
        source = _scope_evidence(
            root, planned, result["capture"], observed=completed, cutoff=cutoff
        )
        requests = result["requests"]
        if (
            len(requests) != len(source["pages"])
            or len(requests) != planned["request_page_limit"]
        ):
            raise ValueError("scope_inputs_request_count_conflict")
        previous = reserved_at
        for page_no, (request, page) in enumerate(
            zip(requests, source["pages"], strict=True), 1
        ):
            start = timestamp(request["started_at"])
            end = timestamp(request["completed_at"])
            collected = timestamp(page["collected_at"])
            if (
                request["page_no"] != page_no
                or request["http_status"] != 200
                or request["gateway_result_code"] != "00"
                or not previous <= start <= end <= collected <= completed
            ):
                raise ValueError("scope_inputs_request_evidence_conflict")
            previous = collected
    if source != result["evidence"]:
        raise ValueError("scope_inputs_source_evidence_conflict")
    return source


def preflight(
    root: Path,
    receipt_reference: dict,
    *,
    schedule_sha256: str,
    first_cutoff: str,
    clock=now,
) -> dict:
    """Return every projected race, or fail without a partial input package."""
    started = _utc(clock())
    cutoff = timestamp(first_cutoff)
    if started >= cutoff:
        raise ValueError("scope_inputs_receipt_or_readback_outside_deadline")
    root = root.resolve()
    receipt_path, raw = _pinned(root, receipt_reference)
    receipt = parse_json(raw)
    if (
        receipt["format"] != INTAKE_FORMAT
        or receipt["status"] != "captured_locally"
        or receipt["stop_reason"] is not None
        or receipt["study_registered"] is not False
        or receipt["independent_publication_verified"] is not False
    ):
        raise ValueError("scope_inputs_requires_complete_local_receipt")

    path, raw = _pinned(root, receipt["reservation"])
    if receipt_path.name != "receipt.json" or path != receipt_path.with_name(
        "reservation.json"
    ):
        raise ValueError("scope_inputs_reservation_path_conflict")
    reservation = parse_json(raw)
    if timestamp(reservation["first_block_cutoff"]) != cutoff:
        raise ValueError("scope_inputs_original_cutoff_conflict")
    if reservation["schedule"]["sha256"] != schedule_sha256:
        raise ValueError("scope_inputs_original_schedule_conflict")
    reserved_at = timestamp(reservation.pop("reserved_at"))
    completed = timestamp(receipt["completed_at"])
    if not reserved_at <= completed <= started < cutoff:
        raise ValueError("scope_inputs_receipt_or_readback_outside_deadline")

    reuse = [
        s["reused_source"]["manifest"]
        for s in reservation["scopes"]
        if "reused_source" in s
    ]
    plan = plan_intake(
        root,
        reservation["schedule"],
        reservation["race_dates"],
        first_cutoff=first_cutoff,
        reuse=reuse,
        observed=reserved_at,
    )
    if encoded(reservation) != encoded(plan) or len(receipt["scopes"]) != len(
        plan["scopes"]
    ):
        raise ValueError("scope_inputs_reservation_does_not_replay")

    missing = dict.fromkeys(inference.API_FIELDS, 0)
    bindings = []
    request_count = 0
    for scope, result in zip(plan["scopes"], receipt["scopes"], strict=True):
        source = _source(
            root,
            scope,
            result,
            window=receipt_path.parent,
            reserved_at=reserved_at,
            completed=completed,
            cutoff=cutoff,
        )
        request_count += len(result["requests"])
        ref = source["manifest"]
        for item in scope["races"]:
            race = item | {
                "race_date": scope["race_date"],
                "meet": scope["meet"],
                "feature_cutoff_at": (
                    timestamp(item["scheduled_start_at"])
                    - timedelta(minutes=FEATURE_CUTOFF_MINUTES)
                ).isoformat(),
            }
            try:
                projected = inference.project_capture(
                    race, Path(ref["path"]), root, expected_sha256=ref["sha256"]
                )
            except ValueError as exc:
                raise ValueError(
                    f"scope_inputs_invalid_features:{race['race_id']}:{exc}"
                ) from exc
            for row in projected["feature_rows"]:
                for field in missing:
                    missing[field] += int(row["features"][f"{field}_missing"])
            bindings.append(
                {"race": race, "entry_manifest": ref, "shared_input": projected}
            )
    if request_count != receipt["actual_http_requests"]:
        raise ValueError("scope_inputs_request_count_conflict")
    finished = _utc(clock())
    if not started <= finished < cutoff:
        raise ValueError("scope_inputs_receipt_or_readback_outside_deadline")
    return {
        "format": FORMAT,
        "status": "verified_local_inputs_only",
        "intake_receipt": {
            "path": str(receipt_path.relative_to(root)),
            "sha256": receipt_reference["sha256"],
        },
        "schedule": plan["schedule"],
        "race_dates": plan["race_dates"],
        "first_block_cutoff": plan["first_block_cutoff"],
        "local_readback_at": finished.isoformat(),
        "race_count": plan["race_count"],
        "declaration_count": sum(s["runner_count"] for s in plan["scopes"]),
        "feature_missing_counts": missing,
        "bindings": bindings,
        "http_requests_made": 0,
        "study_registered": False,
        "independent_publication_verified": False,
        "predictions_computed": False,
    }


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--receipt", required=True)
    cli.add_argument("--receipt-sha256", required=True)
    cli.add_argument("--schedule-sha256", required=True)
    cli.add_argument("--first-cutoff", required=True)
    args = cli.parse_args(argv)
    ref = {"path": args.receipt, "sha256": args.receipt_sha256}
    result = preflight(
        Path.cwd(),
        ref,
        schedule_sha256=args.schedule_sha256,
        first_cutoff=args.first_cutoff,
    )
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
