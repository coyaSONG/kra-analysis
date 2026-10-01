import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, call

import pytest

from scripts import batch_backfill


def _race_plan_response(items, *, page_no, num_rows, total_count):
    return {
        "response": {
            "body": {
                "items": {"item": items},
                "pageNo": page_no,
                "numOfRows": num_rows,
                "totalCount": total_count,
            }
        }
    }


@pytest.mark.asyncio
@pytest.mark.unit
async def test_discover_race_plan_month_paginates_and_deduplicates():
    api = SimpleNamespace(
        _make_request=AsyncMock(
            side_effect=[
                _race_plan_response(
                    [
                        {"rcDate": "20240106", "meet": "1", "rcNo": "1"},
                        {"rcDate": "20240106", "meet": "1", "rcNo": "2"},
                    ],
                    page_no=1,
                    num_rows=2,
                    total_count=3,
                ),
                _race_plan_response(
                    [
                        {"rcDate": "20240106", "meet": "1", "rcNo": "2"},
                        {"rcDate": "20240107", "meet": "3", "rcNo": "1"},
                    ],
                    page_no=2,
                    num_rows=2,
                    total_count=3,
                ),
            ]
        )
    )

    races = await batch_backfill.discover_race_plan_month(
        api,
        year=2024,
        month=1,
        num_rows=2,
    )

    assert [race.race_id for race in races] == [
        "20240106_1_1",
        "20240106_1_2",
        "20240107_3_1",
    ]
    assert api._make_request.await_args_list == [
        call(
            endpoint="API72_2/racePlan_2",
            params={
                "rc_year": "2024",
                "rc_month": "01",
                "numOfRows": 2,
                "pageNo": 1,
            },
        ),
        call(
            endpoint="API72_2/racePlan_2",
            params={
                "rc_year": "2024",
                "rc_month": "01",
                "numOfRows": 2,
                "pageNo": 2,
            },
        ),
    ]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_discover_race_range_filters_partial_months(monkeypatch):
    async def fake_month(_api, *, year, month, meet):
        assert (year, month, meet) in {(2024, 1, 1), (2024, 2, 1)}
        return [
            batch_backfill.RaceKey(f"{year:04d}{month:02d}01", 1, 1),
            batch_backfill.RaceKey(f"{year:04d}{month:02d}20", 1, 1),
        ]

    monkeypatch.setattr(batch_backfill, "discover_race_plan_month", fake_month)

    races = await batch_backfill.discover_race_range(
        object(),
        start="20240115",
        end="20240210",
        meet=1,
    )

    assert [race.race_id for race in races] == ["20240120_1_1", "20240201_1_1"]


@pytest.mark.unit
def test_write_discovery_manifest_is_structured(tmp_path):
    output = tmp_path / "discovery.json"
    races = [batch_backfill.RaceKey("20240106", 1, 2)]

    batch_backfill.write_discovery_manifest(
        output,
        start="20240101",
        end="20240131",
        meet=None,
        races=races,
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["race_count"] == 1
    assert payload["races"] == [
        {
            "meet": 1,
            "race_date": "20240106",
            "race_id": "20240106_1_2",
            "race_number": 2,
        }
    ]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_discover_or_collect_routes_every_race_through_workflow(
    monkeypatch, tmp_path
):
    races = [
        batch_backfill.RaceKey("20240106", 1, 1),
        batch_backfill.RaceKey("20240107", 3, 2),
    ]

    class FakeKRAAPI:
        instances = []

        def __init__(self):
            self.close = AsyncMock()
            self.__class__.instances.append(self)

    async def fake_discover(_api, *, start, end, meet):
        assert (start, end, meet) == ("20240101", "20240131", None)
        return races

    collect_mock = AsyncMock()
    fake_workflow = SimpleNamespace(collect=collect_mock)

    @asynccontextmanager
    async def fake_session():
        yield object()

    monkeypatch.setattr(batch_backfill, "KRAAPIService", FakeKRAAPI)
    monkeypatch.setattr(batch_backfill, "discover_race_range", fake_discover)
    monkeypatch.setattr(
        batch_backfill, "_build_workflow", lambda kra_api, db: fake_workflow
    )
    monkeypatch.setattr(batch_backfill, "async_session_maker", lambda: fake_session())
    monkeypatch.setattr(batch_backfill.asyncio, "sleep", AsyncMock())
    output = tmp_path / "discovery.json"

    await batch_backfill.discover_or_collect_races(
        start="20240101",
        end="20240131",
        meet=None,
        output=output,
        collect=True,
    )

    assert [
        awaited.args[0].key.race_id for awaited in collect_mock.await_args_list
    ] == ["20240106_1_1", "20240107_3_2"]
    assert json.loads(output.read_text(encoding="utf-8"))["race_count"] == 2
    FakeKRAAPI.instances[0].close.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_backfill_enrichment_uses_workflow_materialize(monkeypatch):
    async def fake_get_pending_enrichment(start, end):
        assert start == "20250101"
        assert end == "20250131"
        return ["20250101_1_1", "20250101_1_2"]

    class FakeKRAAPI:
        instances = []

        def __init__(self):
            self.close = AsyncMock()
            self.__class__.instances.append(self)

    materialize_mock = AsyncMock()
    fake_workflow = SimpleNamespace(materialize=materialize_mock)

    @asynccontextmanager
    async def fake_session():
        yield object()

    monkeypatch.setattr(
        batch_backfill, "get_pending_enrichment", fake_get_pending_enrichment
    )
    monkeypatch.setattr(batch_backfill, "KRAAPIService", FakeKRAAPI)
    monkeypatch.setattr(
        batch_backfill, "_build_workflow", lambda kra_api, db: fake_workflow
    )
    monkeypatch.setattr(batch_backfill, "async_session_maker", lambda: fake_session())

    await batch_backfill.backfill_enrichment("20250101", "20250131")

    assert materialize_mock.await_count == 2
    first_command = materialize_mock.await_args_list[0].args[0]
    second_command = materialize_mock.await_args_list[1].args[0]
    assert first_command.race_id == "20250101_1_1"
    assert second_command.race_id == "20250101_1_2"
    assert first_command.target == "enriched"
    assert second_command.target == "enriched"
    FakeKRAAPI.instances[0].close.assert_awaited_once()
