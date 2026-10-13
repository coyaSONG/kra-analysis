"""Recover API26 race conditions without changing any frozen prediction model."""

from __future__ import annotations

import argparse
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from shared.kra_entry_sheet import build_entry_snapshot

from autoresearch.kra_race_card_pdf_replay import (
    MAX_MANIFEST_BYTES,
    archive_path,
    parse_json,
    read_bytes,
    replay_entry_pages,
    sha256,
)
from autoresearch.observed_history_seed import save
from autoresearch.prerace_hash_witness import (
    DOCUMENT,
    audit_archive,
    collect_publication,
    timestamp,
)
from autoresearch.race_conditions import CLASS

PLAN_SHA = "0ac4a309d07901d6f4da8c4503c937fee9529fb5e05871cfdcd5252116a52be0"
BUNDLE_SHA = "8061a185401bf72c4bfee2751529acb164b695eb2985dbf4d6a43e187a8ecdd6"
COMPARISON_SHA = "818f0be674ef148b9c83e46192a52686be1e5ba2805b5daf8c601134aaaa6123"


def distance_value(value):
    if type(value) is int:
        number = value
    elif isinstance(value, str) and re.fullmatch(r"[0-9]{3,4}", value):
        number = int(value)
    else:
        return None
    return number if 500 <= number <= 5000 else None


def class_value(value):
    return value if isinstance(value, str) and CLASS.fullmatch(value) else None


def unanimous(rows, key, parser):
    raw = [{"chul_no": int(r["chulNo"]), "value": r.get(key)} for r in rows]
    values = [parser(r["value"]) for r in raw]
    reason = None
    if any(value is None for value in values):
        reason = "missing_or_invalid_runner_value"
    elif len(set(values)) != 1:
        reason = "conflicting_runner_values"
    return {
        "status": "unknown" if reason else "observed",
        "value": None if reason else values[0],
        "reason": reason,
        "source_key": key,
        "raw_values": raw,
    }


def project_conditions(rows, *, meet, race_date, race_no, collected_at):
    snapshot = build_entry_snapshot(
        rows,
        meet=meet,
        race_date=race_date,
        race_no=race_no,
        collected_at=collected_at,
    )
    selected = sorted(
        (r for r in rows if int(r["rcNo"]) == race_no),
        key=lambda r: int(r["chulNo"]),
    )
    start = datetime.strptime(
        race_date + snapshot["scheduled_start_time"], "%Y%m%d%H%M"
    ).replace(tzinfo=ZoneInfo("Asia/Seoul"))
    return {
        "race_id": f"{race_date}_{meet}_{race_no}",
        "meet": meet,
        "runner_count": len(snapshot["entries"]),
        "roster": snapshot["entries"],
        "captured_at": snapshot["collected_at"],
        "cutoff": (start - timedelta(minutes=30)).isoformat(),
        "distance_m": unanimous(selected, "rcDist", distance_value),
        "class_text": unanimous(selected, "rank", class_value),
    }


def source_available(projected, audit, witness):
    if projected["race_id"] != audit["race_id"]:
        raise ValueError("condition_audit_identity_mismatch")
    published = timestamp(witness["merged_at"])
    return all(
        audit.get(key) is True
        for key in (
            "raw_chain_verified",
            "content_bound_before_cutoff",
            "feature_projection_matches_publication",
        )
    ) and (
        timestamp(projected["captured_at"])
        <= published
        < timestamp(projected["cutoff"])
    )


def compare_conditions(projected, historical):
    """Never copy retrospective values into the independently projected inputs."""
    if historical and historical["race_id"] != projected["race_id"]:
        raise ValueError("condition_comparison_identity_mismatch")
    comparisons = {}
    for key in ("distance_m", "class_text"):
        actual = projected[key]
        expected = historical.get(key) if historical else None
        state = "not_comparable"
        if (
            actual["status"] == "observed"
            and historical
            and historical["status"] == "observed"
        ):
            state = "match" if actual["value"] == expected else "conflict"
        comparisons[key] = {"state": state, "historical_value": expected}
    return comparisons


def pinned_bytes(path, expected):
    content = read_bytes(path, limit=64 * MAX_MANIFEST_BYTES)
    if sha256(content) != expected:
        raise ValueError("condition_input_hash_mismatch")
    return content


def run(plan_path, bundle_path, root, comparison_path, directory):
    plan_bytes = pinned_bytes(plan_path, PLAN_SHA)
    bundle_bytes = pinned_bytes(bundle_path, BUNDLE_SHA)
    historical = parse_json(pinned_bytes(comparison_path, COMPARISON_SHA))["records"]
    plan = parse_json(plan_bytes)
    directory.mkdir(parents=True, exist_ok=False)
    with httpx.Client(timeout=30, follow_redirects=False, trust_env=False) as client:
        document, witness = collect_publication(
            directory, number=61, document=DOCUMENT, client=client
        )
    audit = audit_archive(
        plan_bytes=plan_bytes,
        bundle_bytes=bundle_bytes,
        document_bytes=document,
        witness=witness,
        archive_root=root,
    )
    audited = {r["race_id"]: r for r in audit["ledger"]}
    ledger = []
    for record in sorted(plan["races"], key=lambda r: r["race_id"]):
        identity = record["race_id"]
        proof = audited[identity]
        path = archive_path(
            proof["evidence"]["entry"]["manifest_path"], archive_root=root
        )
        rows, manifest, evidence = replay_entry_pages(
            path,
            archive_root=root,
            meet=record["meet"],
            race_date=record["race_date"],
            expected_sha256=record["entry_manifest_sha256"],
        )
        projected = project_conditions(
            rows,
            **{k: record[k] for k in ("meet", "race_date", "race_no")},
            collected_at=timestamp(manifest["collected_at"]),
        )
        ledger.append(
            {
                **projected,
                "source": evidence,
                "source_content_available_before_cutoff": source_available(
                    projected, proof, witness
                ),
                "original_pdf_audit_reasons": proof["reasons"],
                "comparison": compare_conditions(projected, historical.get(identity)),
            }
        )
    report = {
        "format_version": "kra-original-prerace-conditions-v1",
        "scope": "original_28_race_capture_inventory_not_full_national_universe",
        "plan_sha256": PLAN_SHA,
        "bundle_sha256": BUNDLE_SHA,
        "comparison_sha256": COMPARISON_SHA,
        "comparison_basis": "pinned_retrospective_condition_artifact_not_prerace_input",
        "implementation_sha256": sha256(Path(__file__).read_bytes()),
        "publication": witness,
        "witness_audit": audit,
        "race_count": len(ledger),
        "runner_count": sum(r["runner_count"] for r in ledger),
        "source_available_race_count": sum(
            r["source_content_available_before_cutoff"] for r in ledger
        ),
        "field_status_counts": {
            k: dict(Counter(r[k]["status"] for r in ledger))
            for k in ("distance_m", "class_text")
        },
        "comparison_counts": {
            k: dict(Counter(r["comparison"][k]["state"] for r in ledger))
            for k in ("distance_m", "class_text")
        },
        "ledger": ledger,
        "training_approved": False,
        "model_fit_performed": False,
        "model_promoted": False,
        "counts_as_70_percent_evidence": False,
    }
    digest = save(directory / "report.json", report)
    return {
        "report_path": str(directory / "report.json"),
        "sha256": digest,
        **{
            k: report[k]
            for k in (
                "race_count",
                "runner_count",
                "source_available_race_count",
                "field_status_counts",
                "comparison_counts",
            )
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "bundle", "archive-root", "comparison", "output-dir"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    args = parser.parse_args()
    print(
        run(args.plan, args.bundle, args.archive_root, args.comparison, args.output_dir)
    )


if __name__ == "__main__":
    main()
