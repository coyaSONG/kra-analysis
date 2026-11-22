"""Optional, bounded API26 collection for an already reconciled whole card."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import defaultdict
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

import httpx
from shared.kra_entry_sheet import build_entry_snapshot, parse_entry_sheet_page
from shared.kra_race_identity import validate_race_identity

from autoresearch.history_api_probe import classify
from autoresearch.kra_entry_sheet_snapshot import (
    ENTRY_URL,
    MAX_PAGE_BYTES,
    PAGE_SIZE,
    collect_entry_sheet_snapshot,
)
from autoresearch.kra_race_card_pdf_replay import (
    MAX_MANIFEST_BYTES,
    archive_path,
    read_bytes,
    replay_entry_pages,
)
from autoresearch.kra_schedule_snapshot import (
    FEATURE_CUTOFF_MINUTES,
    replay_schedule_snapshot,
)
from autoresearch.observed_history_seed import digest, exclusive, pin, save
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import horse_id, parse_json

FORMAT = "kra-api26-scope-intake-v1"
KST = ZoneInfo("Asia/Seoul")
HTTP_FAILURES = {401: "authentication_error", 403: "access_denied", 429: "rate_limited"}
MAX_DENIAL_BYTES = 16 * 1024
GATEWAY_FAILURES = {
    "03": "no_data_unconfirmed",
    "20": "access_denied",
    "21": "authentication_error",
    "22": "rate_limited",
    "30": "authentication_error",
    "31": "authentication_error",
    "32": "access_denied",
}


def now():
    return datetime.now(UTC)


def _utc(value):
    if value.utcoffset() is None:
        raise ValueError("scope_intake_requires_timezone")
    return value.astimezone(UTC)


def _pinned(root, ref):
    path = archive_path(ref["path"], archive_root=root)
    raw = read_bytes(path, limit=MAX_MANIFEST_BYTES)
    if digest(raw) != ref["sha256"]:
        raise ValueError("scope_intake_source_pin_mismatch")
    return path, raw


def _scope_evidence(root, scope, ref, *, observed, cutoff):
    path, _ = _pinned(root, ref)
    rows, manifest, proof = replay_entry_pages(
        path,
        archive_root=root,
        meet=scope["meet"],
        race_date=scope["race_date"],
        expected_sha256=ref["sha256"],
    )
    captured = timestamp(manifest["collected_at"])
    numbers = {r["race_no"] for r in scope["races"]}
    if not (captured <= observed and captured < cutoff):
        raise ValueError("scope_intake_source_late_or_future")
    if (
        manifest["race_no"] not in numbers
        or len(rows) != scope["runner_count"]
        or {int(h["rcNo"]) for h in rows} != numbers
    ):
        raise ValueError("scope_intake_roster_scope_mismatch")
    for r in scope["races"]:
        entry = build_entry_snapshot(
            rows,
            meet=scope["meet"],
            race_date=scope["race_date"],
            race_no=r["race_no"],
            collected_at=captured,
        )
        roster = entry["entries"]
        if (
            len(roster) != r["runners"]
            or len({horse_id(h["hrNo"]) for h in roster}) != len(roster)
            or entry["scheduled_start_time"]
            != timestamp(r["scheduled_start_at"]).astimezone(KST).strftime("%H%M")
        ):
            raise ValueError("scope_intake_schedule_or_roster_mismatch")
    return {
        "manifest": {"path": str(path.relative_to(root)), "sha256": ref["sha256"]},
        "collected_at": captured.isoformat(),
        "pages": proof["pages"],
    }


def plan_intake(root, schedule, dates, *, first_cutoff=None, reuse=(), observed=None):
    """No HTTP, inference, or study creation during planning."""
    root = root.resolve()
    path, _ = _pinned(root, schedule)
    dates = tuple(dates)
    if not dates or dates != tuple(sorted(set(dates))):
        raise ValueError("scope_intake_dates_must_be_unique_and_sorted")
    for day in dates:
        validate_race_identity(1, day, 1)
    if (
        datetime.strptime(dates[-1], "%Y%m%d") - datetime.strptime(dates[0], "%Y%m%d")
    ).days >= 7:
        raise ValueError("scope_intake_expects_one_calendar_week_window")
    observed = _utc(now() if observed is None else observed)

    groups = defaultdict(list)
    seen = set()
    for day in dates:
        report = replay_schedule_snapshot(path, race_date=day)
        if (
            report["status"] != "reconciled"
            or report["source_failures"]
            or report["capture_manifest_sha256"] != schedule["sha256"]
            or set(report["observed_dates"]) != set(dates)
            or timestamp(report["capture_completed_at"]) > observed
        ):
            raise ValueError("scope_intake_requires_whole_official_schedule")
        for item in report["races"]:
            row = item["source_observations"]["national"]
            rid = row["race_id"]
            validate_race_identity(row["meet"], row["race_date"], row["race_no"])
            if (
                row["race_date"] != day
                or rid in seen
                or rid != f"{day}_{row['meet']}_{row['race_no']}"
                or type(row["runners"]) is not int
                or row["runners"] < 3
            ):
                raise ValueError("scope_intake_invalid_schedule_race")
            seen.add(rid)
            groups[(day, row["meet"])].append(
                {
                    key: row[key]
                    for key in ("race_id", "race_no", "runners", "scheduled_start_at")
                }
            )
    if not seen:
        raise ValueError("scope_intake_empty_official_schedule")
    cutoff = min(
        timestamp(r["scheduled_start_at"]) for rows in groups.values() for r in rows
    ) - timedelta(minutes=FEATURE_CUTOFF_MINUTES)
    if first_cutoff is not None and timestamp(first_cutoff) != cutoff:
        raise ValueError("scope_intake_original_cutoff_conflict")
    if observed >= cutoff:
        raise ValueError("scope_intake_first_block_cutoff_passed")

    reserved = {}
    for ref in reuse:
        _, raw = _pinned(root, ref)
        manifest = parse_json(raw)
        key = manifest["race_date"], manifest["meet"]
        if key not in groups or key in reserved:
            raise ValueError("scope_intake_duplicate_or_unexpected_reuse_scope")
        reserved[key] = ref
    scopes = []
    for (day, meet), rows in sorted(groups.items()):
        races = sorted(rows, key=lambda r: r["race_no"])
        total = sum(r["runners"] for r in races)
        scope = {
            "race_date": day,
            "meet": meet,
            "anchor_race_no": races[0]["race_no"],
            "races": races,
            "runner_count": total,
            "request_page_limit": (total + PAGE_SIZE - 1) // PAGE_SIZE,
        }
        ref = reserved.get((day, meet))
        if ref is not None:
            scope["reused_source"] = _scope_evidence(
                root, scope, ref, observed=observed, cutoff=cutoff
            )
            scope["request_page_limit"] = 0
        scopes.append(scope)
    return {
        "format": FORMAT,
        "schedule": {"path": str(path.relative_to(root)), "sha256": schedule["sha256"]},
        "race_dates": list(dates),
        "race_count": len(seen),
        "first_block_cutoff": cutoff.isoformat(),
        "max_http_requests": sum(s["request_page_limit"] for s in scopes),
        "scopes": scopes,
        "study_registered": False,
        "independent_publication_verified": False,
    }


def _payload_state(body, page_no, expected):
    if not body.strip():
        return "empty_unconfirmed", None
    try:
        payload = parse_json(body)
        if "OpenAPI_ServiceResponse" in payload:
            raise ValueError("entry_gateway_error_envelope")
        _, total = parse_entry_sheet_page(payload, page_no=page_no, page_size=PAGE_SIZE)
    except (ValueError, TypeError, RecursionError):
        code = classify(body).get("result_code")
        if code in GATEWAY_FAILURES:
            return GATEWAY_FAILURES[code], code
        return (
            "provider_error_or_invalid_body",
            None if code == "other_or_absent" else code,
        )
    if not total:
        return "empty_unconfirmed", "00"
    if total != expected:
        return "schedule_runner_count_conflict", "00"
    return None, "00"


async def _denial_code(response):
    """Read one small error body without recording the body or message."""
    body = bytearray()
    try:
        async with asyncio.timeout(1):
            async for chunk in response.aiter_bytes(chunk_size=4096):
                if len(body) + len(chunk) > MAX_DENIAL_BYTES:
                    return None
                body.extend(chunk)
    except (TimeoutError, httpx.HTTPError):
        return None
    info = classify(bytes(body))
    code = info.get("result_code")
    if info["category"] in {"api_error", "xml_response"} and code in GATEWAY_FAILURES:
        return code
    return None


class _ScopeClient:
    """Guard the original collector's injected client; never reissue a page."""

    def __init__(self, client, scope, cutoff, clock):
        self.client = client
        self.scope = scope
        self.cutoff = cutoff
        self.clock = clock
        self.events = []
        self.stop = None

    @asynccontextmanager
    async def stream(self, method, url, *, params, follow_redirects):
        page = len(self.events) + 1
        expected = {
            "meet": self.scope["meet"],
            "rc_date": self.scope["race_date"],
            "rc_no": self.scope["anchor_race_no"],
            "pageNo": page,
            "numOfRows": PAGE_SIZE,
            "_type": "json",
        }
        started = _utc(self.clock())
        if started >= self.cutoff:
            self.stop = "first_block_cutoff_passed"
        if self.stop is not None:
            raise ValueError("scope_intake_no_further_request")
        if (
            url != ENTRY_URL
            or method != "GET"
            or follow_redirects is not False
            or params.keys() != expected.keys() | {"serviceKey"}
            or any(params[k] != v for k, v in expected.items())
            or page > self.scope["request_page_limit"]
            or self.events
            and started < timestamp(self.events[-1]["completed_at"])
        ):
            self.stop = "request_budget_or_identity_conflict"
            raise ValueError("scope_intake_no_further_request")
        receipt = {
            "page_no": page,
            "started_at": started.isoformat(),
            "http_status": None,
        }
        self.events.append(receipt)
        try:
            async with self.client.stream(
                method, url, params=params, follow_redirects=False
            ) as response:
                receipt["http_status"] = response.status_code
                if response.status_code != 200:
                    self.stop = HTTP_FAILURES.get(response.status_code, "http_error")
                    if response.status_code == 403:
                        value = await _denial_code(response)
                        if value is not None:
                            receipt["gateway_result_code"] = value
                            if value != "03":
                                self.stop = GATEWAY_FAILURES[value]
                    raise ValueError("scope_intake_http_failure")
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(body) + len(chunk) > MAX_PAGE_BYTES:
                        self.stop = "response_too_large"
                        raise ValueError("scope_intake_body_limit")
                    body.extend(chunk)
                payload = bytes(body)
                self.stop, receipt["gateway_result_code"] = _payload_state(
                    payload, page, self.scope["runner_count"]
                )
                # Relay the already decoded body exactly once to the original raw writer.
                headers = httpx.Headers(response.headers)
                headers.pop("content-encoding", None)
                headers.pop("content-length", None)
                yield httpx.Response(
                    200, headers=headers, request=response.request, content=payload
                )
        except httpx.TimeoutException:
            self.stop = "transport_timeout"
            raise
        except httpx.HTTPError:
            self.stop = "transport_failure"
            raise
        finally:
            receipt["completed_at"] = _utc(self.clock()).isoformat()


async def _capture_scope(client, scope, root, output, cutoff, clock, key):
    guard = _ScopeClient(client, scope, cutoff, clock)
    finished = None
    try:
        remaining = (cutoff - _utc(clock())).total_seconds()
        if remaining <= 0:
            return {"state": "first_block_cutoff_passed", "requests": []}
        credentials = {"api_key": key}
        async with asyncio.timeout(min(60, remaining)):
            manifest = await collect_entry_sheet_snapshot(
                meet=scope["meet"],
                race_date=scope["race_date"],
                race_no=scope["anchor_race_no"],
                output_dir=output,
                client=cast(httpx.AsyncClient, guard),
                clock=clock,
                **credentials,
            )
        path = archive_path(manifest["manifest_path"], archive_root=root)
        ref = pin(root, path)
        finished = {"capture": ref, "requests": guard.events}
        if guard.stop is not None:
            return finished | {"state": guard.stop}
        if manifest["collection_status"] != "captured":
            return finished | {"state": "entry_capture_not_verified"}
        observed = _utc(clock())
        if observed >= cutoff:
            return finished | {"state": "first_block_cutoff_passed"}
        proof = _scope_evidence(root, scope, ref, observed=observed, cutoff=cutoff)
        return finished | {"state": "captured", "evidence": proof}
    except TimeoutError:
        return {"state": "scope_timeout_or_cutoff", "requests": guard.events}
    except (ValueError, TypeError, KeyError, OSError, OverflowError):
        return (finished or {"requests": guard.events}) | {
            "state": "scope_evidence_unverified"
        }


def _reserve(parent, dates):
    # Identical or overlapping dates cannot consume another attempt in this archive.
    known = set(dates)
    for previous in parent.glob("window_*"):
        if known.intersection(previous.name.removeprefix("window_").split("_")):
            raise ValueError("scope_intake_window_already_reserved")
    target = parent / ("window_" + "_".join(dates))
    target.mkdir(mode=0o700, exist_ok=False)
    return target


async def capture_intake(
    root,
    output_root,
    schedule,
    dates,
    *,
    first_cutoff,
    reuse=(),
    max_requests,
    api_key_file,
    clock: Callable[[], datetime] = now,
    transport: httpx.AsyncBaseTransport | None = None,
):
    cutoff = timestamp(first_cutoff)
    current = _utc(clock())
    if current >= cutoff:
        raise ValueError("scope_intake_first_block_cutoff_passed")
    underlying = clock

    def checked_clock():
        nonlocal current
        value = _utc(underlying())
        if value < current:
            raise ValueError("scope_intake_clock_moved_backwards")
        current = value
        return current

    clock = checked_clock
    root = root.resolve()
    plan = plan_intake(
        root, schedule, dates, first_cutoff=first_cutoff, reuse=reuse, observed=clock()
    )
    budget = plan["max_http_requests"]
    if type(max_requests) is not int or max_requests < budget:
        raise ValueError("scope_intake_budget_not_authorized")
    out = archive_path(output_root, archive_root=root)
    out.mkdir(parents=True, exist_ok=True)
    with exclusive(out):
        reserved_at = _utc(clock())
        if reserved_at >= cutoff:
            raise ValueError("scope_intake_first_block_cutoff_passed")
        if budget and not api_key_file:
            raise ValueError("scope_intake_api_key_file_required")
        key = api_key_file.read_text().strip() if budget else None
        if budget and not key:
            raise ValueError("scope_intake_api_key_file_empty")
        target = _reserve(out, plan["race_dates"])
        save(
            target / "reservation.json", plan | {"reserved_at": reserved_at.isoformat()}
        )
        results = []
        stop = None
        async with httpx.AsyncClient(
            transport=transport, timeout=15, follow_redirects=False, trust_env=False
        ) as client:
            for scope in plan["scopes"]:
                if "reused_source" in scope:
                    info = {
                        "state": "reused",
                        "evidence": scope["reused_source"],
                        "requests": [],
                    }
                elif stop is not None:
                    info = {
                        "state": "not_attempted",
                        "stop_reason": stop,
                        "requests": [],
                    }
                else:
                    info = await _capture_scope(
                        client, scope, root, target / "entries", cutoff, clock, key
                    )
                    if info["state"] != "captured":
                        stop = info["state"]
                results.append(scope | info)
        try:
            completed = clock()
        except ValueError:
            completed = None
            stop = "clock_unverified"
        if stop is None and completed >= cutoff:
            stop = "first_block_cutoff_passed"
        receipt = {
            "format": FORMAT,
            "reservation": pin(root, target / "reservation.json"),
            "scopes": results,
            "status": "captured_locally" if stop is None else "incomplete",
            "stop_reason": stop,
            "actual_http_requests": sum(len(s["requests"]) for s in results),
            "completed_at": completed.isoformat() if completed is not None else None,
            "study_registered": False,
            "independent_publication_verified": False,
        }
        save(target / "receipt.json", receipt)
        return target / "receipt.json", receipt


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=("plan", "collect"))
    ap.add_argument("--schedule-capture", required=True)
    ap.add_argument("--schedule-sha256", required=True)
    ap.add_argument("--first-cutoff", help="Previously fixed cutoff with timezone")
    ap.add_argument("--date", action="append", required=True)
    ap.add_argument("--reuse-entry", nargs=2, action="append", default=[])
    ap.add_argument("--output-dir", type=Path)
    ap.add_argument("--max-requests", type=int)
    ap.add_argument("--api-key-file", type=Path)
    args = ap.parse_args(argv)
    root = Path.cwd()
    ref = {"path": args.schedule_capture, "sha256": args.schedule_sha256}
    reuse = [{"path": path, "sha256": sha} for path, sha in args.reuse_entry]
    if args.mode == "plan":
        plan = plan_intake(
            root, ref, args.date, first_cutoff=args.first_cutoff, reuse=reuse
        )
        print(json.dumps(plan, indent=2))
        return 0
    if (
        args.output_dir is None
        or args.max_requests is None
        or args.first_cutoff is None
    ):
        ap.error("collect requires --first-cutoff, --output-dir and --max-requests")
    path, result = asyncio.run(
        capture_intake(
            root,
            args.output_dir,
            ref,
            args.date,
            first_cutoff=args.first_cutoff,
            reuse=reuse,
            max_requests=args.max_requests,
            api_key_file=args.api_key_file,
        )
    )
    print(json.dumps({"receipt": str(path), "status": result["status"]}))
    return 0 if result["status"] == "captured_locally" else 2


if __name__ == "__main__":
    raise SystemExit(main())
