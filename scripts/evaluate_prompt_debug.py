#!/usr/bin/env python3
"""
디버그 모드 평가 스크립트 - 오류 원인 추적
"""

import json
import os
import subprocess
import sys
from pathlib import Path
import time

def run_single_prediction(race_file, prompt_path):
    """단일 경주 예측 실행 (디버그 정보 포함)"""
    
    # 데이터 로드
    with open(race_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 기권/제외 말 필터링
    original_count = len(data["horses"])
    data["horses"] = [h for h in data["horses"] if h.get("win_odds", 999) > 0]
    filtered_count = original_count - len(data["horses"])
    
    if filtered_count > 0:
        print(f"  기권/제외 {filtered_count}마리 필터링")
    
    # 결과 필드 제거
    for horse in data["horses"]:
        for field in ["result", "ord", "rc_time"]:
            if field in horse:
                del horse[field]
    
    # 프롬프트 읽기
    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt_template = f.read()
    
    # 데이터 크기 확인
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    print(f"  데이터 크기: {len(json_str)}자")
    
    # 프롬프트 구성
    prompt = f"""{prompt_template}

경주 데이터:
```json
{json_str}
```"""
    
    print(f"  프롬프트 크기: {len(prompt)}자")
    
    # 임시 파일로 저장 (너무 긴 경우 대비)
    temp_file = f"/tmp/race_debug_{os.getpid()}.txt"
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    try:
        # Claude 실행
        start_time = time.time()
        
        # 방법 1: 직접 프롬프트
        if len(prompt) < 5000:
            cmd = ['claude', '-p', prompt]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        else:
            # 방법 2: 파일에서 읽기
            cmd = ['claude', '-p', f'@{temp_file}']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        elapsed = time.time() - start_time
        print(f"  실행 시간: {elapsed:.1f}초")
        
        if result.returncode != 0:
            print(f"  ❌ 오류 코드: {result.returncode}")
            print(f"  stderr: {result.stderr[:200]}")
            return None
            
        output = result.stdout.strip()
        
        # 결과 파싱
        import re
        
        # JSON 추출 시도
        json_match = re.search(r'\{.*\}', output, re.DOTALL)
        if json_match:
            try:
                prediction = json.loads(json_match.group())
                print(f"  ✅ 성공")
                return prediction
            except json.JSONDecodeError as e:
                print(f"  ❌ JSON 파싱 실패: {e}")
                print(f"  출력: {output[:200]}...")
                return None
        else:
            print(f"  ❌ JSON 없음")
            print(f"  출력: {output[:200]}...")
            return None
            
    except subprocess.TimeoutExpired:
        print(f"  ⏱️ 타임아웃 (60초)")
        return None
    except Exception as e:
        print(f"  ❌ 예외: {type(e).__name__}: {e}")
        return None
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def main():
    if len(sys.argv) < 3:
        print("Usage: python evaluate_prompt_debug.py <prompt_file> <race_file>")
        sys.exit(1)
    
    prompt_file = sys.argv[1]
    race_file = sys.argv[2]
    
    print(f"\n디버그 평가:")
    print(f"프롬프트: {prompt_file}")
    print(f"경주: {race_file}")
    print("-" * 60)
    
    result = run_single_prediction(race_file, prompt_file)
    
    if result:
        print(f"\n예측 결과:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"\n예측 실패")


if __name__ == "__main__":
    main()