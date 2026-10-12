"""Bounded API diagnostics, never a data capture or training approval."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree

import httpx
from shared.kra_entry_sheet import parse_entry_sheet_page
from shared.kra_race_identity import validate_race_identity

from autoresearch.kra_entry_sheet_snapshot import ENTRY_URL
from autoresearch.kra_result_snapshot import RESULT_URL
from autoresearch.observed_history_seed import save

ENDPOINTS = {"api214": RESULT_URL, "api26": ENTRY_URL}
MAX_BYTES = 5 * 1024 * 1024
DEADLINE = 45
CODES = {
    "00",
    "01",
    "02",
    "03",
    "04",
    "05",
    "10",
    "11",
    "12",
    "20",
    "21",
    "22",
    "30",
    "31",
    "32",
    "99",
}


def code(value):
    return value if isinstance(value, str) and value in CODES else "other_or_absent"


def classify(raw: bytes) -> dict:
    """Emit only fixed vocabulary and counts, not any free-form server text."""
    if len(raw) > MAX_BYTES:
        return {"category": "body_limit"}
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeError, RecursionError):
        # DTD/entity expansion is unnecessary for gateway error diagnostics.
        upper = raw.upper()
        if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper or b"\x00" in raw:
            return {"category": "non_json_unparsed"}
        try:
            root = ElementTree.fromstring(raw)
        except (ElementTree.ParseError, ValueError):
            return {"category": "non_json_unparsed"}
        value = root.findtext(".//returnReasonCode") or root.findtext(".//resultCode")
        return {"category": "xml_response", "result_code": code(value)}
    if not isinstance(payload, dict):
        return {"category": "json_non_object"}
    response = payload.get("response")
    envelope = "response"
    if not isinstance(response, dict):
        response = payload
        envelope = "top_level"
    header = response.get("header")
    result = header.get("resultCode") if isinstance(header, dict) else None
    summary = {
        "category": "json_schema_mismatch",
        "envelope": envelope,
        "result_code": code(result),
        "has_body": isinstance(response.get("body"), dict),
        "has_error": any(k in payload for k in ("error", "errorCode", "message")),
    }
    if result is not None and result != "00":
        summary["category"] = "api_error"
        return summary
    try:
        rows, total = parse_entry_sheet_page(payload, page_no=1, page_size=100)
    except (ValueError, TypeError):
        return summary
    summary.update(
        category="valid_page" if total else "empty_unconfirmed",
        page_rows=len(rows),
        total_count=total,
    )
    return summary


async def probe(endpoint, day, meet, api_key, *, client=None):
    validate_race_identity(meet, day, 1)
    url = ENDPOINTS[endpoint]
    key = unquote(api_key.strip())
    if not key:
        raise ValueError("missing_api_key")
    params = {
        "serviceKey": key,
        "meet": meet,
        "rc_date": day,
        "pageNo": 1,
        "numOfRows": 100,
        "_type": "json",
    }
    if endpoint == "api26":
        params["rc_no"] = 1
    receipt = {
        "format_version": "history-api-probe-v1",
        "endpoint": endpoint,
        "day": day,
        "meet": meet,
        "started_at": datetime.now(UTC).isoformat(),
        "http_status": None,
        "byte_count": 0,
        "data_capture": False,
        "counts_as_70_percent_evidence": False,
    }
    own = client is None
    client = client or httpx.AsyncClient(
        timeout=DEADLINE,
        trust_env=False,
        follow_redirects=False,
    )
    start = time.monotonic()
    try:
        async with asyncio.timeout(DEADLINE):
            async with client.stream(
                "GET",
                url,
                params=params,
                follow_redirects=False,
            ) as response:
                receipt["http_status"] = response.status_code
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    receipt["byte_count"] += len(chunk)
                    if receipt["byte_count"] > MAX_BYTES:
                        receipt["diagnosis"] = {"category": "body_limit"}
                        break
                    body.extend(chunk)
                else:
                    receipt["diagnosis"] = classify(bytes(body))
                    if response.status_code != 200:
                        receipt["diagnosis"]["response_category"] = receipt[
                            "diagnosis"
                        ]["category"]
                        receipt["diagnosis"]["category"] = "http_error"
    except (TimeoutError, httpx.TimeoutException):
        receipt["diagnosis"] = {"category": "timeout"}
    except httpx.HTTPError:
        receipt["diagnosis"] = {"category": "transport_error"}
    finally:
        if own:
            await client.aclose()
    receipt["elapsed_seconds"] = round(time.monotonic() - start, 3)
    receipt["completed_at"] = datetime.now(UTC).isoformat()
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", choices=ENDPOINTS, required=True)
    parser.add_argument("--day", required=True)
    parser.add_argument("--meet", type=int, required=True)
    parser.add_argument("--api-key-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("output_already_exists")
    result = asyncio.run(
        probe(
            args.endpoint,
            args.day,
            args.meet,
            args.api_key_file.read_text(),
        )
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sha = save(args.output, result)
    print(json.dumps({"sha256": sha, **result}))


if __name__ == "__main__":
    main()
