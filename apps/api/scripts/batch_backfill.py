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
import json
import logging
import math
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

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
    CollectRaceCommand,
    MaterializeRaceCommand,
    RaceKey,
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
DEFAULT_DISCOVERY_OUTPUT = (
    API_DIR.parent.parent / ".cache/autoresearch/kra_race_plan_discovery.json"
)


def _build_workflow(kra_api: KRAAPIService, db):
    return build_race_processing_workflow(kra_api, db)


def _response_body(response: dict[str, Any]) -> dict[str, Any]:
    envelope = response.get("response")
    body = envelope.get("body") if isinstance(envelope, dict) else None
    if not isinstance(body, dict):
        raise ValueError("KRA race-plan response is missing response.body")
    return body


def _page_items(body: dict[str, Any]) -> list[dict[str, Any]]:
    items_container = body.get("items")
    raw_items = (
        items_container.get("item") if isinstance(items_container, dict) else None
    )
    if raw_items in (None, ""):
        return []
    if isinstance(raw_items, dict):
        return [raw_items]
    if isinstance(raw_items, list) and all(isinstance(item, dict) for item in raw_items):
        return raw_items
    raise ValueError("KRA race-plan response has an invalid item collection")


def _int_value(item: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            try:
                return int(str(value).strip())
            except ValueError as error:
                raise ValueError(f"invalid integer field {key}: {value!r}") from error
    raise ValueError(f"missing required field: {'/'.join(keys)}")


def _race_key_from_plan_item(item: dict[str, Any]) -> RaceKey:
    raw_date = _int_value(item, "rcDate", "rc_date")
    race_date = f"{raw_date:08d}"
    datetime.strptime(race_date, "%Y%m%d")
    raw_meet = item.get("meet")
    meet_names = {"서울": 1, "제주": 2, "부산": 3, "부산경남": 3}
    if isinstance(raw_meet, str) and raw_meet.strip() in meet_names:
        meet = meet_names[raw_meet.strip()]
    else:
        meet = _int_value(item, "meet")
    race_number = _int_value(item, "rcNo", "rc_no")
    if meet not in MEET_NAMES or race_number < 1:
        raise ValueError(f"invalid race key fields: {item!r}")
    return RaceKey(race_date=race_date, meet=meet, race_number=race_number)


async def discover_race_plan_month(
    kra_api: KRAAPIService,
    *,
    year: int,
    month: int,
    meet: int | None = None,
    num_rows: int = 100,
) -> list[RaceKey]:
    """API72_2 월 조회를 끝까지 페이지네이션해 고유 경주를 반환한다."""
    if year < 1990 or not 1 <= month <= 12:
        raise ValueError("year/month is outside the supported range")
    if meet is not None and meet not in MEET_NAMES:
        raise ValueError("meet must be one of 1, 2, or 3")
    if num_rows < 1:
        raise ValueError("num_rows must be positive")

    page_number = 1
    discovered: dict[str, RaceKey] = {}
    while True:
        params: dict[str, Any] = {
            "rc_year": f"{year:04d}",
            "rc_month": f"{month:02d}",
            "numOfRows": num_rows,
            "pageNo": page_number,
        }
        if meet is not None:
            params["meet"] = str(meet)
        response = await kra_api._make_request(  # noqa: SLF001
            endpoint="API72_2/racePlan_2",
            params=params,
        )
        body = _response_body(response)
        for item in _page_items(body):
            key = _race_key_from_plan_item(item)
            if not key.race_date.startswith(f"{year:04d}{month:02d}"):
                raise ValueError(f"race plan returned an out-of-month date: {key.race_id}")
            if meet is not None and key.meet != meet:
                raise ValueError(f"race plan returned an unexpected meet: {key.race_id}")
            discovered[key.race_id] = key

        total_count = int(body.get("totalCount") or len(discovered))
        response_rows = int(body.get("numOfRows") or num_rows)
        if response_rows < 1:
            response_rows = num_rows
        page_count = max(1, math.ceil(total_count / response_rows))
        if page_number >= page_count:
            break
        page_number += 1
    return sorted(
        discovered.values(),
        key=lambda key: (key.race_date, key.meet, key.race_number),
    )


def _month_starts(start: str, end: str) -> list[tuple[int, int]]:
    start_date = datetime.strptime(start, "%Y%m%d")
    end_date = datetime.strptime(end, "%Y%m%d")
    if start_date > end_date:
        raise ValueError("start must not be later than end")
    year, month = start_date.year, start_date.month
    result: list[tuple[int, int]] = []
    while (year, month) <= (end_date.year, end_date.month):
        result.append((year, month))
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
    return result


async def discover_race_range(
    kra_api: KRAAPIService,
    *,
    start: str,
    end: str,
    meet: int | None = None,
) -> list[RaceKey]:
    discovered: dict[str, RaceKey] = {}
    for year, month in _month_starts(start, end):
        monthly = await discover_race_plan_month(
            kra_api,
            year=year,
            month=month,
            meet=meet,
        )
        for key in monthly:
            if start <= key.race_date <= end:
                discovered[key.race_id] = key
    return sorted(
        discovered.values(),
        key=lambda key: (key.race_date, key.meet, key.race_number),
    )


def write_discovery_manifest(
    path: Path,
    *,
    start: str,
    end: str,
    meet: int | None,
    races: list[RaceKey],
) -> None:
    payload = {
        "format_version": "kra-race-plan-discovery-v1",
        "endpoint": "API72_2/racePlan_2",
        "start": start,
        "end": end,
        "meet": meet,
        "race_count": len(races),
        "races": [
            {
                "race_id": key.race_id,
                "race_date": key.race_date,
                "meet": key.meet,
                "race_number": key.race_number,
            }
            for key in races
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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
# Race discovery and initial collection
# ---------------------------------------------------------------------------
async def discover_or_collect_races(
    *,
    start: str,
    end: str,
    meet: int | None,
    output: Path,
    collect: bool,
) -> None:
    kra_api = KRAAPIService()
    try:
        races = await discover_race_range(
            kra_api,
            start=start,
            end=end,
            meet=meet,
        )
        write_discovery_manifest(
            output,
            start=start,
            end=end,
            meet=meet,
            races=races,
        )
        logger.info("경주 발견 완료: %d건, manifest=%s", len(races), output)
        if not collect:
            return

        collected = 0
        failed = 0
        for index, key in enumerate(races, start=1):
            try:
                async with async_session_maker() as db:
                    workflow = _build_workflow(kra_api, db)
                    await workflow.collect(CollectRaceCommand(key=key))
                collected += 1
            except Exception as error:
                failed += 1
                logger.error("초기 경주 수집 실패: %s error=%s", key.race_id, error)
            if index % 20 == 0 or index == len(races):
                logger.info(
                    "[%d/%d] 초기 수집: 완료=%d, 실패=%d",
                    index,
                    len(races),
                    collected,
                    failed,
                )
            await asyncio.sleep(API_DELAY_SECONDS)
        logger.info(
            "초기 경주 수집 완료: 성공=%d, 실패=%d (총 %d건)",
            collected,
            failed,
            len(races),
        )
    finally:
        await kra_api.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main(
    command: str,
    start: str | None,
    end: str | None,
    meet: int | None,
    output: Path,
) -> None:
    try:
        if command in ("discover", "collect"):
            if not start or not end:
                raise ValueError("discover/collect requires --start and --end")
            await discover_or_collect_races(
                start=start,
                end=end,
                meet=meet,
                output=output,
                collect=command == "collect",
            )
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
        choices=["discover", "collect", "results", "enrich", "odds", "all"],
        help=(
            "discover=경주목록, collect=신규경주수집, results=결과수집, "
            "enrich=enrichment, odds=배당률, all=기존경주 후처리"
        ),
    )
    parser.add_argument("--start", default=None, help="시작일 (YYYYMMDD)")
    parser.add_argument("--end", default=None, help="종료일 (YYYYMMDD)")
    parser.add_argument("--meet", type=int, choices=sorted(MEET_NAMES), default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_DISCOVERY_OUTPUT)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args.command, args.start, args.end, args.meet, args.output))
