"""Outcome-free, fixed-policy condition contrast for the published October block."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path

from autoresearch import condition_form_research as condition
from autoresearch import history_form_research as form
from autoresearch.kra_race_card_pdf_replay import replay_entry_pages
from autoresearch.observed_history_seed import digest, save
from autoresearch.official_history_catalog import read_pin
from autoresearch.prerace_conditions import project_conditions
from autoresearch.restricted_cohort import horse_id

PUBLIC = Path("docs/research/commitments/2026-10-16-18")
PINS = {
    "m0.json": "de82b4d1dc1d69b7982af04b7d83557d008381ea23202f0dff661721388f7a2c",
    "api27.json": "a51f7b8ca425251fa6bc7602788031a6675b3b9de195c55db76789d5847f6646",
    "training-inputs.json": "b4ab302c93bb01a947bd149622770d3413690f5fa95bbec8c13a00ed2808fa32",
}
HISTORY = Path(".cache/autoresearch/condition-form-research-20261013/run-1")
HISTORY_SHA = "f718152b1465bea5990145ed30afb2402eaaba9ce2640a89163841e6211e5125"
CONDITIONS_SHA = "818f0be674ef148b9c83e46192a52686be1e5ba2805b5daf8c601134aaaa6123"
FORWARD = Path(".cache/autoresearch/local-m0-forward/local_m0_20261016_18_v1")


def project(targets, history, conditions):
    """Return exact deltas and missingness, never selections or target outcomes."""
    if not targets:
        raise ValueError("delta_empty_targets")
    indexed, withheld = form.index_history(history)
    ledger = []
    for identity, roster in sorted(targets.items()):
        if not roster or any(set(r) != {"horse_id", "chul_no"} for r in roster):
            raise ValueError("delta_target_not_identity_only")
        form.group_records([{"race_id": identity, **r} for r in roster])
        context = conditions.get(identity, {})
        rows = []
        for runner in sorted(roster, key=lambda r: r["chul_no"]):
            prior = form.prior_rows(
                indexed[runner["horse_id"]], identity[:8], "expanded90"
            )
            matched = [
                r
                for r in prior
                if condition.eligible(
                    context, conditions.get(r["race_id"], {}), "joint90"
                )
            ]
            fallback = (
                "missing_target_conditions"
                if context.get("status") != "observed"
                else "no_eligible_prior"
                if not matched
                else None
            )
            baseline = form.form_score(prior, "expanded90")
            joint = baseline if fallback else form.form_score(matched, "expanded90")
            rows.append(
                {
                    **runner,
                    "expanded90": str(baseline),
                    "joint90": str(joint),
                    "delta": str(joint - baseline),
                    "fallback": fallback,
                    "baseline_prior_ids": [r["race_id"] for r in prior],
                    "eligible_prior_ids": [r["race_id"] for r in matched],
                    "missing_history_conditions": sum(
                        conditions.get(r["race_id"], {}).get("status") != "observed"
                        for r in prior
                    ),
                }
            )
        ledger.append(
            {
                "race_id": identity,
                "meet": context.get("meet"),
                "distance_m": context.get("distance_m"),
                "class_text": context.get("class_text"),
                "within_race_delta_varies": len({r["delta"] for r in rows}) > 1,
                "all_fallback": all(r["fallback"] is not None for r in rows),
                "rows": rows,
            }
        )
    return {"ledger": ledger, "invalid_history_rows_withheld": withheld}


def summarize(ledger):
    counts = Counter(
        races=0,
        runner_rows=0,
        varying_races=0,
        all_fallback_races=0,
        fallback_rows=0,
        observed_zero_rows=0,
        nonzero_rows=0,
        no_history_rows=0,
        missing_history_condition_links=0,
    )
    for race in ledger:
        counts.update(
            races=1,
            runner_rows=len(race["rows"]),
            varying_races=int(race["within_race_delta_varies"]),
            all_fallback_races=int(race["all_fallback"]),
        )
        for row in race["rows"]:
            counts.update(
                fallback_rows=int(row["fallback"] is not None),
                observed_zero_rows=int(
                    row["fallback"] is None and Fraction(row["delta"]) == 0
                ),
                nonzero_rows=int(Fraction(row["delta"]) != 0),
                no_history_rows=int(not row["baseline_prior_ids"]),
                missing_history_condition_links=row["missing_history_conditions"],
            )
    return dict(counts)


def load_targets(commitment):
    targets, contexts, evidence = {}, {}, []
    for day in commitment["days"]:
        for item in day["races"]:
            identity = item["race_id"]
            date, meet, number = identity.split("_")
            if date != day["race_date"] or identity in targets:
                raise ValueError("delta_population_identity_mismatch")
            packet = read_pin(
                FORWARD / date / f"prediction_{identity}.json", item["packet_sha256"]
            )
            if packet["prediction"]["race_id"] != identity:
                raise ValueError("delta_packet_identity_mismatch")
            source = packet["prediction"]["source"]
            raw, manifest, proof = replay_entry_pages(
                Path(source["manifest_path"]),
                archive_root=FORWARD.resolve(),
                meet=int(meet),
                race_date=date,
                expected_sha256=source["manifest_sha256"],
            )
            projected = project_conditions(
                raw,
                meet=int(meet),
                race_date=date,
                race_no=int(number),
                collected_at=datetime.fromisoformat(manifest["collected_at"]),
            )
            captured = datetime.fromisoformat(projected["captured_at"])
            cutoff = datetime.fromisoformat(packet["feature_cutoff_at"])
            if not captured < cutoff or cutoff != datetime.fromisoformat(
                projected["cutoff"]
            ):
                raise ValueError("delta_capture_not_timely")
            targets[identity] = [
                {"horse_id": horse_id(r["hrNo"]), "chul_no": r["chulNo"]}
                for r in projected["roster"]
            ]
            expected = [
                {k: r[k] for k in ("horse_id", "chul_no")}
                for r in packet["prediction"]["feature_rows"]
            ]
            if targets[identity] != expected:
                raise ValueError("delta_roster_mismatch")
            contexts[identity] = {
                "status": "observed"
                if all(
                    projected[k]["status"] == "observed"
                    for k in ("distance_m", "class_text")
                )
                else "unknown",
                "meet": int(meet),
                **{k: projected[k]["value"] for k in ("distance_m", "class_text")},
            }
            evidence.append(
                {
                    "race_id": identity,
                    "packet_sha256": item["packet_sha256"],
                    "captured_at": projected["captured_at"],
                    "source": proof,
                }
            )
    if len(targets) != 50 or sum(map(len, targets.values())) != 534:
        raise ValueError("delta_incomplete_frozen_population")
    return targets, contexts, evidence


def run(output):
    commitments = {name: read_pin(PUBLIC / name, sha) for name, sha in PINS.items()}
    history = read_pin(HISTORY / "history.json", HISTORY_SHA)["records"]
    conditions = read_pin(HISTORY / "conditions.json", CONDITIONS_SHA)["records"]
    targets, contexts, evidence = load_targets(commitments["m0.json"])
    if set(targets) & set(conditions) or any(
        r["race_id"][:8] >= min(targets)[:8] for r in history
    ):
        raise ValueError("delta_history_overlaps_target_block")
    projection = project(targets, history, {**conditions, **contexts})
    groups = {}
    for key in ("meet", "distance_m", "class_text"):
        grouped = defaultdict(list)
        for race in projection["ledger"]:
            grouped[str(race[key])].append(race)
        groups[key] = {k: summarize(v) for k, v in sorted(grouped.items())}
    for name, sha in PINS.items():
        read_pin(PUBLIC / name, sha)
    report = {
        "created_at": datetime.now(UTC).isoformat(),
        "format_version": "october-condition-delta-diagnostic-v1",
        "recipe": "joint90-minus-expanded90; unchanged 90d/200m/exact-class policy",
        "fit_count": 0,
        "target_outcomes_loaded": False,
        "training_approved": False,
        "counts_as_70_percent_evidence": False,
        "accuracy": None,
        "historical_prerace_availability_verified": False,
        "public_commitments_unchanged": PINS,
        "history_sha256": HISTORY_SHA,
        "conditions_sha256": CONDITIONS_SHA,
        "code_sha256": digest(Path(__file__).read_bytes()),
        "summary": summarize(projection["ledger"]),
        "segments": groups,
        "input_evidence": evidence,
        **projection,
    }
    output.mkdir(parents=True, exist_ok=True)
    return save(output / "report.json", report), report["summary"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(run(args.output_dir))
