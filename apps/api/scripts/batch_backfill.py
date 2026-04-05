"""
2025년 데이터 백필 스크립트.

result_status=pending인 경주의 결과를 수집하고,
enrichment_status=pending인 경주의 enrichment를 실행한다.

Usage:
    uv run python3 apps/api/scripts/batch_backfill.py results
    uv run python3 apps/api/scripts/batch_backfill.py enrich
    uv run python3 apps/api/scripts/batch_backfill.py all          # results → enrich 순차
    uv run python3 apps/api/scripts/batch_backfill.py results --start 20250901 --end 20251231
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
API_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_DIR))
os.chdir(API_DIR)

# ---------------------------------------------------------------------------
# apps/api imports (after path setup)
# ---------------------------------------------------------------------------
from sqlalchemy import select  # noqa: E402

from infrastructure.database import async_session_maker, close_db  # noqa: E402
from models.database_models import DataStatus, Race  # noqa: E402
from services.kra_api_service import KRAAPIService  # noqa: E402
from services.race_processing_workflow import (  # noqa: E402
    MaterializeRaceCommand,
    build_race_processing_workflow,
)
from services.result_collection_service import (  # noqa: E402
    ResultCollectionService,
    ResultNotFoundError,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("batch_backfill")

API_DELAY_SECONDS = 1.0
MEET_NAMES = {1: "서울", 2: "제주", 3: "부산경남"}


def _build_workflow(kra_api: KRAAPIService, db):
    return build_race_processing_workflow(kra_api, db)


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------
async def get_pending_results(
    start: str | None = None, end: str | None = None
) -> list[tuple[str, int, int]]:
    """result_status=pending인 경주 목록을 반환한다."""
    async with async_session_maker() as db:
        q = select(Race.date, Race.meet, Race.race_number).where(
            Race.result_status == DataStatus.PENDING,
            Race.collection_status.in_([DataStatus.COLLECTED, DataStatus.ENRICHED]),
        )
        if start:
            q = q.where(Race.date >= start)
        if end:
            q = q.where(Race.date <= end)
        q = q.order_by(Race.date, Race.meet, Race.race_number)
        result = await db.execute(q)
        return [(r[0], r[1], r[2]) for r in result.fetchall()]


async def get_pending_enrichment(
    start: str | None = None, end: str | None = None
) -> list[str]:
    """enrichment_status=pending이고 basic_data가 있는 경주 ID 목록을 반환한다."""
    async with async_session_maker() as db:
        q = select(Race.race_id).where(
            Race.enrichment_status == DataStatus.PENDING,
            Race.collection_status.in_([DataStatus.COLLECTED, DataStatus.ENRICHED]),
            Race.basic_data.isnot(None),
        )
        if start:
            q = q.where(Race.date >= start)
        if end:
            q = q.where(Race.date <= end)
        q = q.order_by(Race.race_id)
        result = await db.execute(q)
        return [r[0] for r in result.fetchall()]


# ---------------------------------------------------------------------------
# Result collection
# ---------------------------------------------------------------------------
async def backfill_results(start: str | None, end: str | None) -> None:
    pending = await get_pending_results(start, end)
    logger.info("결과 미수집 경주: %d건", len(pending))
    if not pending:
        return

    kra_api = KRAAPIService()
    result_svc = ResultCollectionService()
    collected, failed, not_found = 0, 0, 0

    try:
        for idx, (race_date, meet, race_no) in enumerate(pending, 1):
            try:
                async with async_session_maker() as db:
                    await result_svc.collect_result(
                        race_date=race_date,
                        meet=meet,
                        race_number=race_no,
                        db=db,
                        kra_api=kra_api,
                    )
                collected += 1
                logger.info(
                    "[%d/%d] 결과 수집: %s %s %dR",
                    idx,
                    len(pending),
                    race_date,
                    MEET_NAMES.get(meet, str(meet)),
                    race_no,
                )
            except ResultNotFoundError:
                not_found += 1
                logger.debug("결과 없음: %s meet=%d race=%d", race_date, meet, race_no)
            except Exception as e:
                failed += 1
                logger.error(
                    "결과 수집 실패: %s meet=%d race=%d error=%s",
                    race_date,
                    meet,
                    race_no,
                    e,
                )
            await asyncio.sleep(API_DELAY_SECONDS)

            if idx % 50 == 0:
                logger.info(
                    "중간 통계 (%d/%d): 수집=%d, 없음=%d, 실패=%d",
                    idx,
                    len(pending),
                    collected,
                    not_found,
                    failed,
                )
    finally:
        await kra_api.close()

    logger.info(
        "결과 수집 완료: 수집=%d, 없음=%d, 실패=%d (총 %d건)",
        collected,
        not_found,
        failed,
        len(pending),
    )


# ---------------------------------------------------------------------------
# Enrichment
# ---------------------------------------------------------------------------
async def backfill_enrichment(start: str | None, end: str | None) -> None:
    pending = await get_pending_enrichment(start, end)
    logger.info("enrichment 미실행 경주: %d건", len(pending))
    if not pending:
        return

    kra_api = KRAAPIService()
    enriched, failed = 0, 0

    try:
        for idx, race_id in enumerate(pending, 1):
            try:
                async with async_session_maker() as db:
                    workflow = _build_workflow(kra_api, db)
                    await workflow.materialize(
                        MaterializeRaceCommand(race_id=race_id, target="enriched")
                    )
                enriched += 1
                if idx % 20 == 0 or idx == len(pending):
                    logger.info(
                        "[%d/%d] enrichment 진행: 완료=%d, 실패=%d",
                        idx,
                        len(pending),
                        enriched,
                        failed,
                    )
            except Exception as e:
                failed += 1
                logger.error("enrichment 실패: %s error=%s", race_id, e)

            if idx % 50 == 0:
                await asyncio.sleep(0.5)
    finally:
        await kra_api.close()

    logger.info(
        "enrichment 완료: 성공=%d, 실패=%d (총 %d건)",
        enriched,
        failed,
        len(pending),
    )


# ---------------------------------------------------------------------------
# Odds collection
# ---------------------------------------------------------------------------
async def backfill_odds(start: str | None, end: str | None) -> None:
    """result_status=collected인 경주의 배당률을 수집한다."""
    # 간단하게: race_odds에 없는 경주를 직접 쿼리
    async with async_session_maker() as db:
        from sqlalchemy import text as sa_text

        # 이미 odds가 있는 race_id
        existing_result = await db.execute(
            sa_text("SELECT DISTINCT race_id FROM race_odds")
        )
        existing_ids = {r[0] for r in existing_result.fetchall()}

        # result_status=collected인 전체 경주
        q = select(Race.race_id, Race.date, Race.meet, Race.race_number).where(
            Race.result_status == DataStatus.COLLECTED,
        )
        if start:
            q = q.where(Race.date >= start)
        if end:
            q = q.where(Race.date <= end)
        q = q.order_by(Race.date, Race.meet, Race.race_number)
        result = await db.execute(q)
        all_races = [(r[0], r[1], r[2], r[3]) for r in result.fetchall()]

    missing = [
        (rid, d, m, rn) for rid, d, m, rn in all_races if rid not in existing_ids
    ]
    logger.info("배당률 미수집 경주: %d건 (전체 %d건)", len(missing), len(all_races))
    if not missing:
        return

    kra_api = KRAAPIService()
    from services.result_collection_service import ResultCollectionService

    result_svc = ResultCollectionService()
    collected, failed = 0, 0

    try:
        for idx, (race_id, race_date, meet, race_no) in enumerate(missing, 1):
            try:
                async with async_session_maker() as db:
                    odds_result = await result_svc._collect_odds_after_result(
                        race_date=race_date,
                        meet=meet,
                        race_number=race_no,
                        race_id=race_id,
                        db=db,
                        kra_api=kra_api,
                    )
                    if odds_result.get("collected"):
                        collected += 1
                    else:
                        failed += 1
                        if idx <= 5:
                            logger.warning(
                                "odds 수집 실패: %s reason=%s",
                                race_id,
                                odds_result.get("reason"),
                            )
            except Exception as e:
                failed += 1
                logger.error("odds 수집 에러: %s error=%s", race_id, e)

            await asyncio.sleep(API_DELAY_SECONDS)

            if idx % 100 == 0:
                logger.info(
                    "odds 중간 통계 (%d/%d): 수집=%d, 실패=%d",
                    idx,
                    len(missing),
                    collected,
                    failed,
                )
    finally:
        await kra_api.close()

    logger.info(
        "배당률 수집 완료: 수집=%d, 실패=%d (총 %d건)",
        collected,
        failed,
        len(missing),
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main(command: str, start: str | None, end: str | None) -> None:
    try:
        if command in ("results", "all"):
            await backfill_results(start, end)
        if command in ("enrich", "all"):
            await backfill_enrichment(start, end)
        if command in ("odds", "all"):
            await backfill_odds(start, end)
    finally:
        await close_db()
        logger.info("리소스 정리 완료")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KRA 데이터 백필")
    parser.add_argument(
        "command",
        choices=["results", "enrich", "odds", "all"],
        help="results=결과수집, enrich=enrichment, odds=배당률, all=전체 순차 실행",
    )
    parser.add_argument("--start", default=None, help="시작일 (YYYYMMDD)")
    parser.add_argument("--end", default=None, help="종료일 (YYYYMMDD)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args.command, args.start, args.end))
