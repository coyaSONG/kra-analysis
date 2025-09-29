#!/usr/bin/env python3
"""
API214_1을 통해 경주 결과 가져오기
"""

import json
import os
from pathlib import Path

import requests
import urllib3
from dotenv import load_dotenv

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

# 환경 변수에서 API 키 가져오기
API_KEY = os.getenv("KRA_SERVICE_KEY")
if not API_KEY:
    print("API 키가 없습니다. .env 파일을 확인하세요.")
    exit(1)

BASE_URL = "https://apis.data.go.kr/B551015/API214_1/RaceDetailResult_1"


def fetch_race_result_api214(meet: str, rc_date: str, rc_no: int) -> dict | None:
    """API214_1을 통해 경주 결과 가져오기"""
    # meet 코드 매핑
    meet_codes = {"서울": "1", "제주": "2", "부산경남": "3"}

    meet_code = meet_codes.get(meet, "1")

    # URL 파라미터
    params = {
        "serviceKey": API_KEY,
        "numOfRows": "50",
        "pageNo": "1",
        "meet": meet_code,
        "rc_date": rc_date,
        "rc_no": str(rc_no),
        "_type": "json",
    }

    try:
        # API 호출 (requests 사용)
        response = requests.get(BASE_URL, params=params, verify=False, timeout=30)
        response.raise_for_status()

        data = response.json()

        # 응답 확인
        if data["response"]["header"]["resultCode"] == "00":
            return data
        else:
            print(f"API 오류: {data['response']['header']['resultMsg']}")
            return None

    except requests.exceptions.SSLError as e:
        print(f"SSL 오류 발생: {e}")
        # SSL 오류 시 다시 시도
        try:
            response = requests.get(BASE_URL, params=params, verify=False, timeout=30)
            data = response.json()
            if data["response"]["header"]["resultCode"] == "00":
                return data
        except Exception as e2:
            print(f"재시도 실패: {e2}")

    except Exception as e:
        print(f"결과 가져오기 실패 ({meet} {rc_date} {rc_no}경주): {e}")

    return None


def extract_top3_from_api214(result_data: dict) -> list[int]:
    """API214_1 데이터에서 1-3위 말 번호 추출"""
    try:
        items = result_data["response"]["body"]["items"]["item"]

        # 단일 결과인 경우 리스트로 변환
        if isinstance(items, dict):
            items = [items]

        # ord가 0이 아닌 항목만 필터링하고 순위별로 정렬
        results = [item for item in items if item.get("ord", 0) > 0]
        results.sort(key=lambda x: x["ord"])

        # 1-3위 말 번호 추출
        top3 = []
        for item in results[:3]:
            top3.append(item["chulNo"])

        return top3

    except Exception as e:
        print(f"결과 추출 오류: {e}")
        return []


def save_result_cache(
    result_data: dict,
    meet: str,
    rc_date: str,
    rc_no: int,
    cache_dir: Path = Path("data/cache/results"),
):
    """결과를 캐시에 저장"""
    cache_dir.mkdir(parents=True, exist_ok=True)

    meet_codes = {"서울": "1", "제주": "2", "부산경남": "3"}
    meet_code = meet_codes.get(meet, "1")

    # 파일명 생성
    filename = f"result_{rc_date}_{meet_code}_{rc_no}.json"
    cache_file = cache_dir / filename

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    return cache_file


def load_result_cache(
    meet: str, rc_date: str, rc_no: int, cache_dir: Path = Path("data/cache/results")
) -> dict | None:
    """캐시에서 결과 로드"""
    meet_codes = {"서울": "1", "제주": "2", "부산경남": "3"}
    meet_code = meet_codes.get(meet, "1")

    filename = f"result_{rc_date}_{meet_code}_{rc_no}.json"
    cache_file = cache_dir / filename

    if cache_file.exists():
        try:
            with open(cache_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    return None


def get_race_result_with_cache(meet: str, rc_date: str, rc_no: int) -> list[int] | None:
    """캐시를 활용하여 경주 결과의 1-3위 가져오기"""
    # 캐시 확인
    cached_data = load_result_cache(meet, rc_date, rc_no)
    if cached_data:
        return extract_top3_from_api214(cached_data)

    # API 호출
    result_data = fetch_race_result_api214(meet, rc_date, rc_no)
    if result_data:
        # 캐시 저장
        save_result_cache(result_data, meet, rc_date, rc_no)
        return extract_top3_from_api214(result_data)

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
        rc_date = "20241228"  # 테스트용 과거 날짜
        rc_no = 1

    print(f"\n경주 결과 가져오기: {meet} {rc_date} {rc_no}경주")
    top3 = get_race_result_with_cache(meet, rc_date, rc_no)

    if top3:
        print(f"✅ 1-3위: {top3}")
    else:
        print("❌ 결과를 가져올 수 없습니다.")
