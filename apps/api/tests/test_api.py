#!/usr/bin/env python3
"""
FastAPI 서버 테스트 스크립트
"""

import httpx
import asyncio
import json
from datetime import datetime


BASE_URL = "http://localhost:8000"


async def test_health_check():
    """헬스 체크 테스트"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        print(f"Health Check: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200


async def test_collect_races():
    """경주 데이터 수집 테스트"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 특정 날짜의 서울 경마장 데이터 수집
        data = {
            "date": "20250608",
            "meet": 1,  # 서울
            "race_no": 1  # 1경주만 테스트
        }
        
        print(f"\n경주 수집 요청: {data}")
        response = await client.post(
            f"{BASE_URL}/api/v1/races/collect",
            json=data
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Job ID: {result['job_id']}")
            print(f"Message: {result['message']}")
            return result['job_id']
        else:
            print(f"Error: {response.text}")
            return None


async def test_list_races():
    """경주 목록 조회 테스트"""
    async with httpx.AsyncClient() as client:
        date = "20250608"
        
        print(f"\n{date} 경주 목록 조회")
        response = await client.get(f"{BASE_URL}/api/v1/races/{date}")
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            races = response.json()
            print(f"총 {len(races)}개 경주 조회됨")
            
            for race in races[:3]:  # 처음 3개만 출력
                print(f"- {race['race_no']}R: {race['race_name']} "
                      f"({race['horse_count']}두 출전)")
        else:
            print(f"Error: {response.text}")


async def test_enrich_race(race_id: str):
    """경주 데이터 보강 테스트"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        print(f"\n경주 {race_id} 데이터 보강 요청")
        
        response = await client.post(
            f"{BASE_URL}/api/v1/races/enrich/{race_id}"
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Result: {result}")
        else:
            print(f"Error: {response.text}")


async def test_get_race_result():
    """경주 결과 조회 테스트"""
    async with httpx.AsyncClient() as client:
        date = "20250608"
        meet = 1
        race_no = 1
        
        print(f"\n{date} {meet}경마장 {race_no}R 결과 조회")
        
        response = await client.get(
            f"{BASE_URL}/api/v1/races/results/{date}/{meet}/{race_no}"
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"1위: {result['winner']}번")
            print(f"2위: {result['second']}번")
            print(f"3위: {result['third']}번")
        else:
            print(f"Error: {response.text}")


async def main():
    """메인 테스트 함수"""
    print("=" * 60)
    print("KRA Race Prediction API 테스트")
    print("=" * 60)
    
    # 1. 헬스 체크
    if not await test_health_check():
        print("서버가 실행 중이지 않습니다!")
        return
    
    # 2. 경주 수집
    job_id = await test_collect_races()
    
    if job_id:
        # 잠시 대기 (백그라운드 작업 진행)
        print("\n5초 대기 중...")
        await asyncio.sleep(5)
        
        # 3. 경주 목록 조회
        await test_list_races()
        
        # 4. 경주 결과 조회
        await test_get_race_result()
    
    print("\n테스트 완료!")


if __name__ == "__main__":
    asyncio.run(main())