import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_collect_race_data_async_error(monkeypatch, authenticated_client):
    import routers.collection_v2 as r
    def boom():
        raise RuntimeError('uuid fail')
    monkeypatch.setattr(r.uuid, 'uuid4', boom)

    resp = await authenticated_client.post(
        '/api/v2/collection/async',
        json={'date': '20240719', 'meet': 1, 'race_numbers': [1]}
    )
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_collect_race_data_top_level_error(monkeypatch, authenticated_client):
    import routers.collection_v2 as r
    class BadService:
        def __init__(self, *a, **k):
            raise RuntimeError('init fail')
    monkeypatch.setattr(r, 'CollectionService', BadService)

    resp = await authenticated_client.post(
        '/api/v2/collection/',
        json={'date': '20240719', 'meet': 1, 'race_numbers': [1]}
    )
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_get_collection_status_error(monkeypatch, authenticated_client):
    import routers.collection_v2 as r
    class Raising:
        def __init__(self, *a, **k):
            raise RuntimeError('dto fail')
    monkeypatch.setattr(r, 'CollectionStatus', Raising)

    resp = await authenticated_client.get('/api/v2/collection/status?date=20240719&meet=1')
    assert resp.status_code == 500

