#!/usr/bin/env python3
"""
v4 재귀 개선 실행 스크립트
- 수정된 평가 스크립트 사용
- 날짜별 순차 실행
"""

import subprocess
import sys
import time
from pathlib import Path

def run_v4_improvement(date: str):
    """v4 개선 실행"""
    cmd = [
        'python3',
        'scripts/prompt_improvement/recursive_prompt_improvement_v4.py',
        'prompts/base-prompt-v1.0.md',
        date,
        '3',  # 3번 반복
        '2'   # 2개 동시 실행
    ]
    
    # evaluate_prompt_v3_base.py를 사용하도록 환경 변수 설정
    import os
    env = os.environ.copy()
    env['EVALUATION_SCRIPT'] = 'scripts/evaluation/evaluate_prompt_v3_base.py'
    
    print(f"\n{'='*70}")
    print(f"🚀 {date} 데이터로 v4 개선 시작")
    print(f"{'='*70}")
    
    try:
        result = subprocess.run(
            cmd,
            env=env,
            timeout=3600  # 1시간 타임아웃
        )
        
        if result.returncode == 0:
            print(f"✅ {date} 개선 완료")
            return True
        else:
            print(f"❌ {date} 개선 실패")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏱️ {date} 타임아웃 (1시간 초과)")
        return False
    except Exception as e:
        print(f"❌ {date} 오류: {e}")
        return False

def main():
    """메인 실행"""
    # v4 스크립트가 평가 스크립트를 동적으로 선택할 수 있도록 수정 필요
    # 일단 단일 날짜로 테스트
    
    dates = ['20250607']  # 먼저 6월 7일만 테스트
    
    for date in dates:
        success = run_v4_improvement(date)
        if not success:
            print(f"⚠️ {date} 실패로 인해 중단")
            break
        
        # 다음 날짜 전 대기
        if date != dates[-1]:
            print(f"⏳ 30초 대기...")
            time.sleep(30)
    
    print("\n✅ 개선 프로세스 완료")

if __name__ == "__main__":
    main()