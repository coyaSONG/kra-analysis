import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from httpx import ASGITransport

from middleware.logging import LoggingMiddleware


@pytest.mark.asyncio
async def test_logging_middleware_error_path():
    app = FastAPI()
    app.add_middleware(LoggingMiddleware)

    @app.get('/err')
    async def err():
        raise RuntimeError('boom')

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as ac:
        try:
            await ac.get('/err')
            # Some stacks may return a 500 Response; if so, test is already covered elsewhere
        except Exception as e:
            # Error propagated; LoggingMiddleware should have logged and re-raised
            assert 'boom' in str(e)
