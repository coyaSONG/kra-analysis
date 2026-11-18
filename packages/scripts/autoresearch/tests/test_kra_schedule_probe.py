import asyncio
import gzip
import hashlib
import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.kra_schedule import SOURCE_URLS

from autoresearch.kra_schedule_probe import collect_first_date_probe, main
from autoresearch.kra_schedule_snapshot import (
    freeze_universe_candidate,
    replay_schedule_snapshot,
)
from autoresearch.tests.test_kra_schedule import DATE, NOW, page


def probe(tmp_path, day, respond):
    calls = []

    def handle(request):
        calls.append(str(request.url))
        return respond(request)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await collect_first_date_probe(
                race_date=day, output_dir=tmp_path, client=client, clock=lambda: NOW
            )

    receipt = asyncio.run(run())
    observation = json.loads(receipt.read_bytes())
    capture = receipt.with_name(observation["capture"]["path"])
    assert (
        observation["capture"]["sha256"]
        == hashlib.sha256(capture.read_bytes()).hexdigest()
    )
    return capture, observation, calls


def response(request, *, national=None, status_code=200, gzip_national=False):
    source = next(name for name, url in SOURCE_URLS.items() if url == str(request.url))
    content = page(source) if national is None or source != "national" else national
    headers = {
        "content-type": "text/html; charset=utf-8",
        "date": "Wed, 14 Oct 2026 09:00:00 GMT",
    }
    if gzip_national and source == "national":
        headers["content-encoding"] = "gzip"
        content = gzip.compress(content)
    return httpx.Response(status_code, headers=headers, content=content)


def test_exact_date_uses_original_collector_and_preserves_all_bytes(tmp_path):
    capture, result, requests = probe(
        tmp_path, DATE, lambda req: response(req, gzip_national=True)
    )
    assert requests == list(SOURCE_URLS.values())
    assert result["status"] == "national_date_seen"
    assert result["race_date"] == DATE
    manifest = json.loads(capture.read_bytes())
    assert manifest["format_version"] == "kra-schedule-capture-v1"
    assert "first_date_probe" not in manifest
    for label, original in manifest["sources"].items():
        assert result["sources"][label] == {"status": "attempted", "http_status": 200}
        assert (capture.parent / original["raw_file"]).read_bytes() == page(label)
        assert original["http_date"] == "Wed, 14 Oct 2026 09:00:00 GMT"
    replay = replay_schedule_snapshot(capture, race_date=DATE)
    assert replay["status"] == "reconciled" and len(replay["source_pins"]) == 4


@pytest.mark.parametrize(
    ("day", "body", "http_code", "status"),
    [
        ("20261023", page("national"), 200, "date_not_in_national_card"),
        (DATE, b"\n ", 200, "empty_national_response"),
        (DATE, b"<html>missing table</html>", 200, "invalid_national_card"),
        (DATE, b"", 401, "authentication_required"),
        (DATE, b"", 403, "access_denied"),
        (DATE, b"", 429, "rate_limited"),
        (DATE, b"", 503, "http_error"),
    ],
)
def test_gate_keeps_unseen_date_empty_payload_and_http_errors_separate(
    tmp_path, day, body, http_code, status
):
    capture, result, requests = probe(
        tmp_path, day, lambda req: response(req, national=body, status_code=http_code)
    )
    assert requests == [SOURCE_URLS["national"]]
    assert result["status"] == status
    assert result["sources"]["national"]["http_status"] == http_code
    sources = json.loads(capture.read_bytes())["sources"]
    if http_code == 200:
        assert (capture.parent / sources["national"]["raw_file"]).read_bytes() == body
    else:
        assert "raw_file" not in sources["national"]
    for name in set(SOURCE_URLS) - {"national"}:
        assert result["sources"][name] == {
            "status": "not_attempted",
            "skip_reason": status,
        }
        assert sources[name]["error"] == "schedule_source_skipped_by_first_date_probe"
        assert "raw_file" not in sources[name]
    assert replay_schedule_snapshot(capture, race_date=day)["status"] != "reconciled"
    with pytest.raises(ValueError, match="complete_reconciled"):
        freeze_universe_candidate(
            capture,
            race_date=day,
            output=tmp_path / "no-freeze.json",
            clock=lambda: NOW,
        )


def test_regional_rate_limit_stops_the_rest_of_the_batch(tmp_path):
    capture, result, requests = probe(
        tmp_path,
        DATE,
        lambda req: response(
            req, status_code=429 if str(req.url) == SOURCE_URLS["region_2"] else 200
        ),
    )
    assert requests == list(SOURCE_URLS.values())[:3]
    assert result["status"] == "national_date_seen"
    assert result["sources"]["region_2"]["http_status"] == 429
    assert result["sources"]["region_3"]["skip_reason"] == "rate_limited"
    assert replay_schedule_snapshot(capture, race_date=DATE)["status"] != "reconciled"


def test_transport_failure_does_not_retry(tmp_path):
    def fail(req):
        raise httpx.ReadTimeout("upstream did not respond", request=req)

    _, result, requests = probe(tmp_path, DATE, fail)
    assert requests == [SOURCE_URLS["national"]]
    assert result["status"] == "transport_failure"
    assert "http_status" not in result["sources"]["national"]
    assert result["sources"]["region_1"]["skip_reason"] == "transport_failure"


def test_redirect_does_not_leave_the_pinned_route(tmp_path):
    _, result, requests = probe(
        tmp_path,
        DATE,
        lambda req: httpx.Response(302, headers={"location": "https://example.org/"}),
    )
    assert requests == [SOURCE_URLS["national"]]
    assert result["status"] == "http_error"


def test_rejects_invalid_day_before_writing_or_requesting(tmp_path):
    with pytest.raises(ValueError):
        probe(tmp_path, "20260230", lambda req: pytest.fail("unexpected request"))
    assert not list(tmp_path.iterdir())


def test_cli_returns_original_capture_and_separate_receipt(
    tmp_path, capsys, monkeypatch
):
    day = "20261023"
    capture, _, _ = probe(tmp_path, day, response)
    receipt = capture.with_name("first_date_probe.json")

    async def existing_probe(*, race_date, output_dir):
        assert (race_date, output_dir) == (day, tmp_path)
        return receipt

    monkeypatch.setattr(
        "autoresearch.kra_schedule_probe.collect_first_date_probe", existing_probe
    )
    assert main(["--race-date", day, "--output-dir", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "capture": str(capture),
        "probe": str(receipt),
        "national_status": "date_not_in_national_card",
    }
