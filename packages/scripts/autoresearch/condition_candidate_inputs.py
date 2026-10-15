"""Freeze a separate 24+10 candidate matrix, without fitting or changing inputs."""

from __future__ import annotations

import argparse
import math
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path

from autoresearch import condition_delta_diagnostic as delta
from autoresearch import official_history_recency as recency
from autoresearch.observed_history_seed import digest, save
from autoresearch.official_history_catalog import read_pin
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import API_COLUMNS

BASE_COLUMNS = (
    *API_COLUMNS,
    *recency.FIELDS,
    *(f"{k}_missing" for k in recency.FIELDS),
)
COUNTS = (
    "prior90_count",
    "similar90_count",
    "older_count",
    "older_same_venue_similar_count",
    "older_other_venue_count",
    "older_missing_condition_count",
)
MEMORY_FIELDS = {*COUNTS, "condition_delta90", "fallback90", "older_career_form"}
EXTRA_COLUMNS = (
    "memory_condition_delta90",
    "memory_fallback90",
    *("memory_" + k for k in COUNTS),
    "memory_older_career_form",
    "memory_older_career_form_missing",
)
COLUMNS = (*BASE_COLUMNS, *EXTRA_COLUMNS)
MEMORY_PATH = Path(
    ".cache/autoresearch/observed-history-extension-20260501-14/audit-report.json"
)
MEMORY_SHA = "0ff580a8e1ff3123f2f18ffb226ceb7ebf6c759f071697fbde0e9ad67bbb85e3"


def key(race_id, row):
    gate, horse = row["chul_no"], row["horse_id"]
    if (
        type(gate) is not int
        or gate < 1
        or not isinstance(horse, str)
        or not horse.isascii()
        or not horse.isdigit()
        or horse != str(int(horse))
        or int(horse) <= 0
    ):
        raise ValueError("candidate_invalid_identity")
    return race_id, gate, horse


def rational(value, low, high):
    if not isinstance(value, str):
        raise ValueError("candidate_fraction_type")
    try:
        fraction = Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError("candidate_invalid_fraction") from exc
    if not low <= fraction <= high:
        raise ValueError("candidate_fraction_range")
    return float(fraction)


def memory_features(features):
    if set(features) != MEMORY_FIELDS:
        raise ValueError("candidate_memory_columns")
    for name in COUNTS:
        if type(features[name]) is not int or features[name] < 0:
            raise ValueError("candidate_invalid_support_count")
    similar, older = features["similar90_count"], features["older_count"]
    if similar > features["prior90_count"] or any(
        features[name] > older for name in COUNTS[3:]
    ):
        raise ValueError("candidate_inconsistent_support_count")
    fallback = features["fallback90"]
    if fallback != ("no_eligible_prior" if similar == 0 else None):
        raise ValueError("candidate_inconsistent_fallback")
    form = features["older_career_form"]
    if (form is None) != (older == 0):
        raise ValueError("candidate_inconsistent_missing_form")
    contrast = rational(features["condition_delta90"], -1, 1)
    if fallback and contrast != 0:
        raise ValueError("candidate_nonzero_fallback")
    return {
        "memory_condition_delta90": contrast,
        "memory_fallback90": fallback is not None,
        **{"memory_" + name: features[name] for name in COUNTS},
        "memory_older_career_form": None if form is None else rational(form, 0, 1),
        "memory_older_career_form_missing": form is None,
    }


def base_features(features):
    if set(features) != set(BASE_COLUMNS):
        raise ValueError("candidate_base_columns")
    for name, value in features.items():
        boolean = name.endswith("_missing") or name == recency.FIELDS[-1]
        if boolean:
            if type(value) is not bool and not (
                name == recency.FIELDS[-1] and value is None
            ):
                raise ValueError("candidate_invalid_boolean")
        elif value is not None and (
            type(value) not in (int, float) or not math.isfinite(value)
        ):
            raise ValueError("candidate_invalid_numeric")
        if name.endswith("_missing") and value != (features[name[:-8]] is None):
            raise ValueError("candidate_missing_flag")
    return {name: features[name] for name in BASE_COLUMNS}


def build(packets, memory, targets, created):
    if (
        memory["target_outcomes_loaded"] is not False
        or memory["training_approved"] is not False
    ):
        raise ValueError("candidate_memory_not_label_free")
    expected = {key(rid, r) for rid, roster in targets.items() for r in roster}
    if len(expected) != sum(len(roster) for roster in targets.values()):
        raise ValueError("candidate_duplicate_target")
    for roster in targets.values():
        if not 3 <= len(roster) <= 20 or any(
            len({r[field] for r in roster}) != len(roster)
            for field in ("chul_no", "horse_id")
        ):
            raise ValueError("candidate_invalid_target_roster")
    supplemental = {}
    for row in memory["rows"]:
        identity = key(row["race_id"], row)
        if identity in supplemental:
            raise ValueError("candidate_duplicate_memory")
        supplemental[identity] = memory_features(row["features"])
    if set(supplemental) != expected:
        raise ValueError("candidate_memory_universe")
    rows, races, seen = [], [], set()
    for packet in packets:
        rid = packet["race_id"]
        if rid not in targets or rid in {r["race_id"] for r in races}:
            raise ValueError("candidate_packet_universe")
        cutoff = timestamp(packet["feature_cutoff_at"])
        clocks = [
            timestamp(packet["api_source"]["available_at"]),
            timestamp(packet["history_source"]["available_at"]),
            timestamp(packet["history_source"]["public_existence_bound_at"]),
            timestamp(packet["materialized_at"]),
            timestamp(memory["created_at"]),
        ]
        if created.utcoffset() is None or not max(clocks) <= created < cutoff:
            raise ValueError("candidate_not_before_cutoff")
        for row in packet["feature_rows"]:
            identity = key(rid, row)
            if identity not in expected or identity in seen:
                raise ValueError("candidate_packet_identity")
            seen.add(identity)
            features = {**base_features(row["features"]), **supplemental[identity]}
            rows.append(
                {
                    "race_id": rid,
                    "chul_no": identity[1],
                    "horse_id": identity[2],
                    "features": features,
                }
            )
        races.append({"race_id": rid, "feature_cutoff_at": packet["feature_cutoff_at"]})
    if seen != expected or len(races) != len(targets) or not rows:
        raise ValueError("candidate_incomplete_population")
    rows.sort(key=lambda r: (r["race_id"], r["chul_no"], int(r["horse_id"])))
    return {
        "format_version": "condition-candidate-inputs-v1",
        "created_at": created.isoformat(),
        "columns": list(COLUMNS),
        "base_columns": list(BASE_COLUMNS),
        "extra_columns": list(EXTRA_COLUMNS),
        "races": sorted(races, key=lambda r: r["race_id"]),
        "rows": rows,
        "race_count": len(races),
        "runner_count": len(rows),
        "null_counts": {
            c: sum(r["features"][c] is None for r in rows) for c in COLUMNS
        },
        "fit_count": 0,
        "target_outcomes_loaded": False,
        "training_approved": False,
        "new_evaluation_arm_registered": False,
        "counts_as_70_percent_evidence": False,
        "accuracy": None,
        "publication_review_required": True,
        "interpretation": "candidate_input_only_not_amendment_of_original_24_column_reservation",
    }


def run(output):
    created = datetime.now(UTC)
    code_sha = digest(Path(__file__).read_bytes())
    public = {k: read_pin(delta.PUBLIC / k, v) for k, v in delta.PINS.items()}
    targets, _, _ = delta.load_targets(public["m0.json"])
    memory = read_pin(MEMORY_PATH, MEMORY_SHA)
    packets, pins = [], []
    for day in public["training-inputs.json"]["days"]:
        for item in day["ledger"]:
            if item["status"] != "locally_sealed" or item["timing_reasons"]:
                raise ValueError("candidate_original_packet_not_timely")
            packet = read_pin(Path(item["packet_path"]), item["packet_sha256"])
            if packet["race_id"] != item["race_id"]:
                raise ValueError("candidate_packet_manifest_identity")
            packets.append(packet)
            pins.append(
                {
                    "race_id": item["race_id"],
                    "path": item["packet_path"],
                    "sha256": item["packet_sha256"],
                }
            )
    result = build(packets, memory, targets, created)
    if result["race_count"] != 50 or result["runner_count"] != 534:
        raise ValueError("candidate_frozen_october_population")
    result.update(
        source_pins={"public": delta.PINS, "memory": MEMORY_SHA, "packets": pins},
        implementation_sha256=code_sha,
    )
    if datetime.now(UTC) >= min(timestamp(p["feature_cutoff_at"]) for p in packets):
        raise ValueError("candidate_completion_after_cutoff")
    for name, sha in delta.PINS.items():
        read_pin(delta.PUBLIC / name, sha)
    for pin in pins:
        read_pin(Path(pin["path"]), pin["sha256"])
    read_pin(MEMORY_PATH, MEMORY_SHA)
    if digest(Path(__file__).read_bytes()) != code_sha:
        raise ValueError("candidate_implementation_changed")
    output.mkdir(parents=True, exist_ok=False)
    sha = save(output / "matrix.json", result)
    return {
        "sha256": sha,
        "rows": result["runner_count"],
        "columns": len(COLUMNS),
        "null_counts": result["null_counts"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    print(run(parser.parse_args().output_dir))
