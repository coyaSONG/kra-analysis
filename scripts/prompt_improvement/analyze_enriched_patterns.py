#!/usr/bin/env python3
"""
Enriched 데이터의 패턴 분석
- 배당률 순위와 실제 순위의 상관관계
- 기수/말 성적과 실제 순위의 상관관계
"""

import json
import glob
from pathlib import Path
from typing import Dict, List, Tuple

def load_race_with_result(enriched_file: str) -> Tuple[Dict, List[int]]:
    """enriched 파일과 대응하는 결과 로드"""
    # enriched 파일에서 정보 추출
    path_parts = Path(enriched_file).parts
    date = path_parts[-4]  # 20250601
    venue = path_parts[-2]  # seoul, busan, jeju
    filename = path_parts[-1]  # race_1_20250601_1_enriched.json
    
    # 경주 번호 추출
    race_no = filename.split('_')[3]
    
    # 결과 파일 경로
    venue_map = {'seoul': '서울', 'busan': '부산경남', 'jeju': '제주'}
    result_file = f"data/cache/results/top3_{date}_{venue_map.get(venue, venue)}_{race_no}.json"
    
    # 데이터 로드
    with open(enriched_file, 'r', encoding='utf-8') as f:
        race_data = json.load(f)
    
    # 결과 로드
    if Path(result_file).exists():
        with open(result_file, 'r', encoding='utf-8') as f:
            result = json.load(f)
        return race_data, result
    
    return race_data, []

def analyze_patterns():
    """전체 경주 데이터 패턴 분석"""
    # enriched 파일 찾기
    files = glob.glob("data/races/2025/06/*/*/*/*_enriched.json")
    
    # 통계 초기화
    stats = {
        'total_races': 0,
        'odds_rank_in_top3': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
        'jockey_win_rate_correlation': [],
        'horse_place_rate_correlation': []
    }
    
    for file in files:
        race_data, result = load_race_with_result(file)
        
        if not result or len(result) != 3:
            continue
            
        stats['total_races'] += 1
        
        # 말 데이터 추출
        horses = race_data['response']['body']['items']['item']
        if not isinstance(horses, list):
            horses = [horses]
        
        # 기권/제외 제거
        valid_horses = [h for h in horses if h.get('winOdds', 0) > 0]
        
        # 배당률 순위 매기기
        valid_horses.sort(key=lambda x: x['winOdds'])
        odds_rank = {h['chulNo']: i+1 for i, h in enumerate(valid_horses)}
        
        # 실제 1-3위 말들의 배당률 순위 확인
        for place_horse in result:
            if place_horse in odds_rank:
                rank = odds_rank[place_horse]
                if rank <= 5:
                    stats['odds_rank_in_top3'][rank] += 1
        
        # 기수 승률과 말 입상률 계산
        for horse in valid_horses:
            chul_no = horse['chulNo']
            
            # 기수 승률
            if 'jkDetail' in horse and horse['jkDetail']:
                jk = horse['jkDetail']
                if jk.get('rcCntT', 0) > 0:
                    win_rate = jk.get('ord1CntT', 0) / jk['rcCntT']
                    is_top3 = chul_no in result
                    stats['jockey_win_rate_correlation'].append((win_rate, is_top3))
            
            # 말 입상률
            if 'hrDetail' in horse and horse['hrDetail']:
                hr = horse['hrDetail']
                if hr.get('rcCntT', 0) > 0:
                    place_rate = (hr.get('ord1CntT', 0) + hr.get('ord2CntT', 0) + 
                                 hr.get('ord3CntT', 0)) / hr['rcCntT']
                    is_top3 = chul_no in result
                    stats['horse_place_rate_correlation'].append((place_rate, is_top3))
    
    # 결과 출력
    print(f"=== Enriched 데이터 패턴 분석 결과 ===")
    print(f"분석 경주 수: {stats['total_races']}개\n")
    
    print("=== 배당률 순위별 실제 입상 횟수 ===")
    for rank, count in stats['odds_rank_in_top3'].items():
        pct = count / (stats['total_races'] * 3) * 100 if stats['total_races'] > 0 else 0
        print(f"배당률 {rank}위: {count}회 ({pct:.1f}%)")
    
    # 기수 승률 분석
    if stats['jockey_win_rate_correlation']:
        top3_rates = [r for r, t in stats['jockey_win_rate_correlation'] if t]
        non_top3_rates = [r for r, t in stats['jockey_win_rate_correlation'] if not t]
        
        print(f"\n=== 기수 승률과 입상 상관관계 ===")
        print(f"입상 말의 평균 기수 승률: {sum(top3_rates)/len(top3_rates)*100:.1f}%")
        print(f"미입상 말의 평균 기수 승률: {sum(non_top3_rates)/len(non_top3_rates)*100:.1f}%")
    
    # 말 입상률 분석
    if stats['horse_place_rate_correlation']:
        top3_rates = [r for r, t in stats['horse_place_rate_correlation'] if t]
        non_top3_rates = [r for r, t in stats['horse_place_rate_correlation'] if not t]
        
        print(f"\n=== 말 입상률과 실제 입상 상관관계 ===")
        print(f"입상 말의 평균 과거 입상률: {sum(top3_rates)/len(top3_rates)*100:.1f}%")
        print(f"미입상 말의 평균 과거 입상률: {sum(non_top3_rates)/len(non_top3_rates)*100:.1f}%")

if __name__ == "__main__":
    analyze_patterns()