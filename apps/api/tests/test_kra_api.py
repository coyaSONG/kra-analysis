#!/usr/bin/env python3
"""KRA API 직접 테스트"""

import os
from urllib.parse import unquote

import requests  # type: ignore[import-untyped]
import urllib3
from dotenv import load_dotenv

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 환경 변수 로드
load_dotenv()


API_KEY = os.getenv("KRA_API_KEY")
print(f"API Key loaded: {'Yes' if API_KEY else 'No'}")

# API 키가 URL 인코딩되어 있을 수 있음
if API_KEY and "%" in API_KEY:
    API_KEY_DECODED = unquote(API_KEY)
    print(f"API Key appears to be URL encoded. Decoded length: {len(API_KEY_DECODED)}")
else:
    API_KEY_DECODED = API_KEY

# 과거 날짜로 테스트 (실제 경주가 있었던 날짜)
test_date = "20241208"  # 2024년 12월 8일
meet = 1  # 서울
race_no = 1

# API 호출
url = "https://apis.data.go.kr/B551015/API214_1/RaceDetailResult_1"
params = {
    "serviceKey": API_KEY_DECODED,
    "numOfRows": "50",
    "pageNo": "1",
    "meet": str(meet),
    "rc_date": test_date,
    "rc_no": str(race_no),
    "_type": "json",
}

print(f"\nTesting KRA API with date: {test_date}")
print(f"URL: {url}")
print(f"Params: {params}")

try:
    # SSL 검증 비활성화 (개발 환경용)
    response = requests.get(url, params=params, verify=False, timeout=30)
    print(f"\nStatus Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Response: {data}")

        if data.get("response", {}).get("header", {}).get("resultCode") == "00":
            body = data.get("response", {}).get("body", {})
            if body.get("items"):
                items = body["items"]["item"]
                if not isinstance(items, list):
                    items = [items]
                print(f"\n✅ Success! Found {len(items)} horses")
                for horse in items[:3]:  # 처음 3마리만 출력
                    print(
                        f"  - {horse.get('hrName')} (출전번호: {horse.get('chulNo')})"
                    )
            else:
                print("❌ No data found for this race")
        else:
            print(
                f"❌ API Error: {data.get('response', {}).get('header', {}).get('resultMsg')}"
            )
    else:
        print(f"❌ HTTP Error: {response.status_code}")
        print(f"Response: {response.text[:500]}")

except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
