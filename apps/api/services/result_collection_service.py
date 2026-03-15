"""
경주 결과 수집 서비스.

라우터 레이어에서 직접 KRA 응답 파싱/DB 업데이트를 하지 않도록 분리한다.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

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

    async def _mark_result_failure_with_retry(
        self, race: Race | None, db: AsyncSession
    ) -> None:
        """Fail-open retry wrapper for result failure persistence."""
        last_exc: Exception | None = None

        for attempt in range(2):
            try:
                await self._mark_result_failure(race, db)
                return
            except Exception as exc:
                last_exc = exc
                if attempt < 1:
                    await asyncio.sleep(0.5)

        if last_exc is not None:
            logger.error(
                "Failed to persist result collection failure after retries",
                error=str(last_exc),
            )

    async def collect_result(
        self,
        *,
        race_date: str,
        meet: int,
        race_number: int,
        db: AsyncSession,
        kra_api: KRAAPIService,
    ) -> dict[str, Any]:
        race_id = f"{race_date}_{meet}_{race_number}"
        query_result = await db.execute(select(Race).where(Race.race_id == race_id))
        race = query_result.scalar_one_or_none()
        try:
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
                raise ResultNotFoundError(
                    f"1-3위 결과가 부족합니다 (찾은 수: {len(top3)})"
                )

            if race is None:
                raise ResultNotFoundError(f"경주를 찾을 수 없습니다: {race_id}")

            race.result_data = top3
            race.result_status = DataStatus.COLLECTED
            race.result_collected_at = datetime.now(UTC).replace(tzinfo=None)
            race.updated_at = datetime.now(UTC).replace(tzinfo=None)

            await db.commit()
            logger.info("Race result collected", race_id=race_id, top3=top3)

            # 확정 배당률 자동 수집 (경주 종료 후 확정값)
            odds_result = await self._collect_odds_after_result(
                race_date=race_date,
                meet=meet,
                race_number=race_number,
                race_id=race_id,
                db=db,
                kra_api=kra_api,
            )

            return {"race_id": race_id, "top3": top3, "odds": odds_result}
        except Exception:
            await self._mark_result_failure_with_retry(race, db)
            raise

    async def _collect_odds_after_result(
        self,
        *,
        race_date: str,
        meet: int,
        race_number: int,
        race_id: str,
        db: AsyncSession,
        kra_api: KRAAPIService,
    ) -> dict[str, Any]:
        """결과 수집 직후 확정 배당률 수집 (실패해도 결과 수집에 영향 없음)."""
        try:
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            from models.database_models import RaceOdds

            response = await kra_api.get_final_odds(
                race_date, str(meet), race_no=race_number
            )

            if not KRAResponseAdapter.is_successful_response(response):
                logger.warning("Odds API returned unsuccessful response", race_id=race_id)
                return {"collected": False, "reason": "API response failed"}

            items = KRAResponseAdapter.extract_items(response)

            pool_map = {
                "단승식": "WIN", "연승식": "PLC", "복승식": "QNL",
                "쌍승식": "EXA", "복연승식": "QPL", "삼복승식": "TLA",
                "삼쌍승식": "TRI", "쌍복승식": "XLA",
                "WIN": "WIN", "PLC": "PLC", "QNL": "QNL",
                "EXA": "EXA", "QPL": "QPL", "TLA": "TLA",
                "TRI": "TRI", "XLA": "XLA",
            }
            valid_pools = {"WIN", "PLC", "QNL", "EXA", "QPL", "TLA", "TRI", "XLA"}

            rows = []
            for item in items:
                pool = pool_map.get(item.get("pool", ""), "")
                if pool not in valid_pools:
                    continue
                rows.append({
                    "race_id": race_id,
                    "pool": pool,
                    "chul_no": item.get("chulNo", 0),
                    "chul_no2": item.get("chulNo2", 0),
                    "chul_no3": item.get("chulNo3", 0),
                    "odds": item.get("odds", 0),
                    "rc_date": race_date,
                    "source": "API160_1",
                })

            if rows:
                from sqlalchemy.sql import func

                stmt = pg_insert(RaceOdds).values(rows)
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_race_odds_entry",
                    set_={"odds": stmt.excluded.odds, "collected_at": func.now()},
                )
                await db.execute(stmt)
                await db.commit()

            logger.info("Odds collected after result", race_id=race_id, count=len(rows))
            return {"collected": True, "count": len(rows)}

        except Exception as e:
            logger.warning("Odds collection failed (non-blocking)", race_id=race_id, error=str(e))
            try:
                await db.rollback()
            except Exception:
                pass
            return {"collected": False, "reason": str(e)}

    async def _mark_result_failure(self, race: Race | None, db: AsyncSession) -> None:
        """Persist a result collection failure without overwriting valid collected results."""
        if race is None:
            return

        if race.result_status == DataStatus.COLLECTED and race.result_data:
            return

        try:
            race.result_status = DataStatus.FAILED
            race.updated_at = datetime.now(UTC).replace(tzinfo=None)
            await db.commit()
        except Exception as exc:
            logger.error("Failed to persist result collection failure", error=str(exc))
            await db.rollback()
            raise
