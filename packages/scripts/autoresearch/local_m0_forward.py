"""Local research run/resume for a fixed M0 arm; not independent registration."""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from shared.kra_entry_sheet import build_entry_snapshot

from autoresearch import local_m0_inference as inference
from autoresearch.kra_entry_sheet_snapshot import collect_entry_sheet_snapshot
from autoresearch.kra_schedule_snapshot import (
    _write_new,
    collect_schedule_snapshot,
    freeze_universe_candidate,
    replay_schedule_snapshot,
)
from autoresearch.observed_history_seed import exclusive
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import ROOT, encoded, implementation


def now():
    return datetime.now(UTC)


def read(path: Path) -> dict:
    return inference.parse_json(
        inference.read_bytes(path, limit=inference.MAX_MANIFEST_BYTES)
    )


def save(path: Path, value: dict) -> str:
    raw = encoded(value)
    _write_new(path, raw)
    return inference.sha256(raw)


def contract() -> dict:
    code = implementation()
    for module in (
        "local_m0_forward.py",
        "local_m0_inference.py",
        "kra_schedule_snapshot.py",
        "observed_history_seed.py",
    ):
        code["source_sha256"][f"autoresearch/{module}"] = inference.sha256(
            (ROOT / "packages/scripts/autoresearch" / module).read_bytes()
        )
    code["source_sha256"]["shared/kra_schedule.py"] = inference.sha256(
        (ROOT / "packages/scripts/shared/kra_schedule.py").read_bytes()
    )
    return {
        "format_version": "kra-local-m0-contract-v1",
        "series": inference.SERIES,
        "race_dates": list(inference.DATES),
        "arm": "M0",
        "model_sha256": inference.MODEL_SHA,
        "fit_receipt_sha256": inference.RECEIPT_SHA,
        "review_sha256": inference.REVIEW_SHA,
        "implementation": code,
        "cutoff_minutes": 30,
        "selection": "one_unordered_three_first_valid_capture_no_fallback",
        "population": "all_reconciled_national_races_each_declared_date",
        "input_attempt_policy": "one_capture_per_unsealed_race_per_invocation_before_cutoff",
        "fallback": "none_invalid_input_is_missing_prediction_in_full_population",
        "outcomes": "not_joined_here_no_ordinary_outcome_subset_accuracy",
        "trust": "local_owner_and_system_clock_not_independent_registration",
        "counts_as_70_percent_evidence": False,
        "model_promoted": False,
    }


def scheduled_races(report: dict) -> list[dict]:
    if report["status"] != "reconciled" or report["source_failures"]:
        raise ValueError("local_m0_unreconciled_schedule")
    return [
        {
            **r["source_observations"]["national"],
            "feature_cutoff_at": (
                timestamp(r["source_observations"]["national"]["scheduled_start_at"])
                - timedelta(minutes=30)
            ).isoformat(),
            "source_observations": r["source_observations"],
        }
        for r in report["races"]
    ]


def verify_study(study: dict, expected_contract: str) -> None:
    universe = study["universe"]
    date = universe["race_date"]
    if date not in inference.DATES or study["contract_sha256"] != expected_contract:
        raise ValueError("local_m0_study_contract_conflict")
    report = replay_schedule_snapshot(Path(study["schedule_capture"]), race_date=date)
    if (
        report["capture_manifest_sha256"] != universe["capture_manifest_sha256"]
        or scheduled_races(report) != universe["races"]
        or universe["race_count"] != len(universe["races"])
        or not timestamp(report["capture_completed_at"])
        <= timestamp(universe["frozen_at"])
        <= timestamp(study["created_at"])
        < min(timestamp(r["feature_cutoff_at"]) for r in universe["races"])
    ):
        raise ValueError("local_m0_frozen_population_conflict")


def packet_for(model: dict, race: dict, projected: dict, study_sha: str, completed):
    return {
        "format_version": "kra-local-m0-packet-v1",
        "series": inference.SERIES,
        "model_sha256": inference.MODEL_SHA,
        "study_sha256": study_sha,
        "feature_cutoff_at": race["feature_cutoff_at"],
        "computed_at": completed.isoformat(),
        "prediction": inference.score_capture(model, projected),
        "independent_timestamp_verified": False,
        "counts_as_70_percent_evidence": False,
    }


def recover_packet(path, race, model, receipt, root, study_sha):
    packet = read(path)
    source = packet["prediction"]["source"]
    projected = inference.project_capture(
        race,
        Path(source["manifest_path"]),
        root,
        expected_sha256=source["manifest_sha256"],
    )
    completed = timestamp(packet["computed_at"])
    inference.check_prospective_times(race, projected, receipt, completed)
    if packet != packet_for(model, race, projected, study_sha, completed):
        raise ValueError("local_m0_saved_packet_conflict")
    return packet


def observe_packet(
    path: Path, observation_path: Path, cutoff: str, *, time_key="computed_at"
) -> dict:
    # Observe complete bytes after publication; a late retry cannot backdate this.
    raw = inference.read_bytes(path, limit=inference.MAX_MANIFEST_BYTES)
    digest = inference.sha256(raw)
    computed = timestamp(inference.parse_json(raw)[time_key])
    if observation_path.exists():
        observation = read(observation_path)
    else:
        observed = now()
        if observed < computed:
            raise ValueError("local_m0_clock_moved_backwards")
        observation = {"packet_sha256": digest, "observed_at": observed.isoformat()}
        save(observation_path, observation)
    if (
        observation["packet_sha256"] != digest
        or not computed <= timestamp(observation["observed_at"]) <= now()
    ):
        raise ValueError("local_m0_observation_conflict")
    return {
        **observation,
        "status": "locally_observed_before_cutoff"
        if timestamp(observation["observed_at"]) < timestamp(cutoff)
        else "local_persistence_timeliness_unproven",
        "independent_timestamp_verified": False,
    }


async def run_day(root: Path, date: str, contract_sha: str, model, receipt, key_path):
    directory = root / date
    directory.mkdir(exist_ok=True)
    study_path = directory / "study.json"
    if study_path.exists():
        study = read(study_path)
    else:
        captured = await collect_schedule_snapshot(output_dir=directory / "schedules")
        report = replay_schedule_snapshot(captured, race_date=date)
        if report["status"] != "reconciled" or report["source_failures"]:
            return {
                "race_date": date,
                "status": "awaiting_card",
                "schedule_capture": str(captured),
                "schedule_status": report["status"],
                "race_count": None,
                "ledger": [],
            }
        candidate = directory / f"candidate_{now().strftime('%Y%m%dT%H%M%S%f')}.json"
        freeze_universe_candidate(captured, race_date=date, output=candidate)
        study = {
            "contract_sha256": contract_sha,
            "schedule_capture": str(captured),
            "universe": read(candidate),
            "created_at": now().isoformat(),
        }
        verify_study(study, contract_sha)
        save(study_path, study)
    verify_study(study, contract_sha)
    study_sha = inference.sha256(encoded(study))
    population_observation = observe_packet(
        study_path,
        directory / "study_observation.json",
        min(r["feature_cutoff_at"] for r in study["universe"]["races"]),
        time_key="created_at",
    )
    rows = []
    for race in sorted(
        study["universe"]["races"],
        key=lambda r: (timestamp(r["feature_cutoff_at"]), r["race_id"]),
    ):
        row = {"race_id": race["race_id"], "status": "missing_prediction"}
        path = directory / f"prediction_{race['race_id']}.json"
        try:
            if population_observation["status"] != "locally_observed_before_cutoff":
                raise ValueError("local_m0_population_persistence_unproven")
            if path.exists():
                packet = recover_packet(path, race, model, receipt, root, study_sha)
            else:
                if now() >= timestamp(race["feature_cutoff_at"]):
                    raise ValueError("local_m0_deadline_passed")
                pending_path = directory / f"input_{race['race_id']}.json"
                if pending_path.exists():
                    source = read(pending_path)
                    if source["study_sha256"] != study_sha:
                        raise ValueError("local_m0_pending_input_conflict")
                    projected = inference.project_capture(
                        race,
                        Path(source["manifest_path"]),
                        root,
                        expected_sha256=source["manifest_sha256"],
                    )
                else:
                    credentials = {"api_key": key_path.read_text()}
                    remaining = (
                        timestamp(race["feature_cutoff_at"]) - now()
                    ).total_seconds()
                    async with asyncio.timeout(min(60, max(0, remaining))):
                        capture = await collect_entry_sheet_snapshot(
                            **{k: race[k] for k in ("meet", "race_date", "race_no")},
                            **credentials,
                            output_dir=directory / "entries",
                        )
                    projected = inference.project_capture(
                        race, Path(capture["manifest_path"]), root
                    )
                    save(
                        pending_path,
                        {
                            "study_sha256": study_sha,
                            "manifest_path": projected["source"]["manifest_path"],
                            "manifest_sha256": projected["source"]["manifest_sha256"],
                        },
                    )
                # Score first, then check completion against the fixed deadline.
                packet = packet_for(model, race, projected, study_sha, now())
                completed = now()
                inference.check_prospective_times(race, projected, receipt, completed)
                packet["computed_at"] = completed.isoformat()
                save(path, packet)
            observation = observe_packet(
                path,
                directory / f"observation_{race['race_id']}.json",
                race["feature_cutoff_at"],
            )
            row.update(
                **observation,
                horse_ids=packet["prediction"]["horse_ids"],
                prediction_path=str(path),
            )
        except (ValueError, KeyError, TypeError, OSError, TimeoutError) as exc:
            row.update(error_type=type(exc).__name__)
            if isinstance(exc, ValueError):
                row["reason"] = str(exc)
        rows.append(row)
    return {
        "race_date": date,
        "status": "locally_complete"
        if all(r["status"] == "locally_observed_before_cutoff" for r in rows)
        else "incomplete",
        "race_count": len(study["universe"]["races"]),
        "study_sha256": study_sha,
        "population_observation": population_observation,
        "ledger": rows,
    }


async def run(root: Path, model_dir: Path, key_path: Path) -> dict:
    root = root.resolve() / inference.SERIES
    root.mkdir(parents=True, exist_ok=True)
    with exclusive(root):
        model, receipt = inference.load_model(model_dir)
        current = contract()
        path = root / "contract.json"
        if path.exists():
            if read(path) != current:
                raise ValueError("local_m0_series_contract_changed")
        else:
            save(path, current)
        digest = inference.sha256(encoded(current))
        days = []
        for date in inference.DATES:
            try:
                days.append(await run_day(root, date, digest, model, receipt, key_path))
            except (ValueError, KeyError, TypeError, OSError, TimeoutError) as exc:
                days.append(
                    {
                        "race_date": date,
                        "status": "failed",
                        "error_type": type(exc).__name__,
                    }
                )
        report = {
            "series": inference.SERIES,
            "contract_sha256": digest,
            "completed_at": now().isoformat(),
            "days": days,
            "model_promoted": False,
            "counts_as_70_percent_evidence": False,
            "independent_timestamp_verified": False,
        }
        attempt = now().strftime("%Y%m%dT%H%M%S%f")
        commitment = commitment_manifest(root, digest, days)
        report["commitment_path"] = str(root / f"commitment_{attempt}.json")
        report["commitment_sha256"] = save(Path(report["commitment_path"]), commitment)
        report["block_membership_status"] = commitment["block_membership_status"]
        save(root / f"run_{attempt}.json", report)
        return report


def commitment_manifest(root: Path, contract_sha: str, days: list[dict]) -> dict:
    """Hashes ready for publication, never a claim that publication happened."""
    records, starts, observed = [], [], []
    for day in days:
        item = {
            "race_date": day["race_date"],
            "status": day["status"],
            "race_count": day.get("race_count"),
        }
        study_path = root / day["race_date"] / "study.json"
        if day.get("study_sha256"):
            study = read(study_path)
            starts.extend(
                timestamp(r["feature_cutoff_at"]) for r in study["universe"]["races"]
            )
            observed.append(timestamp(day["population_observation"]["observed_at"]))
            item["study_sha256"] = day["study_sha256"]
            item["study_observation_sha256"] = inference.sha256(
                (study_path.parent / "study_observation.json").read_bytes()
            )
            item["races"] = []
            for row in day["ledger"]:
                slot = {"race_id": row["race_id"], "status": row["status"]}
                packet_path = study_path.parent / f"prediction_{row['race_id']}.json"
                # Even an invalid/unobserved occupied slot remains publicly visible.
                if packet_path.exists():
                    slot["packet_sha256"] = inference.sha256(packet_path.read_bytes())
                observation_path = (
                    study_path.parent / f"observation_{row['race_id']}.json"
                )
                if observation_path.exists():
                    slot["observation_sha256"] = inference.sha256(
                        observation_path.read_bytes()
                    )
                item["races"].append(slot)
        records.append(item)
    whole = len(observed) == len(inference.DATES) and bool(starts)
    return {
        "format_version": "kra-local-m0-commitment-v1",
        "series": inference.SERIES,
        "contract_sha256": contract_sha,
        "model_sha256": inference.MODEL_SHA,
        "block_membership_status": "locally_frozen_before_first_block_cutoff"
        if whole and max(observed) < min(starts)
        else "complete_block_freeze_not_proven",
        "days": records,
        "external_publication_verified": False,
        "independent_timestamp_verified": False,
        "counts_as_70_percent_evidence": False,
    }


def rehearse_inventory(plan: dict, model: dict, entries: dict) -> list[dict]:
    output, seen = [], set()
    for identity in plan.get("roster_inventory", []):
        key = identity["race_id"]
        if key in seen:
            raise ValueError("local_m0_duplicate_inventory_race")
        seen.add(key)
        row = {"race_id": key, "status": "missing_input"}
        source = entries.get((identity["race_date"], identity["meet"]))
        try:
            if source is not None:
                path = inference.archive_path(
                    Path(source["path"]), archive_root=Path(plan["entry_archive_root"])
                )
                raw, manifest, _ = inference.replay_entry_pages(
                    path,
                    archive_root=Path(plan["entry_archive_root"]),
                    meet=identity["meet"],
                    race_date=identity["race_date"],
                    expected_sha256=source["sha256"],
                )
                snapshot = build_entry_snapshot(
                    raw,
                    **{k: identity[k] for k in ("meet", "race_date", "race_no")},
                    collected_at=timestamp(manifest["collected_at"]),
                )
                start = datetime.strptime(
                    identity["race_date"] + snapshot["scheduled_start_time"],
                    "%Y%m%d%H%M",
                ).replace(tzinfo=ZoneInfo("Asia/Seoul"))
                race = {
                    **identity,
                    "runners": len(snapshot["entries"]),
                    "scheduled_start_at": start.isoformat(),
                }
                projected = inference.project_capture(
                    race,
                    path,
                    Path(plan["entry_archive_root"]),
                    expected_sha256=source["sha256"],
                )
                row.update(
                    status="rehearsed",
                    prediction=inference.score_capture(model, projected),
                )
        except (ValueError, KeyError, TypeError, OSError) as exc:
            row.update(status="input_conflict", error_type=type(exc).__name__)
            if isinstance(exc, ValueError):
                row["reason"] = str(exc)
        output.append(row)
    return output


def rehearse(plan_path: Path, plan_sha: str, model_dir: Path) -> dict:
    plan = inference.pinned_json(plan_path, plan_sha)
    if plan.get("roster_inventory"):
        source = plan["inventory_source_plan"]
        original = inference.pinned_json(Path(source["path"]), source["sha256"])
        expected = [
            {key: race[key] for key in ("race_id", "race_date", "meet", "race_no")}
            for race in original["races"]
        ]
        if expected != plan["roster_inventory"]:
            raise ValueError("local_m0_original_inventory_membership_mismatch")
    model, _ = inference.load_model(model_dir)
    entries = {}
    for item in plan["entry_captures"]:
        key = (item["race_date"], item["meet"])
        if key in entries:
            raise ValueError("local_m0_duplicate_rehearsal_source")
        entries[key] = item
    days, seen = [], set()
    for item in plan["schedule_captures"]:
        date = item["race_date"]
        if date in seen:
            raise ValueError("local_m0_duplicate_rehearsal_date")
        seen.add(date)
        inference.pinned_json(Path(item["path"]), item["sha256"])
        report = replay_schedule_snapshot(Path(item["path"]), race_date=date)
        rows = []
        for race in scheduled_races(report):
            row = {"race_id": race["race_id"], "status": "missing_input"}
            try:
                source = entries.get((date, race["meet"]))
                if source is not None:
                    projected = inference.project_capture(
                        race,
                        Path(source["path"]),
                        Path(plan["entry_archive_root"]),
                        expected_sha256=source["sha256"],
                    )
                    row.update(
                        status="rehearsed",
                        prediction=inference.score_capture(model, projected),
                    )
            except (ValueError, KeyError, TypeError, OSError) as exc:
                row.update(status="input_conflict", error_type=type(exc).__name__)
                if isinstance(exc, ValueError):
                    row["reason"] = str(exc)
            rows.append(row)
        days.append({"race_date": date, "race_count": len(rows), "ledger": rows})
    return {
        "format_version": "kra-local-m0-rehearsal-v1",
        "plan_sha256": plan_sha,
        "model_sha256": inference.MODEL_SHA,
        "days": days,
        "inventory_scope": "separate_api_source_inventory_not_national_population",
        "inventory": rehearse_inventory(plan, model, entries),
        "status": "historical_source_software_rehearsal_not_prediction",
        "model_fitted_after_targets": True,
        "counts_as_70_percent_evidence": False,
        "prediction_registration_verified": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    live = commands.add_parser("run")
    live.add_argument("--archive", type=Path, required=True)
    live.add_argument("--api-key-file", type=Path, required=True)
    replay = commands.add_parser("rehearse")
    replay.add_argument("--plan", type=Path, required=True)
    replay.add_argument("--plan-sha256", required=True)
    replay.add_argument("--output", type=Path, required=True)
    for command in (live, replay):
        command.add_argument("--model-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "run":
        result = asyncio.run(run(args.archive, args.model_dir, args.api_key_file))
        summary = result
    else:
        result = rehearse(args.plan, args.plan_sha256, args.model_dir)
        pin = save(args.output, result)
        summary = {
            "output": str(args.output),
            "sha256": pin,
            "status": result["status"],
            "days": [
                {
                    "race_date": d["race_date"],
                    "race_count": d["race_count"],
                    "statuses": dict(Counter(r["status"] for r in d["ledger"])),
                }
                for d in result["days"]
            ],
            "counts_as_70_percent_evidence": False,
        }
    print(encoded(summary).decode())
    return (
        0
        if args.command == "rehearse"
        or all(d["status"] == "locally_complete" for d in result["days"])
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
