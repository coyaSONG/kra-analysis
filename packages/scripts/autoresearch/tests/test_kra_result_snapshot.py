"""Result source evidence preserves exceptional rows and never leaks credentials."""

import asyncio
import copy
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.kra_result_history import normalize_result_rows

from autoresearch import kra_result_snapshot as capture
from autoresearch.kra_entry_sheet_snapshot import collect_entry_sheet_snapshot

NOW = datetime(2026, 10, 11, 11, tzinfo=UTC)
SECRET = "synthetic+source/token="


def row(number=1, race_no=1, rank=1, elapsed=75.4):
    return {
        "meet": 4,
        "rcDate": 20261011,
        "rcNo": race_no,
        "chulNo": number,
        "hrNo": f"{race_no * 100 + number:07d}",
        "ord": rank,
        "rcTime": elapsed,
    }


def envelope(rows, *, page=1, total=None):
    return {
        "response": {
            "header": {"resultCode": "00"},
            "body": {
                "pageNo": page,
                "numOfRows": 100,
                "totalCount": len(rows) if total is None else total,
                "items": {"item": rows},
            },
        }
    }


async def collect(tmp_path, handler, **kwargs):
    credentials = {"api_key": SECRET}
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        return await capture.collect_result_snapshot(
            meet=4,
            race_date="20261011",
            output_dir=tmp_path,
            client=client,
            clock=kwargs.pop("clock", lambda: NOW),
            **credentials,
            **kwargs,
        )


def test_finish_and_unknown_statuses_are_preserved():
    rows = [
        row(1),
        row(2, rank=99, elapsed=0),
        row(3, rank="중지", elapsed=0),
        row(4, rank=None),
    ]
    result = normalize_result_rows(rows, meet=4, race_date="20261011")
    assert result["row_count"] == 4
    assert result["evidence_counts"] == {"ranked_finish_observed": 1, "unresolved": 3}
    assert [r["raw_ord"] for r in result["records"]] == [1, 99, "중지", None]
    assert not result["complete_actual_start_history_verified"]
    assert not result["historical_pre_race_availability_verified"]


@pytest.mark.parametrize(
    "rank, elapsed",
    [
        (0, 75),
        (91, 75),
        ("실격", 75),
        (1, 0),
        (1, -1),
        (1, None),
        (1, "NaN"),
        (1, "inf"),
        (1.0, 75),
    ],
)
def test_ambiguous_code_or_no_positive_time_is_not_a_finish(rank, elapsed):
    result = normalize_result_rows(
        [row(rank=rank, elapsed=elapsed)], meet=4, race_date="20261011"
    )
    assert result["records"][0]["evidence"] == "unresolved"


@pytest.mark.parametrize(
    "field,value",
    [
        ("ord", True),
        ("ord", []),
        ("rcTime", {}),
        ("rcTime", float("nan")),
        ("hrNo", 0),
        ("chulNo", True),
        ("meet", 3),
        ("rcDate", 20261010),
    ],
)
def test_invalid_or_misbound_rows_fail(field, value):
    entry = row()
    entry[field] = value
    with pytest.raises(ValueError):
        normalize_result_rows([entry], meet=4, race_date="20261011")


def test_duplicates_fail_but_tied_ranks_are_preserved():
    with pytest.raises(ValueError, match="duplicate"):
        normalize_result_rows([row(), row()], meet=4, race_date="20261011")
    second = row(2)
    second["hrNo"] = 101
    with pytest.raises(ValueError, match="duplicate"):
        normalize_result_rows([row(), second], meet=4, race_date="20261011")
    assert (
        normalize_result_rows([row(), row(2)], meet=4, race_date="20261011")[
            "row_count"
        ]
        == 2
    )


def test_explicit_status_note_is_retained_and_cannot_be_ignored():
    entry = row()
    entry["ordBigo"] = "출전취소"
    result = normalize_result_rows([entry], meet=4, race_date="20261011")
    assert result["records"][0]["evidence"] == "unresolved"
    assert result["records"][0]["raw_ord_bigo"] == "출전취소"


@pytest.mark.asyncio
async def test_complete_pagination_capture_replay_and_unique_directories(tmp_path):
    rows = [row(i, race_no=r) for r in range(1, 7) for i in range(1, 19)]
    requests = []

    def handler(request):
        requests.append(request)
        assert request.url.params["serviceKey"] == SECRET
        assert "rc_no" not in request.url.params
        page = int(request.url.params["pageNo"])
        return httpx.Response(
            200,
            json=envelope(rows[(page - 1) * 100 : page * 100], page=page, total=108),
        )

    first = await collect(tmp_path, handler)
    result = capture.replay_result_snapshot(first)
    assert len(requests) == 2
    assert result["row_count"] == 108
    assert len(result["race_counts"]) == 6
    assert not result["independent_timestamp_verified"]
    original = first.read_bytes()
    second = await collect(tmp_path, handler)
    assert first != second and first.read_bytes() == original
    assert SECRET not in first.read_text()
    assert "serviceKey" not in first.read_text()
    assert result["records"][0]["raw_horse_id"] == "0000101"


@pytest.mark.asyncio
async def test_empty_api_result_remains_unconfirmed(tmp_path):
    path = await collect(
        tmp_path, lambda request: httpx.Response(200, json=envelope([]))
    )
    result = capture.replay_result_snapshot(path)
    assert result["population_status"] == "empty_unconfirmed"
    assert result["row_count"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    [
        "wrong_page",
        "short_page",
        "api_error",
        "malformed_json",
        "wrong_venue",
        "duplicates",
    ],
)
async def test_safe_originals_survive_validation_failures(tmp_path, case):
    payload = envelope([row()])
    if case == "wrong_page":
        payload["response"]["body"]["pageNo"] = 2
    elif case == "short_page":
        payload["response"]["body"]["totalCount"] = 2
    elif case == "api_error":
        payload["response"]["header"]["resultCode"] = "03"
    elif case == "wrong_venue":
        payload["response"]["body"]["items"]["item"][0]["meet"] = 3
    elif case == "duplicates":
        payload = envelope([row(), row()])
    raw = b"not-json" if case == "malformed_json" else json.dumps(payload).encode()
    path = await collect(tmp_path, lambda request: httpx.Response(200, content=raw))
    manifest = json.loads(path.read_bytes())
    assert manifest["status"] == "failed"
    assert (path.parent / manifest["pages"][0]["raw_file"]).read_bytes() == raw
    with pytest.raises(ValueError, match="not_successful"):
        capture.replay_result_snapshot(path)


@pytest.mark.asyncio
async def test_changed_total_is_not_accepted(tmp_path):
    rows = [row(i, race_no=r) for r in range(1, 6) for i in range(1, 21)]

    def handler(request):
        page = int(request.url.params["pageNo"])
        return httpx.Response(
            200,
            json=envelope(
                rows if page == 1 else [row(1, 6)],
                page=page,
                total=102 if page == 1 else 101,
            ),
        )

    path = await collect(tmp_path, handler)
    assert json.loads(path.read_bytes())["status"] == "failed"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    [
        "http",
        "redirect",
        "credential_echo",
        "encoded_echo",
        "oversize",
        "timeout",
        "clock",
    ],
)
async def test_transport_and_clock_failures_do_not_leak_credentials(
    tmp_path, monkeypatch, case
):
    async def handler(request):
        if case == "http":
            raise httpx.ConnectError(f"failure {request.url}", request=request)
        if case == "redirect":
            return httpx.Response(302, headers={"Location": "https://example.org/"})
        if case == "credential_echo":
            return httpx.Response(200, content=SECRET.encode())
        if case == "encoded_echo":
            return httpx.Response(200, content=capture.quote(SECRET, safe="").encode())
        if case == "oversize":
            return httpx.Response(200, content=b"x" * 101)
        if case == "timeout":
            await asyncio.sleep(1)
        return httpx.Response(200, json=envelope([row()]))

    if case == "oversize":
        monkeypatch.setattr(capture, "MAX_BYTES", 100)
    if case == "timeout":
        monkeypatch.setattr(capture, "REQUEST_SECONDS", 0.01)
    stamps = iter([NOW, NOW, NOW - timedelta(seconds=1), NOW])
    kwargs = {"clock": lambda: next(stamps)} if case == "clock" else {}
    path = await collect(tmp_path, handler, **kwargs)
    manifest = json.loads(path.read_bytes())
    assert manifest["status"] == "failed"
    assert SECRET not in path.read_text() and "serviceKey" not in path.read_text()
    assert not manifest["pages"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case", ["hash", "path", "clock", "params", "total", "page", "symlink"]
)
async def test_replay_rejects_tampered_capture(tmp_path, case):
    path = await collect(
        tmp_path, lambda request: httpx.Response(200, json=envelope([row()]))
    )
    manifest = json.loads(path.read_bytes())
    page = manifest["pages"][0]
    raw = path.parent / page["raw_file"]
    if case == "hash":
        raw.write_bytes(b"tampered")
    elif case == "path":
        page["raw_file"] = "../outside.json"
    elif case == "clock":
        page["fetch_started_at"] = (NOW + timedelta(seconds=1)).isoformat()
    elif case == "params":
        page["request_parameters"]["meet"] = 3
    elif case == "total":
        manifest["total_count"] = 2
    elif case == "page":
        manifest["pages"].append(copy.deepcopy(page))
    elif case == "symlink":
        moved = raw.with_suffix(".backup")
        raw.rename(moved)
        raw.symlink_to(moved)
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        capture.replay_result_snapshot(path)


@pytest.mark.asyncio
async def test_replay_ignores_supplied_projection(tmp_path):
    path = await collect(
        tmp_path, lambda request: httpx.Response(200, json=envelope([row(rank=99)]))
    )
    manifest = json.loads(path.read_bytes())
    manifest["summary"] = {
        "row_count": 999,
        "complete_actual_start_history_verified": True,
    }
    path.write_text(json.dumps(manifest))
    replay = capture.replay_result_snapshot(path)
    assert replay["row_count"] == 1
    assert replay["records"][0]["evidence"] == "unresolved"
    assert not replay["complete_actual_start_history_verified"]


async def entry_capture(
    tmp_path, *, extra=False, wrong_id=False, venue=4, postrace=False
):
    entries = []
    for r in range(1, 4 if extra else 3):
        for n in range(1, 3):
            entry = row(n, r)
            entry.update(meet=venue, hrName=f"horse-{r}-{n}", stTime="1245", dusu=2)
            if postrace and r == 2:
                entry["dusu"] = 1
            if wrong_id and r == 2 and n == 2:
                entry["hrNo"] = "999"
            entries.append(entry)
    credentials = {"api_key": SECRET}
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=envelope(entries))
        )
    ) as client:
        result = await collect_entry_sheet_snapshot(
            meet=venue,
            race_date="20261011",
            race_no=1,
            output_dir=tmp_path / "entries",
            client=client,
            clock=lambda: NOW + timedelta(seconds=10),
            **credentials,
        )
    return Path(result["manifest_path"])


@pytest.mark.asyncio
async def test_missing_venue_requires_independent_complete_roster_and_later_time(
    tmp_path,
):
    rows = [row(n, r) for r in (1, 2) for n in (1, 2)]
    for entry in rows:
        del entry["meet"]
    path = await collect(
        tmp_path, lambda request: httpx.Response(200, json=envelope(rows))
    )
    assert json.loads(path.read_bytes())["status"] == "identity_unresolved"
    with pytest.raises(ValueError, match="missing_result_venue"):
        capture.replay_result_snapshot(path)
    entries = await entry_capture(tmp_path)
    result = capture.replay_result_snapshot(
        path, entry_capture=entries, archive_root=tmp_path
    )
    assert result["row_count"] == 4
    assert all(r["raw_meet"] is None for r in result["records"])
    assert all(
        r["venue_identity_basis"] == "api26_full_day_roster" for r in result["records"]
    )
    assert (
        result["combined_sources_available_at"]
        == (NOW + timedelta(seconds=10)).isoformat()
    )
    assert result["entry_binding_pins"]


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["extra_race", "wrong_id", "wrong_venue", "tamper"])
async def test_binding_cannot_hide_population_or_identity_conflicts(tmp_path, case):
    rows = [row(n, r) for r in (1, 2) for n in (1, 2)]
    for entry in rows:
        entry.pop("meet")
    path = await collect(
        tmp_path, lambda request: httpx.Response(200, json=envelope(rows))
    )
    entries = await entry_capture(
        tmp_path,
        extra=case == "extra_race",
        wrong_id=case == "wrong_id",
        venue=3 if case == "wrong_venue" else 4,
    )
    if case == "tamper":
        manifest = json.loads(entries.read_bytes())
        Path(manifest["pages"][0]["raw_path"]).write_bytes(b"tampered")
    with pytest.raises(ValueError):
        capture.replay_result_snapshot(
            path, entry_capture=entries, archive_root=tmp_path
        )


@pytest.mark.asyncio
async def test_postrace_identity_binding_does_not_weaken_prerace_roster(tmp_path):
    from autoresearch.kra_race_card_pdf_replay import _replay_entries

    rows = [row(n, r) for r in (1, 2) for n in (1, 2)]
    for entry in rows:
        entry.pop("meet")
    path = await collect(
        tmp_path, lambda request: httpx.Response(200, json=envelope(rows))
    )
    entries = await entry_capture(tmp_path, postrace=True)
    assert (
        capture.replay_result_snapshot(
            path, entry_capture=entries, archive_root=tmp_path
        )["row_count"]
        == 4
    )
    with pytest.raises(ValueError, match="incomplete_entry_field"):
        _replay_entries(
            entries,
            archive_root=tmp_path,
            identity={"meet": 4, "race_date": "20261011", "race_no": 2},
            expected_sha256=None,
        )


@pytest.mark.asyncio
async def test_ambiguous_json_original_is_retained_but_rejected(tmp_path):
    raw = (
        json.dumps(envelope([row()]))
        .replace('"ord": 1', '"ord": 92, "ord": 1')
        .encode()
    )
    path = await collect(tmp_path, lambda request: httpx.Response(200, content=raw))
    manifest = json.loads(path.read_bytes())
    assert manifest["status"] == "failed"
    assert (path.parent / manifest["pages"][0]["raw_file"]).read_bytes() == raw
