"""
경주 결과 수집 서비스.

라우터 레이어에서 직접 KRA 응답 파싱/DB 업데이트를 하지 않도록 분리한다.
"""

from datetime import UTC, datetime
from typing import Any, cast

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.kra_response_adapter import KRAResponseAdapter
from models.database_models import DataStatus, Race
from services.kra_api_service import KRAAPIService

logger = structlog.get_logger()


class ResultNotFoundError(Exception):
    """결과 데이터를 찾지 못했을 때 사용."""


class ResultCollectionService:
    """경주 결과(1~3위) 수집/저장 서비스."""

    async def collect_result(
        self,
        *,
        race_date: str,
        meet: int,
        race_number: int,
        db: AsyncSession,
        kra_api: KRAAPIService,
    ) -> dict[str, Any]:
        result_response = await kra_api.get_race_result(
            race_date, str(meet), race_number
        )

        if not KRAResponseAdapter.is_successful_response(result_response):
            raise ResultNotFoundError(
                f"경주 결과를 찾을 수 없습니다: {race_date} {meet}경마장 {race_number}R"
            )

        items = KRAResponseAdapter.extract_items(result_response)
        if not items:
            raise ResultNotFoundError("경주 결과 데이터가 비어있습니다")

        sorted_items = sorted(
            [item for item in items if item.get("ord") and int(item["ord"]) > 0],
            key=lambda item: int(item["ord"]),
        )
        top3 = [int(item["chulNo"]) for item in sorted_items[:3]]
        if len(top3) < 3:
            raise ResultNotFoundError(f"1-3위 결과가 부족합니다 (찾은 수: {len(top3)})")

        race_id = f"{race_date}_{meet}_{race_number}"
        query_result = await db.execute(select(Race).where(Race.race_id == race_id))
        race = query_result.scalar_one_or_none()
        if race is None:
            raise ResultNotFoundError(f"경주를 찾을 수 없습니다: {race_id}")

        # SQLAlchemy 모델 타입 힌트 제약으로 인해 런타임 객체로 취급한다.
        race_record = cast(Any, race)
        race_record.result_data = top3
        race_record.result_status = DataStatus.COLLECTED
        race_record.result_collected_at = datetime.now(UTC)
        race_record.updated_at = datetime.now(UTC)

        await db.commit()
        logger.info("Race result collected", race_id=race_id, top3=top3)

        return {"race_id": race_id, "top3": top3}
