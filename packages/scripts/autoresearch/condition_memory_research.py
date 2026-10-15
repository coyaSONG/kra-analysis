"""Outcome-free older-career features and recent condition sensitivity."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path

from autoresearch import condition_delta_diagnostic as delta
from autoresearch import condition_form_research as condition
from autoresearch import history_form_research as form
from autoresearch import history_gap_expansion as expansion
from autoresearch.observed_history_seed import digest, save
from autoresearch.official_history_catalog import read_pin

EXPANSION_SHA = "3302c5bb1abb62f70565535751991c01896b9b437e4160168ea3700fbbc09866"
PLAN = Path("docs/plans/2026-10-15-condition-memory-execplan.md")


def contrast(prior, matched):
    return (
        form.form_score(matched, "expanded90") - form.form_score(prior, "expanded90")
        if matched
        else Fraction(0)
    )


def deletion_diagnostic(prior, matched):
    """Remove each observation once; these ranges are not uncertainty intervals."""
    original = contrast(prior, matched)
    cases = []
    for omitted in prior:
        identity = omitted["race_id"]
        remaining = [r for r in prior if r["race_id"] != identity]
        eligible = [r for r in matched if r["race_id"] != identity]
        cases.append(
            {
                "omitted_race_id": identity,
                "delta": str(contrast(remaining, eligible)),
                "no_eligible_prior": not eligible,
            }
        )
    values = [Fraction(r["delta"]) for r in cases]
    return {
        "cases": cases,
        "minimum": str(min(values)) if values else None,
        "maximum": str(max(values)) if values else None,
        "strict_sign_reversal": any(v * original < 0 for v in values),
        "nonzero_can_become_zero": original != 0 and Fraction(0) in values,
        "eligible_support_can_disappear": bool(matched)
        and any(r["no_eligible_prior"] for r in cases),
    }


def validate_context(identity, context):
    if context.get("status") != "observed":
        return
    if (
        type(context.get("meet")) is not int
        or context["meet"] != int(identity.split("_")[1])
        or type(context.get("distance_m")) is not int
        or context["distance_m"] <= 0
        or not isinstance(context.get("class_text"), str)
        or not context["class_text"].strip()
    ):
        raise ValueError("memory_invalid_physical_context")


def project(targets, baseline, extension, contexts):
    if not targets:
        raise ValueError("memory_empty_targets")
    history = baseline + extension
    indexed, withheld = form.index_history(history)
    if withheld:
        raise ValueError("memory_invalid_rank_size")
    for identity in set(targets) | {r["race_id"] for r in history}:
        datetime.strptime(identity[:8], "%Y%m%d")
        validate_context(identity, contexts.get(identity, {}))
    if any(r["race_id"][:8] >= min(targets)[:8] for r in history):
        raise ValueError("memory_target_or_future_history")
    old = delta.project(targets, baseline, contexts)
    current = delta.project(targets, history, contexts)
    if current != old:
        raise ValueError("memory_changed_recent_contrast")
    additions = {(r["race_id"], r["horse_id"]) for r in extension}
    rows = []
    for race in current["ledger"]:
        identity = race["race_id"]
        for recent in race["rows"]:
            horse = recent["horse_id"]
            prior = form.prior_rows(indexed[horse], identity[:8], "expanded90")
            eligible_ids = set(recent["eligible_prior_ids"])
            matched = [r for r in prior if r["race_id"] in eligible_ids]
            recent_ids = set(recent["baseline_prior_ids"])
            older = [
                r
                for r in form.prior_rows(indexed[horse], identity[:8], "expanded180")
                if r["race_id"] not in recent_ids
            ]
            before = [r for r in older if (r["race_id"], horse) not in additions]
            similar = [
                r
                for r in older
                if condition.eligible(
                    contexts.get(identity, {}),
                    contexts.get(r["race_id"], {}),
                    "joint90",
                )
            ]
            older_form = str(form.form_score(older, "expanded90")) if older else None
            previous = str(form.form_score(before, "expanded90")) if before else None
            rows.append(
                {
                    "race_id": identity,
                    "horse_id": horse,
                    "chul_no": recent["chul_no"],
                    "features": {
                        "condition_delta90": recent["delta"],
                        "prior90_count": len(prior),
                        "similar90_count": len(matched),
                        "fallback90": recent["fallback"],
                        "older_count": len(older),
                        "older_career_form": older_form,
                        "older_same_venue_similar_count": len(similar),
                        "older_other_venue_count": sum(
                            r["race_id"].split("_")[1] != identity.split("_")[1]
                            for r in older
                        ),
                        "older_missing_condition_count": sum(
                            contexts.get(r["race_id"], {}).get("status") != "observed"
                            for r in older
                        ),
                    },
                    "provenance": {
                        "recent_ids": [r["race_id"] for r in prior],
                        "similar90_ids": sorted(eligible_ids),
                        "older_ids": [r["race_id"] for r in older],
                        "older_tiers": [r["tier"] for r in older],
                        "older_similar_ids": [r["race_id"] for r in similar],
                        "added_may_ids": [
                            r["race_id"]
                            for r in older
                            if (r["race_id"], horse) in additions
                        ],
                    },
                    "expansion_diagnostic": {
                        "older_count_before": len(before),
                        "older_form_before": previous,
                        "older_form_changed": previous != older_form,
                    },
                    "deletion_diagnostic": deletion_diagnostic(prior, matched),
                }
            )
    return {"rows": rows, "recent_ledger": current["ledger"]}


def summarize(rows):
    result = Counter(runner_rows=len(rows), races=len({r["race_id"] for r in rows}))
    for row in rows:
        f, s = row["features"], row["deletion_diagnostic"]
        result.update(
            older_supported=int(f["older_count"] > 0),
            older_only=int(f["older_count"] > 0 and f["prior90_count"] == 0),
            older_similar_supported=int(f["older_same_venue_similar_count"] > 0),
            added_may_supported=int(bool(row["provenance"]["added_may_ids"])),
            older_form_changed=int(row["expansion_diagnostic"]["older_form_changed"]),
            recent_fallback=int(f["fallback90"] is not None),
            recent_nonzero=int(Fraction(f["condition_delta90"]) != 0),
            single_similar_prior=int(f["similar90_count"] == 1),
            strict_sign_reversal=int(s["strict_sign_reversal"]),
            nonzero_can_become_zero=int(s["nonzero_can_become_zero"]),
            eligible_support_can_disappear=int(s["eligible_support_can_disappear"]),
        )
    return dict(result)


def check_time(created_at, cutoff):
    if (
        created_at.utcoffset() is None
        or cutoff.utcoffset() is None
        or created_at >= cutoff
    ):
        raise ValueError("memory_snapshot_not_before_cutoff")


def run(output):
    created = datetime.now(UTC)
    commitments = {k: read_pin(delta.PUBLIC / k, v) for k, v in delta.PINS.items()}
    packets = [
        read_pin(
            delta.FORWARD / d["race_date"] / f"prediction_{r['race_id']}.json",
            r["packet_sha256"],
        )
        for d in commitments["m0.json"]["days"]
        for r in d["races"]
    ]
    cutoff = min(datetime.fromisoformat(p["feature_cutoff_at"]) for p in packets)
    check_time(created, cutoff)
    extra = read_pin(expansion.ROOT / "report-v2.json", EXPANSION_SHA)
    baseline = read_pin(delta.HISTORY / "history.json", delta.HISTORY_SHA)["records"]
    contexts = read_pin(delta.HISTORY / "conditions.json", delta.CONDITIONS_SHA)[
        "records"
    ]
    if contexts.keys() & extra["extension_conditions"].keys():
        raise ValueError("memory_overlapping_conditions")
    targets, target_context, evidence = delta.load_targets(commitments["m0.json"])
    contexts = {**contexts, **extra["extension_conditions"]}
    if any(
        datetime.fromisoformat(c["captured_at"]) > created for c in contexts.values()
    ):
        raise ValueError("memory_future_source_capture")
    projection = project(
        targets, baseline, extra["extension_history"], {**contexts, **target_context}
    )
    reference = read_pin(expansion.PRIOR_REPORT, expansion.PRIOR_SHA)
    if projection["recent_ledger"] != reference["ledger"]:
        raise ValueError("memory_changed_published_recent_ledger")
    segments = defaultdict(list)
    for row in projection["rows"]:
        segments[row["race_id"].split("_")[1]].append(row)
    implementations = {
        p.name: digest(p.read_bytes())
        for p in (
            Path(__file__),
            Path(form.__file__),
            Path(condition.__file__),
            Path(delta.__file__),
            Path(expansion.__file__),
        )
    }
    report = {
        "format_version": "condition-memory-research-v1",
        "created_at": created.isoformat(),
        "first_cutoff": cutoff.isoformat(),
        "recipe": {
            "recent": "unchanged joint90-minus-expanded90 with existing fallback",
            "older": "[D-180,D-90); general career; rank prior mean=1/2,count=2",
            "similarity": "same physical venue, exact class, distance <=200m",
            "stress": "delete one recent observation; diagnostic, not a confidence interval",
        },
        "source_pins": {
            "history": delta.HISTORY_SHA,
            "conditions": delta.CONDITIONS_SHA,
            "expansion": EXPANSION_SHA,
            "recent_ledger": expansion.PRIOR_SHA,
        },
        "implementation": implementations,
        "plan_sha256": digest(PLAN.read_bytes()),
        "public_commitments_unchanged": delta.PINS,
        "input_evidence": evidence,
        "fit_count": 0,
        "target_outcomes_loaded": False,
        "training_approved": False,
        "historical_prerace_availability_verified": False,
        "model_promoted": False,
        "new_evaluation_arm_registered": False,
        "accuracy": None,
        "counts_as_70_percent_evidence": False,
        "summary": summarize(projection["rows"]),
        "by_meet": {k: summarize(v) for k, v in sorted(segments.items())},
        **projection,
    }
    check_time(datetime.now(UTC), cutoff)
    for name, sha in delta.PINS.items():
        read_pin(delta.PUBLIC / name, sha)
    output.mkdir(parents=True, exist_ok=False)
    return save(output / "report.json", report), report["summary"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    print(run(parser.parse_args().output_dir))
