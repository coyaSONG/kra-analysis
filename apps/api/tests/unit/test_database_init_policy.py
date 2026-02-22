from types import SimpleNamespace

import pytest

import infrastructure.database as database


class _FakeBeginContext:
    def __init__(self):
        self.run_sync_called = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def run_sync(self, fn):
        self.run_sync_called = True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_init_db_skips_create_all_outside_development(monkeypatch):
    begin_ctx = _FakeBeginContext()
    fake_engine = SimpleNamespace(begin=lambda: begin_ctx)

    monkeypatch.setattr(database, "engine", fake_engine)
    monkeypatch.setattr(database.settings, "environment", "test")
    monkeypatch.setattr(database.settings, "db_auto_create_on_startup", False)

    await database.init_db()

    assert begin_ctx.run_sync_called is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_init_db_runs_create_all_in_development(monkeypatch):
    begin_ctx = _FakeBeginContext()
    fake_engine = SimpleNamespace(begin=lambda: begin_ctx)

    monkeypatch.setattr(database, "engine", fake_engine)
    monkeypatch.setattr(database.settings, "environment", "development")
    monkeypatch.setattr(database.settings, "db_auto_create_on_startup", False)

    await database.init_db()

    assert begin_ctx.run_sync_called is True
