#!/usr/bin/env python3
"""
날짜별 순차 프롬프트 개선 실행 스크립트
- 6월 1일, 7일, 8일 데이터를 순차적으로 사용
- 각 날짜당 2회 반복만 실행 (타임아웃 방지)
- 확장된 타임아웃 설정 사용
- 각 날짜 완료 후 결과 저장
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import time


def run_improvement_for_date(base_prompt: str, date: str, max_iterations: int = 2, max_workers: int = 3):
    """특정 날짜에 대한 개선 프로세스 실행"""
    print(f"\n{'='*70}")
    print(f"🗓️  날짜 {date} 개선 시작")
    print(f"{'='*70}")
    
    # 환경변수 설정 (확장된 타임아웃)
    env = os.environ.copy()
    env['BASH_DEFAULT_TIMEOUT_MS'] = '600000'  # 10분
    env['DISABLE_INTERLEAVED_THINKING'] = 'true'
    
    # recursive_prompt_improvement_v4.py 실행
    cmd = [
        'python3',
        'scripts/prompt_improvement/recursive_prompt_improvement_v4.py',
        base_prompt,
        date,
        str(max_iterations),
        str(max_workers)
    ]
    
    try:
        # 프로세스 실행
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=1200  # 20분 전체 타임아웃
        )
        
        if result.returncode != 0:
            print(f"❌ 날짜 {date} 실행 중 오류 발생:")
            print(result.stderr)
            return False
            
        print(f"✅ 날짜 {date} 개선 완료")
        
        # 결과 저장
        save_date_results(date)
        
        return True
        
    except subprocess.TimeoutExpired:
        print(f"⏱️ 날짜 {date} 타임아웃 발생 (20분 초과)")
        return False
    except Exception as e:
        print(f"❌ 날짜 {date} 실행 중 예외 발생: {e}")
        return False


def save_date_results(date: str):
    """각 날짜의 결과를 별도 파일로 저장"""
    # 최신 개선 보고서 찾기
    working_dir = Path("data/recursive_improvement_v4")
    report_files = list(working_dir.glob("improvement_report_*.md"))
    
    if not report_files:
        print(f"⚠️ 날짜 {date}의 보고서를 찾을 수 없습니다")
        return
        
    # 가장 최근 파일
    latest_report = max(report_files, key=lambda x: x.stat().st_mtime)
    
    # 날짜별 디렉토리 생성
    date_dir = Path("data/prompt_improvement_by_date") / date
    date_dir.mkdir(parents=True, exist_ok=True)
    
    # 보고서 복사
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_report = date_dir / f"report_{date}_{timestamp}.md"
    
    with open(latest_report, 'r', encoding='utf-8') as f:
        content = f.read()
    
    with open(target_report, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"📄 날짜 {date} 결과 저장: {target_report}")
    
    # 프롬프트 파일들도 복사
    prompt_files = list(working_dir.glob("prompt_*.md"))
    for prompt_file in prompt_files:
        target_prompt = date_dir / prompt_file.name
        with open(prompt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        with open(target_prompt, 'w', encoding='utf-8') as f:
            f.write(content)


def main():
    """메인 실행 함수"""
    # 테스트할 날짜 목록
    test_dates = ['20250601', '20250607', '20250608']
    
    # 기본 프롬프트 설정
    base_prompt = 'prompts/base-prompt-v1.0.md'
    
    if not Path(base_prompt).exists():
        print(f"❌ 기본 프롬프트를 찾을 수 없습니다: {base_prompt}")
        sys.exit(1)
    
    print("🚀 날짜별 순차 프롬프트 개선 시작")
    print(f"기본 프롬프트: {base_prompt}")
    print(f"테스트 날짜: {', '.join(test_dates)}")
    print(f"각 날짜당 반복: 2회")
    print(f"병렬 처리: 3개 동시 실행")
    print("=" * 70)
    
    # 전체 시작 시간
    start_time = time.time()
    
    # 각 날짜별로 순차 실행
    results = {}
    for date in test_dates:
        print(f"\n⏳ {date} 처리 시작...")
        
        success = run_improvement_for_date(
            base_prompt=base_prompt,
            date=date,
            max_iterations=2,  # 타임아웃 방지를 위해 2회만
            max_workers=3
        )
        
        results[date] = success
        
        # 다음 날짜 전 대기 (API 부하 방지)
        if date != test_dates[-1]:  # 마지막이 아니면
            print(f"\n⏳ 다음 날짜 처리 전 30초 대기...")
            time.sleep(30)
    
    # 전체 소요 시간
    elapsed_time = time.time() - start_time
    
    # 최종 요약
    print("\n" + "=" * 70)
    print("📊 전체 실행 요약")
    print("=" * 70)
    
    for date, success in results.items():
        status = "✅ 성공" if success else "❌ 실패"
        print(f"{date}: {status}")
    
    print(f"\n총 소요 시간: {elapsed_time/60:.1f}분")
    
    # 최종 통합 보고서 생성
    create_final_summary_report(test_dates, results)


def create_final_summary_report(test_dates: list, results: dict):
    """모든 날짜의 결과를 통합한 최종 보고서 생성"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_path = Path("data/prompt_improvement_by_date") / f"final_summary_{timestamp}.md"
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("# 날짜별 프롬프트 개선 통합 보고서\n\n")
        f.write(f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"테스트 날짜: {', '.join(test_dates)}\n\n")
        
        f.write("## 실행 결과 요약\n\n")
        f.write("| 날짜 | 상태 | 세부 결과 경로 |\n")
        f.write("|------|------|----------------|\n")
        
        for date in test_dates:
            status = "✅ 완료" if results.get(date, False) else "❌ 실패"
            date_dir = Path("data/prompt_improvement_by_date") / date
            
            if date_dir.exists():
                report_files = list(date_dir.glob("report_*.md"))
                if report_files:
                    latest_report = max(report_files, key=lambda x: x.stat().st_mtime)
                    f.write(f"| {date} | {status} | {latest_report.relative_to('.')} |\n")
                else:
                    f.write(f"| {date} | {status} | 보고서 없음 |\n")
            else:
                f.write(f"| {date} | {status} | 결과 없음 |\n")
        
        # 각 날짜별 최고 성능 추출
        f.write("\n## 날짜별 최고 성능\n\n")
        
        for date in test_dates:
            if not results.get(date, False):
                continue
                
            date_dir = Path("data/prompt_improvement_by_date") / date
            if not date_dir.exists():
                continue
                
            report_files = list(date_dir.glob("report_*.md"))
            if not report_files:
                continue
                
            latest_report = max(report_files, key=lambda x: x.stat().st_mtime)
            
            # 보고서에서 성능 정보 추출
            with open(latest_report, 'r', encoding='utf-8') as rf:
                content = rf.read()
                
                # 최종 성능 찾기
                import re
                final_perf_match = re.search(r'최종 성능: ([\d.]+)% \(평균 ([\d.]+)마리\)', content)
                if final_perf_match:
                    f.write(f"\n### {date}\n")
                    f.write(f"- 최종 적중률: {final_perf_match.group(1)}%\n")
                    f.write(f"- 평균 적중 말: {final_perf_match.group(2)}마리\n")
        
        f.write("\n## 권장 사항\n\n")
        f.write("1. 각 날짜별 세부 보고서를 검토하여 공통 패턴 확인\n")
        f.write("2. 가장 성능이 좋은 날짜의 프롬프트를 기준으로 추가 개선\n")
        f.write("3. 날짜별 특성(경주 난이도 등)을 고려한 적응형 전략 개발\n")
    
    print(f"\n📄 최종 통합 보고서 생성: {summary_path}")


if __name__ == "__main__":
    main()