#!/usr/bin/env python3
"""
여러 경주 파일을 일괄 전처리하는 스크립트
"""

import os
import glob
import json
from preprocess_race_data_v2 import clean_race_data_v2 as clean_race_data

def batch_process_races(pattern: str, output_dir: str = "data/processed/pre-race"):
    """
    패턴에 맞는 모든 경주 파일을 전처리
    
    Args:
        pattern: 파일 패턴 (예: "data/race_*.json")
        output_dir: 출력 디렉토리
    """
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    # 매칭되는 파일 찾기
    files = sorted(glob.glob(pattern))
    print(f"\n📁 {len(files)}개 파일 발견")
    
    stats = {
        'processed': 0,
        'failed': 0,
        'total_horses': 0,
        'excluded_horses': 0
    }
    
    for file_path in files:
        print(f"\n{'='*60}")
        print(f"📄 처리 중: {os.path.basename(file_path)}")
        
        try:
            # 원본 데이터 읽기
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            # 원본 말 수
            orig_count = 0
            if 'response' in raw_data and 'body' in raw_data['response']:
                items = raw_data['response']['body'].get('items', {})
                if items and 'item' in items:
                    orig_items = items['item']
                    orig_count = len(orig_items) if isinstance(orig_items, list) else 1
            
            # 데이터 정제
            cleaned_data = clean_race_data(raw_data)
            
            # 정제된 말 수
            clean_count = cleaned_data['response']['body'].get('totalCount', 0)
            
            # 경주 정보 추출
            if cleaned_data['response']['body']['items']:
                sample_item = cleaned_data['response']['body']['items']['item']
                if isinstance(sample_item, list) and sample_item:
                    sample_item = sample_item[0]
                elif not sample_item:
                    sample_item = {}
                
                race_info = {
                    'date': sample_item.get('rcDate', ''),
                    'meet': sample_item.get('meet', ''),
                    'race_no': sample_item.get('rcNo', ''),
                    'distance': sample_item.get('rcDist', ''),
                    'weather': sample_item.get('weather', ''),
                    'track': sample_item.get('track', '')
                }
                
                print(f"📅 경주 정보: {race_info['date']} {race_info['meet']} {race_info['race_no']}R")
                print(f"🏃 거리: {race_info['distance']}m | 날씨: {race_info['weather']} | 주로: {race_info['track']}")
            
            # 통계 업데이트
            stats['total_horses'] += orig_count
            stats['excluded_horses'] += (orig_count - clean_count)
            
            # 정제된 데이터 저장
            output_filename = os.path.basename(file_path).replace('.json', '_prerace.json')
            output_path = os.path.join(output_dir, output_filename)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 전처리 완료: {orig_count}두 → {clean_count}두")
            if orig_count > clean_count:
                print(f"   ⚠️  {orig_count - clean_count}두 제외 (기권/제외)")
            
            # 샘플 출력
            if clean_count > 0:
                print("\n출전마 리스트:")
                horses = cleaned_data['response']['body']['items']['item']
                if not isinstance(horses, list):
                    horses = [horses]
                
                for horse in horses[:5]:  # 처음 5마리만
                    odds_str = f"{horse.get('winOdds', 'N/A'):>5}"
                    print(f"  {horse.get('chulNo'):>2}번 {horse.get('hrName'):<12} "
                          f"기수: {horse.get('jkName'):<6} 배당률: {odds_str}")
                
                if len(horses) > 5:
                    print(f"  ... 외 {len(horses) - 5}두")
            
            stats['processed'] += 1
            
        except Exception as e:
            print(f"❌ 처리 실패: {e}")
            stats['failed'] += 1
    
    # 최종 통계
    print(f"\n{'='*60}")
    print("📊 전체 처리 결과")
    print(f"  - 처리 성공: {stats['processed']}개 파일")
    print(f"  - 처리 실패: {stats['failed']}개 파일")
    print(f"  - 총 말 수: {stats['total_horses']}두")
    print(f"  - 제외된 말: {stats['excluded_horses']}두")
    print(f"  - 최종 말 수: {stats['total_horses'] - stats['excluded_horses']}두")


def create_race_summary(prerace_dir: str = "data/processed/pre-race"):
    """
    전처리된 경주 데이터 요약 생성
    """
    files = sorted(glob.glob(os.path.join(prerace_dir, "*.json")))
    
    summary = []
    for file_path in files:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if data['response']['body']['items']:
            items = data['response']['body']['items']['item']
            if not isinstance(items, list):
                items = [items]
            
            if items:
                race_info = {
                    'file': os.path.basename(file_path),
                    'date': items[0].get('rcDate'),
                    'meet': items[0].get('meet'),
                    'race_no': items[0].get('rcNo'),
                    'distance': items[0].get('rcDist'),
                    'horses': len(items),
                    'has_odds': any(h.get('winOdds') for h in items)
                }
                summary.append(race_info)
    
    # 요약 출력
    print("\n📋 전처리된 경주 요약")
    print("="*70)
    print("날짜      장소  R  거리    두수  배당률")
    print("-"*70)
    
    for race in summary:
        date_val = str(race['date']) if race['date'] else ''
        date_str = date_val[:4] + '-' + date_val[4:6] + '-' + date_val[6:] if date_val else 'N/A'
        odds_str = "있음" if race['has_odds'] else "없음"
        print(f"{date_str}  {race['meet']:<4}  {race['race_no']:>2}  {race['distance']:>4}m  {race['horses']:>4}  {odds_str}")
    
    # 요약 파일 저장
    with open(os.path.join(prerace_dir, '_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        pattern = sys.argv[1]
    else:
        # 기본값: 오늘 서울 경마장 데이터
        pattern = "data/race_1_20250608_*.json"
    
    print(f"🔍 패턴: {pattern}")
    batch_process_races(pattern)
    
    # 요약 생성
    create_race_summary()