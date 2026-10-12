"""Replay-backed prior-event coverage for acquisition planning, not model fitting."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from shared.official_result_support import reconcile_group

from autoresearch.frozen_history_view import replay_frozen
from autoresearch.observed_history_seed import digest, save
from autoresearch.official_history_support import replay_archive


def project(records, groups, *, target_ids=None):
    by_race, by_horse = defaultdict(list), defaultdict(list)
    seen = set()
    for row in records:
        key = row["race_id"], row["horse_id"]
        if key in seen:
            raise ValueError("duplicate_history_study_member")
        seen.add(key)
        by_race[row["race_id"]].append(row)
        by_horse[row["horse_id"]].append(row)
    if set(groups) != set(by_race) or not records:
        raise ValueError("history_study_group_membership")
    targets = set(by_race) if target_ids is None else set(target_ids)
    if not targets or not targets <= by_race.keys():
        raise ValueError("history_study_target_membership")
    ranked, linked = set(), set()
    for identity, group in groups.items():
        if group["race_id"] != identity:
            raise ValueError("history_study_group_identity")
        if (group["official_event_support"], group["roster_support"]) != (
            "confirmed",
            "exact",
        ):
            continue
        expected = {(r["horse_id"], r["chul_no"]) for r in by_race[identity]}
        actual = {(r["horse_id"], r["chul_no"]) for r in group["rows"]}
        if actual != expected or len(actual) != len(group["rows"]):
            raise ValueError("history_study_roster_mismatch")
        for row in group["rows"]:
            key = identity, row["horse_id"]
            if row["ranked_feature_supported"]:
                ranked.add(key)
            elif row["event_linked_api_unresolved"]:
                linked.add(key)
    output, strata = [], defaultdict(Counter)
    for identity, members in sorted(by_race.items()):
        if identity not in targets:
            continue
        day, meet, _ = identity.split("_")
        lower = (datetime.strptime(day, "%Y%m%d") - timedelta(days=90)).strftime(
            "%Y%m%d"
        )
        complete_one = complete_three = True
        for row in sorted(members, key=lambda r: r["chul_no"]):
            prior = [
                r for r in by_horse[row["horse_id"]] if lower <= r["race_id"][:8] < day
            ]
            supported = [r for r in prior if (r["race_id"], r["horse_id"]) in ranked]
            unresolved = [r for r in prior if (r["race_id"], r["horse_id"]) in linked]
            withheld = len(prior) - len(supported) - len(unresolved)
            complete_one &= len(supported) >= 1
            complete_three &= len(supported) >= 3
            target_supported = (identity, row["horse_id"]) in ranked
            output.append(
                {
                    "race_id": identity,
                    "horse_id": row["horse_id"],
                    "chul_no": row["chul_no"],
                    "target_rank_supported": target_supported,
                    "prior_supported_ranked_count_90d": len(supported),
                    "prior_linked_unresolved_count_90d": len(unresolved),
                    "prior_withheld_count_90d": withheld,
                    "prior_supported_race_ids": sorted(r["race_id"] for r in supported),
                }
            )
            for scope in ("all", f"month:{day[:6]}", f"meet:{meet}"):
                strata[scope].update(
                    {
                        "runner_rows": 1,
                        "target_rank_supported": int(target_supported),
                        "with_prior_ranked": int(bool(supported)),
                        "with_three_prior_ranked": int(len(supported) >= 3),
                        "with_withheld_prior": int(withheld > 0),
                        "with_linked_unresolved_prior": int(bool(unresolved)),
                    }
                )
        for scope in ("all", f"month:{day[:6]}", f"meet:{meet}"):
            strata[scope].update(
                {
                    "race_groups": 1,
                    "all_runners_have_prior_ranked": int(complete_one),
                    "all_runners_have_three_prior_ranked": int(complete_three),
                }
            )
    return {"rows": output, "strata": dict(sorted(strata.items()))}


def replay_source(root, seed_path, seed_sha, archive_dir, archive_sha):
    seed = replay_frozen(root, seed_path, seed_sha)
    evidence = replay_archive(archive_dir, archive_sha, seed, seed_sha)
    by_race = defaultdict(list)
    for row in seed["records"]:
        by_race[row["race_id"]].append(row)
    groups = {
        identity: reconcile_group(rows, evidence[identity]["parsed"])
        for identity, rows in by_race.items()
    }
    return seed, groups


def materialize(root, seed_path, seed_sha, archive_dir, archive_sha, *, extensions=()):
    seed, groups = replay_source(root, seed_path, seed_sha, archive_dir, archive_sha)
    baseline = project(seed["records"], groups)
    records, targets = list(seed["records"]), set(groups)
    sources = []
    for source in extensions:
        extra_seed, extra_groups = replay_source(*source)
        if groups.keys() & extra_groups.keys():
            raise ValueError("history_study_overlapping_sources")
        if max(r["race_id"][:8] for r in extra_seed["records"]) >= min(
            r["race_id"][:8] for r in seed["records"]
        ):
            raise ValueError("history_study_extension_not_earlier")
        records.extend(extra_seed["records"])
        groups.update(extra_groups)
        sources.append(
            {
                "seed_sha256": source[2],
                "archive_sha256": source[4],
                "source_inventory_status_counts": extra_seed["status_counts"],
                "runner_rows": len(extra_seed["records"]),
                "race_groups": len(extra_groups),
                "event_support_counts": dict(
                    Counter(g["official_event_support"] for g in extra_groups.values())
                ),
                "supported_ranked_rows": sum(
                    r["ranked_feature_supported"]
                    for g in extra_groups.values()
                    for r in g["rows"]
                ),
            }
        )
    expanded = project(records, groups, target_ids=targets)
    if [(r["race_id"], r["chul_no"], r["horse_id"]) for r in expanded["rows"]] != [
        (r["race_id"], r["chul_no"], r["horse_id"]) for r in baseline["rows"]
    ]:
        raise ValueError("history_study_changed_target_roster")
    return {
        "format_version": "history-coverage-study-v1",
        "seed_sha256": seed_sha,
        "archive_sha256": archive_sha,
        "implementation_sha256": digest(Path(__file__).read_bytes()),
        "event_support_counts": dict(
            Counter(g["official_event_support"] for g in groups.values())
        ),
        "source_inventory_status_counts": seed["status_counts"],
        "extension_sources": sources,
        "baseline_strata": baseline["strata"],
        "coverage_delta": {
            scope: {
                key: value - baseline["strata"][scope][key]
                for key, value in counts.items()
            }
            for scope, counts in expanded["strata"].items()
        },
        "scope": "complete_archived_seed_not_complete_national_race_universe",
        "window": "target_day_minus_90_inclusive_to_target_day_exclusive",
        "zero_meaning": "no_supported_prior_observation_not_debut",
        "training_approved": False,
        "historical_pre_race_availability_verified": False,
        "complete_actual_start_history_verified": False,
        "counts_as_70_percent_evidence": False,
        **expanded,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--seed-sha256", required=True)
    parser.add_argument("--archive-dir", type=Path, required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--history-source",
        nargs=5,
        action="append",
        default=[],
        metavar=("ROOT", "SEED", "SEED_SHA256", "ARCHIVE_DIR", "ARCHIVE_SHA256"),
        help="Earlier, non-overlapping history; targets remain the entire base seed",
    )
    args = parser.parse_args()
    result = materialize(
        args.root,
        args.seed,
        args.seed_sha256,
        args.archive_dir,
        args.archive_sha256,
        extensions=[
            (Path(a), Path(b), c, Path(d), e) for a, b, c, d, e in args.history_source
        ],
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sha = save(args.output, result)
    print(json.dumps({"sha256": sha, "strata": result["strata"]}, indent=2))


if __name__ == "__main__":
    main()
