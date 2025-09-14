#!/usr/bin/env python3
"""
API v2 테스트 스크립트 (legacy v1 경로 제거)

- 헬스 체크:        GET  /health
- 데이터 수집:      POST /api/v2/collection/
- 수집 상태 조회:   GET  /api/v2/collection/status?date=YYYYMMDD&meet=1
- 작업 목록 조회:   GET  /api/v2/jobs/

실행 전 개발/테스트 환경에서는 기본 테스트 키가 자동 활성화됩니다.
프로덕션에서는 환경변수 VALID_API_KEYS 설정이 필요합니다.
"""

import asyncio

import httpx

BASE_URL = "http://localhost:8000"
HEADERS = {"X-API-Key": "test-api-key-123456789"}


async def test_health_check() -> bool:
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE_URL}/health")
        print(f"Health Check: {r.status_code}")
        try:
            print(f"Response: {r.json()}")
        except Exception:
            print("Response: <non-json>")
        return r.status_code == 200


async def test_collect_v2() -> str | None:
    async with httpx.AsyncClient(timeout=30.0, headers=HEADERS) as client:
        payload = {"date": "20250608", "meet": 1, "race_numbers": [1]}
        print(f"\n[POST] /api/v2/collection/ :: {payload}")
        r = await client.post(f"{BASE_URL}/api/v2/collection/", json=payload)
        print(f"Status: {r.status_code}")
        if r.status_code in (200, 202):
            data = r.json()
            print(f"Result: {data}")
            return data.get("job_id")
        print(f"Error: {r.text}")
        return None


async def test_collection_status_v2():
    async with httpx.AsyncClient(headers=HEADERS) as client:
        date = "20250608"
        meet = 1
        print(f"\n[GET] /api/v2/collection/status?date={date}&meet={meet}")
        r = await client.get(
            f"{BASE_URL}/api/v2/collection/status", params={"date": date, "meet": meet}
        )
        print(f"Status: {r.status_code}")
        try:
            print(f"Body: {r.json()}")
        except Exception:
            print("Body: <non-json>")


async def test_list_jobs_v2():
    async with httpx.AsyncClient(headers=HEADERS) as client:
        print("\n[GET] /api/v2/jobs/")
        r = await client.get(f"{BASE_URL}/api/v2/jobs/")
        print(f"Status: {r.status_code}")
        try:
            data = r.json()
            print(f"Jobs: total={data.get('total')} items={len(data.get('jobs', []))}")
        except Exception:
            print("Body: <non-json>")


async def main():
    print("=" * 60)
    print("KRA API v2 Quick Test")
    print("=" * 60)

    if not await test_health_check():
        print("서버가 실행 중이 아닙니다.")
        return

    job_id = await test_collect_v2()
    if job_id:
        print("\n5초 대기 중...")
        await asyncio.sleep(5)
        await test_collection_status_v2()
        await test_list_jobs_v2()

    print("\n테스트 완료!")


if __name__ == "__main__":
    asyncio.run(main())
