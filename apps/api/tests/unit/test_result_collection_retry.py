from unittest.mock import AsyncMock

import pytest

from services.result_collection_service import ResultCollectionService


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mark_result_failure_retries_and_succeeds(monkeypatch):
    service = ResultCollectionService()
    calls = {"count": 0}
    sleep = AsyncMock()

    async def flaky_mark_failure(race, db):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("commit failed")

    monkeypatch.setattr(service, "_mark_result_failure", flaky_mark_failure)
    monkeypatch.setattr("services.result_collection_service.asyncio.sleep", sleep)

    await service._mark_result_failure_with_retry(None, None)

    assert calls["count"] == 2
    sleep.assert_awaited_once_with(0.5)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mark_result_failure_logs_error_after_all_retries_fail(monkeypatch):
    service = ResultCollectionService()
    sleep = AsyncMock()
    error_calls = []

    async def always_fail(race, db):
        raise RuntimeError("still failing")

    monkeypatch.setattr(service, "_mark_result_failure", always_fail)
    monkeypatch.setattr("services.result_collection_service.asyncio.sleep", sleep)
    monkeypatch.setattr(
        "services.result_collection_service.logger.error",
        lambda event, **kwargs: error_calls.append((event, kwargs)),
    )

    await service._mark_result_failure_with_retry(None, None)

    sleep.assert_awaited_once_with(0.5)
    assert error_calls == [
        (
            "Failed to persist result collection failure after retries",
            {"error": "still failing"},
        )
    ]
