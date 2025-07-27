#!/usr/bin/env python3
"""
API 기능 테스트 스크립트
"""

import requests
import json
import sys

# API 설정
BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key-123456789"

def test_health():
    """헬스체크 테스트"""
    print("1. Testing health endpoint...")
    resp = requests.get(f"{BASE_URL}/health")
    if resp.status_code == 200:
        print("✅ Health check passed:", resp.json())
    else:
        print("❌ Health check failed:", resp.status_code, resp.text)
    print()

def test_jobs_list():
    """작업 목록 조회 테스트"""
    print("2. Testing jobs list...")
    headers = {"X-API-Key": API_KEY}
    resp = requests.get(f"{BASE_URL}/api/v2/jobs/", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Jobs list passed: {data['total']} jobs found")
    else:
        print("❌ Jobs list failed:", resp.status_code, resp.text)
    print()

def test_collection():
    """데이터 수집 테스트"""
    print("3. Testing collection endpoint...")
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "date": "20240119",
        "meet": 1,
        "race_numbers": [1, 2]
    }
    resp = requests.post(f"{BASE_URL}/api/v2/collection/", 
                        headers=headers, 
                        json=payload)
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Collection passed: {data['message']}")
    else:
        print("❌ Collection failed:", resp.status_code, resp.text)
    print()

def test_invalid_auth():
    """잘못된 인증 테스트"""
    print("4. Testing invalid authentication...")
    headers = {"X-API-Key": "invalid-key"}
    resp = requests.get(f"{BASE_URL}/api/v2/jobs/", headers=headers)
    if resp.status_code == 401:
        print("✅ Auth validation passed: Correctly rejected invalid key")
    else:
        print("❌ Auth validation failed: Expected 401 but got", resp.status_code)
    print()

def main():
    """메인 함수"""
    print("=== KRA API Server Test ===\n")
    
    # 서버 연결 확인
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=2)
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running on", BASE_URL)
        print("Please start the server first:")
        print("  python3 -m uvicorn main_v2:app --host 0.0.0.0 --port 8000")
        sys.exit(1)
    
    # 테스트 실행
    test_health()
    test_jobs_list()
    test_collection()
    test_invalid_auth()
    
    print("=== Test Complete ===")

if __name__ == "__main__":
    main()