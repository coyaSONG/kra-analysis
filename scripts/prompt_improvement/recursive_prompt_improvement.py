#!/usr/bin/env python3
"""
재귀적 프롬프트 개선 시스템
- 평가 → 분석 → 개선 → 재평가 사이클 자동화
- 각 iteration의 결과를 추적하고 개선 방향 도출
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import time

class RecursivePromptImprover:
    def __init__(self, base_prompt_path: str, max_iterations: int = 5):
        self.base_prompt_path = Path(base_prompt_path)
        self.max_iterations = max_iterations
        self.working_dir = Path("data/recursive_improvement")
        self.working_dir.mkdir(parents=True, exist_ok=True)
        
        self.iteration_history = []
        
    def run_evaluation(self, prompt_version: str, prompt_path: str, test_limit: int = 10) -> Dict:
        """프롬프트 평가 실행"""
        cmd = [
            'python3', 'scripts/evaluate_prompt.py',
            prompt_version, prompt_path, str(test_limit)
        ]
        
        print(f"\n평가 실행: {prompt_version}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return None
        
        # 최신 평가 결과 파일 찾기
        eval_files = list(Path("data/prompt_evaluation").glob(f"evaluation_{prompt_version}_*.json"))
        if not eval_files:
            return None
            
        latest_file = max(eval_files, key=lambda x: x.stat().st_mtime)
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def analyze_results(self, current_results: Dict, previous_results: Dict = None) -> Dict:
        """결과 분석 및 개선 방향 도출"""
        analysis = {
            "current_performance": {
                "success_rate": current_results["success_rate"],
                "avg_correct": current_results["average_correct_horses"]
            }
        }
        
        # 이전 결과와 비교
        if previous_results:
            analysis["improvement"] = {
                "success_rate_change": current_results["success_rate"] - previous_results["success_rate"],
                "avg_correct_change": current_results["average_correct_horses"] - previous_results["average_correct_horses"]
            }
        
        # 실패 패턴 분석
        failure_patterns = self.analyze_failure_patterns(current_results)
        analysis["failure_patterns"] = failure_patterns
        
        # 개선 제안 생성
        analysis["suggestions"] = self.generate_improvement_suggestions(failure_patterns, current_results)
        
        return analysis
    
    def analyze_failure_patterns(self, results: Dict) -> Dict:
        """실패 패턴 상세 분석"""
        patterns = {
            "missed_popular_horses": [],
            "data_shortage_issues": [],
            "weight_change_misinterpretation": [],
            "wrong_market_evaluation": []
        }
        
        for race_result in results["detailed_results"]:
            if race_result.get("failure_analysis"):
                for missed in race_result["failure_analysis"]["missed_horses"]:
                    # 인기마 놓침
                    if missed["popularity_rank"] <= 3:
                        patterns["missed_popular_horses"].append({
                            "race_id": race_result["race_id"],
                            "horse": missed["hr_name"],
                            "rank": missed["popularity_rank"]
                        })
                    
                    # 데이터 부족
                    if missed["data_count"] < 3:
                        patterns["data_shortage_issues"].append({
                            "race_id": race_result["race_id"],
                            "horse": missed["hr_name"],
                            "data_count": missed["data_count"]
                        })
        
        return patterns
    
    def generate_improvement_suggestions(self, patterns: Dict, results: Dict) -> List[Dict]:
        """구체적인 개선 제안 생성"""
        suggestions = []
        
        # 인기마 놓침 문제
        missed_popular_count = len(patterns["missed_popular_horses"])
        if missed_popular_count > results["total_races"] * 0.3:
            suggestions.append({
                "type": "weight_adjustment",
                "target": "market_evaluation",
                "current": 20,
                "suggested": 25,
                "reason": f"{missed_popular_count}개 경주에서 상위 인기마 놓침"
            })
        
        # 데이터 부족 문제
        data_shortage_count = len(patterns["data_shortage_issues"])
        if data_shortage_count > results["total_races"] * 0.2:
            suggestions.append({
                "type": "logic_improvement",
                "target": "c_group_handling",
                "action": "increase_market_weight_multiplier",
                "current": 2,
                "suggested": 2.5,
                "reason": f"{data_shortage_count}개 케이스에서 데이터 부족 말 과소평가"
            })
        
        # 전반적 성능이 낮은 경우
        if results["success_rate"] < 15:
            suggestions.append({
                "type": "structural_change",
                "target": "analysis_process",
                "action": "add_verification_step",
                "reason": "전체 성공률이 15% 미만, 검증 단계 강화 필요"
            })
        
        return suggestions
    
    def apply_improvements(self, current_prompt_path: Path, 
                          suggestions: List[Dict], 
                          new_version: str) -> Path:
        """개선사항을 프롬프트에 적용"""
        with open(current_prompt_path, 'r', encoding='utf-8') as f:
            prompt_content = f.read()
        
        # 개선사항 적용
        for suggestion in suggestions:
            if suggestion["type"] == "weight_adjustment":
                # 가중치 조정
                old_pattern = f"{suggestion['target']}: {suggestion['current']}%"
                new_pattern = f"{suggestion['target']}: {suggestion['suggested']}%"
                prompt_content = prompt_content.replace(old_pattern, new_pattern)
                
                print(f"  - {suggestion['target']} 가중치: {suggestion['current']}% → {suggestion['suggested']}%")
            
            elif suggestion["type"] == "logic_improvement":
                # 로직 개선 (주석으로 표시)
                improvement_note = f"\n# IMPROVEMENT {new_version}: {suggestion['reason']}\n"
                prompt_content = improvement_note + prompt_content
                
                print(f"  - {suggestion['target']} 로직 개선: {suggestion['action']}")
        
        # 새 버전 저장
        new_prompt_path = self.working_dir / f"prompt_{new_version}.md"
        with open(new_prompt_path, 'w', encoding='utf-8') as f:
            f.write(prompt_content)
        
        return new_prompt_path
    
    def run_improvement_cycle(self, initial_test_limit: int = 10):
        """전체 개선 사이클 실행"""
        current_prompt_path = self.base_prompt_path
        previous_results = None
        
        print(f"재귀적 프롬프트 개선 시작")
        print(f"최대 반복: {self.max_iterations}회")
        print(f"테스트 경주 수: {initial_test_limit}개")
        print("=" * 60)
        
        for iteration in range(self.max_iterations):
            version = f"v{iteration+1}.{iteration}"
            
            print(f"\n\n=== Iteration {iteration+1}/{self.max_iterations} ===")
            
            # 1. 현재 프롬프트 평가
            evaluation_results = self.run_evaluation(version, str(current_prompt_path), initial_test_limit)
            
            if not evaluation_results:
                print("평가 실패, 중단")
                break
            
            # 2. 결과 분석
            analysis = self.analyze_results(evaluation_results, previous_results)
            
            # 3. 이력 저장
            self.iteration_history.append({
                "iteration": iteration + 1,
                "version": version,
                "results": evaluation_results,
                "analysis": analysis
            })
            
            # 4. 성능 출력
            print(f"\n성능 요약:")
            print(f"  - 완전 적중률: {evaluation_results['success_rate']:.1f}%")
            print(f"  - 평균 적중 말: {evaluation_results['average_correct_horses']:.2f}/3")
            
            if previous_results:
                print(f"  - 적중률 변화: {analysis['improvement']['success_rate_change']:+.1f}%p")
            
            # 5. 목표 달성 확인
            if evaluation_results['success_rate'] >= 30:
                print(f"\n목표 달성! (적중률 30% 이상)")
                break
            
            # 6. 개선 불가능 확인
            if previous_results and analysis['improvement']['success_rate_change'] < 0.5:
                print(f"\n개선 정체 (0.5%p 미만 향상)")
                if iteration >= 2:  # 최소 3회는 시도
                    break
            
            # 7. 다음 반복을 위한 개선
            if iteration < self.max_iterations - 1:
                print(f"\n개선사항 적용:")
                new_version = f"v{iteration+2}.{iteration+1}"
                new_prompt_path = self.apply_improvements(
                    current_prompt_path,
                    analysis["suggestions"],
                    new_version
                )
                
                current_prompt_path = new_prompt_path
                previous_results = evaluation_results
                
                # 다음 반복 전 대기
                print(f"\n다음 반복 준비 중...")
                time.sleep(5)
        
        # 최종 보고서 생성
        self.generate_final_report()
    
    def generate_final_report(self):
        """최종 개선 보고서 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.working_dir / f"improvement_report_{timestamp}.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# 프롬프트 재귀 개선 보고서\n\n")
            f.write(f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"총 반복: {len(self.iteration_history)}회\n\n")
            
            f.write("## 성능 변화 추이\n\n")
            f.write("| Iteration | Version | 적중률 | 평균 적중 | 변화 |\n")
            f.write("|-----------|---------|--------|----------|------|\n")
            
            for i, history in enumerate(self.iteration_history):
                results = history["results"]
                change = ""
                if i > 0:
                    prev_rate = self.iteration_history[i-1]["results"]["success_rate"]
                    change = f"{results['success_rate'] - prev_rate:+.1f}%p"
                
                f.write(f"| {history['iteration']} | {history['version']} | "
                       f"{results['success_rate']:.1f}% | "
                       f"{results['average_correct_horses']:.2f} | {change} |\n")
            
            f.write("\n## 주요 개선사항\n\n")
            for history in self.iteration_history:
                if history["analysis"].get("suggestions"):
                    f.write(f"\n### {history['version']}\n")
                    for suggestion in history["analysis"]["suggestions"]:
                        f.write(f"- {suggestion['reason']}\n")
                        if suggestion["type"] == "weight_adjustment":
                            f.write(f"  - {suggestion['target']}: "
                                   f"{suggestion['current']}% → {suggestion['suggested']}%\n")
            
            f.write("\n## 결론\n\n")
            
            # 최종 성능
            final_results = self.iteration_history[-1]["results"]
            initial_results = self.iteration_history[0]["results"]
            
            f.write(f"- 초기 성능: {initial_results['success_rate']:.1f}%\n")
            f.write(f"- 최종 성능: {final_results['success_rate']:.1f}%\n")
            f.write(f"- 전체 개선: {final_results['success_rate'] - initial_results['success_rate']:+.1f}%p\n")
            
            # 최적 버전
            best_iteration = max(self.iteration_history, 
                               key=lambda x: x["results"]["success_rate"])
            f.write(f"\n최고 성능 버전: {best_iteration['version']} "
                   f"(적중률 {best_iteration['results']['success_rate']:.1f}%)\n")
        
        print(f"\n\n최종 보고서 생성: {report_path}")
        
        # 최적 프롬프트 복사
        best_prompt = self.working_dir / f"prompt_{best_iteration['version']}.md"
        if best_prompt.exists():
            final_prompt = Path("prompts") / f"prediction-template-optimized.md"
            subprocess.run(['cp', str(best_prompt), str(final_prompt)])
            print(f"최적화된 프롬프트 저장: {final_prompt}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python recursive_prompt_improvement.py <base_prompt_file> [test_limit] [max_iterations]")
        print("Example: python recursive_prompt_improvement.py prompts/prediction-template-v2.0.md 10 5")
        sys.exit(1)
    
    base_prompt = sys.argv[1]
    test_limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    max_iterations = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    
    # 재귀 개선 실행
    improver = RecursivePromptImprover(base_prompt, max_iterations)
    improver.run_improvement_cycle(test_limit)


if __name__ == "__main__":
    main()