import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from dependencies.auth import check_resource_access, require_resource_access
from infrastructure.database import get_db
from models.database_models import APIKey as DBAPIKey
from models.database_models import Job, JobStatus, JobType, Prediction
from policy.principal import AuthenticatedPrincipal, PolicyLimits


def _principal(
    *,
    owner_ref: str,
    display_name: str | None,
    permissions: list[str] | None = None,
) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        principal_id=f"api_key:{owner_ref}",
        subject_id=owner_ref,
        owner_ref=owner_ref,
        credential_id=owner_ref,
        display_name=display_name,
        auth_method="api_key",
        permissions=frozenset(permissions or []),
        limits=PolicyLimits(),
    )


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_resource_access_prediction_true(db_session):
    p = Prediction(
        prediction_id="pred-1",
        race_id="race-x",
        prompt_id="p1",
        predicted_positions=[1, 2, 3],
        created_by="x",
    )
    db_session.add(p)
    await db_session.commit()

    ok = await check_resource_access(
        "prediction",
        "pred-1",
        _principal(owner_ref="principal-x", display_name="x"),
        db_session,
    )
    assert ok is True


@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_resource_access_prediction_denies_non_owner(db_session):
    p = Prediction(
        prediction_id="pred-2",
        race_id="race-x",
        prompt_id="p1",
        predicted_positions=[1, 2, 3],
        created_by="owner",
    )
    db_session.add(p)
    await db_session.commit()

    ok = await check_resource_access(
        "prediction",
        "pred-2",
        _principal(owner_ref="other-user", display_name="other-user"),
        db_session,
    )
    assert ok is False


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

    dbkey = DBAPIKey(
        key="test-api-key-123",
        name="Environment Key",
        is_active=True,
        permissions=["read", "write"],
    )
    db_session.add(dbkey)
    await db_session.commit()

    app = FastAPI()

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


@pytest.mark.asyncio
@pytest.mark.unit
async def test_require_resource_access_verifies_db_key_once(db_session):
    presented_key = "resource-access-key-12345"
    dbkey = DBAPIKey(
        key=presented_key,
        name="Resource User",
        is_active=True,
        permissions=["read", "write"],
        today_requests=0,
        total_requests=0,
    )
    job = Job(
        type=JobType.COLLECTION,
        status=JobStatus.PENDING,
        parameters={},
        created_by=presented_key,
    )
    db_session.add_all([dbkey, job])
    await db_session.commit()
    await db_session.refresh(job)

    app = FastAPI()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    @app.get("/guard/jobs/{job_id}")
    async def guard(job_id: str, _=Depends(require_resource_access("job", "job_id"))):
        return {"ok": True}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            f"/guard/jobs/{job.job_id}", headers={"X-API-Key": presented_key}
        )

    assert response.status_code == 200
    await db_session.refresh(dbkey)
    assert dbkey.today_requests == 1
    assert dbkey.total_requests == 1
