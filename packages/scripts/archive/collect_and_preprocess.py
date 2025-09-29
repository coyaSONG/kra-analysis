#!/usr/bin/env python3
"""
통합 데이터 수집 및 전처리 스크립트
- API214_1을 사용하여 경주 데이터 수집
- 자동으로 스마트 전처리 적용
"""

import json
import os
import urllib.parse
from datetime import datetime, timedelta
from typing import Any

import requests
import urllib3
from dotenv import load_dotenv
from smart_preprocess_races import smart_process_race_file

# SSL 경고 비활성화 (개발 환경용)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 환경 변수 로드
load_dotenv()

API_KEY = os.getenv("KRA_SERVICE_KEY")
if not API_KEY:
    raise ValueError("KRA_SERVICE_KEY가 .env 파일에 설정되어 있지 않습니다.")

# URL 디코딩 (이미 인코딩된 경우 처리)
if "%" in API_KEY:
    API_KEY = urllib.parse.unquote(API_KEY)

BASE_URL = "https://apis.data.go.kr/B551015/API214_1/RaceDetailResult_1"


def collect_race_data(meet: str, rc_date: str, rc_no: int) -> dict[str, Any]:
    """
    특정 경주의 데이터 수집

    Args:
        meet: 경마장 코드 (1:서울, 2:제주, 3:부산)
        rc_date: 경주일자 (YYYYMMDD)
        rc_no: 경주번호

    Returns:
        경주 데이터 (JSON)
    """
    params = {
        "serviceKey": API_KEY,
        "numOfRows": "50",
        "pageNo": "1",
        "meet": meet,
        "rc_date": rc_date,
        "rc_no": str(rc_no),
        "_type": "json",
    }

    try:
        # SSL 검증 비활성화 옵션 추가 (개발 환경용)
        response = requests.get(BASE_URL, params=params, timeout=10, verify=False)
        response.raise_for_status()

        data = response.json()

        if data["response"]["header"]["resultCode"] == "00":
            if data["response"]["body"]["items"]:
                return data

        return None

    except Exception as e:
        print(f"❌ API 호출 실패 ({meet}/{rc_date}/{rc_no}R): {e}")
        return None


def collect_all_races_for_day(meet: str, rc_date: str, max_races: int = 15) -> list[dict[str, Any]]:
    """
    특정 날짜의 모든 경주 수집

    Args:
        meet: 경마장 코드
        rc_date: 경주일자
        max_races: 최대 경주 수

    Returns:
        수집된 경주 데이터 리스트
    """
    meet_names = {"1": "서울", "2": "제주", "3": "부산경남"}
    print(f"\n📅 {rc_date} {meet_names.get(meet, meet)} 경마장 데이터 수집")
    print("=" * 60)

    races = []

    for rc_no in range(1, max_races + 1):
        print(f"\n{rc_no}R 수집 중...", end=" ")

        data = collect_race_data(meet, rc_date, rc_no)

        if data:
            # 원본 데이터 저장
            raw_filename = f"data/race_{meet}_{rc_date}_{rc_no}.json"
            with open(raw_filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # 경주 정보 출력
            items = data["response"]["body"]["items"]["item"]
            if not isinstance(items, list):
                items = [items]

            print(f"✅ {len(items)}두 출전")

            # 스마트 전처리 적용
            result = smart_process_race_file(raw_filename, "data/processed/pre-race")

            races.append({
                'race_no': rc_no,
                'horses': len(items),
                'status': result.get('status', 'Unknown'),
                'raw_file': raw_filename,
                'processed_file': result.get('output', '')
            })

        else:
            print("❌ 데이터 없음 (경주 종료)")
            break

    return races


def collect_recent_races(days_back: int = 7, meets: list[str] = None):
    """
    최근 며칠간의 경주 데이터 수집

    Args:
        days_back: 며칠 전까지 수집할지
        meets: 경마장 리스트 (기본값: 모든 경마장)
    """
    if meets is None:
        meets = ['1', '2', '3']  # 서울, 제주, 부산

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    all_results = []

    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y%m%d')

        # 주말(금토일)에만 경마 진행
        if current_date.weekday() in [4, 5, 6]:  # 금토일
            for meet in meets:
                races = collect_all_races_for_day(meet, date_str)
                if races:
                    all_results.append({
                        'date': date_str,
                        'meet': meet,
                        'races': races
                    })

        current_date += timedelta(days=1)

    # 수집 결과 요약
    print(f"\n{'='*60}")
    print("📊 전체 수집 결과")
    print(f"{'='*60}")

    total_races = 0
    total_completed = 0
    total_waiting = 0

    for result in all_results:
        date_races = len(result['races'])
        completed = sum(1 for r in result['races'] if '완료' in r['status'])
        waiting = date_races - completed

        total_races += date_races
        total_completed += completed
        total_waiting += waiting

        meet_names = {'1': '서울', '2': '제주', '3': '부산'}
        print(f"{result['date']} {meet_names[result['meet']]}: "
              f"{date_races}개 경주 (완료: {completed}, 대기: {waiting})")

    print(f"\n총계: {total_races}개 경주")
    print(f"  - 완료 (전처리): {total_completed}개")
    print(f"  - 대기 (원본): {total_waiting}개")

    # 요약 파일 저장
    summary_path = "data/collection_summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump({
            'collection_date': datetime.now().isoformat(),
            'days_collected': days_back,
            'total_races': total_races,
            'completed': total_completed,
            'waiting': total_waiting,
            'details': all_results
        }, f, ensure_ascii=False, indent=2)

    print(f"\n📄 수집 요약: {summary_path}")


def collect_specific_date(date_str: str, meet: str = '1'):
    """
    특정 날짜의 경주 데이터 수집 및 전처리

    Args:
        date_str: 날짜 (YYYYMMDD)
        meet: 경마장 코드 (기본값: 1-서울)
    """
    races = collect_all_races_for_day(meet, date_str)

    if races:
        print(f"\n✅ {len(races)}개 경주 수집 및 전처리 완료")
        return races
    else:
        print("\n❌ 수집된 경주가 없습니다.")
        return []


if __name__ == "__main__":
    import sys

    # 디렉토리 생성
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/processed/pre-race", exist_ok=True)

    if len(sys.argv) > 1:
        # 특정 날짜 수집
        date_str = sys.argv[1]
        meet = sys.argv[2] if len(sys.argv) > 2 else '1'

        print(f"특정 날짜 수집: {date_str} (경마장: {meet})")
        collect_specific_date(date_str, meet)
    else:
        # 오늘 날짜 수집
        today = datetime.now().strftime('%Y%m%d')
        print(f"오늘 날짜 수집: {today}")
        collect_specific_date(today, '1')  # 서울 경마장
