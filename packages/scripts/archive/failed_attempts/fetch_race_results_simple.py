#!/usr/bin/env python3
"""
경주 결과를 API299를 통해 가져오는 스크립트 (간단한 버전)
"""

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

# .env 파일 로드
from dotenv import load_dotenv

load_dotenv()

# 환경 변수에서 API 키 가져오기
API_KEY = os.getenv("KRA_SERVICE_KEY")
if not API_KEY:
    print("API 키가 없습니다. .env 파일을 확인하세요.")
    exit(1)

BASE_URL = "https://apis.data.go.kr/B551015/API299/entryRacingResult"

def fetch_race_result_simple(meet: str, rc_date: str, rc_no: int) -> dict | None:
    """API299를 통해 경주 결과 가져오기 (간단한 버전)"""
    # meet 코드 매핑
    meet_codes = {
        "서울": "1",
        "제주": "2",
        "부산경남": "3"
    }

    meet_code = meet_codes.get(meet, "1")

    # URL 직접 구성 (JavaScript와 동일한 방식)
    url = f"{BASE_URL}?serviceKey={API_KEY}&meet={meet_code}&rcDate={rc_date}&rcNo={rc_no}&_type=json"

    print(f"API URL: {url}")

    try:
        # API 호출
        request = urllib.request.Request(url)
        with urllib.request.urlopen(request) as response:
            data = json.loads(response.read().decode("utf-8"))

        # 응답 확인
        if data["response"]["header"]["resultCode"] == "00":
            return data
        else:
            print(f"API 오류: {data['response']['header']['resultMsg']}")
            return None

    except Exception as e:
        print(f"결과 가져오기 실패: {e}")
        print(f"상세 오류: {type(e).__name__}")
        return None

def extract_top3(result_data: dict) -> list[int]:
    """결과 데이터에서 1-3위 말 번호 추출"""
    try:
        items = result_data["response"]["body"]["items"]["item"]

        # 단일 결과인 경우 리스트로 변환
        if isinstance(items, dict):
            items = [items]

        # 순위별로 정렬
        sorted_items = sorted(items, key=lambda x: x["ord"])

        # 1-3위 말 번호 추출
        top3 = []
        for item in sorted_items[:3]:
            top3.append(item["chulNo"])

        return top3

    except Exception as e:
        print(f"결과 추출 오류: {e}")
        return []

def save_result_cache(result_data: dict, cache_dir: Path = Path("data/cache/results")):
    """결과를 캐시에 저장"""
    cache_dir.mkdir(parents=True, exist_ok=True)

    # 파일명 생성
    items = result_data["response"]["body"]["items"]["item"]
    if isinstance(items, dict):
        items = [items]

    if items:
        first_item = items[0]
        filename = f"result_{first_item["rcDate"]}_{first_item["meet"]}_{first_item["rcNo"]}.json"
        cache_file = cache_dir / filename

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        print(f"캐시 저장: {cache_file}")
        return cache_file

    return None

def get_race_result_with_cache(meet: str, rc_date: str, rc_no: int) -> list[int] | None:
    """캐시를 활용하여 경주 결과의 1-3위 가져오기"""
    cache_dir = Path("data/cache/results")
    meet_codes = {"서울": "1", "제주": "2", "부산경남": "3"}
    meet_code = meet_codes.get(meet, "1")

    # 캐시 파일 경로
    filename = f"result_{rc_date}_{meet_code}_{rc_no}.json"
    cache_file = cache_dir / filename

    # 캐시 확인
    if cache_file.exists():
        try:
            with open(cache_file, encoding="utf-8") as f:
                cached_data = json.load(f)
            print(f"캐시 사용: {cache_file}")
            return extract_top3(cached_data)
        except Exception:
            pass

    # API 호출
    result_data = fetch_race_result_simple(meet, rc_date, rc_no)
    if result_data:
        # 캐시 저장
        save_result_cache(result_data)
        return extract_top3(result_data)

    return None

if __name__ == "__main__":
    # 테스트
    import sys

    if len(sys.argv) > 3:
        meet = sys.argv[1]
        rc_date = sys.argv[2]
        rc_no = int(sys.argv[3])
    else:
        meet = "서울"
        rc_date = "20241228"  # 더 과거 날짜로 테스트
        rc_no = 1

    print(f"\n경주 결과 가져오기: {meet} {rc_date} {rc_no}경주")
    top3 = get_race_result_with_cache(meet, rc_date, rc_no)

    if top3:
        print(f"✅ 1-3위: {top3}")
    else:
        print("❌ 결과를 가져올 수 없습니다.")
