"""Official HTML-only acquisition; never an API seed or training approval."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from shared.kra_race_identity import validate_race_identity
from shared.official_result_support import LIST_CAPTION, seconds, selected, tables

from autoresearch import official_history_support as support
from autoresearch.kra_race_card_pdf_replay import parse_json
from autoresearch.observed_history_seed import digest, pinned_path, save

INDEX_FORMAT = "official-list-request-index-v1"


def read_pin(path, sha):
    raw = path.read_bytes()
    if digest(raw) != sha:
        raise ValueError("catalog_pin_mismatch")
    return parse_json(raw)


def make_index(discovery, discovery_sha, start, end):
    validate_race_identity(1, start, 1)
    validate_race_identity(1, end, 1)
    if start > end:
        raise ValueError("catalog_invalid_window")
    archive = read_pin(discovery / "archive.json", discovery_sha)
    plan = parse_json(pinned_path(discovery, archive["plan"]).read_bytes())
    # This discovery archive has only the fixed 12 list requests, no API rows.
    evidence = support.replay_archive(
        discovery, discovery_sha, {"records": []}, plan["seed_sha256"]
    )
    selected, bounds, seen = set(), {}, set()
    for key, item in evidence.items():
        rows = item["parsed"]
        if not isinstance(rows, list) or not rows:
            raise ValueError("catalog_discovery_incomplete")
        ids = [r["race_id"] for r in rows]
        if len(set(ids)) != len(ids) or seen.intersection(ids):
            raise ValueError("catalog_duplicate_listing")
        seen.update(ids)
        selected.update(i for i in ids if start <= i[:8] <= end)
        bounds[key] = {
            "first_date": max(i[:8] for i in ids),
            "last_date": min(i[:8] for i in ids),
            "race_count": len(ids),
        }
    if not selected:
        raise ValueError("catalog_no_listed_targets")
    if len(selected) + 12 > 512:
        raise ValueError("catalog_request_budget_exceeded")
    return {
        "format_version": INDEX_FORMAT,
        "source_tier": "official_html_only",
        "discovery_sha256": discovery_sha,
        "start": start,
        "end": end,
        "list_bounds": bounds,
        "records": [{"race_id": identity} for identity in sorted(selected)],
        "national_completeness_verified": False,
        "api_corroboration_verified": False,
    }


async def collect(
    directory, discovery, discovery_sha, start, end, *, client=None, delay=0.25
):
    index = make_index(discovery, discovery_sha, start, end)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "index.json"
    if path.exists():
        if parse_json(path.read_bytes()) != index:
            raise ValueError("catalog_index_changed")
        index_sha = digest(path.read_bytes())
    else:
        index_sha = save(path, index)
    receipt = await support.collect(
        directory / "details", index, index_sha, client=client, delay=delay
    )
    return {"index_sha256": index_sha, **receipt}


def list_provenance(discovery, archive_sha):
    archive = read_pin(discovery / "archive.json", archive_sha)
    plan = parse_json(pinned_path(discovery, archive["plan"]).read_bytes())
    evidence = support.replay_archive(
        discovery, archive_sha, {"records": []}, plan["seed_sha256"]
    )
    result = {}
    for key, source in evidence.items():
        capture = source["capture"]
        html = (
            pinned_path(discovery, capture["raw"])
            .read_bytes()
            .decode(capture["encoding"])
        )
        positions = {}
        for position, row in enumerate(selected(tables(html), LIST_CAPTION).rows):
            if row and all(cell.tag == "th" for cell in row):
                continue
            order = int(row[0].text)
            if order in positions:
                raise ValueError("catalog_duplicate_list_order")
            positions[order] = {
                "page_key": key,
                "row_index": position,
                "list_order": order,
                "result_links": row[3].links,
                "result_text": row[3].text,
                "receipt": source["receipt"],
                # A notice can refer to one race within a day. Withhold the whole
                # listed row until reviewed instead of guessing its scope.
                "void_notice_requires_review": "\uacbd\uc8fc\ubd88\uc131\ub9bd"
                in row[3].text,
            }
        for item in source["parsed"]:
            result[item["race_id"]] = positions[item["list_order"]]
    return result


def replay(directory, index_sha, archive_sha, discovery):
    index = read_pin(directory / "index.json", index_sha)
    if index.get("format_version") != INDEX_FORMAT or index != make_index(
        discovery, index["discovery_sha256"], index["start"], index["end"]
    ):
        raise ValueError("catalog_index_replay_mismatch")
    evidence = support.replay_archive(
        directory / "details", archive_sha, index, index_sha
    )
    listings = list_provenance(discovery, index["discovery_sha256"])
    groups, records = [], []
    for item in index["records"]:
        identity = item["race_id"]
        source = evidence[identity]
        parsed = source["parsed"]
        status = parsed["event_support"]
        if status == "confirmed" and parsed["race_id"] != identity:
            status = "identity_conflict"
        members = parsed["rows"] if status == "confirmed" else []
        if status == "confirmed" and not members:
            raise ValueError("catalog_empty_confirmed_roster")
        reason = parsed.get("reason")
        if status == "identity_conflict":
            reason = "official_body_identity_mismatch"
        if status == "confirmed" and listings[identity]["void_notice_requires_review"]:
            status = "list_notice_requires_review"
            reason = "list_void_notice_scope_unresolved"
        groups.append(
            {
                "race_id": identity,
                "status": status,
                "reason": reason,
                "runner_count": len(members),
                "receipt": source["receipt"],
                "listing": listings[identity],
            }
        )
        for row in members:
            rank = row["rank_text"]
            duration = seconds(row["time_text"])
            numeric = (
                status == "confirmed"
                and rank.isascii()
                and rank.isdigit()
                and 1 <= int(rank) <= 20
                and duration is not None
                and duration > 0
            )
            records.append(
                {
                    "race_id": identity,
                    "horse_id": row["horse_id"],
                    "chul_no": row["chul_no"],
                    "rank_text": rank,
                    "time_text": row["time_text"],
                    "row_index": row["row_index"],
                    "timing_locations": row["timing_locations"],
                    "numeric_rank_time_observed": numeric,
                    "source_available_at": source["capture"]["completed_at"],
                    "receipt": source["receipt"],
                }
            )
    return {
        "format_version": "official-html-only-history-v1",
        "source_tier": "official_html_only",
        "index_sha256": index_sha,
        "archive_sha256": archive_sha,
        "discovery_sha256": index["discovery_sha256"],
        "start": index["start"],
        "end": index["end"],
        "groups": groups,
        "records": records,
        "status_counts": dict(Counter(g["status"] for g in groups)),
        "numeric_rank_time_rows": sum(r["numeric_rank_time_observed"] for r in records),
        "api_corroboration_verified": False,
        "training_approved": False,
        "historical_pre_race_availability_verified": False,
        "complete_actual_start_history_verified": False,
        "counts_as_70_percent_evidence": False,
    }


def compare(base, catalog):
    if base.get("format_version") != "history-coverage-study-v1":
        raise ValueError("catalog_invalid_baseline")
    history, seen = defaultdict(list), set()
    for row in catalog["records"]:
        key = row["race_id"], row["horse_id"]
        if key in seen:
            raise ValueError("catalog_duplicate_history_member")
        seen.add(key)
        if row["numeric_rank_time_observed"]:
            history[row["horse_id"]].append(row["race_id"])
    output, targets, strata = [], set(), defaultdict(Counter)
    for row in base["rows"]:
        identity, horse = row["race_id"], row["horse_id"]
        key = identity, horse
        if key in targets:
            raise ValueError("catalog_duplicate_target")
        targets.add(key)
        day, meet, _ = identity.split("_")
        lower = (datetime.strptime(day, "%Y%m%d") - timedelta(days=90)).strftime(
            "%Y%m%d"
        )
        api_ids = row["prior_supported_race_ids"]
        if len(set(api_ids)) != len(api_ids) or any(
            not lower <= i[:8] < day for i in api_ids
        ):
            raise ValueError("catalog_invalid_baseline_lineage")
        if len(api_ids) != row["prior_supported_ranked_count_90d"]:
            raise ValueError("catalog_baseline_count_mismatch")
        html_ids = sorted(i for i in history[horse] if lower <= i[:8] < day)
        if set(api_ids).intersection(html_ids):
            raise ValueError("catalog_overlapping_source_tiers")
        api_n, html_n = len(api_ids), len(html_ids)
        output.append(
            {
                "race_id": identity,
                "horse_id": horse,
                "chul_no": row["chul_no"],
                "api_supported_prior_count": api_n,
                "html_only_prior_count": html_n,
                "combined_prior_count": api_n + html_n,
                "html_only_prior_race_ids": html_ids,
            }
        )
        for scope in ("all", f"month:{day[:6]}", f"meet:{meet}"):
            strata[scope].update(
                {
                    "runner_rows": 1,
                    "api_with_prior": int(api_n > 0),
                    "api_with_three_prior": int(api_n >= 3),
                    "html_only_with_prior": int(html_n > 0),
                    "html_only_with_three_prior": int(html_n >= 3),
                    "combined_with_prior": int(api_n + html_n > 0),
                    "combined_with_three_prior": int(api_n + html_n >= 3),
                    "newly_covered_by_html_only": int(api_n == 0 and html_n > 0),
                }
            )
    if not output or len(output) != base["strata"]["all"]["runner_rows"]:
        raise ValueError("catalog_target_count_mismatch")
    return {"rows": output, "strata": dict(sorted(strata.items()))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("collect", "compare"))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--discovery", type=Path, required=True)
    parser.add_argument("--discovery-sha256")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--index-sha256")
    parser.add_argument("--archive-sha256")
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--baseline-sha256")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.action == "collect":
        if not all((args.discovery_sha256, args.start, args.end)):
            parser.error("collect requires discovery pin and date bounds")
        print(
            json.dumps(
                asyncio.run(
                    collect(
                        args.directory,
                        args.discovery,
                        args.discovery_sha256,
                        args.start,
                        args.end,
                    )
                )
            )
        )
        return
    if not all(
        (
            args.index_sha256,
            args.archive_sha256,
            args.baseline,
            args.baseline_sha256,
            args.output,
        )
    ):
        parser.error("compare requires index/archive/baseline pins and output")
    catalog = replay(
        args.directory, args.index_sha256, args.archive_sha256, args.discovery
    )
    result = {
        "format_version": "official-html-only-coverage-comparison-v1",
        "catalog": catalog,
        "baseline_report_sha256": args.baseline_sha256,
        "implementation_sha256": digest(Path(__file__).read_bytes()),
        "training_approved": False,
        "counts_as_70_percent_evidence": False,
        **compare(read_pin(args.baseline, args.baseline_sha256), catalog),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sha = save(args.output, result)
    print(
        json.dumps(
            {
                "sha256": sha,
                "status_counts": catalog["status_counts"],
                "catalog_rows": len(catalog["records"]),
                "numeric_rank_time_rows": catalog["numeric_rank_time_rows"],
                "strata": result["strata"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
