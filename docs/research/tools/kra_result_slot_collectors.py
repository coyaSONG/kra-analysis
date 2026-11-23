"""Bounded raw source calls for one original result observation."""

import asyncio
from pathlib import Path

import httpx
import kra_result_slot_witness as witness
from autoresearch import observed_history_seed as history
from autoresearch import official_history_support as official
from autoresearch.history_api_probe import classify
from autoresearch.kra_entry_scope_intake import (
    GATEWAY_FAILURES,
    HTTP_FAILURES,
    _denial_code,
    _ScopeClient,
)
from autoresearch.kra_entry_sheet_snapshot import (
    ENTRY_URL,
    collect_entry_sheet_snapshot,
)
from autoresearch.kra_result_snapshot import (
    PAGE_SIZE,
    RESULT_URL,
    collect_result_snapshot,
)

fold = witness.fold
parse, require, timestamp = fold.parse_json, fold.require, witness.timestamp


class Stop(RuntimeError):
    """Stop before another request and record only a stable reason code."""


def _http_state(status):
    if status != 200:
        return HTTP_FAILURES.get(status, "http_error")
    return None


def _capture_state(directory, capture):
    for page in capture.get("pages", []):
        raw = witness.custody._path(directory, page["raw_file"]).read_bytes()
        if not raw.strip():
            return "empty_unconfirmed"
        code = classify(raw).get("result_code")
        if code in GATEWAY_FAILURES:
            return GATEWAY_FAILURES[code]
    if capture.get("error_type") in {"ConnectTimeout", "ReadTimeout", "TimeoutError"}:
        return "transport_timeout"
    if capture.get("error_type") in {
        "ConnectError",
        "ReadError",
        "RemoteProtocolError",
    }:
        return "transport_failure"
    return "provider_error_or_unresolved_identity"


async def capture_api(card, directory, credential, transport, delay):
    directory.mkdir(exist_ok=False)
    dates = card.scope["race_dates"]
    digest = history.save(
        directory / "plan.json",
        history.make_plan(dates[0], dates[-1], card.slot["api_request_budget"]),
    )
    marks = directory / "requests"
    marks.mkdir()
    count, failure, active = 0, None, None
    seen = set()

    async def reserve(request):
        nonlocal count, failure
        card.clock()
        if count:
            await asyncio.sleep(delay)
        at = card.clock()
        params = request.url.params
        url = str(request.url.copy_with(query=None))
        source = {RESULT_URL: "API214", ENTRY_URL: "API26"}.get(url)
        fields = {"meet", "rc_date", "numOfRows", "pageNo", "_type", "serviceKey"}
        if source == "API26":
            fields.add("rc_no")
        day, meet, page = (
            params.get("rc_date"),
            int(params["meet"]),
            int(params["pageNo"]),
        )
        expected = card.expected.get((day, meet))
        key = (source, day, meet, page)
        if (
            request.method != "GET"
            or (source, day, meet) != active
            or expected is None
            or set(params) != fields
            or len(params.multi_items()) != len(fields)
            or params["numOfRows"] != str(PAGE_SIZE)
            or params["_type"] != "json"
            or not 1 <= page <= expected["pages"]
            or key in seen
            or (source == "API26" and int(params["rc_no"]) != expected["anchor"])
        ):
            raise Stop("result_slot_request_not_in_frozen_scope")
        if count >= card.slot["api_request_budget"]:
            raise Stop("result_slot_api_budget_exhausted")
        count += 1
        seen.add(key)
        history.save(
            marks / f"{count:06d}.json",
            {
                "ordinal": count,
                "plan_sha256": digest,
                "day": day,
                "meet": meet,
                "page": page,
                "source": source,
                "reserved_at": at.isoformat(),
            },
        )
        failure = None
        card.clock()

    async def response(reply):
        nonlocal failure
        failure = _http_state(reply.status_code)
        if reply.status_code == 403 and active[0] == "API214":
            code = await _denial_code(reply)
            if code is not None and code != "03":
                failure = GATEWAY_FAILURES[code]

    async with httpx.AsyncClient(
        timeout=30,
        follow_redirects=False,
        trust_env=False,
        transport=transport,
        event_hooks={"request": [reserve], "response": [response]},
    ) as client:
        for (day, meet), expected in sorted(card.expected.items()):
            active = ("API214", day, meet)
            result = await collect_result_snapshot(
                meet=meet,
                race_date=day,
                output_dir=directory / "results",
                client=client,
                clock=fold.now,
                **{"api_key": credential},
            )
            info = parse(result.read_bytes())
            result_problem = None
            if info["status"] == "failed":
                result_problem = failure or _capture_state(result.parent, info)
            entry_pin, entry_problem = None, None
            if info["status"] == "identity_unresolved":
                active = ("API26", day, meet)
                guard = _ScopeClient(
                    client,
                    {
                        "meet": meet,
                        "race_date": day,
                        "anchor_race_no": expected["anchor"],
                        "request_page_limit": expected["pages"],
                        "runner_count": expected["runners"],
                    },
                    timestamp(card.slot["closes_at"]),
                    fold.now,
                )
                entry = await collect_entry_sheet_snapshot(
                    meet=meet,
                    race_date=day,
                    race_no=expected["anchor"],
                    output_dir=directory / "entries",
                    client=guard,
                    clock=fold.now,
                    **{"api_key": credential},
                )
                entry_path = Path(entry["manifest_path"])
                entry_pin = history.pin(directory, entry_path)
                entry_problem = guard.stop
                if not entry_problem and entry["collection_status"] != "captured":
                    entry_problem = failure or "result_slot_entry_identity_unverified"
            unit = {"day": day, "meet": meet}
            receipt = {
                "plan_sha256": digest,
                "unit": unit,
                "result": history.pin(directory, result),
                "entry": entry_pin,
            }
            folder = directory / "receipts" / f"{day}_{meet}"
            folder.mkdir(parents=True, exist_ok=False)
            history.save(folder / "0001.json", receipt)
            if result_problem or entry_problem:
                raise Stop(result_problem or entry_problem)
            found = history.inspect_receipt(directory, receipt, unit, digest)
            if found["status"] != "api_reported_rows":
                raise Stop(found["status"])
            if sorted({row["race_id"] for row in found["records"]}) != expected["ids"]:
                raise Stop("result_slot_api_population_conflict")

    seed = history.replay(directory)
    path = directory / "selected-seed.json"
    return seed, path, history.save(path, seed)


async def capture_official(card, directory, seed, seed_sha, transport, delay):
    requests = official.request_plan(seed, seed_sha)["requests"]
    sent, previous_failure = 0, None

    def check_previous():
        if sent:
            request = requests[sent - 1]
            key = request["key"]
            info = parse((directory / f"{key}.json").read_bytes())
            if info["status"] != "captured":
                raise Stop(previous_failure or "official_fetch_error")
            if request["kind"] == "detail":
                event = official.replay_receipt(directory, info, request)
                if event["event_support"] != "confirmed":
                    raise Stop("official_detail_unconfirmed")
                if event["race_id"] != key:
                    raise Stop("official_detail_identity_conflict")

    async def reserve(request):
        nonlocal sent
        card.clock()
        check_previous()
        card.clock()
        if (
            sent >= len(requests)
            or request.method != "GET"
            or str(request.url) != requests[sent]["url"]
        ):
            raise Stop("result_slot_unexpected_official_request")
        sent += 1

    async def response(reply):
        nonlocal previous_failure
        previous_failure = _http_state(reply.status_code)

    async with httpx.AsyncClient(
        timeout=30,
        follow_redirects=False,
        trust_env=False,
        transport=transport,
        event_hooks={"request": [reserve], "response": [response]},
    ) as client:
        archive = await official.collect(
            directory, seed, seed_sha, client=client, delay=delay
        )
    check_previous()
    require(sent == len(requests), "result_slot_official_archive_not_one_pass")
    return archive
