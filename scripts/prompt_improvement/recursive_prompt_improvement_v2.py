#!/usr/bin/env python3
"""
재귀적 프롬프트 개선 시스템 v2
- evaluate_prompt_v3.py와 완벽 호환
- enriched 데이터 기반 분석
- 고도화된 개선 전략
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import time
import re
from collections import defaultdict

class RecursivePromptImproverV2:
    def __init__(self, base_prompt_path: str, max_iterations: int = 5):
        self.base_prompt_path = Path(base_prompt_path)
        self.max_iterations = max_iterations
        self.working_dir = Path("data/recursive_improvement_v2")
        self.working_dir.mkdir(parents=True, exist_ok=True)
        
        self.iteration_history = []
        self.base_version = self._extract_version()
        
    def _extract_version(self) -> str:
        """프롬프트 파일명에서 버전 추출"""
        filename = self.base_prompt_path.stem
        match = re.search(r'v(\d+\.\d+)', filename)
        if match:
            return match.group(1)
        return "10.3"  # 기본값
        
    def run_evaluation(self, prompt_version: str, prompt_path: str, 
                      test_limit: int = 30, max_workers: int = 3) -> Optional[Dict]:
        """evaluate_prompt_v3.py를 사용한 프롬프트 평가"""
        cmd = [
            'python3', 'scripts/evaluation/evaluate_prompt_v3.py',
            prompt_version, prompt_path, str(test_limit), str(max_workers)
        ]
        
        print(f"\n평가 실행: {prompt_version}")
        print(f"명령어: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"Error: {result.stderr}")
                return None
            
            # 최신 평가 결과 파일 찾기
            eval_files = list(Path("data/prompt_evaluation").glob(f"evaluation_{prompt_version}_*.json"))
            if not eval_files:
                print("평가 결과 파일을 찾을 수 없습니다.")
                return None
                
            latest_file = max(eval_files, key=lambda x: x.stat().st_mtime)
            print(f"평가 완료: {latest_file}")
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            print(f"평가 실행 중 오류: {e}")
            return None
    
    def analyze_results(self, current_results: Dict, previous_results: Dict = None) -> Dict:
        """결과 분석 및 개선 방향 도출"""
        analysis = {
            "current_performance": {
                "success_rate": current_results["success_rate"],
                "avg_correct": current_results["average_correct_horses"],
                "error_rate": current_results.get("error_stats", {}).get("parse_error", 0) / current_results["total_races"] * 100
            }
        }
        
        # 이전 결과와 비교
        if previous_results:
            analysis["improvement"] = {
                "success_rate_change": current_results["success_rate"] - previous_results["success_rate"],
                "avg_correct_change": current_results["average_correct_horses"] - previous_results["average_correct_horses"]
            }
        
        # 실패 패턴 분석
        failure_patterns = self.analyze_failure_patterns_v3(current_results)
        analysis["failure_patterns"] = failure_patterns
        
        # 개선 제안 생성
        analysis["suggestions"] = self.generate_improvement_suggestions_v3(failure_patterns, current_results)
        
        return analysis
    
    def analyze_failure_patterns_v3(self, results: Dict) -> Dict:
        """v3 평가 결과에 맞춘 실패 패턴 분석"""
        patterns = {
            "low_odds_missed": 0,  # 낮은 배당률 말 놓침
            "high_odds_selected": 0,  # 높은 배당률 말 선택
            "perfect_miss": 0,  # 3마리 모두 놓침
            "partial_hit_1": 0,  # 1마리만 맞춤
            "partial_hit_2": 0,  # 2마리만 맞춤
            "confidence_mismatch": []  # 신뢰도와 실제 결과 불일치
        }
        
        for race in results["detailed_results"]:
            correct_count = race["reward"]["correct_count"]
            
            if correct_count == 0:
                patterns["perfect_miss"] += 1
            elif correct_count == 1:
                patterns["partial_hit_1"] += 1
            elif correct_count == 2:
                patterns["partial_hit_2"] += 1
                
            # 신뢰도 분석 (있는 경우)
            if "confidence" in race:
                confidence = race["confidence"]
                hit_rate = race["reward"]["hit_rate"]
                if abs(confidence - hit_rate) > 30:  # 30% 이상 차이
                    patterns["confidence_mismatch"].append({
                        "race_id": race["race_id"],
                        "confidence": confidence,
                        "actual_hit_rate": hit_rate
                    })
        
        # 놓친 말과 선택한 말의 배당률 분석은 
        # enriched 데이터를 읽어서 수행해야 함 (별도 구현 필요)
        
        return patterns
    
    def generate_improvement_suggestions_v3(self, patterns: Dict, results: Dict) -> List[Dict]:
        """v3에 맞춘 구체적인 개선 제안"""
        suggestions = []
        total_races = results["total_races"]
        
        # 완전 실패율이 높은 경우
        if patterns["perfect_miss"] > total_races * 0.3:
            suggestions.append({
                "type": "strategy_change",
                "target": "selection_logic",
                "action": "increase_conservative_approach",
                "reason": f"{patterns['perfect_miss']}/{total_races} 경주에서 완전 실패",
                "implementation": "상위 3개 인기마 기본 선택 후 조정"
            })
        
        # 부분 적중이 많은 경우 (개선 가능성 높음)
        partial_hits = patterns["partial_hit_1"] + patterns["partial_hit_2"]
        if partial_hits > total_races * 0.5:
            suggestions.append({
                "type": "fine_tuning",
                "target": "scoring_weights",
                "action": "optimize_composite_score",
                "reason": f"{partial_hits}/{total_races} 경주에서 부분 적중",
                "implementation": "배당률 가중치 상향, 기수/말 성적 가중치 미세 조정"
            })
        
        # 신뢰도 불일치가 심한 경우
        if len(patterns["confidence_mismatch"]) > total_races * 0.2:
            suggestions.append({
                "type": "calibration",
                "target": "confidence_calculation",
                "action": "recalibrate_confidence",
                "reason": f"{len(patterns['confidence_mismatch'])} 경주에서 신뢰도 불일치",
                "implementation": "신뢰도 계산 로직 개선"
            })
        
        # 평균 적중률 기반 제안
        avg_correct = results["average_correct_horses"]
        if avg_correct < 1.0:
            suggestions.append({
                "type": "major_revision",
                "target": "entire_strategy",
                "action": "switch_to_market_driven",
                "reason": f"평균 적중 {avg_correct:.2f}마리로 매우 낮음",
                "implementation": "시장 평가(배당률) 중심 전략으로 전환"
            })
        elif avg_correct < 1.5:
            suggestions.append({
                "type": "enhancement",
                "target": "data_usage",
                "action": "better_enriched_data_usage",
                "reason": f"평균 적중 {avg_correct:.2f}마리로 개선 필요",
                "implementation": "enriched 데이터의 기수승률, 말입상률 활용도 증가"
            })
        
        return suggestions
    
    def apply_improvements(self, current_prompt_path: Path, 
                          suggestions: List[Dict], 
                          new_version: str) -> Path:
        """개선사항을 프롬프트에 적용"""
        with open(current_prompt_path, 'r', encoding='utf-8') as f:
            prompt_content = f.read()
        
        # 개선 내역 기록
        improvement_log = f"\n## 개선 내역 ({new_version})\n"
        improvement_log += f"생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        for suggestion in suggestions:
            improvement_log += f"- **{suggestion['type']}**: {suggestion['reason']}\n"
            improvement_log += f"  - 대상: {suggestion['target']}\n"
            improvement_log += f"  - 액션: {suggestion['action']}\n"
            improvement_log += f"  - 구현: {suggestion['implementation']}\n\n"
            
            # 실제 프롬프트 수정
            if suggestion["type"] == "strategy_change" and "conservative" in suggestion["action"]:
                # 보수적 접근 강화
                prompt_content = self._apply_conservative_strategy(prompt_content)
                
            elif suggestion["type"] == "fine_tuning" and "composite_score" in suggestion["action"]:
                # 복합 점수 가중치 조정
                prompt_content = self._adjust_composite_weights(prompt_content)
                
            elif suggestion["type"] == "major_revision" and "market_driven" in suggestion["action"]:
                # 시장 중심 전략으로 전환
                prompt_content = self._apply_market_driven_strategy(prompt_content)
        
        # 버전 정보 업데이트
        prompt_content = re.sub(
            r'# 경마 삼복연승 예측.*?\n',
            f'# 경마 삼복연승 예측 프롬프트 {new_version}\n',
            prompt_content
        )
        
        # 개선 내역을 프롬프트 상단에 추가
        prompt_content = prompt_content.split('\n', 1)
        prompt_content = prompt_content[0] + '\n' + improvement_log + prompt_content[1]
        
        # 새 파일 저장
        new_prompt_path = self.working_dir / f"prompt_{new_version}.md"
        with open(new_prompt_path, 'w', encoding='utf-8') as f:
            f.write(prompt_content)
        
        # prompts 폴더에도 복사
        official_path = Path("prompts") / f"prediction-template-{new_version}.md"
        with open(official_path, 'w', encoding='utf-8') as f:
            f.write(prompt_content)
        
        print(f"\n개선된 프롬프트 생성:")
        print(f"  - 작업 경로: {new_prompt_path}")
        print(f"  - 공식 경로: {official_path}")
        
        return official_path
    
    def _apply_conservative_strategy(self, content: str) -> str:
        """보수적 전략 적용"""
        # 기존 전략 부분을 찾아서 교체
        conservative_strategy = """## 핵심 전략: 보수적 접근

1. **기본 선택**: 배당률 1-3위 말을 우선 선택
2. **교체 조건**: 다음 조건을 모두 만족할 때만 4위 이하 말로 교체
   - 기수 승률이 현저히 높음 (20% 이상)
   - 말의 최근 입상률이 50% 이상
   - 교체 대상 인기마에 명확한 약점 존재
3. **안전 장치**: 불확실한 경우 항상 인기마 선택"""
        
        # 전략 섹션 교체
        content = re.sub(
            r'## 핵심 전략.*?(?=\n##|\n\n##|\Z)',
            conservative_strategy,
            content,
            flags=re.DOTALL
        )
        return content
    
    def _adjust_composite_weights(self, content: str) -> str:
        """복합 점수 가중치 조정"""
        # 현재 v10.3의 가중치를 찾아서 조정
        new_weights = """### 복합 점수 계산 (조정됨)
- 배당률 점수: 50% (상향)
- 기수 승률: 25% (유지)  
- 말 입상률: 25% (하향)"""
        
        content = re.sub(
            r'### 복합 점수.*?(?=\n###|\n\n###|\Z)',
            new_weights,
            content,
            flags=re.DOTALL
        )
        return content
    
    def _apply_market_driven_strategy(self, content: str) -> str:
        """시장 중심 전략 적용"""
        market_strategy = """## 핵심 전략: 시장 평가 중심

### 기본 원칙
시장(배당률)이 가장 정확한 예측 지표임을 인정하고, 데이터는 보조 지표로만 활용

### 선택 프로세스
1. 배당률 순위 1-5위 확인
2. 1-3위는 자동 선택
3. 4-5위 중에서 다음 조건 충족 시 3위와 교체:
   - 기수 승률 15% 이상
   - 말 최근 3경주 중 1회 이상 입상
   - 3위 말에 데이터 부족 또는 부진 이력

### 예외 처리
- 배당률 0 (기권/제외): 완전 제외
- 신마/데이터 부족: 배당률만으로 평가"""
        
        # 전체 전략 교체
        content = re.sub(
            r'## 핵심 전략.*?(?=\n## 응답 형식|\Z)',
            market_strategy + "\n",
            content,
            flags=re.DOTALL
        )
        return content
    
    def run_improvement_cycle(self, initial_test_limit: int = 30, max_workers: int = 3):
        """전체 개선 사이클 실행"""
        current_prompt_path = self.base_prompt_path
        previous_results = None
        
        print(f"=== 재귀적 프롬프트 개선 v2 시작 ===")
        print(f"기본 프롬프트: {self.base_prompt_path}")
        print(f"기본 버전: v{self.base_version}")
        print(f"최대 반복: {self.max_iterations}회")
        print(f"테스트 경주 수: {initial_test_limit}개")
        print(f"병렬 처리: {max_workers}개")
        print("=" * 60)
        
        for iteration in range(self.max_iterations):
            # 버전 생성: v11.0, v11.1, v11.2...
            major_version = int(float(self.base_version)) + 1
            version = f"v{major_version}.{iteration}"
            
            print(f"\n\n{'='*60}")
            print(f"Iteration {iteration+1}/{self.max_iterations} - {version}")
            print(f"{'='*60}")
            
            # 1. 현재 프롬프트 평가
            evaluation_results = self.run_evaluation(
                version, 
                str(current_prompt_path), 
                initial_test_limit,
                max_workers
            )
            
            if not evaluation_results:
                print("평가 실패, 중단")
                break
            
            # 2. 결과 분석
            analysis = self.analyze_results(evaluation_results, previous_results)
            
            # 3. 이력 저장
            self.iteration_history.append({
                "iteration": iteration + 1,
                "version": version,
                "prompt_path": str(current_prompt_path),
                "results": evaluation_results,
                "analysis": analysis
            })
            
            # 4. 성능 출력
            print(f"\n📊 성능 요약:")
            print(f"  - 완전 적중률: {evaluation_results['success_rate']:.1f}%")
            print(f"  - 평균 적중 말: {evaluation_results['average_correct_horses']:.2f}/3")
            print(f"  - 에러율: {analysis['current_performance']['error_rate']:.1f}%")
            
            if previous_results:
                print(f"\n📈 개선 현황:")
                print(f"  - 적중률 변화: {analysis['improvement']['success_rate_change']:+.1f}%p")
                print(f"  - 평균 적중 변화: {analysis['improvement']['avg_correct_change']:+.2f}")
            
            # 5. 목표 달성 확인
            if evaluation_results['success_rate'] >= 40:
                print(f"\n🎯 목표 달성! (적중률 40% 이상)")
                break
            
            # 6. 개선 정체 확인
            if previous_results:
                if (analysis['improvement']['success_rate_change'] < 1.0 and
                    analysis['improvement']['avg_correct_change'] < 0.1):
                    print(f"\n⚠️ 개선 정체 감지")
                    if iteration >= 2:  # 최소 3회는 시도
                        print("충분한 시도 후 정체, 종료")
                        break
            
            # 7. 다음 반복을 위한 개선
            if iteration < self.max_iterations - 1:
                print(f"\n🔧 개선사항 적용:")
                
                # 개선 제안 출력
                for i, suggestion in enumerate(analysis["suggestions"][:3]):  # 상위 3개만
                    print(f"\n{i+1}. {suggestion['type'].upper()}")
                    print(f"   이유: {suggestion['reason']}")
                    print(f"   구현: {suggestion['implementation']}")
                
                # 새 버전 생성
                new_version = f"v{major_version}.{iteration+1}"
                new_prompt_path = self.apply_improvements(
                    current_prompt_path,
                    analysis["suggestions"],
                    new_version
                )
                
                current_prompt_path = new_prompt_path
                previous_results = evaluation_results
                
                # 다음 반복 전 대기
                print(f"\n⏳ 10초 후 다음 반복 시작...")
                time.sleep(10)
        
        # 최종 보고서 생성
        self.generate_final_report()
    
    def generate_final_report(self):
        """최종 개선 보고서 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.working_dir / f"improvement_report_{timestamp}.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# 프롬프트 재귀 개선 보고서 v2\n\n")
            f.write(f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"기본 프롬프트: {self.base_prompt_path}\n")
            f.write(f"총 반복: {len(self.iteration_history)}회\n\n")
            
            # 성능 변화 표
            f.write("## 성능 변화 추이\n\n")
            f.write("| Iteration | Version | 적중률 | 평균 적중 | 에러율 | 변화 |\n")
            f.write("|-----------|---------|--------|----------|--------|------|\n")
            
            for i, history in enumerate(self.iteration_history):
                results = history["results"]
                analysis = history["analysis"]
                change = ""
                if i > 0:
                    prev_rate = self.iteration_history[i-1]["results"]["success_rate"]
                    change = f"{results['success_rate'] - prev_rate:+.1f}%p"
                
                error_rate = analysis["current_performance"]["error_rate"]
                
                f.write(f"| {history['iteration']} | {history['version']} | "
                       f"{results['success_rate']:.1f}% | "
                       f"{results['average_correct_horses']:.2f} | "
                       f"{error_rate:.1f}% | {change} |\n")
            
            # 주요 개선사항
            f.write("\n## 주요 개선사항\n")
            for history in self.iteration_history:
                if history["analysis"].get("suggestions"):
                    f.write(f"\n### {history['version']}\n")
                    for suggestion in history["analysis"]["suggestions"][:3]:
                        f.write(f"\n**{suggestion['type']}**: {suggestion['reason']}\n")
                        f.write(f"- 대상: {suggestion['target']}\n")
                        f.write(f"- 구현: {suggestion['implementation']}\n")
            
            # 결론
            f.write("\n## 결론\n\n")
            
            final_results = self.iteration_history[-1]["results"]
            initial_results = self.iteration_history[0]["results"]
            
            f.write(f"### 성능 개선\n")
            f.write(f"- 초기 성능: {initial_results['success_rate']:.1f}% "
                   f"(평균 {initial_results['average_correct_horses']:.2f}마리)\n")
            f.write(f"- 최종 성능: {final_results['success_rate']:.1f}% "
                   f"(평균 {final_results['average_correct_horses']:.2f}마리)\n")
            f.write(f"- 전체 개선: {final_results['success_rate'] - initial_results['success_rate']:+.1f}%p\n\n")
            
            # 최적 버전
            best_iteration = max(self.iteration_history, 
                               key=lambda x: (x["results"]["success_rate"], 
                                            x["results"]["average_correct_horses"]))
            f.write(f"### 최고 성능 버전\n")
            f.write(f"- 버전: {best_iteration['version']}\n")
            f.write(f"- 적중률: {best_iteration['results']['success_rate']:.1f}%\n")
            f.write(f"- 평균 적중: {best_iteration['results']['average_correct_horses']:.2f}마리\n")
            f.write(f"- 프롬프트 경로: {best_iteration['prompt_path']}\n")
            
            # 권장사항
            f.write("\n### 권장사항\n")
            if final_results['success_rate'] >= 40:
                f.write("- ✅ 목표 성능 달성! 프로덕션 사용 가능\n")
            elif final_results['success_rate'] >= 30:
                f.write("- ⚠️ 준수한 성능이나 추가 개선 여지 있음\n")
            else:
                f.write("- ❌ 목표 미달성, 전략적 재검토 필요\n")
        
        print(f"\n\n📄 최종 보고서 생성: {report_path}")
        
        # 최적 프롬프트를 공식 위치에 복사
        best_prompt = Path(best_iteration['prompt_path'])
        if best_prompt.exists():
            final_prompt = Path("prompts") / f"prediction-template-optimized-v2.md"
            subprocess.run(['cp', str(best_prompt), str(final_prompt)])
            print(f"🏆 최적화된 프롬프트 저장: {final_prompt}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python recursive_prompt_improvement_v2.py <base_prompt_file> [test_limit] [max_iterations] [max_workers]")
        print("Example: python recursive_prompt_improvement_v2.py prompts/prediction-template-v10.3.md 30 5 3")
        sys.exit(1)
    
    base_prompt = sys.argv[1]
    test_limit = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    max_iterations = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    max_workers = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    
    # 파일 존재 확인
    if not Path(base_prompt).exists():
        print(f"Error: 프롬프트 파일을 찾을 수 없습니다: {base_prompt}")
        sys.exit(1)
    
    # 재귀 개선 실행
    improver = RecursivePromptImproverV2(base_prompt, max_iterations)
    improver.run_improvement_cycle(test_limit, max_workers)


if __name__ == "__main__":
    main()