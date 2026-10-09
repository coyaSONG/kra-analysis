"""Build a complete local PDF/API capture chain through offline mock HTTP."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from shared.kra_entry_sheet import build_entry_snapshot

from autoresearch.kra_entry_sheet_snapshot import collect_entry_sheet_snapshot
from autoresearch.kra_race_card_pdf_snapshot import collect_race_card_pdf
from autoresearch.tests.race_card_pdf_fixture import HORSE_NAME, make_card_pdf

IDENTITY = {"meet": 1, "race_date": "20260627", "race_no": 1}


def entry(number: int, *, race_no: int = 1, count: int = 2) -> dict[str, Any]:
    return {
        "meet": 1,
        "rcDate": 20260627,
        "rcNo": race_no,
        "chulNo": number,
        "hrName": HORSE_NAME,
        "hrNo": f"00{number}",
        "stTime": "1035",
        "dusu": count,
        "rank": "class_not_outcome",
    }


async def capture_chain(
    directory: Path,
    *,
    rows: list[dict[str, Any]] | None = None,
    captured_at: datetime = datetime(2026, 6, 27, 1, 0, tzinfo=UTC),
) -> dict[str, Any]:
    rows = rows if rows is not None else [entry(1), entry(2)]

    def response(request: httpx.Request) -> httpx.Response:
        if request.url.host == "race.kra.co.kr":
            return httpx.Response(
                200,
                content=make_card_pdf(),
                headers={"content-type": "application/pdf"},
            )
        number = int(request.url.params["pageNo"])
        page_rows = rows[(number - 1) * 100 : number * 100]
        return httpx.Response(
            200,
            json={
                "response": {
                    "header": {"resultCode": "00"},
                    "body": {
                        "totalCount": len(rows),
                        "numOfRows": 100,
                        "pageNo": number,
                        "items": {"item": page_rows},
                    },
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
        credentials = {"api_key": "fixture-credential-not-a-secret"}
        entries = await collect_entry_sheet_snapshot(
            **IDENTITY,
            **credentials,
            output_dir=directory,
            client=client,
            clock=lambda: datetime(2026, 6, 27, 0, 30, tzinfo=UTC),
        )
        pdf = await collect_race_card_pdf(
            **IDENTITY,
            output_dir=directory,
            entries=entries["entry_snapshot"],
            scheduled_start_time="1035",
            client=client,
            clock=lambda: captured_at,
        )
    return {"pdf": pdf, "entries": entries}


async def capture_reused_entry_chain(directory: Path) -> dict[str, Any]:
    rows = [entry(1), entry(2), entry(1, race_no=2), entry(2, race_no=2)]
    source = await capture_chain(directory, rows=rows)
    target_identity = {**IDENTITY, "race_no": 2}
    captured = datetime.fromisoformat(source["entries"]["collected_at"])
    entries = build_entry_snapshot(rows, **target_identity, collected_at=captured)
    entries["source_manifest_path"] = source["entries"]["manifest_path"]
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                content=make_card_pdf(race_no=2),
                headers={"content-type": "application/pdf"},
            )
        )
    ) as client:
        pdf = await collect_race_card_pdf(
            **target_identity,
            entries=entries,
            scheduled_start_time="1035",
            output_dir=directory,
            client=client,
            clock=lambda: datetime(2026, 6, 27, 1, 0, tzinfo=UTC),
        )
    return {"pdf": pdf, "entries": source["entries"]}


def save_json(path: str | Path, payload: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
