"""Pagination, identity completeness, and credential-safe entry captures."""

import copy
import hashlib
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.kra_entry_sheet import build_entry_snapshot, parse_entry_sheet_page

from autoresearch import kra_entry_sheet_snapshot as snapshot
from autoresearch.tests.race_card_pdf_fixture import HORSE_NAME

CAPTURED = datetime(2026, 6, 27, 0, 30, tzinfo=UTC)


def entry(number=1, race_no=1, count=2):
    return {
        "meet": "\uc11c\uc6b8",
        "rcDate": 20260627,
        "rcNo": race_no,
        "chulNo": number,
        "hrName": HORSE_NAME,
        "hrNo": f"00{number}",
        "stTime": "\ucd9c\ubc1c :10:35",
        "dusu": count,
        "rank": "\uad6d6\ub4f1\uae09",
    }


def page(rows=None, *, number=1, total=2, size=100):
    return {
        "response": {
            "header": {"resultCode": "00"},
            "body": {
                "numOfRows": size,
                "pageNo": number,
                "totalCount": total,
                "items": {"item": rows if rows is not None else [entry(1), entry(2)]},
            },
        }
    }


def build(rows):
    return build_entry_snapshot(
        rows, meet=1, race_date="20260627", race_no=1, collected_at=CAPTURED
    )


def test_response_filtering_complete_field_and_start_time():
    result = build([entry(2), entry(1), entry(3, race_no=2, count=1)])
    assert result["scheduled_start_time"] == "1035"
    assert result["declared_horse_count"] == 2
    assert [row["chulNo"] for row in result["entries"]] == [1, 2]
    assert result["entries"][0]["hrNo"] == "001"
    assert "rank" not in result["entries"][0]
    assert result["collected_at"] == CAPTURED.isoformat()


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("meet", "\uc81c\uc8fc", "entry_date_or_meeting_mismatch"),
        ("rcDate", 20260628, "entry_date_or_meeting_mismatch"),
        ("chulNo", True, "invalid_entry_integer"),
        ("hrName", " ", "missing_entry_horse_name"),
        ("hrNo", None, "invalid_entry_horse_id"),
        ("hrNo", "A123", "invalid_entry_horse_id"),
        ("hrNo", True, "invalid_entry_horse_id"),
        ("hrNo", 0, "invalid_entry_horse_id"),
        ("stTime", "24:30", "invalid_entry_start_time"),
        ("stTime", "11:00", "inconsistent_entry_start_times"),
        ("dusu", 3, "incomplete_entry_field"),
        ("chulNo", 2, "duplicate_entry_runner"),
        ("hrNo", "002", "duplicate_entry_horse_id"),
    ],
)
def test_bad_identity_or_incomplete_field_blocks(field, value, reason):
    rows = [entry(1), entry(2)]
    rows[0][field] = value
    with pytest.raises(ValueError, match=reason):
        build(rows)


def test_missing_runner_and_missing_requested_race_do_not_pass():
    with pytest.raises(ValueError, match="incomplete_entry_field"):
        build([entry(1)])
    with pytest.raises(ValueError, match="no_entries_for_requested_race"):
        build([entry(1, race_no=2)])


def test_numeric_horse_id_is_preserved_without_guessing_leading_zeroes():
    rows = [entry(1), entry(2)]
    rows[1]["hrNo"] = 1412244
    assert build(rows)["entries"][1]["hrNo"] == "1412244"


def test_naive_entry_capture_is_not_accepted():
    with pytest.raises(ValueError, match="entry_capture_requires_timezone"):
        build_entry_snapshot(
            [entry(1), entry(2)],
            meet=1,
            race_date="20260627",
            race_no=1,
            collected_at=CAPTURED.replace(tzinfo=None),
        )


def test_singleton_items_are_structurally_normalized():
    rows, total = parse_entry_sheet_page(
        page(entry(count=1), total=1), page_no=1, page_size=100
    )
    assert len(rows) == total == 1


@pytest.mark.parametrize(
    "mutation,reason",
    [
        ("error_header", "entry_api_unsuccessful"),
        ("page_no", "entry_pagination_mismatch"),
        ("num_rows", "entry_pagination_mismatch"),
        ("truncated_rows", "incomplete_entry_page"),
        ("bad_row", "invalid_entry_items"),
        ("oversize_total", "entry_integer_out_of_range"),
    ],
)
def test_bad_pages_are_rejected(mutation, reason):
    payload = page()
    body = payload["response"]["body"]
    if mutation == "error_header":
        payload["response"]["header"]["resultCode"] = "30"
    elif mutation == "page_no":
        body["pageNo"] = 2
    elif mutation == "num_rows":
        body["numOfRows"] = 10
    elif mutation == "truncated_rows":
        body["items"]["item"].pop()
    elif mutation == "bad_row":
        body["items"]["item"][0] = None
    else:
        body["totalCount"] = 10_001
    with pytest.raises(ValueError, match=reason):
        parse_entry_sheet_page(payload, page_no=1, page_size=100)


@pytest.mark.asyncio
async def test_pagination_preserves_original_bytes_hashes_and_last_capture_time(
    tmp_path,
):
    requested = []
    filler = [entry(1, race_no=2, count=1) for _ in range(98)]
    payloads = [
        page([entry(1), *filler, entry(2)], total=101),
        page([entry(3, race_no=3, count=1)], number=2, total=101),
    ]
    contents = [json.dumps(payload).encode() for payload in payloads]

    def handler(request):
        requested.append(dict(request.url.params))
        return httpx.Response(200, content=contents[len(requested) - 1])

    times = iter(CAPTURED + timedelta(seconds=i) for i in range(3))
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await snapshot.collect_entry_sheet_snapshot(
            meet=1,
            race_date="20260627",
            race_no=1,
            api_key="test-credential",
            output_dir=tmp_path,
            client=client,
            clock=lambda: next(times),
        )
        assert not client.is_closed
    assert result["collection_status"] == "captured"
    assert result["collected_at"] == (CAPTURED + timedelta(seconds=2)).isoformat()
    assert [params["pageNo"] for params in requested] == ["1", "2"]
    assert len(result["entry_snapshot"]["entries"]) == 2
    for observed, content in zip(result["pages"], contents, strict=True):
        assert Path(observed["raw_path"]).read_bytes() == content
        assert observed["sha256"] == hashlib.sha256(content).hexdigest()
    assert "test-credential" not in Path(result["manifest_path"]).read_text()
    assert "serviceKey" not in json.dumps(result)
    assert (
        json.loads(Path(result["entry_snapshot_path"]).read_text())
        == result["entry_snapshot"]
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure", ["http", "timeout", "echo", "total_changed", "oversize"]
)
async def test_network_errors_and_invalid_bodies_do_not_leak_keys(
    tmp_path, failure, monkeypatch
):
    requests = []
    key = "never-persist-this-credential"
    first = page([entry(1), entry(2)] + [entry(1, race_no=2)] * 98, total=101)

    def handler(request):
        requests.append(request)
        if failure == "http":
            return httpx.Response(403, text=key)
        if failure == "timeout":
            raise httpx.ReadTimeout(f"request failed {request.url}", request=request)
        if failure == "echo":
            payload = copy.deepcopy(page())
            payload["debug"] = key
            return httpx.Response(200, json=payload)
        if failure == "total_changed":
            return httpx.Response(
                200,
                json=first
                if len(requests) == 1
                else page([entry(1), entry(2)], number=2, total=102),
            )
        return httpx.Response(200, content=b"x" * 11)

    if failure == "oversize":
        monkeypatch.setattr(snapshot, "MAX_PAGE_BYTES", 10)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await snapshot.collect_entry_sheet_snapshot(
            meet=1,
            race_date="20260627",
            race_no=1,
            api_key=key,
            output_dir=tmp_path,
            client=client,
            clock=lambda: CAPTURED,
        )
    assert result["collection_status"] != "captured"
    assert result["entry_snapshot"] is None
    assert result["entry_snapshot_path"] is None
    for path in tmp_path.rglob("*.json"):
        assert key not in path.read_text()
        assert "serviceKey" not in path.read_text()
