"""
2025년 전체 경주 데이터 배치 수집 스크립트.

매일(365일) 순회하면서 경주 데이터 + 결과(1-3위)를 수집한다.
이미 수집된 경주는 건너뛰고(재시작 가능), 개별 실패는 로깅 후 계속 진행한다.

Usage:
    uv run python3 packages/scripts/batch_collect_2025.py
    uv run python3 packages/scripts/batch_collect_2025.py --start 20250301 --end 20250331
    uv run python3 packages/scripts/batch_collect_2025.py --meets 1,2,3
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup: apps/api 모듈을 import 하기 위한 경로 설정
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
API_DIR = PROJECT_ROOT / "apps" / "api"

sys.path.insert(0, str(API_DIR))

# config.py 가 .env 파일을 상대 경로(cwd 기준)로 찾으므로 cwd 변경 필수
os.chdir(API_DIR)

# ---------------------------------------------------------------------------
# apps/api 모듈 import (sys.path, chdir 이후)
# ---------------------------------------------------------------------------
from adapters.kra_response_adapter import KRAResponseAdapter  # noqa: E402
from infrastructure.database import async_session_maker, close_db  # noqa: E402
from models.database_models import DataStatus, Race  # noqa: E402
from services.collection_service import CollectionService  # noqa: E402
from services.kra_api_service import KRAAPIService  # noqa: E402
from services.result_collection_service import (  # noqa: E402
    ResultCollectionService,
    ResultNotFoundError,
)
from sqlalchemy import select  # noqa: E402

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("batch_collect")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_RACE_NO = 15  # 한 경마장에서 하루 최대 경주 수
API_DELAY_SECONDS = 1.0
BACKOFF_SECONDS = 3.0
STATS_INTERVAL_DAYS = 10

MEET_NAMES = {1: "서울", 2: "제주", 3: "부산경남"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def date_range(start: str, end: str) -> list[str]:
    """YYYYMMDD 형식의 시작/종료일 사이 모든 날짜를 반환한다."""
    start_dt = datetime.strptime(start, "%Y%m%d")
    end_dt = datetime.strptime(end, "%Y%m%d")
    days = (end_dt - start_dt).days + 1
    return [(start_dt + timedelta(days=i)).strftime("%Y%m%d") for i in range(days)]


async def is_race_already_collected(race_date: str, meet: int, race_no: int) -> bool:
    """DB에서 이미 collected/enriched 상태인 경주인지 확인한다."""
    race_id = f"{race_date}_{meet}_{race_no}"
    async with async_session_maker() as db:
        result = await db.execute(select(Race).where(Race.race_id == race_id))
        race = result.scalar_one_or_none()
        if race is None:
            return False
        return race.collection_status in (DataStatus.COLLECTED, DataStatus.ENRICHED)


async def is_result_already_collected(race_date: str, meet: int, race_no: int) -> bool:
    """DB에서 이미 결과가 수집된 경주인지 확인한다."""
    race_id = f"{race_date}_{meet}_{race_no}"
    async with async_session_maker() as db:
        result = await db.execute(select(Race).where(Race.race_id == race_id))
        race = result.scalar_one_or_none()
        if race is None:
            return False
        return race.result_status == DataStatus.COLLECTED


async def has_races_on_date(kra_api: KRAAPIService, race_date: str, meet: int) -> bool:
    """해당 날짜+경마장에 경주가 있는지 race_no=1 조회로 확인한다."""
    try:
        response = await kra_api.get_race_info(race_date, str(meet), 1, use_cache=False)
        if not KRAResponseAdapter.is_successful_response(response):
            return False
        items = KRAResponseAdapter.extract_items(response)
        return len(items) > 0
    except Exception as e:
        logger.warning("경주 존재 확인 실패: %s meet=%d error=%s", race_date, meet, e)
        return False


# ---------------------------------------------------------------------------
# Core collection logic
# ---------------------------------------------------------------------------
async def collect_single_race(
    collection_svc: CollectionService,
    result_svc: ResultCollectionService,
    kra_api: KRAAPIService,
    race_date: str,
    meet: int,
    race_no: int,
    stats: dict,
) -> bool:
    """단일 경주 데이터 + 결과 수집. 성공 시 True, 경주 없음 시 False 반환."""

    # 1) 경주 데이터 수집
    if await is_race_already_collected(race_date, meet, race_no):
        logger.debug("이미 수집됨 - skip: %s meet=%d race=%d", race_date, meet, race_no)
        stats["skipped"] += 1
    else:
        try:
            # DB 저장 전에 API 응답을 먼저 확인하여 빈 경주 저장 방지
            response = await kra_api.get_race_info(
                race_date, str(meet), race_no, use_cache=False
            )
            if not KRAResponseAdapter.is_successful_response(
                response
            ) or not KRAResponseAdapter.extract_items(response):
                logger.debug(
                    "데이터 없음: %s meet=%d race=%d", race_date, meet, race_no
                )
                return False

            async with async_session_maker() as db:
                result = await collection_svc.collect_race_data(
                    race_date, meet, race_no, db
                )
            stats["collected"] += 1
            logger.info(
                "수집 완료: %s %s %dR (%d두)",
                race_date,
                MEET_NAMES.get(meet, str(meet)),
                race_no,
                len(result.get("horses", [])),
            )
        except Exception as e:
            error_msg = str(e).lower()
            # 데이터 없음 관련 에러면 이 경주부터 없다고 판단
            if (
                "no items" in error_msg
                or "not found" in error_msg
                or "비어" in error_msg
            ):
                logger.debug("경주 없음: %s meet=%d race=%d", race_date, meet, race_no)
                return False
            stats["failed"] += 1
            logger.error(
                "수집 실패: %s meet=%d race=%d error=%s", race_date, meet, race_no, e
            )
            return True  # 일반 에러는 다음 경주 시도

    await asyncio.sleep(API_DELAY_SECONDS)

    # 2) 결과 수집
    if await is_result_already_collected(race_date, meet, race_no):
        logger.debug(
            "결과 이미 수집됨 - skip: %s meet=%d race=%d", race_date, meet, race_no
        )
        stats["result_skipped"] += 1
    else:
        try:
            async with async_session_maker() as db:
                await result_svc.collect_result(
                    race_date=race_date,
                    meet=meet,
                    race_number=race_no,
                    db=db,
                    kra_api=kra_api,
                )
            stats["result_collected"] += 1
            logger.info(
                "결과 수집 완료: %s %s %dR",
                race_date,
                MEET_NAMES.get(meet, str(meet)),
                race_no,
            )
        except ResultNotFoundError:
            # 결과가 아직 없는 경주 (미래 경주 등) - 정상 상황
            stats["result_not_found"] += 1
            logger.debug("결과 없음: %s meet=%d race=%d", race_date, meet, race_no)
        except Exception as e:
            stats["result_failed"] += 1
            logger.error(
                "결과 수집 실패: %s meet=%d race=%d error=%s",
                race_date,
                meet,
                race_no,
                e,
            )

    await asyncio.sleep(API_DELAY_SECONDS)
    return True


async def collect_date_meet(
    collection_svc: CollectionService,
    result_svc: ResultCollectionService,
    kra_api: KRAAPIService,
    race_date: str,
    meet: int,
    stats: dict,
) -> None:
    """특정 날짜+경마장의 모든 경주를 수집한다."""

    # 먼저 해당 날짜에 경주가 있는지 확인 (race_no=1)
    if not await has_races_on_date(kra_api, race_date, meet):
        logger.debug("경주 없음: %s %s", race_date, MEET_NAMES.get(meet, str(meet)))
        stats["no_race_days"] += 1
        await asyncio.sleep(API_DELAY_SECONDS)
        return

    stats["race_days"] += 1
    meet_name = MEET_NAMES.get(meet, str(meet))
    logger.info("경주 발견: %s %s - 수집 시작", race_date, meet_name)

    for race_no in range(1, MAX_RACE_NO + 1):
        # collect_race_data가 내부에서 API를 호출하므로 별도 존재 확인 불필요.
        # 수집 실패(데이터 없음) 시 False 반환 → 이후 경주도 없다고 판단하고 중단.
        ok = await collect_single_race(
            collection_svc,
            result_svc,
            kra_api,
            race_date,
            meet,
            race_no,
            stats,
        )
        if not ok:
            break


def log_stats(stats: dict, label: str) -> None:
    """통계를 로깅한다."""
    logger.info(
        "=== %s ===\n"
        "  처리 날짜: %d일 (경주 있음: %d, 없음: %d)\n"
        "  수집: %d (skip: %d, 실패: %d)\n"
        "  결과: %d (skip: %d, 없음: %d, 실패: %d)",
        label,
        stats["race_days"] + stats["no_race_days"],
        stats["race_days"],
        stats["no_race_days"],
        stats["collected"],
        stats["skipped"],
        stats["failed"],
        stats["result_collected"],
        stats["result_skipped"],
        stats["result_not_found"],
        stats["result_failed"],
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main(start: str, end: str, meets: list[int]) -> None:
    dates = date_range(start, end)
    logger.info(
        "배치 수집 시작: %s ~ %s (%d일), 경마장=%s",
        start,
        end,
        len(dates),
        [MEET_NAMES.get(m, str(m)) for m in meets],
    )

    stats: dict = {
        "race_days": 0,
        "no_race_days": 0,
        "collected": 0,
        "skipped": 0,
        "failed": 0,
        "result_collected": 0,
        "result_skipped": 0,
        "result_not_found": 0,
        "result_failed": 0,
    }

    kra_api = KRAAPIService()
    collection_svc = CollectionService(kra_api)
    result_svc = ResultCollectionService()

    try:
        for idx, race_date in enumerate(dates, 1):
            for meet in meets:
                try:
                    await collect_date_meet(
                        collection_svc,
                        result_svc,
                        kra_api,
                        race_date,
                        meet,
                        stats,
                    )
                except Exception as e:
                    logger.error(
                        "날짜/경마장 처리 중 예외: %s meet=%d error=%s",
                        race_date,
                        meet,
                        e,
                    )
                    await asyncio.sleep(BACKOFF_SECONDS)

            # 10일마다 중간 통계
            if idx % STATS_INTERVAL_DAYS == 0:
                log_stats(stats, f"중간 통계 ({idx}/{len(dates)}일)")

        log_stats(stats, "최종 통계")

    finally:
        await kra_api.close()
        await close_db()
        logger.info("리소스 정리 완료")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="2025년 KRA 경주 데이터 배치 수집")
    parser.add_argument("--start", default="20250101", help="시작일 (YYYYMMDD)")
    parser.add_argument("--end", default="20251231", help="종료일 (YYYYMMDD)")
    parser.add_argument(
        "--meets",
        default="1,3",
        help="경마장 코드 (콤마 구분, 1=서울 2=제주 3=부산경남)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    meets = [int(m.strip()) for m in args.meets.split(",")]
    asyncio.run(main(args.start, args.end, meets))
