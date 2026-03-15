# 2025년 전체 경주 데이터 배치 수집 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 2025년 1월 1일 ~ 12월 31일 서울(meet=1), 부산경남(meet=3) 전체 경주 데이터를 full enrichment로 수집하여 Supabase DB에 저장하는 독립 배치 스크립트 작성

**Architecture:** API 서버를 거치지 않고 기존 `CollectionService` + `KRAAPIService`를 직접 import하여 사용하는 독립 async 스크립트. 365일 × 2 meets를 순회하며, 이미 수집된 경주는 skip하고, rate limiting과 진행률 로깅을 포함. 결과 수집(`ResultCollectionService`)도 함께 수행.

**Tech Stack:** Python 3.13, asyncio, SQLAlchemy async, httpx, structlog, 기존 apps/api 모듈 재사용

---

## 핵심 설계 결정

- **경주 없는 날 감지**: race_no=1 호출 시 빈 응답이면 해당 날짜+meet 전체 skip
- **재시작 가능**: DB에 이미 `collection_status=collected`인 경주는 건너뜀
- **Rate limiting**: API 호출 간 1초 딜레이, 연속 실패 시 백오프
- **진행률**: 날짜별 진행 상황 + 전체 통계 출력
- **결과 수집**: basic_data 수집 후 결과(1-3위)도 함께 수집

---

### Task 1: 배치 수집 스크립트 생성

**Files:**
- Create: `packages/scripts/batch_collect_2025.py`

**Step 1: 스크립트 작성**

```python
"""
2025년 전체 경주 데이터 배치 수집 스크립트

Usage:
    uv run python3 packages/scripts/batch_collect_2025.py [--start YYYYMMDD] [--end YYYYMMDD] [--meets 1,3]

기본값: 2025-01-01 ~ 2025-12-31, 서울(1) + 부산경남(3)
이미 수집된 경주는 자동 skip (재시작 가능)
"""

import argparse
import asyncio
import sys
from datetime import date, timedelta, datetime, UTC
from pathlib import Path

# apps/api 모듈을 import하기 위해 sys.path 조정
API_DIR = Path(__file__).parent.parent.parent / "apps" / "api"
sys.path.insert(0, str(API_DIR))

import structlog
from sqlalchemy import select, and_

from config import settings  # noqa: E402 - apps/api의 config
from infrastructure.database import async_session_maker, init_db, close_db, engine
from models.database_models import Race, DataStatus
from services.collection_service import CollectionService
from services.kra_api_service import KRAAPIService
from services.result_collection_service import ResultCollectionService, ResultNotFoundError
from adapters.kra_response_adapter import KRAResponseAdapter

logger = structlog.get_logger()

# 통계 추적
stats = {
    "dates_checked": 0,
    "dates_with_races": 0,
    "races_collected": 0,
    "races_skipped": 0,  # 이미 수집됨
    "races_failed": 0,
    "results_collected": 0,
    "results_failed": 0,
    "api_calls": 0,
}

MEET_NAMES = {1: "서울", 2: "제주", 3: "부산경남"}


def generate_dates(start: date, end: date) -> list[date]:
    """시작일부터 종료일까지 모든 날짜 생성"""
    dates = []
    current = start
    while current <= end:
        dates.append(current)
        current += timedelta(days=1)
    return dates


async def is_race_collected(db, race_date: str, meet: int, race_no: int) -> bool:
    """해당 경주가 이미 수집되었는지 확인"""
    race_id = f"{race_date}_{meet}_{race_no}"
    result = await db.execute(
        select(Race.collection_status).where(Race.race_id == race_id)
    )
    status = result.scalar_one_or_none()
    return status == DataStatus.COLLECTED or status == DataStatus.ENRICHED


async def collect_single_date_meet(
    kra_api: KRAAPIService,
    collection_service: CollectionService,
    result_service: ResultCollectionService,
    race_date: str,
    meet: int,
):
    """한 날짜 + 한 경마장의 모든 경주 수집"""
    meet_name = MEET_NAMES.get(meet, str(meet))

    async with async_session_maker() as db:
        for race_no in range(1, 16):
            try:
                # 이미 수집된 경주는 skip
                if await is_race_collected(db, race_date, meet, race_no):
                    stats["races_skipped"] += 1
                    continue

                # 경주 데이터 수집 (basic + enrichment)
                result = await collection_service.collect_race_data(
                    race_date, meet, race_no, db
                )

                if not result:
                    # 이 경주 번호에 데이터 없음 → 이후 경주도 없을 가능성 높음
                    break

                stats["races_collected"] += 1
                logger.info(
                    f"  수집 완료: {race_date} {meet_name} {race_no}R",
                    horses=len(result.get("horses", [])),
                )

                # 결과 수집 (1-3위)
                try:
                    await result_service.collect_result(
                        race_date=race_date,
                        meet=meet,
                        race_number=race_no,
                        db=db,
                        kra_api=kra_api,
                    )
                    stats["results_collected"] += 1
                except ResultNotFoundError:
                    stats["results_failed"] += 1
                except Exception as e:
                    stats["results_failed"] += 1
                    logger.warning(f"  결과 수집 실패: {race_no}R - {e}")

                # Rate limiting
                await asyncio.sleep(1.0)

            except Exception as e:
                error_msg = str(e)
                # API에서 데이터 없음 응답 → 이 meet의 경주가 여기서 끝
                if "resultCode" in error_msg or "no items" in error_msg.lower():
                    break

                stats["races_failed"] += 1
                logger.error(f"  수집 실패: {race_date} {meet_name} {race_no}R - {e}")

                # 연속 실패 시 백오프
                await asyncio.sleep(3.0)


async def run_batch(start_date: date, end_date: date, meets: list[int]):
    """배치 수집 메인 루프"""
    dates = generate_dates(start_date, end_date)
    total_days = len(dates)

    logger.info(
        f"배치 수집 시작: {start_date} ~ {end_date} ({total_days}일)",
        meets=[MEET_NAMES.get(m, str(m)) for m in meets],
    )

    # DB 초기화
    await init_db()

    # 서비스 초기화
    kra_api = KRAAPIService()
    collection_service = CollectionService(kra_api)
    result_service = ResultCollectionService()

    try:
        for i, d in enumerate(dates):
            race_date = d.strftime("%Y%m%d")
            stats["dates_checked"] += 1

            date_had_races = False

            for meet in meets:
                meet_name = MEET_NAMES.get(meet, str(meet))

                # 먼저 race 1이 있는지 빠르게 확인
                try:
                    race_info = await kra_api.get_race_info(
                        race_date, str(meet), 1, use_cache=False
                    )
                    if not KRAResponseAdapter.is_successful_response(race_info):
                        continue
                    items = KRAResponseAdapter.extract_items(race_info)
                    if not items:
                        continue
                except Exception:
                    continue

                date_had_races = True
                logger.info(
                    f"[{i+1}/{total_days}] {race_date} {meet_name} - 경주 발견, 수집 시작"
                )

                await collect_single_date_meet(
                    kra_api, collection_service, result_service, race_date, meet
                )

                # meet 간 딜레이
                await asyncio.sleep(0.5)

            if date_had_races:
                stats["dates_with_races"] += 1

            # 10일마다 중간 통계 출력
            if (i + 1) % 10 == 0:
                print_stats(i + 1, total_days)

    finally:
        await kra_api.close()
        await close_db()

    # 최종 통계
    print_stats(total_days, total_days, final=True)


def print_stats(current: int, total: int, final: bool = False):
    """진행 통계 출력"""
    prefix = "=== 최종 통계 ===" if final else f"--- 진행: {current}/{total}일 ---"
    print(f"\n{prefix}")
    print(f"  확인한 날짜: {stats['dates_checked']}")
    print(f"  경마 개최일: {stats['dates_with_races']}")
    print(f"  수집 완료: {stats['races_collected']}경주")
    print(f"  이미 수집 (skip): {stats['races_skipped']}경주")
    print(f"  수집 실패: {stats['races_failed']}경주")
    print(f"  결과 수집: {stats['results_collected']}경주")
    print(f"  결과 실패: {stats['results_failed']}경주")
    print()


def parse_args():
    parser = argparse.ArgumentParser(description="2025년 경주 데이터 배치 수집")
    parser.add_argument(
        "--start", default="20250101", help="시작 날짜 (YYYYMMDD, 기본: 20250101)"
    )
    parser.add_argument(
        "--end", default="20251231", help="종료 날짜 (YYYYMMDD, 기본: 20251231)"
    )
    parser.add_argument(
        "--meets", default="1,3", help="경마장 코드 (쉼표 구분, 기본: 1,3)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    start_date = date(int(args.start[:4]), int(args.start[4:6]), int(args.start[6:8]))
    end_date = date(int(args.end[:4]), int(args.end[4:6]), int(args.end[6:8]))
    meets = [int(m.strip()) for m in args.meets.split(",")]

    asyncio.run(run_batch(start_date, end_date, meets))


if __name__ == "__main__":
    main()
```

**Step 2: 스크립트를 짧은 범위로 테스트 (2025-01-03 ~ 2025-01-05, 3일)**

Run: `cd /Users/chsong/Developer/Personal/kra-analysis && uv run python3 packages/scripts/batch_collect_2025.py --start 20250103 --end 20250105 --meets 1,3`

Expected: 경마 개최일이면 경주 수집, 없으면 skip. 수집 통계 출력.

**Step 3: 정상 동작 확인 후 커밋**

```bash
git add packages/scripts/batch_collect_2025.py
git commit -m "feat(scripts): add 2025 batch collection script

Standalone async script that collects all race data (basic + enriched)
for Seoul and Busan meets across 2025. Supports resumption by skipping
already-collected races, rate limiting, and progress logging."
```

---

### Task 2: 전체 2025년 수집 실행

**Step 1: 전체 실행 (background)**

Run: `cd /Users/chsong/Developer/Personal/kra-analysis && uv run python3 packages/scripts/batch_collect_2025.py 2>&1 | tee logs/batch_collect_2025.log`

이 작업은 ~15시간 소요 예상. tmux 또는 background에서 실행 권장.

**Step 2: 중간 진행 확인**

DB에서 직접 확인:
```sql
SELECT
    COUNT(*) as total,
    COUNT(CASE WHEN collection_status = 'collected' THEN 1 END) as collected,
    COUNT(CASE WHEN result_status = 'collected' THEN 1 END) as with_results,
    MIN(date) as earliest,
    MAX(date) as latest
FROM races
WHERE date LIKE '2025%';
```

**Step 3: 실패한 경주 재수집 (필요 시)**

스크립트 재실행 시 이미 수집된 경주는 자동 skip되므로 그냥 다시 실행:
```bash
uv run python3 packages/scripts/batch_collect_2025.py
```

---

### Task 3: 수집 완료 후 검증

**Step 1: 데이터 품질 확인 쿼리**

```sql
-- 월별 수집 현황
SELECT
    SUBSTR(date, 1, 6) as month,
    COUNT(*) as races,
    COUNT(CASE WHEN collection_status = 'collected' THEN 1 END) as collected,
    COUNT(CASE WHEN result_status = 'collected' THEN 1 END) as with_results
FROM races
WHERE date LIKE '2025%'
GROUP BY SUBSTR(date, 1, 6)
ORDER BY month;

-- 경마장별 현황
SELECT
    meet,
    COUNT(*) as races,
    COUNT(DISTINCT date) as race_days
FROM races
WHERE date LIKE '2025%'
GROUP BY meet;
```

**Step 2: basic_data 무결성 확인**

```sql
-- basic_data가 비어있는 수집완료 경주
SELECT race_id, date, meet, race_number
FROM races
WHERE date LIKE '2025%'
  AND collection_status = 'collected'
  AND basic_data IS NULL;
```
