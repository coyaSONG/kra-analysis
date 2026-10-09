"""Collection timestamps, byte preservation, errors, and repeatable snapshots."""

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import kra_race_card_pdf_snapshot as snapshot
from autoresearch.tests.race_card_pdf_fixture import HORSE_NAME, make_card_pdf


@pytest.mark.parametrize(
    "eligible,status,parser_status,exit_code",
    [
        (True, "captured", "parsed", 0),
        (False, "captured", "parsed", 2),
        (False, "fetch_error", None, 1),
        (False, "parse_error", None, 1),
        (False, "captured", "blocked", 1),
    ],
)
def test_cli_auto_entries_derive_schedule_and_require_eligibility(
    monkeypatch, tmp_path, capsys, eligible, status, parser_status, exit_code
):
    monkeypatch.setenv("KRA_API_KEY", "cli-test-credential")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "snapshot",
            "--meet",
            "1",
            "--race-date",
            "20260627",
            "--race-no",
            "1",
            "--fetch-entries",
            "--require-eligible",
            "--output-dir",
            str(tmp_path),
        ],
    )
    entries = entry_snapshot()

    async def capture_entries(**kwargs):
        assert kwargs["api_key"] == "cli-test-credential"
        return {"entry_snapshot": entries, "manifest_path": "entries.json"}

    async def capture_pdf(**kwargs):
        assert kwargs["entries"] == entries
        assert kwargs["scheduled_start_time"] == "1035"
        return {
            "race_id": "20260627_1_1",
            "manifest_path": "snapshot.json",
            "collection_status": status,
            "collected_at": entries["collected_at"],
            "sha256": "0" * 64,
            "parsed": {"parser_status": parser_status},
            "audit": {},
            "eligible_for_prerace_features": eligible,
        }

    monkeypatch.setattr(snapshot, "collect_entry_sheet_snapshot", capture_entries)
    monkeypatch.setattr(snapshot, "collect_race_card_pdf", capture_pdf)
    assert snapshot.main() == exit_code
    output = capsys.readouterr().out
    assert "cli-test-credential" not in output
    assert json.loads(output)["eligible_for_prerace_features"] is eligible


def test_cli_missing_key_stops_before_network(monkeypatch, tmp_path):
    monkeypatch.delenv("KRA_API_KEY", raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "snapshot",
            "--meet",
            "1",
            "--race-date",
            "20260627",
            "--race-no",
            "1",
            "--fetch-entries",
            "--api-key-file",
            str(tmp_path / "absent"),
        ],
    )
    with pytest.raises(SystemExit) as exc:
        snapshot.main()
    assert exc.value.code == 2


def clock_values(*timestamps):
    values = iter(datetime.fromisoformat(value) for value in timestamps)
    return lambda: next(values)


def entry_snapshot():
    return {
        "meet": 1,
        "race_date": "20260627",
        "race_no": 1,
        "collected_at": "2026-06-27T00:30:00+00:00",
        "scheduled_start_time": "1035",
        "entries": [
            {
                "chulNo": number,
                "hrName": HORSE_NAME,
                "hrNo": str(number),
                "rank": number,
            }
            for number in (1, 2)
        ],
    }


@pytest.mark.asyncio
async def test_capture_preserves_bytes_headers_actual_completion_and_entry_provenance(
    tmp_path,
):
    pytest.importorskip("pdfplumber")
    content = make_card_pdf()
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                content=content,
                headers={
                    "content-type": "application/pdf",
                    "last-modified": "Wed, 24 Jun 2026 07:00:59 GMT",
                },
            )
        )
    )
    async with client:
        result = await snapshot.collect_race_card_pdf(
            meet=1,
            race_date="20260627",
            race_no=1,
            output_dir=tmp_path,
            scheduled_start_time="1035",
            entries=entry_snapshot(),
            client=client,
            clock=clock_values(
                "2026-06-27T00:59:59+00:00",
                "2026-06-27T01:00:01+00:00",
                "2026-06-27T01:00:02+00:00",
            ),
        )
        assert not client.is_closed
    assert result["collection_status"] == "captured"
    assert result["collected_at"] == "2026-06-27T01:00:01+00:00"
    assert result["sha256"] == hashlib.sha256(content).hexdigest()
    assert Path(result["raw_path"]).read_bytes() == content
    assert json.loads(Path(result["manifest_path"]).read_text()) == result
    assert result["eligible_for_prerace_features"] is True
    assert "rank" not in result["entry_snapshot"]["entries"][0]


@pytest.mark.asyncio
async def test_old_last_modified_cannot_backdate_a_historical_fetch(tmp_path):
    pytest.importorskip("pdfplumber")
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                content=make_card_pdf(),
                headers={
                    "content-type": "application/pdf",
                    "last-modified": "Wed, 24 Jun 2026 07:00:59 GMT",
                },
            )
        )
    )
    async with client:
        result = await snapshot.collect_race_card_pdf(
            meet=1,
            race_date="20260627",
            race_no=1,
            output_dir=tmp_path,
            scheduled_start_time="1035",
            entries=entry_snapshot(),
            client=client,
            clock=lambda: datetime(2026, 10, 9, tzinfo=UTC),
        )
    assert result["collection_status"] == "captured"
    assert "source_after_cutoff" in result["audit"]["reasons"]
    assert result["audit"]["feature_rows"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,content,content_type",
    [
        (404, b"missing", "text/html"),
        (200, b"<html>error</html>", "application/pdf"),
        (200, b"%PDF-fake", "text/html"),
        (302, b"", "application/pdf"),
    ],
)
async def test_failures_have_manifest_without_fake_raw_snapshot(
    tmp_path, status, content, content_type
):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                status, content=content, headers={"content-type": content_type}
            )
        )
    ) as client:
        result = await snapshot.collect_race_card_pdf(
            meet=1, race_date="20260627", race_no=1, output_dir=tmp_path, client=client
        )
    assert result["collection_status"] == "fetch_error"
    assert result["raw_path"] is None
    assert result["collected_at"] is None
    assert not result["eligible_for_prerace_features"]
    assert Path(result["manifest_path"]).is_file()


@pytest.mark.asyncio
async def test_parser_failure_still_preserves_raw_evidence(tmp_path):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, content=b"%PDF-broken", headers={"content-type": "application/pdf"}
            )
        )
    ) as client:
        result = await snapshot.collect_race_card_pdf(
            meet=1, race_date="20260627", race_no=1, output_dir=tmp_path, client=client
        )
    assert result["collection_status"] == "parse_error"
    assert Path(result["raw_path"]).read_bytes() == b"%PDF-broken"
    assert not result["eligible_for_prerace_features"]


@pytest.mark.asyncio
async def test_timeout_is_recorded(tmp_path):
    def handler(request):
        raise httpx.ReadTimeout("test timeout", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await snapshot.collect_race_card_pdf(
            meet=1, race_date="20260627", race_no=1, output_dir=tmp_path, client=client
        )
    assert result["collection_status"] == "fetch_error"
    assert result["error_type"] == "ReadTimeout"


@pytest.mark.asyncio
async def test_oversize_response_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshot, "MAX_PDF_BYTES", 10)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                content=b"%PDF-" + b"0" * 10,
                headers={"content-type": "application/pdf"},
            )
        )
    ) as client:
        result = await snapshot.collect_race_card_pdf(
            meet=1, race_date="20260627", race_no=1, output_dir=tmp_path, client=client
        )
    assert result["error"] == "response_too_large"
    assert not result["eligible_for_prerace_features"]


@pytest.mark.asyncio
async def test_same_bytes_and_timestamp_never_overwrite_an_observation(tmp_path):
    pytest.importorskip("pdfplumber")
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                content=make_card_pdf(),
                headers={"content-type": "application/pdf"},
            )
        )
    ) as client:
        results = [
            await snapshot.collect_race_card_pdf(
                meet=1,
                race_date="20260627",
                race_no=1,
                output_dir=tmp_path,
                client=client,
                clock=lambda: datetime(2026, 6, 26, tzinfo=UTC),
            )
            for _ in range(2)
        ]
    assert results[0]["sha256"] == results[1]["sha256"]
    assert results[0]["manifest_path"] != results[1]["manifest_path"]
    assert all(Path(row["manifest_path"]).is_file() for row in results)


@pytest.mark.asyncio
async def test_naive_capture_clock_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="timezone-aware"):
        await snapshot.collect_race_card_pdf(
            meet=1,
            race_date="20260627",
            race_no=1,
            output_dir=tmp_path,
            clock=lambda: datetime(2026, 6, 26),
        )


@pytest.mark.asyncio
async def test_backwards_clock_is_not_accepted(tmp_path):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                content=make_card_pdf(),
                headers={"content-type": "application/pdf"},
            )
        )
    ) as client:
        result = await snapshot.collect_race_card_pdf(
            meet=1,
            race_date="20260627",
            race_no=1,
            output_dir=tmp_path,
            client=client,
            clock=clock_values(
                "2026-06-27T01:00:01+00:00",
                "2026-06-27T01:00:00+00:00",
                "2026-06-27T01:00:02+00:00",
            ),
        )
    assert result["error"] == "capture_clock_moved_backwards"
    assert result["collected_at"] is None
