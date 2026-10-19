"""Replay a reviewed whole-block input reservation without fitting or collection."""

from __future__ import annotations

import numpy as np

from autoresearch import condition_candidate_inputs as candidate
from autoresearch import condition_forward_contract as contract
from autoresearch.condition_training_data import feature_values
from autoresearch.kra_schedule_snapshot import replay_schedule_snapshot
from autoresearch.local_m0_forward import scheduled_races
from autoresearch.prerace_hash_witness import timestamp


def check_sources(protocol):
    pins = protocol["source_receipts"]
    if not pins or len({p["path"] for p in pins}) != len(pins):
        raise ValueError("forward_missing_or_duplicate_source_receipts")
    for pin in pins:
        raw = contract.training.read(contract.local_path(pin["path"]))
        if contract.sha256(raw) != pin["sha256"]:
            raise ValueError("forward_raw_source_hash_mismatch")
        if timestamp(pin["available_at"]) > timestamp(protocol["created_at"]):
            raise ValueError("forward_source_after_registration")


def matrix_for(protocol, created):
    check_sources(protocol)
    schedules = protocol["schedules"]
    if sorted(s["race_date"] for s in schedules) != protocol["race_dates"]:
        raise ValueError("forward_schedule_dates_mismatch")
    scheduled = {}
    for pin in schedules:
        contract.read_pin(pin)
        report = replay_schedule_snapshot(
            contract.local_path(pin["path"]), race_date=pin["race_date"]
        )
        if report["capture_manifest_sha256"] != pin["sha256"] or timestamp(
            report["capture_completed_at"]
        ) > timestamp(protocol["created_at"]):
            raise ValueError("forward_schedule_clock_or_hash_mismatch")
        for race in scheduled_races(report):
            if race["race_id"] in scheduled or race["race_id"][:8] != pin["race_date"]:
                raise ValueError("forward_duplicate_or_wrong_schedule_race")
            scheduled[race["race_id"]] = race
    races = protocol["races"]
    if set(scheduled) != {r["race_id"] for r in races} or any(
        timestamp(r["feature_cutoff_at"])
        != timestamp(scheduled[r["race_id"]]["feature_cutoff_at"])
        for r in races
    ):
        raise ValueError("forward_whole_official_population_mismatch")
    targets = {r["race_id"]: r["roster"] for r in races}
    if any(len(roster) != scheduled[rid]["runners"] for rid, roster in targets.items()):
        raise ValueError("forward_official_runner_count_mismatch")
    packets = [contract.read_pin(p) for p in protocol["packets"]]
    if any(p.get("target_outcomes_loaded") is not False for p in packets):
        raise ValueError("forward_packet_not_label_free")
    if any(
        timestamp(p["feature_cutoff_at"])
        != timestamp(scheduled[p["race_id"]]["feature_cutoff_at"])
        or not max(
            timestamp(p["api_source"]["available_at"]),
            timestamp(p["history_source"]["available_at"]),
            timestamp(p["history_source"]["public_existence_bound_at"]),
        )
        <= timestamp(p["materialized_at"])
        <= timestamp(protocol["created_at"])
        for p in packets
    ):
        raise ValueError("forward_packet_clock_mismatch")
    memory = contract.read_pin(protocol["memory"])
    if timestamp(memory["created_at"]) > timestamp(protocol["created_at"]):
        raise ValueError("forward_memory_after_registration")
    result = candidate.build(packets, memory, targets, created)
    cutoff = min(timestamp(r["feature_cutoff_at"]) for r in races)
    if not timestamp(protocol["created_at"]) <= created < cutoff:
        raise ValueError("forward_whole_block_deadline")
    # Validate all 34 typed cells before conversion; no outcome fields enter X.
    x = np.asarray(
        [feature_values(r["features"]) for r in result["rows"]], dtype=np.float64
    )
    identities = [
        {k: r[k] for k in ("race_id", "chul_no", "horse_id")} for r in result["rows"]
    ]
    return result, x, identities
