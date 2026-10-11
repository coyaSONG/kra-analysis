"""Seal label-free future learning inputs, preserving the frozen M0 series."""

from __future__ import annotations

import argparse
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx

from autoresearch import local_m0_forward as forward
from autoresearch import local_m0_inference as inference
from autoresearch import official_history_recency as recency
from autoresearch.api_training_opportunity import PLAN_SHA, project_original
from autoresearch.kra_race_card_pdf_replay import replay_race_card_snapshot
from autoresearch.local_m0_evaluation import CONTRACT_SHA
from autoresearch.observed_history_seed import exclusive, pinned_path, save
from autoresearch.prerace_hash_witness import collect_publication, timestamp
from autoresearch.restricted_cohort import API_COLUMNS, ROOT, encoded
from autoresearch.versioned_result_observations import source_hashes

SEED_SHA = "0dbe7abe5bdfb0a0b422bb90bddbdf1a3face89e5016254807ba37be95c25c66"
ARCHIVE_SHA = "eaece57cdd27ee4e348e171e04368440da9d82a4417110476f0a1a1400e934e2"
HISTORY_DOCUMENT = "docs/research/2026-10-12-official-history-recency.md"
HISTORY_COMMIT = "cbd299b7f36e317a1583becaa376be9deca15e08"
HISTORY_COLUMNS = (*recency.FIELDS, *(f"{k}_missing" for k in recency.FIELDS))
COLUMNS = (*API_COLUMNS, *HISTORY_COLUMNS)
FORMAT = "kra-prospective-training-input-v1"


def now():
    return datetime.now(UTC)


def contract():
    sources = source_hashes()
    for name in (
        "autoresearch/prospective_training_inputs.py",
        "autoresearch/api_training_opportunity.py",
        "autoresearch/official_history_recency.py",
        "autoresearch/history_identity_audit.py",
        "shared/observed_partial_history.py",
        "shared/observed_result_history.py",
    ):
        sources[name] = inference.sha256(
            (ROOT / "packages/scripts" / name).read_bytes()
        )
    return {
        "format_version": FORMAT,
        "parent_series": inference.SERIES,
        "parent_contract_sha256": CONTRACT_SHA,
        "dates": list(inference.DATES),
        "columns": list(COLUMNS),
        "seed_sha256": SEED_SHA,
        "official_archive_sha256": ARCHIVE_SHA,
        "source_sha256": sources,
        "parent_implementation": forward.contract()["implementation"],
        "selection": "first_eligible_input_using_m0_selected_capture_no_replacement",
        "labels": "absent_later_versioned_sidecar_only",
        "training_approved": False,
        "counts_as_70_percent_evidence": False,
    }


def history_publication(directory):
    with httpx.Client(timeout=30, follow_redirects=False, trust_env=False) as client:
        raw, witness = collect_publication(
            directory, number=85, document=HISTORY_DOCUMENT, client=client
        )
    pins = set(re.findall(rb"(?<![a-f0-9])[a-f0-9]{64}(?![a-f0-9])", raw))
    if (
        witness["merge_commit_sha"] != HISTORY_COMMIT
        or not {SEED_SHA.encode(), ARCHIVE_SHA.encode()} <= pins
    ):
        raise ValueError("training_input_history_publication_conflict")
    return witness


def history_available_at(seed_path, history_root, projection):
    seed = inference.pinned_json(seed_path, SEED_SHA)
    clocks = [timestamp(seed["materialized_at"])]
    for unit in seed["inventory"]:
        for kind, field in (
            ("result", "capture_completed_at"),
            ("entry", "collected_at"),
        ):
            if unit.get(kind):
                capture = forward.read(pinned_path(history_root, unit[kind]))
                clocks.append(timestamp(capture[field]))
    base = projection["support_projection"]
    evidence = [g["evidence"] for g in base["groups"]]
    evidence.extend(base["official_lists"].values())
    clocks.extend(timestamp(item["capture"]["completed_at"]) for item in evidence)
    return max(clocks)


def join_features(projected, history):
    if projected["race_id"] != history["race_id"]:
        raise ValueError("training_input_history_race_mismatch")
    api, rows = projected["feature_rows"], history["feature_rows"]
    lookup = {(r["chul_no"], r["horse_id"]): r for r in rows}
    keys = {(r["chul_no"], r["horse_id"]) for r in api}
    if (
        not 3 <= len(api) <= 20
        or keys != set(lookup)
        or len(keys) != len(api)
        or len(lookup) != len(rows)
        or len({r["chul_no"] for r in api}) != len(api)
        or len({r["horse_id"] for r in api}) != len(api)
    ):
        raise ValueError("training_input_complete_roster_mismatch")
    output = []
    for row in sorted(api, key=lambda r: r["chul_no"]):
        if set(row["features"]) != set(API_COLUMNS):
            raise ValueError("training_input_api_columns_mismatch")
        match = lookup[row["chul_no"], row["horse_id"]]
        values = {k: match["features"][k] for k in HISTORY_COLUMNS}
        for name in recency.FIELDS:
            if type(values[name + "_missing"]) is not bool or values[
                name + "_missing"
            ] != (values[name] is None):
                raise ValueError("training_input_missing_flag_mismatch")
        output.append(
            {
                "chul_no": row["chul_no"],
                "horse_id": row["horse_id"],
                "features": {**row["features"], **values},
                "history_evidence": match,
            }
        )
    return output


def packet_body(item, history, contract_sha, available, publication, mode):
    return {
        "format_version": FORMAT,
        "mode": mode,
        "parent_series": inference.SERIES,
        "parent_study_sha256": item.get("study_sha256"),
        "contract_sha256": contract_sha,
        "race_id": item["race"]["race_id"],
        "feature_cutoff_at": item["race"]["feature_cutoff_at"],
        "api_source": item["projected"]["source"],
        "history_source": {
            "seed_sha256": SEED_SHA,
            "archive_sha256": ARCHIVE_SHA,
            "available_at": available.isoformat(),
            "public_existence_bound_at": publication["merged_at"],
            "publication_commit": publication["merge_commit_sha"],
            "publication_document_sha256": publication["document_sha256"],
        },
        "feature_rows": join_features(item["projected"], history),
        "history_coverage": {
            k: history[k]
            for k in (
                "lookback_start",
                "lookback_end_exclusive",
                "recent_start",
                "response_unit_status_counts",
                "missing_response_units",
            )
        },
        "training_approved": False,
        "counts_as_70_percent_evidence": False,
        "independent_packet_publication_verified": False,
    }


def timing_reasons(packet, completed):
    cutoff = timestamp(packet["feature_cutoff_at"])
    history = packet["history_source"]
    available = timestamp(history["available_at"])
    published = timestamp(history["public_existence_bound_at"])
    api = timestamp(packet["api_source"]["available_at"])
    reasons = []
    if not available <= published < cutoff:
        reasons.append("history_not_proven_before_cutoff")
    if not max(api, available, published) <= completed < cutoff:
        reasons.append("source_or_materialization_not_before_cutoff")
    return reasons


def seal(directory, body):
    path = directory / f"input_{body['race_id']}.json"
    if path.exists():
        packet = forward.read(path)
        if encoded(
            {k: v for k, v in packet.items() if k != "materialized_at"}
        ) != encoded(body):
            raise ValueError("training_input_occupied_slot_conflict")
        completed = timestamp(packet["materialized_at"])
        if completed > now():
            raise ValueError("training_input_future_clock")
    else:
        completed = now()
        packet = {**body, "materialized_at": completed.isoformat()}
        reasons = timing_reasons(packet, completed)
        if body["mode"] == "prospective" and reasons:
            raise ValueError("training_input_not_timely:" + ",".join(reasons))
        save(path, packet)
    reasons = timing_reasons(packet, completed)
    observation = forward.observe_packet(
        path,
        directory / f"observation_{body['race_id']}.json",
        body["feature_cutoff_at"],
        time_key="materialized_at",
    )
    status = (
        "historical_diagnostic"
        if body["mode"] != "prospective"
        else (
            "locally_sealed"
            if not reasons and observation["status"] == "locally_observed_before_cutoff"
            else "local_timeliness_unproven"
        )
    )
    return {
        "race_id": body["race_id"],
        "status": status,
        "packet_path": str(path),
        "packet_sha256": observation["packet_sha256"],
        "observation": observation,
        "timing_reasons": reasons,
        "runner_count": len(body["feature_rows"]),
        "independent_packet_publication_verified": False,
    }


def parent_inputs(root, model_dir):
    inference.pinned_json(root / "contract.json", CONTRACT_SHA)
    if inference.sha256(encoded(forward.contract())) != CONTRACT_SHA:
        raise ValueError("training_input_parent_implementation_changed")
    model, receipt = inference.load_model(model_dir)
    days, items = [], []
    for date in inference.DATES:
        directory = root / date
        study_path = directory / "study.json"
        day = {
            "race_date": date,
            "status": "awaiting_card",
            "race_count": None,
            "ledger": [],
        }
        days.append(day)
        if not study_path.exists():
            continue
        try:
            study = forward.read(study_path)
            forward.verify_study(study, CONTRACT_SHA)
        except (ValueError, OSError, KeyError, TypeError) as exc:
            day.update(
                status="parent_study_conflict",
                reason=str(exc) if isinstance(exc, ValueError) else type(exc).__name__,
            )
            continue
        study_sha = inference.sha256(study_path.read_bytes())
        day.update(
            status="study_available",
            race_count=study["universe"]["race_count"],
            study_sha256=study_sha,
        )
        for race in study["universe"]["races"]:
            slot = {"race_id": race["race_id"], "status": "missing_m0_selected_capture"}
            day["ledger"].append(slot)
            try:
                packet_path = directory / f"prediction_{race['race_id']}.json"
                if packet_path.exists():
                    packet = forward.recover_packet(
                        packet_path, race, model, receipt, root, study_sha
                    )
                    projected = {
                        k: packet["prediction"][k]
                        for k in ("race_id", "feature_rows", "source")
                    }
                else:
                    path = directory / f"input_{race['race_id']}.json"
                    if not path.exists():
                        continue
                    ref = forward.read(path)
                    if ref["study_sha256"] != study_sha:
                        raise ValueError("training_input_parent_study_conflict")
                    projected = inference.project_capture(
                        race,
                        Path(ref["manifest_path"]),
                        root,
                        expected_sha256=ref["manifest_sha256"],
                    )
                items.append(
                    {
                        "race": race,
                        "projected": projected,
                        "study_sha256": study_sha,
                        "slot": slot,
                    }
                )
            except (ValueError, OSError, KeyError, TypeError) as exc:
                slot.update(
                    status="parent_input_conflict",
                    reason=str(exc)
                    if isinstance(exc, ValueError)
                    else type(exc).__name__,
                )
    return days, items


def diagnostic_inputs(plan_path, archive_root):
    plan = inference.pinned_json(plan_path, PLAN_SHA)
    items = []
    for record in plan["races"]:
        replay = replay_race_card_snapshot(
            record["manifest_path"],
            archive_root=archive_root,
            expected_sha256=record["manifest_sha256"],
            expected_identity={k: record[k] for k in ("meet", "race_date", "race_no")},
            expected_pdf_sha256=record["pdf_sha256"],
            expected_entry_manifest_sha256=record["entry_manifest_sha256"],
        )
        projected, cutoff = project_original(record, replay, archive_root)
        items.append(
            {
                "race": {**record, "feature_cutoff_at": cutoff.isoformat()},
                "projected": projected,
                "slot": {"race_id": record["race_id"]},
            }
        )
    return [
        {
            "status": "historical_diagnostic",
            "race_count": len(items),
            "ledger": [r["slot"] for r in items],
        }
    ], items


def materialize_inputs(items, history_root, seed, archive, directory):
    roster = {
        "ledger": [
            {
                "race_id": item["race"]["race_id"],
                "roster": [
                    {k: row[k] for k in ("chul_no", "horse_id")}
                    for row in item["projected"]["feature_rows"]
                ],
            }
            for item in items
        ]
    }
    path = directory / "rosters.json"
    sha = save(path, roster)
    projection = recency.materialize(
        history_root, seed, SEED_SHA, archive, ARCHIVE_SHA, path, sha
    )
    projection_sha = save(directory / "history_projection.json", projection)
    available = history_available_at(seed, history_root, projection)
    return projection, projection_sha, available


def run(args):
    mode = "historical_diagnostic" if args.command == "diagnose" else "prospective"
    root = args.output_dir.resolve() / (
        "diagnostic" if mode != "prospective" else inference.SERIES
    )
    for source in (
        args.parent_root,
        args.model_dir,
        args.history_root,
        args.archive_dir,
        args.seed,
        getattr(args, "raw_archive_root", None),
    ):
        if source is None:
            continue
        resolved = source.resolve()
        if root.is_relative_to(resolved) or resolved.is_relative_to(root):
            raise ValueError("training_input_output_overlaps_source")
    root.mkdir(parents=True, exist_ok=True)
    with exclusive(root):
        current = contract()
        contract_path = root / "contract.json"
        if contract_path.exists():
            if forward.read(contract_path) != current:
                raise ValueError("training_input_contract_changed")
        else:
            save(contract_path, current)
        contract_sha = inference.sha256(encoded(current))
        directory = root / (
            now().strftime("%Y%m%dT%H%M%S.%fZ") + "_" + uuid4().hex[:12]
        )
        directory.mkdir()
        publication = history_publication(directory)
        days, items = (
            diagnostic_inputs(args.plan, args.raw_archive_root)
            if mode != "prospective"
            else parent_inputs(args.parent_root, args.model_dir)
        )
        projection_sha = None
        if items:
            projection, projection_sha, available = materialize_inputs(
                items, args.history_root, args.seed, args.archive_dir, directory
            )
            history = {r["race_id"]: r for r in projection["races"]}
            for item in items:
                try:
                    body = packet_body(
                        item,
                        history[item["race"]["race_id"]],
                        contract_sha,
                        available,
                        publication,
                        mode,
                    )
                    item["slot"].update(seal(root, body))
                except (ValueError, OSError, KeyError, TypeError) as exc:
                    item["slot"].update(
                        status="input_conflict_or_late",
                        reason=str(exc)
                        if isinstance(exc, ValueError)
                        else type(exc).__name__,
                    )
        if current != contract():
            raise ValueError("training_input_implementation_changed_during_run")
        for day in days:
            for slot in day["ledger"]:
                for kind, prefix in (
                    ("packet", "input"),
                    ("observation", "observation"),
                ):
                    path = root / f"{prefix}_{slot['race_id']}.json"
                    if path.exists():
                        slot[f"occupied_{kind}_sha256"] = inference.sha256(
                            path.read_bytes()
                        )
        report = {
            "format_version": FORMAT,
            "mode": mode,
            "contract_sha256": contract_sha,
            "days": days,
            "history_publication": publication,
            "history_projection_sha256": projection_sha,
            "completed_at": now().isoformat(),
            "packet_count": sum(
                "packet_sha256" in r for d in days for r in d["ledger"]
            ),
            "locally_timely_prospective_count": sum(
                r["status"] == "locally_sealed" for d in days for r in d["ledger"]
            ),
            "independently_published_packet_count": 0,
            "training_approved": False,
            "counts_as_70_percent_evidence": False,
        }
        sha = save(directory / "manifest.json", report)
        return report, directory / "manifest.json", sha


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("run", "diagnose"))
    for key in (
        "parent-root",
        "model-dir",
        "history-root",
        "seed",
        "archive-dir",
        "output-dir",
    ):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--raw-archive-root", type=Path)
    args = parser.parse_args(argv)
    if args.command == "diagnose" and not (args.plan and args.raw_archive_root):
        parser.error("diagnose requires original plan and raw archive root")
    report, path, sha = run(args)
    print(
        {
            "manifest": str(path),
            "sha256": sha,
            **{k: v for k, v in report.items() if k.endswith("count")},
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
