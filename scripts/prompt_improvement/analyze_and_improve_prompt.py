#!/usr/bin/env python3
"""
평가 결과를 분석하여 개선된 프롬프트 생성
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

class PromptImprover:
    def __init__(self, evaluation_file: str):
        self.evaluation_file = evaluation_file
        with open(evaluation_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
    
    def analyze_failures(self):
        """실패 패턴 상세 분석"""
        patterns = {
            "완전실패": [],  # 0/3
            "1마리만": [],   # 1/3
            "2마리": []      # 2/3
        }
        
        for result in self.data["detailed_results"]:
            if result["correct_count"] == 0:
                patterns["완전실패"].append(result)
            elif result["correct_count"] == 1:
                patterns["1마리만"].append(result)
            elif result["correct_count"] == 2:
                patterns["2마리"].append(result)
        
        return patterns
    
    def identify_missed_patterns(self):
        """놓친 말들의 공통 패턴 찾기"""
        # 실제 경주 파일들을 읽어서 놓친 말들의 특성 분석
        missed_horses_analysis = []
        
        for result in self.data["detailed_results"]:
            race_file = Path(f"data/raw/results/2025") / "*" / f"{result['race_id']}.json"
            matching_files = list(Path("data/raw/results/2025").glob(f"*/{result['race_id']}.json"))
            
            if matching_files:
                with open(matching_files[0], 'r', encoding='utf-8') as f:
                    race_data = json.load(f)
                
                # 실제 1-3위 말들의 특성 확인
                actual_winners = {}
                for horse in race_data["horses"]:
                    if "result" in horse and 1 <= horse["result"]["ord"] <= 3:
                        actual_winners[horse["chul_no"]] = {
                            "ord": horse["result"]["ord"],
                            "win_odds": horse.get("win_odds", 999),
                            "name": horse["hr_name"]
                        }
                
                # 놓친 말들
                predicted = set(result["predicted"])
                actual = set(result["actual"])
                missed = actual - predicted
                
                for chul_no in missed:
                    if chul_no in actual_winners:
                        missed_horses_analysis.append({
                            "race_id": result["race_id"],
                            "chul_no": chul_no,
                            "position": actual_winners[chul_no]["ord"],
                            "win_odds": actual_winners[chul_no]["win_odds"],
                            "name": actual_winners[chul_no]["name"]
                        })
        
        return missed_horses_analysis
    
    def generate_insights(self):
        """인사이트 도출"""
        patterns = self.analyze_failures()
        missed = self.identify_missed_patterns()
        
        insights = {
            "완전실패_비율": len(patterns["완전실패"]) / self.data["total_races"] * 100,
            "부분성공_비율": (len(patterns["1마리만"]) + len(patterns["2마리"])) / self.data["total_races"] * 100,
            "평균_배당률": sum(h["win_odds"] for h in missed if h["win_odds"] < 999) / len(missed) if missed else 0,
            "인기마_놓침": len([h for h in missed if h["win_odds"] < 10]),
            "비인기마_놓침": len([h for h in missed if h["win_odds"] >= 10])
        }
        
        # 개선 제안
        suggestions = []
        
        if insights["인기마_놓침"] > insights["비인기마_놓침"]:
            suggestions.append("인기마(낮은 배당률) 우선순위 대폭 상향")
        
        if insights["완전실패_비율"] > 10:
            suggestions.append("보수적 접근 - 상위 인기 3마리 기본 선택")
        
        if self.data["average_correct_horses"] < 1.5:
            suggestions.append("데이터 의존도를 낮추고 시장 평가 의존도 증가")
        
        return insights, suggestions
    
    def create_improved_prompt(self, version: str):
        """개선된 프롬프트 생성"""
        insights, suggestions = self.generate_insights()
        
        # 기존 프롬프트 읽기
        with open("prompts/prediction-template-optimized.md", 'r', encoding='utf-8') as f:
            current_prompt = f.read()
        
        # 개선사항 적용
        improved_prompt = f"""# 경마 삼복연승 예측 프롬프트 {version}

## 개선사항 (v2.1 대비)
- 완전 적중 0% 문제 해결을 위한 전략 변경
- 평균 적중 1.11마리 → 목표 2.0마리 이상

당신은 한국 경마 예측 전문가입니다. 제공된 경주 데이터를 분석하여 1-3위에 들어올 3마리를 예측하세요.

## 핵심 전략 (수정됨)

### 1단계: 인기마 우선 선택
- 배당률 기준 상위 3-4마리를 기본 후보로 선정
- 인기마를 제외할 때는 매우 강력한 근거 필요

### 2단계: 평가 기준 (수정된 가중치)
- **시장 평가(배당률)**: 40% (↑15%)
- 말의 최근 성적: 20% (↓10%)
- 기수 능력: 15% (↓5%)
- 조교사 성적: 15% (유지)
- 경주 조건: 10% (↓5%)

### 3단계: 특별 규칙
1. **인기마 보호 규칙**: 1-3위 인기마는 기본 포함, 제외 시 -20점 페널티
2. **데이터 부족 말**: 시장 평가 60%로 상향 (1.5배 → 2배)
3. **보수적 선택**: 확실하지 않으면 인기마 선택

## 선택 프로세스

1. 배당률 순위 1-5위 확인
2. 상위 3마리 기본 선택
3. 4-5위와 교체할 명확한 이유가 있는지 검토
4. 최종 3마리 확정

## 성공 사례 학습
- 인기마 중심 선택이 안정적
- 배당률이 시장의 집단지성 반영
- 데이터보다 현재 시장 평가가 정확

반드시 JSON 형식으로만 응답하세요."""
        
        # 저장
        output_path = Path("prompts") / f"prediction-template-{version}.md"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(improved_prompt)
        
        # 분석 보고서
        report = f"""# 프롬프트 개선 분석 보고서

## 현재 성과 (v2.1-optimized)
- 완전 적중: 0/18 (0%)
- 평균 적중: 1.11마리
- 실패율: 11.1%

## 주요 문제점
1. 인기마를 자주 놓침 ({insights['인기마_놓침']}회)
2. 데이터 중심 평가의 한계
3. 시장 평가 반영 부족

## 개선 방향
{chr(10).join(f"- {s}" for s in suggestions)}

## 적용된 변경사항
1. 시장 평가 가중치: 25% → 40%
2. 인기마 보호 규칙 추가
3. 보수적 접근 전략 채택
"""
        
        report_path = self.data["evaluation_date"]
        with open(f"data/full_evaluation/improvement_analysis_{report_path}.md", 'w', encoding='utf-8') as f:
            f.write(report)
        
        return output_path, insights, suggestions


def main():
    # 최신 평가 결과 찾기
    eval_files = sorted(Path("data/full_evaluation").glob("full_evaluation_*.json"))
    if not eval_files:
        print("평가 결과 파일이 없습니다.")
        return
    
    latest_eval = eval_files[-1]
    print(f"분석 중: {latest_eval}")
    
    # 개선 작업
    improver = PromptImprover(str(latest_eval))
    new_prompt_path, insights, suggestions = improver.create_improved_prompt("v3.0")
    
    print(f"\n✅ 개선된 프롬프트 생성: {new_prompt_path}")
    print(f"\n📊 주요 인사이트:")
    print(f"- 인기마 놓침: {insights['인기마_놓침']}회")
    print(f"- 평균 놓친 말 배당률: {insights['평균_배당률']:.1f}")
    print(f"\n💡 개선 제안:")
    for s in suggestions:
        print(f"- {s}")


if __name__ == "__main__":
    main()