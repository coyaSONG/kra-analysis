#!/usr/bin/env python3
"""
스마트 경주 데이터 전처리 스크립트
- 경주가 완료된 데이터만 전처리
- 경주가 진행되지 않은 데이터는 그대로 사용
"""

import json
import copy
import os
import glob
from typing import Dict, Any, Tuple
from preprocess_race_data_v2 import clean_race_data_v2


def check_race_status(race_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    경주 상태 확인
    
    Returns:
        (is_completed, status_message)
    """
    if 'response' not in race_data or 'body' not in race_data['response']:
        return False, "데이터 형식 오류"
    
    items = race_data['response']['body'].get('items', {})
    if not items or 'item' not in items:
        return False, "말 데이터 없음"
    
    horses = items['item']
    if not isinstance(horses, list):
        horses = [horses]
    
    if not horses:
        return False, "출전마 없음"
    
    # 첫 번째 말로 상태 판단
    first_horse = horses[0]
    
    # 경주 완료 여부 판단 기준:
    # 1. ord(착순)가 0이 아닌 값이 있음
    # 2. rcTime(기록)이 0이 아닌 값이 있음
    # 3. winOdds가 모두 0이면 아직 시작 안함
    
    # 모든 말의 배당률이 0인지 확인
    all_zero_odds = all(h.get('winOdds', 0) == 0 for h in horses)
    
    if all_zero_odds:
        return False, "경주 미시작 (배당률 미확정)"
    
    # ord나 rcTime이 0이 아닌 값이 있는지 확인
    has_results = any(h.get('ord', 0) != 0 or h.get('rcTime', 0) != 0 for h in horses)
    
    if has_results:
        return True, "경주 완료"
    else:
        return False, "경주 대기 중"


def smart_process_race_file(input_path: str, output_dir: str = None) -> Dict[str, Any]:
    """
    스마트 경주 파일 처리
    - 완료된 경주만 전처리
    - 미진행 경주는 그대로 복사
    
    Returns:
        처리 결과 정보
    """
    print(f"\n📄 처리 중: {input_path}")
    
    try:
        # 원본 데이터 읽기
        with open(input_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        # 경주 상태 확인
        is_completed, status_msg = check_race_status(raw_data)
        
        # 출력 경로 결정
        if output_dir:
            # 명시적으로 지정된 경우
            base_name = os.path.basename(input_path).replace('.json', '')
            output_filename = f"{base_name}_prerace.json"
            output_path = os.path.join(output_dir, output_filename)
        else:
            # 입력 파일과 같은 경로에 저장
            if 'temp_' in os.path.basename(input_path):
                # 임시 파일인 경우, 원래 경로 구성
                import re
                match = re.search(r'race_(\d)_(\d{8})_(\d+)', input_path)
                if match:
                    meet, date, race_no = match.groups()
                    year = date[:4]
                    month = date[4:6]
                    meet_folder = {'1': 'seoul', '2': 'jeju', '3': 'busan'}.get(meet, f'meet{meet}')
                    output_dir = f"data/races/{year}/{month}/{date}/{meet_folder}"
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = f"{output_dir}/race_{meet}_{date}_{race_no}_prerace.json"
                else:
                    # 기본값
                    output_path = input_path.replace('.json', '_prerace.json')
            else:
                output_path = input_path.replace('.json', '_prerace.json')
        
        # 통계 정보
        result = {
            'file': os.path.basename(input_path),
            'status': status_msg,
            'processed': False,
            'output': output_filename
        }
        
        if is_completed:
            # 경주가 완료된 경우: 전처리 실행
            print(f"🏁 {status_msg} → 전처리 실행")
            cleaned_data = clean_race_data_v2(raw_data)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
            
            result['processed'] = True
            print(f"✅ 전처리 완료 → {output_filename}")
            
        else:
            # 경주가 진행되지 않은 경우: 그대로 복사
            print(f"⏳ {status_msg} → 원본 유지")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(raw_data, f, ensure_ascii=False, indent=2)
            
            print(f"📋 원본 복사 → {output_filename}")
        
        # 간단한 정보 출력
        horses = raw_data['response']['body']['items']['item']
        if not isinstance(horses, list):
            horses = [horses]
        
        if horses and horses[0]:
            sample = horses[0]
            print(f"   경주: {sample.get('rcDate')} {sample.get('meet')} {sample.get('rcNo')}R")
            print(f"   출전: {len(horses)}두")
            
        return result
        
    except Exception as e:
        print(f"❌ 처리 실패: {e}")
        return {
            'file': os.path.basename(input_path),
            'status': '오류',
            'processed': False,
            'error': str(e)
        }


def batch_smart_process(pattern: str, output_dir: str = None):
    """
    여러 경주 파일을 스마트하게 일괄 처리
    """
    # 출력 디렉토리 생성 (지정된 경우만)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # 매칭되는 파일 찾기
    files = sorted(glob.glob(pattern))
    print(f"\n📁 {len(files)}개 파일 발견")
    print("="*60)
    
    results = []
    stats = {
        'total': len(files),
        'completed': 0,
        'not_started': 0,
        'waiting': 0,
        'error': 0
    }
    
    for file_path in files:
        result = smart_process_race_file(file_path, output_dir)
        results.append(result)
        
        # 통계 업데이트
        if 'error' in result:
            stats['error'] += 1
        elif result['status'] == '경주 완료':
            stats['completed'] += 1
        elif '미시작' in result['status']:
            stats['not_started'] += 1
        else:
            stats['waiting'] += 1
    
    # 최종 통계
    print(f"\n{'='*60}")
    print("📊 처리 결과 요약")
    print(f"  - 전체: {stats['total']}개")
    print(f"  - 경주 완료 (전처리): {stats['completed']}개")
    print(f"  - 경주 미시작 (원본): {stats['not_started']}개")
    print(f"  - 경주 대기 (원본): {stats['waiting']}개")
    print(f"  - 처리 오류: {stats['error']}개")
    
    # 상세 결과 저장 (output_dir이 지정된 경우만)
    if output_dir:
        summary_path = os.path.join(output_dir, '_processing_summary.json')
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump({
                'stats': stats,
                'details': results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 상세 결과: {summary_path}")


def compare_files(file1: str, file2: str):
    """두 파일의 주요 필드 비교"""
    with open(file1, 'r') as f:
        data1 = json.load(f)
    with open(file2, 'r') as f:
        data2 = json.load(f)
    
    horse1 = data1['response']['body']['items']['item']
    horse2 = data2['response']['body']['items']['item']
    
    if isinstance(horse1, list):
        horse1 = horse1[0]
    if isinstance(horse2, list):
        horse2 = horse2[0]
    
    print(f"\n📊 파일 비교")
    print(f"파일1: {os.path.basename(file1)}")
    print(f"파일2: {os.path.basename(file2)}")
    print("-"*40)
    
    fields = ['ord', 'rcTime', 'winOdds', 'plcOdds', 'wgHr']
    for field in fields:
        val1 = horse1.get(field, 'N/A')
        val2 = horse2.get(field, 'N/A')
        match = "✅" if val1 == val2 else "❌"
        print(f"{field:10} {str(val1):>10} → {str(val2):>10} {match}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        pattern = sys.argv[1]
    else:
        # 기본값: 오늘 서울 경마장 데이터
        pattern = "data/race_1_20250608_*.json"
    
    print(f"🔍 패턴: {pattern}")
    batch_smart_process(pattern)