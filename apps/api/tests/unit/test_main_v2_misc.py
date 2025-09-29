import pytest
from starlette.requests import Request
from starlette.types import Scope

from main_v2 import create_required_directories, global_exception_handler


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_required_directories_runs():
    # Function should not raise and ensures dirs exist
    await create_required_directories()


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_global_exception_handler_response():
    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "method": "GET",
        "path": "/boom",
        "headers": [],
        "query_string": b"",
    }
    request = Request(scope)
    resp = await global_exception_handler(request, RuntimeError("boom"))
    assert resp.status_code == 500
    data = resp.body
    assert b"error" in data and b"error_id" in data
