import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from dependencies.auth import check_resource_access, require_resource_access
from models.database_models import Job, JobStatus, JobType, Prediction


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_resource_access_prediction_true(db_session):
    p = Prediction(
        prediction_id="pred-1",
        race_id="race-x",
        prompt_id="p1",
        predicted_positions=[1, 2, 3],
    )
    db_session.add(p)
    await db_session.commit()

    class AK:
        permissions = []
        name = "x"

    ok = await check_resource_access("prediction", "pred-1", AK(), db_session)
    assert ok is True


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_require_resource_access_job_allow_and_deny(db_session):
    # Create job owned by env key name 'Environment Key'
    j = Job(
        type=JobType.COLLECTION,
        status=JobStatus.PENDING,
        parameters={},
        created_by="Environment Key",
    )
    db_session.add(j)
    await db_session.commit()
    await db_session.refresh(j)

    # Ensure the header key exists in DB for this test app
    from models.database_models import APIKey as DBAPIKey

    dbkey = DBAPIKey(
        key="test-api-key-123",
        name="Environment Key",
        is_active=True,
        permissions=["read", "write"],
    )
    db_session.add(dbkey)
    await db_session.commit()

    app = FastAPI()

    from infrastructure.database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    @app.get("/guard/jobs/{job_id}")
    async def guard(job_id: str, _=Depends(require_resource_access("job", "job_id"))):
        return {"ok": True}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Authorized with env key from settings.valid_api_keys (in tests fixture)
        r_ok = await ac.get(
            f"/guard/jobs/{j.job_id}", headers={"X-API-Key": "test-api-key-123"}
        )
        assert r_ok.status_code == 200

        # Deny: wrong job id
        r_dn = await ac.get(
            "/guard/jobs/does-not-exist", headers={"X-API-Key": "test-api-key-123"}
        )
        assert r_dn.status_code == 403
