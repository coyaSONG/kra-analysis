"""Replay the May acquisition and audit coverage, without fitting or rescoring."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path

from autoresearch import condition_delta_diagnostic as delta
from autoresearch import condition_form_research as condition
from autoresearch import history_form_research as form
from autoresearch import official_history_support as support
from autoresearch import race_conditions
from autoresearch.frozen_history_view import replay_frozen
from autoresearch.observed_history_seed import digest, save
from autoresearch.official_history_catalog import read_pin

ROOT = Path(".cache/autoresearch/history-gap-expansion-20261014")
SEED_SHA = "eb54c47dcabecca2f579f7e6821ddc3ffa400e5b935eaeca0353f6d01c77b73a"
PRIOR_REPORT = Path(".cache/autoresearch/condition-delta-20261014/run-2/report.json")
PRIOR_SHA = "69d675229d00b00e82f7aed10dd0d951788d5cf7f01965523942dcba5dac1215"
DISCOVERY_SHA = "dd76fe35cf9c4d16fd5343b5dc847581faf8e2168803b9819b62a95ef30704fc"
DISCOVERY_SEED_SHA = "234e6bebcb2497fad794ea422a8eec33a5c82e602ec0249067d41b1fdee8ba4b"
ARCHIVES = (
    (
        "may-catalog/details",
        "may-catalog/index.json",
        "ce18a669a35c0d37ee7b92ee7fd7813ce342e96e3de3dec6dad09554b5bd7949",
        "3bbdbad2fd5da816685297f224b991d6f631f3a2b6b173db9cf33ff9d6fb38d7",
    ),
    (
        "additional-official",
        "official-gap-index.json",
        "6d7559a66f47eccbfa9481844fe794ab7bc92becb540a641e9af479a27f2d809",
        "5fb136518473aaf45e605bb878cceaa4c00e8ce34dccf41d50a3bece277c676f",
    ),
)


def supported_extension(records, evidence):
    history, groups = [], []
    for identity, members in sorted(form.group_records(records).items()):
        comparison = support.reconcile_group(members, evidence[identity]["parsed"])
        conflict = any(
            row["rank_support"] == "conflict" or row["time_support"] == "conflict"
            for row in comparison["rows"]
        )
        admitted = [
            row
            for row in comparison["rows"]
            if row["ranked_feature_supported"] and not conflict
        ]
        history.extend(
            {
                "race_id": identity,
                "horse_id": row["horse_id"],
                "rank": int(row["official_row"]["rank_text"]),
                "observed_roster_size": len(members),
                "tier": "dual_supported",
            }
            for row in admitted
        )
        groups.append(
            {
                **comparison,
                "observed_rows": len(members),
                "admitted_rows": len(admitted),
                "group_conflict_withheld": conflict,
                "official_receipt": evidence[identity]["receipt"],
            }
        )
    return history, groups


def coverage(targets, baseline, extension, contexts):
    if not targets:
        raise ValueError("expansion_empty_targets")
    old, _ = form.index_history(baseline)
    new, _ = form.index_history(extension)
    form.index_history(baseline + extension)  # Reject overlapping identities.
    if any(r["race_id"][:8] >= min(targets)[:8] for r in extension):
        raise ValueError("expansion_target_or_future_result")
    rows, strata = [], defaultdict(Counter)
    for identity, roster in sorted(targets.items()):
        if not roster or any(set(r) != {"horse_id", "chul_no"} for r in roster):
            raise ValueError("expansion_target_not_identity_only")
        form.group_records([{"race_id": identity, **r} for r in roster])
        for runner in roster:
            horse, day = runner["horse_id"], identity[:8]
            before = form.prior_rows(old[horse], day, "expanded180")
            added = form.prior_rows(new[horse], day, "expanded180")
            base90 = form.prior_rows(old[horse], day, "expanded90")
            if form.prior_rows(new[horse], day, "expanded90"):
                raise ValueError("expansion_changes_frozen_90d_history")
            old_sim, new_sim = [
                [
                    r
                    for r in prior
                    if condition.eligible(
                        contexts.get(identity, {}),
                        contexts.get(r["race_id"], {}),
                        "joint90",
                    )
                ]
                for prior in (before, added)
            ]
            row = {
                "race_id": identity,
                **runner,
                "prior_90d_count_unchanged": len(base90),
                "prior_180d_before": len(before),
                "prior_180d_after": len(before) + len(added),
                "new_prior_ids": [r["race_id"] for r in added],
                "similar_180d_before": len(old_sim),
                "similar_180d_after": len(old_sim) + len(new_sim),
                "new_similar_ids": [r["race_id"] for r in new_sim],
            }
            rows.append(row)
            for scope in ("all", "meet:" + identity.split("_")[1]):
                strata[scope].update(
                    runner_rows=1,
                    rows_with_new_history=int(bool(added)),
                    prior_180d_before=int(bool(before)),
                    prior_180d_after=int(bool(before or added)),
                    three_prior_180d_before=int(len(before) >= 3),
                    three_prior_180d_after=int(len(before) + len(added) >= 3),
                    similar_180d_before=int(bool(old_sim)),
                    similar_180d_after=int(bool(old_sim or new_sim)),
                    no_90d_but_new_older_history=int(not base90 and bool(added)),
                )
    return {"rows": rows, "strata": dict(strata)}


def run(output):
    seed = replay_frozen(ROOT / "may-api", ROOT / "may-api/seed.json", SEED_SHA)
    evidence, contexts = {}, {}
    for directory, index_path, index_sha, archive_sha in ARCHIVES:
        index = read_pin(ROOT / index_path, index_sha)
        replayed = support.replay_archive(
            ROOT / directory, archive_sha, index, index_sha
        )
        for row in index["records"]:
            identity = row["race_id"]
            if identity in evidence:
                raise ValueError("expansion_duplicate_official_source")
            item = replayed[identity]
            evidence[identity] = item
            contexts[identity] = race_conditions.from_capture(
                ROOT / directory,
                identity,
                item["capture"],
                {
                    "archive": directory,
                    "archive_sha256": archive_sha,
                    "receipt": item["receipt"],
                },
            )
    extra, groups = supported_extension(seed["records"], evidence)
    base = read_pin(delta.HISTORY / "history.json", delta.HISTORY_SHA)["records"]
    old_context = read_pin(delta.HISTORY / "conditions.json", delta.CONDITIONS_SHA)[
        "records"
    ]
    discovery_seed = read_pin(ROOT / "discovery-seed.json", DISCOVERY_SEED_SHA)
    discovery = support.replay_archive(
        ROOT / "discovery", DISCOVERY_SHA, discovery_seed, DISCOVERY_SEED_SHA
    )
    listed = {
        r["race_id"]
        for item in discovery.values()
        for r in item["parsed"]
        if "20260718" <= r["race_id"][:8] <= "20261011"
    }
    if old_context.keys() & contexts.keys():
        raise ValueError("expansion_overlapping_conditions")
    for name, sha in delta.PINS.items():
        read_pin(delta.PUBLIC / name, sha)
    targets, target_context, _ = delta.load_targets(
        read_pin(delta.PUBLIC / "m0.json", delta.PINS["m0.json"])
    )
    all_context = {**old_context, **contexts, **target_context}
    previous = read_pin(PRIOR_REPORT, PRIOR_SHA)
    projected = delta.project(targets, base + extra, all_context)
    if projected["ledger"] != previous["ledger"]:
        raise ValueError("expansion_changed_frozen_contrast")
    report = {
        "format_version": "may-history-expansion-audit-v1",
        "api_seed_sha256": SEED_SHA,
        "discovery_sha256": DISCOVERY_SHA,
        "recent_listed_races": len(listed),
        "recent_listed_missing_conditions": sorted(
            i for i in listed if old_context.get(i, {}).get("status") != "observed"
        ),
        "archives": ARCHIVES,
        "baseline_history_sha256": delta.HISTORY_SHA,
        "baseline_conditions_sha256": delta.CONDITIONS_SHA,
        "prior_report_sha256": PRIOR_SHA,
        "api_rows": len(seed["records"]),
        "api_units": seed["status_counts"],
        "api_requests": seed["request_reservations"],
        "supported_new_rows": len(extra),
        "race_count": len(groups),
        "condition_status": dict(Counter(c["status"] for c in contexts.values())),
        "groups": groups,
        "extension_history": extra,
        "extension_conditions": contexts,
        "coverage": coverage(targets, base, extra, all_context),
        "original_90d_contrast_unchanged": True,
        "public_commitments": delta.PINS,
        "fit_count": 0,
        "training_approved": False,
        "accuracy": None,
        "historical_pre_race_availability_verified": False,
        "counts_as_70_percent_evidence": False,
        "code_sha256": digest(Path(__file__).read_bytes()),
    }
    for name, sha in delta.PINS.items():
        read_pin(delta.PUBLIC / name, sha)
    return save(output, report), report["coverage"]["strata"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(run(args.output))
