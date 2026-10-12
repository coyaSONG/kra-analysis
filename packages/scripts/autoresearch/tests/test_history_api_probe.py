"""Diagnostics must not leak credentials or accept error envelopes as data."""

import asyncio
import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import history_api_probe as p


def page(total=0):
    return {
        "response": {
            "header": {"resultCode": "00"},
            "body": {
                "totalCount": total,
                "pageNo": 1,
                "numOfRows": 100,
                "items": {"item": [{}] * min(total, 100)},
            },
        }
    }


@pytest.mark.parametrize(
    "total,category", [(0, "empty_unconfirmed"), (101, "valid_page")]
)
def test_strict_page(total, category):
    result = p.classify(json.dumps(page(total)).encode())
    assert result["category"] == category
    assert result["total_count"] == total
    assert result["page_rows"] == min(total, 100)


@pytest.mark.parametrize(
    "payload,category",
    [
        ({"header": {"resultCode": "22"}, "body": {}}, "api_error"),
        ({"error": "secret in server error"}, "json_schema_mismatch"),
        ({"response": {"header": {"resultCode": "00"}}}, "json_schema_mismatch"),
        ([], "json_non_object"),
    ],
)
def test_gateway_json_never_empty(payload, category):
    result = p.classify(json.dumps(payload).encode())
    assert result["category"] == category
    assert "secret" not in json.dumps(result)


def test_incomplete_and_wrong_pagination_rejected():
    data = page(1)
    data["response"]["body"]["items"] = {}
    assert p.classify(json.dumps(data).encode())["category"] == "json_schema_mismatch"
    data = page()
    data["response"]["body"]["pageNo"] = 2
    assert p.classify(json.dumps(data).encode())["category"] == "json_schema_mismatch"


def test_xml_dtd_malformed_and_secret_text():
    assert p.classify(
        b"<root><returnReasonCode>30</returnReasonCode><msg>secret</msg></root>"
    ) == {
        "category": "xml_response",
        "result_code": "30",
    }
    for value in (
        b"<broken",
        b'<!DOCTYPE x [<!ENTITY a "secret">]><x>&a;</x>',
        b"\x00",
    ):
        assert p.classify(value)["category"] == "non_json_unparsed"
    assert (
        p.classify(b"<root><resultCode>secret</resultCode></root>")["result_code"]
        == "other_or_absent"
    )


def run(handler):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await p.probe("api26", "20260705", 1, "test%2Bsecret", client=client)

    return asyncio.run(go())


def test_probe_does_not_leak_response_headers_body_or_url():
    def handler(request):
        assert request.url.params["serviceKey"] == "test+secret"
        return httpx.Response(
            200, json={"error": str(request.url)}, headers={"secret": "test+secret"}
        )

    receipt = run(handler)
    assert receipt["http_status"] == 200
    assert receipt["diagnosis"]["category"] == "json_schema_mismatch"
    assert "secret" not in json.dumps(receipt)
    assert "serviceKey" not in json.dumps(receipt)


@pytest.mark.parametrize(
    "error,category",
    [
        (httpx.ReadTimeout, "timeout"),
        (httpx.ConnectError, "transport_error"),
    ],
)
def test_exception_message_never_persisted(error, category):
    def handler(request):
        raise error("test+secret", request=request)

    receipt = run(handler)
    assert receipt["diagnosis"]["category"] == category
    assert "secret" not in json.dumps(receipt)


def test_redirect_not_followed():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(302, headers={"location": "https://example.com/?secret"})

    receipt = run(handler)
    assert len(calls) == 1
    assert receipt["http_status"] == 302
    assert receipt["diagnosis"]["category"] == "http_error"


def test_http_failure_cannot_be_valid_data():
    result = run(lambda r: httpx.Response(500, json=page()))
    assert result["diagnosis"]["category"] == "http_error"
    assert result["diagnosis"]["response_category"] == "empty_unconfirmed"


def test_total_deadline(monkeypatch):
    monkeypatch.setattr(p, "DEADLINE", 0.01)

    async def handler(request):
        await asyncio.sleep(1)
        return httpx.Response(200, json=page())

    assert run(handler)["diagnosis"]["category"] == "timeout"


def test_size_bound(monkeypatch):
    monkeypatch.setattr(p, "MAX_BYTES", 10)
    assert (
        run(lambda r: httpx.Response(200, content=b"x" * 11))["diagnosis"]["category"]
        == "body_limit"
    )
