"""Prove new acquisition limits using only synthetic source responses."""

import asyncio
import json
import sys
from datetime import timedelta
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch.kra_entry_scope_intake import (
    _capture_scope,
    capture_intake,
    plan_intake,
)
from autoresearch.kra_entry_sheet_snapshot import collect_entry_sheet_snapshot
from autoresearch.observed_history_seed import pin
from autoresearch.tests.test_kra_schedule import DATE, NOW, capture, page

DUE = NOW + timedelta(days=2, hours=-6, minutes=-30)
TEST_KEY = "synthetic-local-key"


def response_rows(meet, field_count=1):
    return [
        {
            "meet": meet,
            "rcDate": int(DATE),
            "rcNo": no,
            "hrNo": f"{(meet * 1000 + no * 20 + gate):07d}",
            "chulNo": gate,
            "hrName": f"Fixture {meet}.{no}.{gate}",
            "stTime": "1200",
            "dusu": 10,
        }
        for no in range(1, field_count + 1)
        for gate in range(1, 11)
    ]


def answer(rows, page_no):
    start = (page_no - 1) * 100
    return httpx.Response(
        200,
        json={
            "response": {
                "header": {"resultCode": "00"},
                "body": {
                    "totalCount": len(rows),
                    "pageNo": page_no,
                    "numOfRows": 100,
                    "items": {"item": rows[start : start + 100]},
                },
            }
        },
    )


def mock_gateway(request):
    return answer(
        response_rows(int(request.url.params["meet"])),
        int(request.url.params["pageNo"]),
    )


@pytest.fixture
def inputs(tmp_path):
    schedule = capture(tmp_path / "schedule")
    return tmp_path, pin(tmp_path, schedule)


def run(inputs, *, provide=mock_gateway, reuse=(), limit=4, clock=lambda: NOW):
    root, schedule = inputs
    calls = []

    def mock(request):
        calls.append(
            (int(request.url.params["meet"]), int(request.url.params["pageNo"]))
        )
        return provide(request)

    # The fixture uses a path with no real key.
    secret = root / "synthetic-secret.txt"
    secret.write_text(TEST_KEY)
    result = asyncio.run(
        capture_intake(
            root,
            root / "scoped",
            schedule,
            [DATE],
            reuse=reuse,
            max_requests=limit,
            api_key_file=secret,
            clock=clock,
            transport=httpx.MockTransport(mock),
        )
    )
    return result, calls


def test_whole_card_retained_and_same_window_cannot_fetch_again(inputs):
    (out, report), calls = run(inputs)
    assert calls == [(1, 1), (2, 1), (3, 1), (4, 1)]
    assert report["actual_http_requests"] == 4
    assert report["status"] == "captured_locally"
    assert not report["study_registered"]
    assert not report["independent_publication_verified"]
    assert all(r["state"] == "captured" for r in report["scopes"])
    assert json.loads(out.read_bytes()) == report
    assert TEST_KEY.encode() not in out.read_bytes()
    assert "serviceKey" not in out.read_text()
    original = out.read_bytes()
    with pytest.raises(ValueError, match="already_reserved"):
        run(inputs, provide=lambda _: pytest.fail("duplicate request"))
    assert original == out.read_bytes()


@pytest.mark.parametrize(
    ("provider", "failure", "http_code", "gateway_code"),
    [
        (lambda _: httpx.Response(401), "authentication_error", 401, None),
        (lambda _: httpx.Response(403), "access_denied", 403, None),
        (lambda _: httpx.Response(429), "rate_limited", 429, None),
        (
            lambda _: httpx.Response(
                200, content=b"<error><returnReasonCode>30</returnReasonCode></error>"
            ),
            "authentication_error",
            200,
            "30",
        ),
        (
            lambda _: httpx.Response(
                200, json={"response": {"header": {"resultCode": "22"}}}
            ),
            "rate_limited",
            200,
            "22",
        ),
        (
            lambda _: httpx.Response(
                200, json={"response": {"header": {"resultCode": "03"}}}
            ),
            "no_data_unconfirmed",
            200,
            "03",
        ),
        (lambda _: answer([], 1), "empty_unconfirmed", 200, "00"),
        (lambda _: httpx.Response(200, content=b" \n"), "empty_unconfirmed", 200, None),
        (
            lambda _: httpx.Response(200, content=b"<html>maintenance</html>"),
            "provider_error_or_invalid_body",
            200,
            None,
        ),
        (
            lambda _: httpx.Response(
                302, headers={"location": "https://example.invalid/away"}
            ),
            "http_error",
            302,
            None,
        ),
    ],
)
def test_failure_keeps_all_unattempted_scopes(
    inputs, provider, failure, http_code, gateway_code
):
    (out, report), calls = run(inputs, provide=provider)
    assert calls == [(1, 1)]
    assert report["status"] == "incomplete"
    scopes = report["scopes"]
    assert sum(len(s["races"]) for s in scopes) == 4
    assert scopes[0]["state"] == failure
    assert scopes[0]["requests"][0]["http_status"] == http_code
    assert scopes[0]["requests"][0].get("gateway_result_code") == gateway_code
    assert [s["state"] for s in scopes[1:]] == ["not_attempted"] * 3
    assert [s["stop_reason"] for s in scopes[1:]] == [failure] * 3
    assert TEST_KEY.encode() not in out.read_bytes()


def test_transport_error_does_not_retry_or_record_secret_message(inputs):
    def fail(request):
        raise httpx.ReadTimeout(f"do not retain {request.url}", request=request)

    (out, report), calls = run(inputs, provide=fail)
    assert calls == [(1, 1)]
    assert report["scopes"][0]["state"] == "transport_timeout"
    assert TEST_KEY.encode() not in out.read_bytes()
    assert "serviceKey" not in out.read_text()


def test_scope_finishing_at_first_cutoff_preserves_bytes_but_cannot_continue(inputs):
    current = NOW

    def late(request):
        nonlocal current
        current = DUE
        return mock_gateway(request)

    (_, report), calls = run(inputs, provide=late, clock=lambda: current)
    assert calls == [(1, 1)]
    assert report["status"] == "incomplete"
    assert report["stop_reason"] == "first_block_cutoff_passed"
    assert report["scopes"][0]["capture"]["sha256"]
    assert all(s["state"] == "not_attempted" for s in report["scopes"][1:])


def test_reuse_complete_original_scope_without_replacement(inputs):
    root, _ = inputs

    async def earlier():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(mock_gateway)
        ) as client:
            return await collect_entry_sheet_snapshot(
                meet=1,
                race_date=DATE,
                race_no=1,
                output_dir=root / "earlier",
                client=client,
                clock=lambda: NOW,
                **{"api_key": TEST_KEY},
            )

    source = asyncio.run(earlier())
    path = Path(source["manifest_path"])
    original = path.read_bytes()
    (_, report), calls = run(inputs, reuse=[pin(root, path)], limit=3)
    assert report["scopes"][0]["state"] == "reused"
    assert calls == [(2, 1), (3, 1), (4, 1)]
    assert report["status"] == "captured_locally"
    assert path.read_bytes() == original
    with pytest.raises(ValueError, match="source_pin_mismatch"):
        run(inputs, reuse=[pin(root, path) | {"sha256": "0" * 64}])


def test_late_low_budget_and_partial_schedule_do_not_make_requests(inputs, tmp_path):
    def never(_):
        pytest.fail("unexpected request")

    with pytest.raises(ValueError, match="budget_not_authorized"):
        run(inputs, provide=never, limit=3)
    with pytest.raises(ValueError, match="cutoff_passed"):
        run(inputs, provide=never, clock=lambda: DUE)
    path = capture(
        tmp_path / "two-days",
        pages={
            source: page(source, dates={4: "2026/10/17(\ud1a0)"})
            for source in ("national", "region_1", "region_2", "region_3")
        },
    )
    with pytest.raises(ValueError, match="whole_official_schedule"):
        plan_intake(tmp_path, pin(tmp_path, path), [DATE], observed=NOW)
    plan = plan_intake(tmp_path, pin(tmp_path, path), [DATE, "20261017"], observed=NOW)
    assert plan["race_dates"] == [DATE, "20261017"]
    assert plan["race_count"] == 4


@pytest.mark.parametrize(
    ("fields", "observed", "state"),
    [
        (11, [1, 2], "captured"),
        (12, [1], "schedule_runner_count_conflict"),
        (1, [1], "schedule_runner_count_conflict"),
    ],
)
def test_next_page_is_only_used_for_the_reserved_exact_total(
    tmp_path, fields, observed, state
):
    calls = []
    scope = {
        "meet": 1,
        "race_date": DATE,
        "anchor_race_no": 1,
        "runner_count": 110,
        "request_page_limit": 2,
        "races": [
            {
                "race_no": n,
                "runners": 10,
                "scheduled_start_at": "2026-10-16T12:00:00+09:00",
            }
            for n in range(1, 12)
        ],
    }

    def mock(request):
        no = int(request.url.params["pageNo"])
        calls.append(no)
        return answer(response_rows(1, fields), no)

    async def collect():
        async with httpx.AsyncClient(transport=httpx.MockTransport(mock)) as client:
            return await _capture_scope(
                client, scope, tmp_path, tmp_path / "raw", DUE, lambda: NOW, TEST_KEY
            )

    out = asyncio.run(collect())
    assert calls == observed
    assert out["state"] == state
    assert len(out["requests"]) == len(calls)
    original = json.loads((tmp_path / out["capture"]["path"]).read_bytes())
    assert len(original["pages"]) == len(calls)
    assert all("serviceKey" not in p["request_parameters"] for p in original["pages"])


def test_equal_total_cannot_hide_extra_race(tmp_path):
    scope = {
        "meet": 1,
        "race_date": DATE,
        "anchor_race_no": 1,
        "runner_count": 20,
        "request_page_limit": 1,
        "races": [
            {
                "race_no": no,
                "runners": 10,
                "scheduled_start_at": "2026-10-16T12:00:00+09:00",
            }
            for no in (1, 2)
        ],
    }
    rows = response_rows(1, 2)
    rows[-1]["rcNo"] = 3

    async def collect():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: answer(rows, 1))
        ) as client:
            return await _capture_scope(
                client, scope, tmp_path, tmp_path / "raw", DUE, lambda: NOW, TEST_KEY
            )

    assert asyncio.run(collect())["state"] == "scope_evidence_unverified"
