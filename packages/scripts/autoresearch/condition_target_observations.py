"""Replay official outcome targets for a published A24/B34 block; never score."""

import argparse
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from shared import kra_schedule

from autoresearch import condition_forward_contract as contract
from autoresearch import condition_historical_publication as historical
from autoresearch import local_m0_evaluation as evidence
from autoresearch import versioned_result_observations as observations
from autoresearch.kra_race_card_pdf_replay import checked_digest
from autoresearch.kra_schedule_snapshot import replay_schedule_snapshot
from autoresearch.local_m0_forward import scheduled_races
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import encoded, parse_json, sha256

VERSION = "condition-target-observations-v1"
POLICY = {
    "version": VERSION,
    "parent_policy_sha256": evidence.OUTCOME_POLICY_SHA,
    "original_population": "timely_published_and_approved_v2_original_schedule",
    "identity": "exact_original_gate_and_numeric_id_roster_in_both_result_sources",
    "target": "replayed_unique_top3_in_original_protocol_id_spelling",
    "source_clock": "original_scheduled_start_through_selected_observation_cutoff",
    "unconfirmed_void": "pending_evidence",
    "closure": "not_verified",
}
POLICY_SHA = sha256(encoded(POLICY))


def original_authority(root, manifest, report):
    protocol_ref, review_ref = (manifest[key] for key in ("protocol", "approval"))
    if (
        not historical.relative(protocol_ref["document"]).startswith(
            "docs/research/protocols/"
        )
        or review_ref["document"] != contract.REGISTRY
        or protocol_ref["pull_number"] == review_ref["pull_number"]
    ):
        raise ValueError("target_publication_paths_or_separate_review")
    protocol, protocol_fact = historical.archive(root, protocol_ref)
    registry, review_fact = historical.archive(root, review_ref)
    report["publications"] = {"protocol": protocol_fact, "approval": review_fact}
    if protocol is None:
        return None
    if (
        protocol["format_version"] != "condition-forward-protocol-v2"
        or protocol["runtime"]["model_hashes"] != contract.MODEL_HASHES
        or protocol["runtime"]["training_receipt_sha256"] != contract.RECEIPT_SHA
        or type(protocol["runtime"]["fit_count"]) is not int
        or protocol["runtime"]["fit_count"] != 0
    ):
        raise ValueError("target_original_model_contract")
    ids, _, cutoff = historical.protocol_population(protocol, manifest["study_id"])
    first_merge = timestamp(protocol_fact["witness"]["merged_at"])
    created = timestamp(protocol["created_at"])
    if (
        contract.publication_slot(protocol)["pull_number"]
        in {protocol_ref["pull_number"], review_ref["pull_number"]}
        or not created <= first_merge < cutoff
    ):
        raise ValueError("target_original_protocol_not_timely")
    report["declared_race_ids"] = ids
    report["declared_first_cutoff_at"] = cutoff.isoformat()
    if registry is None:
        return None
    review = historical.approval_record(
        registry, protocol, protocol_ref, manifest["study_id"]
    )
    if not (
        first_merge
        <= timestamp(review["reviewed_at"])
        <= timestamp(review_fact["witness"]["merged_at"])
        < cutoff
    ):
        raise ValueError("target_original_approval_not_timely")
    return protocol


def original_schedule(root, protocol, sources):
    pins = protocol["schedules"]
    if (
        type(pins) is not list
        or any(set(pin) != {"path", "race_date", "sha256"} for pin in pins)
        or sorted(pin["race_date"] for pin in pins) != protocol["race_dates"]
        or set(sources) != {pin["sha256"] for pin in pins}
    ):
        raise ValueError("target_original_schedule_coverage")
    declared = {row["race_id"]: row for row in protocol["races"]}
    bindings, groups = {}, defaultdict(list)
    created = timestamp(protocol["created_at"])
    for pin in pins:
        historical.relative(pin["path"])
        day, digest = pin["race_date"], checked_digest(pin["sha256"])
        source = sources[digest]
        if source["sha256"] != digest:
            raise ValueError("target_original_schedule_pin")
        historical.pin(root, source)
        raw = replay_schedule_snapshot(root / source["path"], race_date=day)
        if (
            raw["capture_manifest_sha256"] != digest
            or timestamp(raw["capture_completed_at"]) > created
        ):
            raise ValueError("target_original_schedule_pin_or_clock")
        groups[digest].append(day)
        for race in scheduled_races(raw):
            rid = race["race_id"]
            roster = declared.get(rid)
            if (
                not rid.startswith(day + "_")
                or rid in bindings
                or roster is None
                or len(roster["roster"]) != race["runners"]
                or timestamp(roster["feature_cutoff_at"])
                != timestamp(race["feature_cutoff_at"])
            ):
                raise ValueError("target_original_schedule_or_roster_conflict")
            bindings[rid] = (race, roster["roster"], digest)
    if bindings.keys() != declared.keys():
        raise ValueError("target_original_schedule_population_changed")
    return bindings, groups


def identity_roster(rows):
    keys = {(r["chul_no"], int(r["horse_id"])) for r in rows}
    if len({gate for gate, _ in keys}) != len(rows) or len(
        {horse for _, horse in keys}
    ) != len(rows):
        return None
    return keys


def target_row(binding, row, captures, as_of):
    race, declared, _ = binding
    api = row["api_records"]
    official = row["official_source"]
    refs = [captures[k] for k in sorted({r["source_capture_sha256"] for r in api})]
    clocks = [timestamp(r["source_available_at"]) for r in api]
    clocks.extend(timestamp(r["capture_completed_at"]) for r in refs)
    official_capture = official["capture"] if official is not None else None
    if official_capture is not None:
        clocks.append(timestamp(official_capture["completed_at"]))
    result = {
        "race_id": race["race_id"],
        "status": "pending_evidence",
        "triple": None,
        "official_observation_status": row["status"],
        "observation_reasons": row["reasons"],
        "result_observation_id": row["result_observation_id"],
        "api_captures": refs,
        "official_receipt": official["receipt"] if official is not None else None,
        "official_capture": official_capture,
    }
    if any(
        (ref["race_date"], ref["meet"]) != (race["race_date"], race["meet"])
        for ref in refs
    ) or any(row["race_id"] != r["race_id"] for r in api):
        raise ValueError("target_result_capture_scope")
    scheduled = timestamp(race["scheduled_start_at"])
    if any(clock < scheduled or clock > as_of for clock in clocks):
        return result | {"reason": "result_clock_outside_selected_window"}
    if row["status"] != "unique_top3_observed":
        reason = (
            "void_report_without_whole_race_verification"
            if row["status"] == "void_reported_no_top3"
            else row["status"]
        )
        return result | {"reason": reason}

    roster = identity_roster(declared)
    if (
        official_capture is None
        or not refs
        or roster is None
        or identity_roster(api) != roster
        or identity_roster(row["official_observation"]["rows"]) != roster
    ):
        return result | {"reason": "official_results_not_exact_original_roster"}
    original_id = {int(r["horse_id"]): r["horse_id"] for r in declared}
    top3 = [int(value) for value in row["observed_top3_horse_ids"]]
    if (
        len(set(top3)) != len(top3)
        or len(top3) != 3
        or not set(top3) <= original_id.keys()
    ):
        raise ValueError("target_replayed_top3_conflict")
    return result | {
        "status": "unique_target",
        "triple": [original_id[key] for key in sorted(top3)],
        "reason": None,
    }


def replay_group(root, ref, digest, days, bindings, as_of):
    plan = parse_json(historical.pin(root, ref))
    if plan["schedule_sha256"] != digest or sorted(plan["race_dates"]) != sorted(days):
        raise ValueError("target_result_plan_not_original_schedule_group")
    replay = observations.replay_plan(root / ref["path"], ref["sha256"])
    if (
        replay["observation_policy_sha256"] != POLICY["parent_policy_sha256"]
        or replay["implementation_sha256"] != evidence.OUTCOME_ADAPTER_SHA
        or observations.value_hash(replay["observation_source_sha256"])
        != evidence.OUTCOME_SOURCES_SHA
    ):
        raise ValueError("target_parent_result_policy_changed")
    rows = {r["race_id"]: r for r in replay["ledger"]}
    if (
        rows.keys() != bindings.keys()
        or not len(rows) == len(replay["ledger"]) == replay["scheduled_race_count"]
        or any(
            rows[rid]["scheduled_runner_count"] != binding[0]["runners"]
            for rid, binding in bindings.items()
        )
    ):
        raise ValueError("target_result_population_changed")
    captures = evidence.result_capture_evidence(plan, replay)
    return {
        "status": "observation_plan_replayed",
        "seed_sha256": plan["seed_sha256"],
        "official_archive_sha256": plan["official_archive_sha256"],
        "source_implementation_sha256": evidence.OUTCOME_SOURCES_SHA,
        "extra_api_races": replay["extra_api_races"],
        "extra_official_races": replay["extra_official_races"],
    }, [target_row(bindings[rid], rows[rid], captures, as_of) for rid in sorted(rows)]


def audit(manifest_path, expected_sha):
    path = Path(manifest_path).absolute()
    root = path.parent
    manifest = parse_json(
        historical.pin(root, {"path": path.name, "sha256": expected_sha})
    )
    if (
        set(manifest)
        != {
            "format_version",
            "study_id",
            "observation_cutoff_at",
            "protocol",
            "approval",
            "schedule_sources",
            "result_plans",
        }
        or manifest["format_version"] != VERSION
        or any(
            type(manifest[k]) is not dict for k in ("schedule_sources", "result_plans")
        )
    ):
        raise ValueError("target_manifest_schema")
    as_of = timestamp(manifest["observation_cutoff_at"])
    if as_of > datetime.now(UTC):
        raise ValueError("target_observation_cutoff_in_future")
    report = {
        "format_version": VERSION,
        "scope": "original_week_targets_only_not_population_or_prediction_scoring",
        "status": "pending_original_publication",
        "study_id": manifest["study_id"],
        "manifest_sha256": expected_sha,
        "target_policy_sha256": POLICY_SHA,
        "verifier_sha256": sha256(historical.read(Path(__file__))),
        "schedule_parser_sha256": sha256(historical.read(Path(kra_schedule.__file__))),
        "observation_cutoff_at": as_of.isoformat(),
        "full_population_verified": False,
        "denominator": None,
        "usable_for_scoring": False,
        "counts_as_70_percent_evidence": False,
        "registration_performed": False,
    }
    protocol = original_authority(root, manifest, report)
    if protocol is None:
        return report
    try:
        bindings, groups = original_schedule(
            root, protocol, manifest["schedule_sources"]
        )
    except FileNotFoundError:
        return report | {"status": "pending_original_schedule"}
    if set(manifest["result_plans"]) - groups.keys():
        raise ValueError("target_result_plan_outside_original_schedule_group")
    ledger, versions = [], []
    for digest, days in sorted(groups.items()):
        selected = {rid: b for rid, b in bindings.items() if b[2] == digest}
        ref = manifest["result_plans"].get(digest)
        version = {"status": "no_selected_observation_plan"}
        if ref is not None:
            try:
                version, rows = replay_group(root, ref, digest, days, selected, as_of)
            except FileNotFoundError:
                version = {"status": "missing_original_result_evidence"}
        if version["status"] != "observation_plan_replayed":
            rows = [
                {
                    "race_id": rid,
                    "status": "pending_evidence",
                    "triple": None,
                    "reason": version["status"],
                    "result_observation_id": None,
                }
                for rid in sorted(selected)
            ]
        plan_sha = ref["sha256"] if ref is not None else None
        versions.append(
            version
            | {
                "schedule_sha256": digest,
                "race_dates": sorted(days),
                "plan_sha256": plan_sha,
            }
        )
        ledger.extend(row | {"plan_sha256": plan_sha} for row in rows)
    return report | {
        "status": "original_week_targets_replayed",
        "ledger": sorted(ledger, key=lambda row: row["race_id"]),
        "selected_result_versions": versions,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args(argv)
    try:
        report = audit(args.manifest, args.sha256)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        report = {
            "format_version": VERSION,
            "status": "blocked",
            "reason": str(exc),
            "denominator": None,
            "usable_for_scoring": False,
        }
    print(encoded(report).decode(), end="")
    return 0 if report["status"] == "original_week_targets_replayed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
