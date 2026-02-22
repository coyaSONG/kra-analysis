import re

import pytest
from fastapi import HTTPException
from starlette.requests import Request


def _metric_value(metrics_text: str, metric_name: str, *label_checks: str) -> float:
    pattern = rf"^{metric_name}\{{([^}}]+)\}} ([0-9]+(?:\.[0-9]+)?)$"

    for line in metrics_text.splitlines():
        match = re.match(pattern, line)
        if not match:
            continue

        labels = match.group(1)
        if all(check in labels for check in label_checks):
            return float(match.group(2))

    return 0.0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_metrics_endpoint_returns_prometheus_text(client):
    response = await client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")
    assert "version=0.0.4" in response.headers.get("content-type", "")
    assert "# HELP kra_http_requests_total" in response.text


@pytest.mark.asyncio
@pytest.mark.unit
async def test_metrics_endpoint_tracks_request_count_and_latency(client):
    before_metrics = (await client.get("/metrics")).text
    before_count = _metric_value(
        before_metrics,
        "kra_http_requests_total",
        'method="GET"',
        'path="/health"',
        'status="200"',
    )
    before_latency_count = _metric_value(
        before_metrics,
        "kra_http_request_duration_seconds_count",
        'method="GET"',
        'path="/health"',
    )

    health_response = await client.get("/health")
    assert health_response.status_code == 200

    after_metrics = (await client.get("/metrics")).text
    after_count = _metric_value(
        after_metrics,
        "kra_http_requests_total",
        'method="GET"',
        'path="/health"',
        'status="200"',
    )
    after_latency_count = _metric_value(
        after_metrics,
        "kra_http_request_duration_seconds_count",
        'method="GET"',
        'path="/health"',
    )

    assert after_count >= before_count + 1
    assert after_latency_count >= before_latency_count + 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_metrics_endpoint_respects_metrics_enabled_flag(client):
    import main_v2

    original = main_v2.settings.metrics_enabled
    main_v2.settings.metrics_enabled = False
    try:
        response = await client.get("/metrics")
        assert response.status_code == 404
    finally:
        main_v2.settings.metrics_enabled = original


@pytest.mark.asyncio
@pytest.mark.unit
async def test_metrics_middleware_records_http_exception_status_code(monkeypatch):
    import main_v2

    captured = {}

    def _record(method: str, path: str, status: int, duration: float):
        captured["method"] = method
        captured["path"] = path
        captured["status"] = status
        captured["duration"] = duration

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/__test/http-exception",
        "raw_path": b"/__test/http-exception",
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "root_path": "",
    }
    request = Request(scope)

    async def _raise_http_exception(_request):
        raise HTTPException(status_code=429, detail="rate limited")

    original = main_v2.settings.metrics_enabled
    main_v2.settings.metrics_enabled = True
    monkeypatch.setattr(main_v2, "record_http_request", _record)

    try:
        with pytest.raises(HTTPException):
            await main_v2.metrics_middleware(request, _raise_http_exception)
    finally:
        main_v2.settings.metrics_enabled = original

    assert captured["method"] == "GET"
    assert captured["path"] == "/__test/http-exception"
    assert captured["status"] == 429
    assert captured["duration"] >= 0
