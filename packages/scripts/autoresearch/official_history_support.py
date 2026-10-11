"""Capture/replay official result support without fitting or approving models."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode

import httpx
from shared.observed_partial_history import project_partial_history
from shared.official_result_support import parse_detail, parse_list, reconcile_group

from autoresearch.frozen_history_view import replay_frozen
from autoresearch.history_identity_audit import audit_replayed_seed
from autoresearch.kra_race_card_pdf_replay import parse_json
from autoresearch.kra_schedule_snapshot import _write_new
from autoresearch.observed_history_seed import (
    ROOT,
    digest,
    exclusive,
    pin,
    pinned_path,
    save,
)
from autoresearch.prerace_hash_witness import timestamp

BASE = "https://race.kra.co.kr/raceScore/"
FORMAT = "kra-official-history-archive-v1"
MAX_BYTES = 2 * 1024 * 1024


def request_plan(seed, seed_sha):
    ids = sorted({r["race_id"] for r in seed["records"]})
    requests = []
    for race_id in ids:
        day, meet, number = race_id.split("_")
        params = {
            "Act": "04",
            "Sub": "1",
            "meet": meet,
            "realRcDate": day,
            "realRcNo": number,
        }
        requests.append(
            {
                "key": race_id,
                "kind": "detail",
                "url": BASE + "ScoretableDetailList.do?" + urlencode(params),
            }
        )
    for region in (1, 2, 3):
        for page in range(1, 5):
            params = {"Act": "04", "Sub": "1", "meet": region, "pageIndex": page}
            requests.append(
                {
                    "key": f"list_{region}_{page}",
                    "kind": "list",
                    "url": BASE + "ScoretableScoreList.do?" + urlencode(params),
                }
            )
    return {
        "format_version": FORMAT,
        "seed_sha256": seed_sha,
        "requests": requests,
        "list_scope": "four_pages_per_region_no_global_no_race_claim",
    }


def replay_receipt(directory, receipt, request):
    if receipt["request"] != request:
        raise ValueError("official_request_mismatch")
    start, end = timestamp(receipt["started_at"]), timestamp(receipt["completed_at"])
    if end < start or (end - start).total_seconds() > 90:
        raise ValueError("official_capture_clock_invalid")
    if receipt["status"] == "fetch_error":
        return {"event_support": "unknown", "reason": "fetch_error", "rows": []}
    if receipt["status"] != "captured" or receipt["http_status"] != 200:
        raise ValueError("invalid_official_capture_status")
    raw = pinned_path(directory, receipt["raw"]).read_bytes()
    if not raw or len(raw) > MAX_BYTES or digest(raw) != receipt["raw"]["sha256"]:
        raise ValueError("official_raw_pin_mismatch")
    if len(raw) != receipt["byte_count"] or receipt["response_url"] != request["url"]:
        raise ValueError("official_response_mismatch")
    try:
        html = raw.decode(receipt["encoding"], errors="strict")
        return parse_detail(html) if request["kind"] == "detail" else parse_list(html)
    except (UnicodeError, LookupError, ValueError) as exc:
        return {"event_support": "unknown", "reason": f"parse_error:{exc}", "rows": []}


async def collect(directory, seed, seed_sha, *, client=None, delay=0.25):
    directory.mkdir(parents=True, exist_ok=True)
    plan = request_plan(seed, seed_sha)
    plan_path = directory / "plan.json"
    if plan_path.exists():
        if parse_json(plan_path.read_bytes()) != plan:
            raise ValueError("official_archive_plan_changed")
    else:
        save(plan_path, plan)
    owns = client is None
    client = client or httpx.AsyncClient(timeout=30, follow_redirects=False)
    receipts = []
    try:
        for index, request in enumerate(plan["requests"]):
            path = directory / (request["key"] + ".json")
            if path.exists():
                replay_receipt(directory, parse_json(path.read_bytes()), request)
            else:
                receipt = {
                    "request": request,
                    "started_at": datetime.now(UTC).isoformat(),
                    "status": "fetch_error",
                    "clock_basis": "local_system_only",
                }
                try:
                    async with asyncio.timeout(60):
                        async with client.stream("GET", request["url"]) as response:
                            response.raise_for_status()
                            if (
                                response.status_code != 200
                                or str(response.url) != request["url"]
                            ):
                                raise ValueError("noncanonical_official_response")
                            if (
                                response.headers.get("content-type", "")
                                .split(";")[0]
                                .lower()
                                != "text/html"
                            ):
                                raise ValueError("non_html_official_response")
                            raw = bytearray()
                            async for chunk in response.aiter_bytes():
                                raw.extend(chunk)
                                if len(raw) > MAX_BYTES:
                                    raise ValueError("official_response_too_large")
                            content = bytes(raw)
                            raw_path = directory / (
                                request["key"] + "_" + digest(content) + ".html"
                            )
                            if raw_path.exists():
                                if raw_path.read_bytes() != content:
                                    raise ValueError("official_orphan_raw_mismatch")
                            else:
                                _write_new(raw_path, content)
                            receipt.update(
                                status="captured",
                                raw=pin(directory, raw_path),
                                byte_count=len(content),
                                encoding=response.encoding or "euc-kr",
                                http_status=response.status_code,
                                response_url=str(response.url),
                                http_date=response.headers.get("date"),
                            )
                except (httpx.HTTPError, TimeoutError, ValueError) as exc:
                    receipt["error_type"] = type(exc).__name__
                receipt["completed_at"] = datetime.now(UTC).isoformat()
                save(path, receipt)
                replay_receipt(directory, receipt, request)
                await asyncio.sleep(delay)
            receipts.append(pin(directory, path))
            if (index + 1) % 50 == 0:
                print(
                    json.dumps(
                        {
                            "completed_requests": index + 1,
                            "total": len(plan["requests"]),
                        }
                    ),
                    flush=True,
                )
    finally:
        if owns:
            await client.aclose()
    manifest = {
        "format_version": FORMAT,
        "plan": pin(directory, plan_path),
        "receipts": receipts,
    }
    path = directory / "archive.json"
    if path.exists():
        if parse_json(path.read_bytes()) != manifest:
            raise ValueError("official_archive_changed")
        sha = digest(path.read_bytes())
    else:
        sha = save(path, manifest)
    return {"archive": str(path), "sha256": sha, "requests": len(receipts)}


def replay_archive(directory, archive_sha, seed, seed_sha, cutoff=None):
    raw = (directory / "archive.json").read_bytes()
    if digest(raw) != archive_sha:
        raise ValueError("official_archive_pin_mismatch")
    archive = parse_json(raw)
    plan = parse_json(pinned_path(directory, archive["plan"]).read_bytes())
    expected = request_plan(seed, seed_sha)
    if archive["format_version"] != FORMAT or plan != expected:
        raise ValueError("official_archive_plan_mismatch")
    if len(archive["receipts"]) != len(plan["requests"]):
        raise ValueError("official_archive_incomplete")
    evidence = {}
    for ref, request in zip(archive["receipts"], plan["requests"], strict=True):
        receipt = parse_json(pinned_path(directory, ref).read_bytes())
        if cutoff and timestamp(receipt["completed_at"]) > timestamp(cutoff):
            raise ValueError("official_evidence_after_cutoff")
        evidence[request["key"]] = {
            "receipt": ref,
            "capture": receipt,
            "parsed": replay_receipt(directory, receipt, request),
        }
    return evidence


def materialize(
    root,
    seed_path,
    seed_sha,
    directory,
    archive_sha,
    corpus_path,
    corpus_sha,
    cutoff=None,
):
    seed = replay_frozen(root, seed_path, seed_sha, cutoff=cutoff)
    evidence = replay_archive(directory, archive_sha, seed, seed_sha, cutoff)
    raw = corpus_path.read_bytes()
    if digest(raw) != corpus_sha:
        raise ValueError("official_corpus_pin_mismatch")
    corpus = parse_json(raw)
    groups = defaultdict(list)
    for row in seed["records"]:
        groups[row["race_id"]].append(row)
    comparisons, supported, linked_unresolved = [], set(), set()
    for race_id, records in sorted(groups.items()):
        result = reconcile_group(records, evidence[race_id]["parsed"])
        result["evidence"] = evidence[race_id]
        comparisons.append(result)
        for row in result["rows"]:
            key = race_id, row["horse_id"]
            if row["ranked_feature_supported"]:
                supported.add(key)
            if row["event_linked_api_unresolved"]:
                linked_unresolved.add(key)
    group_support = {r["race_id"]: r for r in comparisons}
    races, seen = [], set()
    for target in corpus["ledger"]:
        race = {"race_id": target["race_id"], "roster": target["roster"]}
        if race["race_id"] in seen:
            raise ValueError("duplicate_official_target")
        seen.add(race["race_id"])
        old = project_partial_history(race, seed)
        rows = []
        rank_lookup = {
            (r["race_id"], r["horse_id"]): r["raw_ord"] for r in seed["records"]
        }
        for runner in old["feature_rows"]:
            used, withheld, unresolved = [], [], []
            for link in runner["lineage"]:
                key = link["race_id"], runner["horse_id"]
                if key in supported:
                    used.append(link)
                elif key in linked_unresolved:
                    unresolved.append(link)
                else:
                    group = group_support[link["race_id"]]
                    reason = group["reason_codes"] or ["rank_or_time_not_supported"]
                    withheld.append({**link, "reason_codes": reason})
            ranks = [
                int(rank_lookup[(link["race_id"], runner["horse_id"])]) for link in used
            ]
            rows.append(
                {
                    "horse_id": runner["horse_id"],
                    "chul_no": runner["chul_no"],
                    "features": {
                        "ranked_finish_count_90d": len(ranks),
                        "win_count_90d": ranks.count(1),
                        "top3_count_90d": sum(r <= 3 for r in ranks),
                        "top3_fraction_90d": sum(r <= 3 for r in ranks) / len(ranks)
                        if ranks
                        else None,
                        "event_linked_api_unresolved_count_90d": len(unresolved),
                    },
                    "used_ranked_lineage": used,
                    "linked_unresolved_lineage": unresolved,
                    "withheld_lineage": withheld,
                }
            )
        races.append(
            {
                "race_id": race["race_id"],
                "observed_partial_v1": old,
                "official_supported_partial_v1": rows,
            }
        )
    if not races:
        raise ValueError("empty_official_target_corpus")
    listed = set()
    list_errors = []
    list_scope = {}
    for region in (1, 2, 3):
        region_rows = []
        for page in range(1, 5):
            key = f"list_{region}_{page}"
            parsed = evidence[key]["parsed"]
            if isinstance(parsed, list):
                region_rows.extend(parsed)
            else:
                list_errors.append(key)
        ids = [r["race_id"] for r in region_rows]
        ordered = sorted({r["list_order"] for r in region_rows})
        start = min(u["day"] for u in seed["inventory"])
        end = max(u["day"] for u in seed["inventory"])
        list_scope[str(region)] = {
            "pages": 4,
            "listed_races": len(ids),
            "range_reached": bool(ids) and min(r[:8] for r in ids) <= start,
            "unique_races": len(set(ids)) == len(ids),
            "consecutive_list_orders": bool(ordered)
            and ordered == list(range(1, max(ordered) + 1)),
            "complete_actual_start_history_verified": False,
        }
        listed.update(r for r in ids if start <= r[:8] <= end)
    return {
        "format_version": "kra-official-supported-partial-v1",
        "seed_sha256": seed_sha,
        "archive_sha256": archive_sha,
        "corpus_sha256": corpus_sha,
        "implementation": {
            n: digest((ROOT / n).read_bytes())
            for n in (
                "shared/official_result_support.py",
                "autoresearch/official_history_support.py",
                "autoresearch/frozen_history_view.py",
                "shared/observed_partial_history.py",
                "shared/observed_result_history.py",
                "autoresearch/history_identity_audit.py",
            )
        },
        "history_source_cutoff": cutoff,
        "availability_basis": "local_clocks_only",
        "groups": comparisons,
        "group_count": len(comparisons),
        "event_support_counts": dict(
            Counter(r["official_event_support"] for r in comparisons)
        ),
        "roster_support_counts": dict(
            Counter(r["roster_support"] for r in comparisons)
        ),
        "supported_ranked_rows": len(supported),
        "event_linked_unresolved_rows": len(linked_unresolved),
        "official_lists": {k: v for k, v in evidence.items() if k.startswith("list_")},
        "official_list_scope": list_scope,
        "official_list_errors": list_errors,
        "official_list_only_races": sorted(listed - groups.keys()),
        "seed_not_in_captured_lists": sorted(groups.keys() - listed),
        "quality_audit": audit_replayed_seed(root, seed, seed_sha),
        "race_count": len(races),
        "runner_count": sum(len(r["official_supported_partial_v1"]) for r in races),
        "races": races,
        "zero_count_meaning": "no_supported_observations_in_selected_sources",
        "scope": "all_pinned_diagnostic_rosters_not_future_national_universe",
        "training_approved": False,
        "historical_pre_race_availability_verified": False,
        "independent_timestamp_verified": False,
        "complete_actual_start_history_verified": False,
        "prediction_registration_verified": False,
        "counts_as_70_percent_evidence": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("collect", "materialize"))
    for key in ("root", "seed", "archive-dir", "corpus", "output"):
        parser.add_argument(
            "--" + key, type=Path, required=key in ("root", "seed", "archive-dir")
        )
    for key in (
        "seed-sha256",
        "archive-sha256",
        "corpus-sha256",
        "history-source-cutoff",
    ):
        parser.add_argument("--" + key, required=key == "seed-sha256")
    args = parser.parse_args()
    with exclusive(args.root):
        if args.action == "collect":
            seed = replay_frozen(args.root, args.seed, args.seed_sha256)
            result = asyncio.run(collect(args.archive_dir, seed, args.seed_sha256))
        else:
            if not all(
                (args.archive_sha256, args.corpus, args.corpus_sha256, args.output)
            ):
                parser.error("materialize requires archive/corpus pins and output")
            report = materialize(
                args.root,
                args.seed,
                args.seed_sha256,
                args.archive_dir,
                args.archive_sha256,
                args.corpus,
                args.corpus_sha256,
                args.history_source_cutoff,
            )
            result = {
                "output": str(args.output),
                "sha256": save(args.output, report),
                **{
                    k: report[k]
                    for k in (
                        "group_count",
                        "event_support_counts",
                        "roster_support_counts",
                        "supported_ranked_rows",
                        "event_linked_unresolved_rows",
                        "race_count",
                        "runner_count",
                    )
                },
            }
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
