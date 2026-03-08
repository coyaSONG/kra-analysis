import pytest
from sqlalchemy import select

from models.database_models import DataStatus, Race
from services.result_collection_service import (
    ResultCollectionService,
    ResultNotFoundError,
)


class EmptyResultKRA:
    async def get_race_result(self, *args, **kwargs):
        return {"response": {"header": {"resultCode": "00"}, "body": {}}}


@pytest.mark.asyncio
@pytest.mark.unit
async def test_collect_result_marks_failed_when_result_missing(db_session):
    race = Race(
        race_id="20240719_1_1",
        date="20240719",
        meet=1,
        race_number=1,
        collection_status=DataStatus.COLLECTED,
        result_status=DataStatus.PENDING,
    )
    db_session.add(race)
    await db_session.commit()

    service = ResultCollectionService()

    with pytest.raises(ResultNotFoundError):
        await service.collect_result(
            race_date="20240719",
            meet=1,
            race_number=1,
            db=db_session,
            kra_api=EmptyResultKRA(),
        )

    refreshed = (
        await db_session.execute(select(Race).where(Race.race_id == "20240719_1_1"))
    ).scalar_one()
    assert refreshed.result_status == DataStatus.FAILED
