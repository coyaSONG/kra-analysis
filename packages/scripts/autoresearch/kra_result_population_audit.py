"""Left-join result observations to pinned official schedules without scoring."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from autoresearch.kra_race_card_pdf_replay import parse_json
from autoresearch.kra_result_snapshot import replay_result_snapshot
from autoresearch.kra_schedule_snapshot import replay_schedule_snapshot


def reconcile_observations(
    scheduled: dict[str, int], records: list[dict[str, Any]]
) -> dict[str, Any]:
    if not scheduled:
        raise ValueError("empty_scheduled_population")
    grouped = defaultdict(list)
    identities = set()
    for row in records:
        key = (row["race_id"], row["chul_no"])
        if key in identities:
            raise ValueError("duplicate_population_runner")
        identities.add(key)
        grouped[row["race_id"]].append(row)
    ledger = []
    for key, count in sorted(scheduled.items()):
        rows = grouped.get(key, [])
        ledger.append(
            {
                "race_id": key,
                "scheduled_runner_count": count,
                "observed_runner_count": len(rows),
                "status": "missing_results"
                if not rows
                else "runner_count_mismatch"
                if len(rows) != count
                else "observed",
                "evidence_counts": dict(Counter(row["evidence"] for row in rows)),
                "exception_notes": dict(
                    Counter(
                        row["raw_ord_bigo"]
                        for row in rows
                        if row["raw_ord_bigo"] not in (None, "", "-")
                    )
                ),
            }
        )
    extras = sorted(set(grouped) - set(scheduled))
    return {
        "format_version": "kra-result-population-audit-v1",
        "scheduled_race_count": len(scheduled),
        "observed_race_count": len(grouped),
        "observed_runner_count": len(records),
        "missing_result_races": sorted(set(scheduled) - set(grouped)),
        "runner_count_mismatch_count": sum(
            r["status"] == "runner_count_mismatch" for r in ledger
        ),
        "extra_result_races": extras,
        "reconciled_observation_population": not extras
        and all(r["status"] == "observed" for r in ledger),
        "evidence_counts": dict(Counter(row["evidence"] for row in records)),
        "counts_as_70_percent_evidence": False,
        "historical_capture_only": True,
        "complete_actual_start_history_verified": False,
        "ledger": ledger,
    }


def audit_plan(path: Path) -> dict[str, Any]:
    original = path.read_bytes()
    plan = parse_json(original)
    if plan["format_version"] != "kra-result-population-plan-v1":
        raise ValueError("unsupported_result_population_plan")
    dates = plan["race_dates"]
    if not dates or len(set(dates)) != len(dates):
        raise ValueError("invalid_result_population_dates")
    scheduled, source_pins, rows = {}, [], []
    for day in dates:
        report = replay_schedule_snapshot(Path(plan["schedule_capture"]), race_date=day)
        if report["capture_manifest_sha256"] != plan["schedule_sha256"]:
            raise ValueError("schedule_pin_mismatch")
        if report["status"] != "reconciled" or report["source_failures"]:
            raise ValueError("unreconciled_official_schedule")
        for race in report["races"]:
            scheduled[race["race_id"]] = race["source_observations"]["national"][
                "runners"
            ]
    failures = []
    for source in plan["result_captures"]:
        try:
            report = replay_result_snapshot(
                Path(source["path"]),
                entry_capture=Path(source["entry_capture"])
                if source.get("entry_capture")
                else None,
                archive_root=Path(plan["archive_root"]),
            )
            if report["capture_manifest_sha256"] != source["sha256"]:
                raise ValueError("result_manifest_pin_mismatch")
            if (
                source.get("entry_capture")
                and report["entry_binding_pins"][0]["manifest_sha256"]
                != source["entry_sha256"]
            ):
                raise ValueError("result_entry_manifest_pin_mismatch")
            rows.extend(report["records"])
            source_pins.append(
                {
                    "path": source["path"],
                    **{k: v for k, v in report.items() if k != "records"},
                }
            )
        except (ValueError, OSError, KeyError, TypeError) as exc:
            failures.append({"path": source["path"], "error": str(exc)})
    result = reconcile_observations(scheduled, rows)
    if failures:
        result["reconciled_observation_population"] = False
    result.update(
        plan_sha256=hashlib.sha256(original).hexdigest(),
        source_pins=source_pins,
        source_failures=failures,
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = audit_plan(args.plan)
    content = json.dumps(result, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(content)
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in ("ledger", "source_pins")},
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["reconciled_observation_population"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
