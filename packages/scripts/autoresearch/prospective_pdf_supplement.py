"""Bounded supplementary PDF acquisition; never change frozen predictions."""

from __future__ import annotations

import asyncio
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

import httpx
from shared.kra_entry_sheet import build_entry_snapshot
from shared.kra_race_card_pdf import NUMERIC_FIELDS

from autoresearch import condition_delta_diagnostic as delta
from autoresearch import kra_race_card_pdf_bundle as bundle_tools
from autoresearch.kra_entry_sheet_snapshot import collect_entry_sheet_snapshot
from autoresearch.kra_race_card_pdf_replay import replay_entry_pages
from autoresearch.kra_race_card_pdf_snapshot import collect_race_card_pdf
from autoresearch.observed_history_seed import digest, save
from autoresearch.official_history_catalog import read_pin
from autoresearch.restricted_cohort import horse_id

ROOT = Path(".cache/autoresearch/prospective-pdf-supplement-20261015")
SUPPORTED = {1, 2, 3}


class RequestBudget:
    def __init__(self, cutoff, limit=60):
        self.cutoff, self.limit, self.count = cutoff, limit, 0

    async def __call__(self, request):
        if datetime.now(UTC) >= self.cutoff:
            raise ValueError("supplement_cutoff_reached")
        if self.count >= self.limit:
            raise ValueError("supplement_request_budget_exhausted")
        self.count += 1
        await asyncio.sleep(0.5)
        if datetime.now(UTC) >= self.cutoff:
            raise ValueError("supplement_cutoff_reached")


def finalize(targets, bundle):
    if not targets:
        raise ValueError("supplement_empty_population")
    expected = {k for k in targets if int(k.split("_")[1]) in SUPPORTED}
    races = {r["race_id"]: r for r in bundle["races"]}
    if len(races) != len(bundle["races"]) or set(races) != expected:
        raise ValueError("supplement_bundle_population_mismatch")
    grouped = defaultdict(list)
    for row in bundle["feature_rows"]:
        if row["race_id"] not in expected:
            raise ValueError("supplement_unexpected_feature_race")
        grouped[row["race_id"]].append(row)
    statuses, available = [], Counter(dict.fromkeys(NUMERIC_FIELDS, 0))
    for identity, roster in sorted(targets.items()):
        required = {(r["chul_no"], r["horse_id"]) for r in roster}
        if not roster or len(required) != len(roster):
            raise ValueError("supplement_invalid_target_roster")
        item = races.get(identity)
        exported = grouped[identity]
        eligible = item is not None and item["eligible_for_prerace_features"] is True
        if eligible:
            actual = {(r["chulNo"], horse_id(r["hrNo"])) for r in exported}
            if actual != required or len(actual) != len(exported):
                raise ValueError("supplement_frozen_roster_mismatch")
            for row in exported:
                for name in NUMERIC_FIELDS:
                    value = row["features"][name]
                    if row["features"][f"{name}_missing"] is not (value is None):
                        raise ValueError("supplement_missing_flag_mismatch")
                    available[name] += value is not None
        elif exported:
            raise ValueError("supplement_blocked_race_has_features")
        statuses.append(
            {
                "race_id": identity,
                "status": "eligible"
                if eligible
                else "blocked"
                if item
                else "unsupported_venue",
                "expected_runner_rows": len(roster),
                "feature_row_count": len(exported),
                "reasons": item["reasons"] if item else ["venue4_pdf_not_supported"],
            }
        )
    total = sum(map(len, targets.values()))
    exported = len(bundle["feature_rows"])
    return {
        "races": statuses,
        "race_count": len(targets),
        "expected_runner_rows": total,
        "exported_runner_rows": exported,
        "status_counts": dict(Counter(r["status"] for r in statuses)),
        "field_coverage": {
            field: {
                "observed": n,
                "missing_of_full_population": total - n,
                "missing_of_exported_rows": exported - n,
            }
            for field, n in available.items()
        },
    }


async def capture():
    public = {k: read_pin(delta.PUBLIC / k, v) for k, v in delta.PINS.items()}
    targets, _, _ = delta.load_targets(public["m0.json"])
    packets = {
        r["race_id"]: read_pin(
            delta.FORWARD / d["race_date"] / f"prediction_{r['race_id']}.json",
            r["packet_sha256"],
        )
        for d in public["m0.json"]["days"]
        for r in d["races"]
    }
    cutoff = min(
        datetime.fromisoformat(p["feature_cutoff_at"]) for p in packets.values()
    )
    if datetime.now(UTC) >= cutoff:
        raise ValueError("supplement_cutoff_reached")
    root = ROOT.resolve()
    root.mkdir(parents=True, exist_ok=False)
    captures = root / "captures"
    observations = {
        k: {"race_id": k, "manifest_path": None, "sha256": None}
        for k in targets
        if int(k.split("_")[1]) in SUPPORTED
    }
    units = sorted({(k[:8], int(k.split("_")[1])) for k in observations})
    plan_sha = save(
        root / "acquisition-plan.json",
        {
            "created_at": datetime.now(UTC).isoformat(),
            "first_cutoff": cutoff.isoformat(),
            "public_commitments": delta.PINS,
            "targets": targets,
            "units": units,
            "max_requests": 60,
            "retries": 0,
            "consecutive_pdf_failure_breaker": 3,
            "purpose": "supplementary_inputs_only_not_replacement_reservations",
            "implementation": bundle_tools.implementation_fingerprint(),
            "orchestration_sha256": digest(Path(__file__).read_bytes()),
        },
    )
    budget, attempts, consecutive = RequestBudget(cutoff), [], 0
    key = Path.home().joinpath(".codex/secrets/kra_api_key").read_text().strip()
    async with httpx.AsyncClient(
        timeout=30, follow_redirects=False, event_hooks={"request": [budget]}
    ) as client:
        for date, meet in units:
            first = f"{date}_{meet}_1"
            source = packets[first]["prediction"]["source"]
            old, _, _ = replay_entry_pages(
                Path(source["manifest_path"]),
                archive_root=delta.FORWARD.resolve(),
                meet=meet,
                race_date=date,
                expected_sha256=source["manifest_sha256"],
            )
            entry = await collect_entry_sheet_snapshot(
                meet=meet,
                race_date=date,
                race_no=1,
                api_key=key,
                output_dir=captures,
                client=client,
            )
            entry_path = Path(entry["manifest_path"])
            receipt = {
                "date": date,
                "meet": meet,
                "entry_manifest": str(entry_path),
                "entry_sha256": digest(entry_path.read_bytes()),
                "status": entry["collection_status"],
            }
            if entry.get("total_count") == 0:
                receipt["availability"] = "empty_unconfirmed"
            attempts.append(receipt)
            save(root / f"entry-check-{date}-{meet}.json", receipt)
            if entry["collection_status"] != "captured":
                break
            raw, _, _ = replay_entry_pages(
                entry_path,
                archive_root=root,
                meet=meet,
                race_date=date,
                expected_sha256=receipt["entry_sha256"],
            )
            receipt["identical_to_frozen_entry_rows"] = raw == old
            if raw != old:
                receipt["status"] = "frozen_entry_source_drift"
                break
            for identity in sorted(
                k for k in observations if k.startswith(f"{date}_{meet}_")
            ):
                number = int(identity.split("_")[2])
                entries = build_entry_snapshot(
                    raw,
                    meet=meet,
                    race_date=date,
                    race_no=number,
                    collected_at=datetime.fromisoformat(entry["collected_at"]),
                )
                entries["source_manifest_path"] = str(entry_path)
                observed = await collect_race_card_pdf(
                    meet=meet,
                    race_date=date,
                    race_no=number,
                    entries=entries,
                    scheduled_start_time=entries["scheduled_start_time"],
                    output_dir=captures,
                    client=client,
                )
                observations[identity] = {
                    k: observed[k] for k in ("race_id", "manifest_path", "sha256")
                }
                consecutive = (
                    0
                    if observed["collection_status"] == "captured"
                    else consecutive + 1
                )
                print(
                    identity,
                    observed["collection_status"],
                    observed["eligible_for_prerace_features"],
                    flush=True,
                )
                if consecutive >= 3 or datetime.now(UTC) >= cutoff:
                    break
            if consecutive >= 3 or datetime.now(UTC) >= cutoff:
                break
    cohort_path = root / "cohort.json"
    save(
        cohort_path,
        {
            "planned_meet_dates": [[m, d] for d, m in units],
            "observations": list(observations.values()),
        },
    )
    plan = bundle_tools.plan_from_cohort(cohort_path, archive_root=root)
    plan_pin = save(root / "input-plan.json", plan)
    bundle = bundle_tools.build_bundle(plan, archive_root=root)
    bundle_pin = save(root / "feature-bundle.json", bundle)
    report = {
        "format_version": "frozen-population-pdf-supplement-v1",
        "completed_at": datetime.now(UTC).isoformat(),
        "acquisition_plan_sha256": plan_sha,
        "input_plan_sha256": plan_pin,
        "feature_bundle_sha256": bundle_pin,
        "requests": budget.count,
        "entry_checks": attempts,
        "public_commitments_unchanged": delta.PINS,
        "training_approved": False,
        "target_outcomes_loaded": False,
        "predictions_modified": False,
        "new_evaluation_arm_registered": False,
        "counts_as_70_percent_evidence": False,
        "accuracy": None,
        **finalize(targets, bundle),
    }
    for k, v in delta.PINS.items():
        read_pin(delta.PUBLIC / k, v)
    sha = save(root / "report.json", report)
    print(sha, report["status_counts"], report["exported_runner_rows"], flush=True)


if __name__ == "__main__":
    asyncio.run(capture())
