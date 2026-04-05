from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from scripts import batch_backfill


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
