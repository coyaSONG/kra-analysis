#!/usr/bin/env python3
"""
재귀적 프롬프트 개선 시스템 v4
- 상세한 개별 경주 분석
- 통합 복기 및 인사이트 도출
- 학습 기반 프롬프트 개선
- prompt-engineering-guide.md 원칙 준수
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import time
import re
from collections import defaultdict

class RecursivePromptImproverV4:
    def __init__(self, base_prompt_path: str, max_iterations: int = 5):
        self.base_prompt_path = Path(base_prompt_path)
        self.max_iterations = max_iterations
        self.working_dir = Path("data/recursive_improvement_v4")
        self.working_dir.mkdir(parents=True, exist_ok=True)
        
        self.iteration_history = []
        self.base_version = self._extract_version()
        
    def _extract_version(self) -> str:
        """프롬프트 파일명에서 버전 추출"""
        filename = self.base_prompt_path.stem
        match = re.search(r'v(\d+\.\d+)', filename)
        if match:
            return match.group(1)
        return "1.0"  # 기본값
    
    def get_available_dates(self) -> List[str]:
        """사용 가능한 경주 날짜 목록 반환"""
        dates = set()
        enriched_files = Path("data/races").glob("*/*/*/*/*_enriched.json")
        
        for file in enriched_files:
            filename = file.name
            match = re.search(r'_(\d{8})_', filename)
            if match:
                dates.add(match.group(1))
        
        return sorted(list(dates))
    
    def count_races_by_date(self, date: str) -> int:
        """특정 날짜의 경주 개수 반환"""
        pattern = f"data/races/*/*/{date}/*/*_enriched.json"
        files = list(Path(".").glob(pattern))
        return len(files)
    
    def run_evaluation_with_date(self, prompt_version: str, prompt_path: str, 
                                date_filter: str, max_workers: int = 3) -> Optional[Dict]:
        """날짜 필터를 적용한 평가 실행"""
        
        # 임시 평가 스크립트 생성 (날짜 필터 적용)
        temp_evaluator = self.working_dir / f"evaluate_filtered_{prompt_version}.py"
        self._create_filtered_evaluator(temp_evaluator, date_filter)
        
        cmd = [
            'python3', str(temp_evaluator),
            prompt_version, prompt_path, str(max_workers)
        ]
        
        if date_filter == "all":
            available_dates = self.get_available_dates()
            total_races = sum(self.count_races_by_date(d) for d in available_dates)
            print(f"\n평가 실행: {prompt_version}")
            print(f"  - 대상: 모든 경주")
            print(f"  - 총 경주 수: {total_races}개")
            print(f"  - 병렬 처리: {max_workers}개")
            print(f"  - 예상 시간: {total_races / max_workers * 5:.0f}초 ~ {total_races / max_workers * 10:.0f}초")
        else:
            race_count = self.count_races_by_date(date_filter)
            print(f"\n평가 실행: {prompt_version}")
            print(f"  - 날짜: {date_filter}")
            print(f"  - 경주 수: {race_count}개")
            print(f"  - 병렬 처리: {max_workers}개")
        
        print("\n평가 진행 중...")
        print("-" * 60)
        
        try:
            # 실시간 출력을 위해 capture_output=False로 변경
            result = subprocess.run(cmd, capture_output=False, text=True)
            
            if result.returncode != 0:
                print(f"Error: 평가 실행 실패 (return code: {result.returncode})")
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
        finally:
            # 임시 파일 삭제
            if temp_evaluator.exists():
                temp_evaluator.unlink()
    
    def analyze_individual_race(self, race_result: Dict, race_data: Optional[Dict] = None) -> Dict:
        """개별 경주에 대한 상세 분석"""
        # 예측 결과가 없는 경우 처리
        if race_result.get("prediction") is None or "predicted" not in race_result:
            return {
                "race_id": race_result["race_id"],
                "error": "No prediction available",
                "error_type": race_result.get("error_type", "unknown")
            }
        
        analysis = {
            "race_id": race_result["race_id"],
            "predicted": race_result["predicted"],
            "actual": race_result["actual"],
            "correct_count": race_result["reward"]["correct_count"],
            "hit_rate": race_result["reward"]["hit_rate"]
        }
        
        # 맞춘 말과 놓친 말 분석
        predicted_set = set(race_result["predicted"])
        actual_set = set(race_result["actual"])
        
        analysis["hits"] = list(predicted_set & actual_set)  # 맞춘 말
        analysis["misses"] = {
            "selected_but_wrong": list(predicted_set - actual_set),  # 선택했지만 틀린 말
            "missed_winners": list(actual_set - predicted_set)       # 놓친 정답 말
        }
        
        # 놓친 이유 분석 (enriched 데이터가 있다면)
        if race_data:
            analysis["why_missed"] = self._analyze_miss_reasons(
                analysis["misses"]["missed_winners"], 
                race_data, 
                race_result
            )
            analysis["why_wrong_selection"] = self._analyze_wrong_selections(
                analysis["misses"]["selected_but_wrong"],
                race_data,
                race_result
            )
        
        # 예측 전략 분석
        if "reasoning" in race_result:
            analysis["strategy_used"] = self._extract_strategy(race_result["reasoning"])
        
        return analysis
    
    def _analyze_miss_reasons(self, missed_horses: List[int], race_data: Dict, race_result: Dict) -> Dict:
        """놓친 말들의 특성 분석"""
        reasons = {}
        
        # race_data에서 말 정보 추출 (구조에 따라 수정 필요)
        horses = race_data.get("horses", [])
        
        for horse_no in missed_horses:
            horse_info = next((h for h in horses if h.get("chulNo") == horse_no), None)
            if horse_info:
                # 배당률 순위
                odds_rank = self._get_odds_rank(horse_info, horses)
                
                reason_parts = []
                if odds_rank <= 3:
                    reason_parts.append(f"인기 {odds_rank}위")
                elif odds_rank >= 8:
                    reason_parts.append(f"비인기 {odds_rank}위")
                
                # 기수 승률
                if "jkDetail" in horse_info:
                    jk_win_rate = horse_info["jkDetail"].get("winRate", 0)
                    if jk_win_rate > 20:
                        reason_parts.append(f"기수승률 {jk_win_rate:.1f}%")
                
                reasons[horse_no] = " / ".join(reason_parts) if reason_parts else "데이터 부족"
        
        return reasons
    
    def _analyze_wrong_selections(self, wrong_horses: List[int], race_data: Dict, race_result: Dict) -> Dict:
        """잘못 선택한 말들의 특성 분석"""
        reasons = {}
        
        horses = race_data.get("horses", [])
        
        for horse_no in wrong_horses:
            horse_info = next((h for h in horses if h.get("chulNo") == horse_no), None)
            if horse_info:
                reason_parts = []
                
                # 과대평가 요인 찾기
                odds_rank = self._get_odds_rank(horse_info, horses)
                if odds_rank > 5:
                    reason_parts.append(f"배당률 {odds_rank}위로 비인기")
                
                # 최근 성적
                if "hrDetail" in horse_info:
                    recent_rank = horse_info["hrDetail"].get("recentAvgRank", 99)
                    if recent_rank > 5:
                        reason_parts.append(f"최근 평균 {recent_rank:.1f}위로 부진")
                
                reasons[horse_no] = " / ".join(reason_parts) if reason_parts else "선택 근거 불명"
        
        return reasons
    
    def _get_odds_rank(self, horse: Dict, all_horses: List[Dict]) -> int:
        """말의 배당률 순위 계산"""
        valid_horses = [h for h in all_horses if h.get("winOdds", 0) > 0]
        sorted_horses = sorted(valid_horses, key=lambda x: x["winOdds"])
        
        for idx, h in enumerate(sorted_horses):
            if h.get("chulNo") == horse.get("chulNo"):
                return idx + 1
        return 99
    
    def _extract_strategy(self, reasoning: str) -> str:
        """추론 과정에서 전략 추출"""
        # 간단한 키워드 기반 전략 추출
        if "인기마" in reasoning or "배당률" in reasoning:
            return "배당률 중심"
        elif "기수" in reasoning:
            return "기수 중심"
        elif "최근" in reasoning:
            return "최근 성적 중심"
        return "복합 전략"
    
    def integrate_iteration_results(self, evaluation_results: Dict, individual_analyses: List[Dict]) -> Dict:
        """이터레이션 결과 통합 복기"""
        
        # 전체 통계
        total_races = len(individual_analyses)
        total_hits = sum(len(a["hits"]) for a in individual_analyses)
        
        # 패턴 분석
        success_patterns = []
        failure_patterns = []
        
        for analysis in individual_analyses:
            if analysis["correct_count"] == 3:  # 완전 성공
                success_patterns.append(analysis)
            elif analysis["correct_count"] == 0:  # 완전 실패
                failure_patterns.append(analysis)
        
        # 공통 패턴 찾기
        missed_horses_stats = defaultdict(int)
        wrong_selection_stats = defaultdict(int)
        
        for analysis in individual_analyses:
            if "why_missed" in analysis:
                for reason in analysis["why_missed"].values():
                    missed_horses_stats[reason] += 1
            if "why_wrong_selection" in analysis:
                for reason in analysis["why_wrong_selection"].values():
                    wrong_selection_stats[reason] += 1
        
        # 강점과 약점 도출
        strengths = []
        weaknesses = []
        
        # 강점 분석
        if evaluation_results["average_correct_horses"] > 1.5:
            strengths.append(f"평균 {evaluation_results['average_correct_horses']:.1f}마리 적중")
        
        if len(success_patterns) > 0:
            strengths.append(f"{len(success_patterns)}개 경주 완전 적중")
        
        # 약점 분석
        top_missed_reasons = sorted(missed_horses_stats.items(), key=lambda x: x[1], reverse=True)[:3]
        for reason, count in top_missed_reasons:
            if count > total_races * 0.2:  # 20% 이상에서 발생
                weaknesses.append(f"{reason} 말들을 자주 놓침 ({count}회)")
        
        # 인사이트 도출
        insights = {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "patterns": {
                "success_rate_by_strategy": self._analyze_strategy_success(individual_analyses),
                "common_miss_patterns": dict(top_missed_reasons[:5]),
                "common_wrong_patterns": dict(sorted(wrong_selection_stats.items(), 
                                                    key=lambda x: x[1], reverse=True)[:5])
            },
            "recommendations": self._generate_recommendations(
                strengths, weaknesses, missed_horses_stats, wrong_selection_stats
            )
        }
        
        return insights
    
    def _analyze_strategy_success(self, analyses: List[Dict]) -> Dict:
        """전략별 성공률 분석"""
        strategy_stats = defaultdict(lambda: {"total": 0, "success": 0})
        
        for analysis in analyses:
            if "strategy_used" in analysis:
                strategy = analysis["strategy_used"]
                strategy_stats[strategy]["total"] += 1
                if analysis["correct_count"] >= 2:  # 2마리 이상 맞춤을 성공으로
                    strategy_stats[strategy]["success"] += 1
        
        # 성공률 계산
        success_rates = {}
        for strategy, stats in strategy_stats.items():
            if stats["total"] > 0:
                success_rates[strategy] = stats["success"] / stats["total"] * 100
        
        return success_rates
    
    def _generate_recommendations(self, strengths: List[str], weaknesses: List[str],
                                 missed_stats: Dict, wrong_stats: Dict) -> List[str]:
        """구체적인 개선 권고사항 생성"""
        recommendations = []
        
        # 놓친 말 패턴 기반 권고
        if "인기" in str(missed_stats):
            recommendations.append("인기마 필터링 기준 완화 필요")
        
        if any("기수승률" in reason for reason in missed_stats):
            recommendations.append("기수 승률 가중치 상향 조정")
        
        # 잘못 선택한 말 패턴 기반 권고
        if any("비인기" in str(reason) for reason in wrong_stats):
            recommendations.append("비인기마 선택 기준 강화")
        
        if any("부진" in str(reason) for reason in wrong_stats):
            recommendations.append("최근 성적 가중치 상향")
        
        # 전반적인 성능 기반 권고
        if len(weaknesses) > len(strengths):
            recommendations.append("전체적인 전략 재검토 필요")
        
        return recommendations
    
    def create_improved_prompt(self, current_prompt_path: Path, insights: Dict, 
                             new_version: str, evaluation_results: Dict) -> Path:
        """인사이트 기반으로 개선된 프롬프트 생성"""
        
        # 현재 프롬프트 읽기
        with open(current_prompt_path, 'r', encoding='utf-8') as f:
            current_content = f.read()
        
        # prompt-engineering-guide.md 원칙에 따른 새 프롬프트 생성
        improved_prompt = self._build_improved_prompt(
            current_content, insights, evaluation_results, new_version
        )
        
        # 새 파일 저장
        new_prompt_path = self.working_dir / f"prompt_{new_version}.md"
        with open(new_prompt_path, 'w', encoding='utf-8') as f:
            f.write(improved_prompt)
        
        # prompts 폴더에도 복사
        official_path = Path("prompts") / f"prediction-template-{new_version}.md"
        with open(official_path, 'w', encoding='utf-8') as f:
            f.write(improved_prompt)
        
        print(f"\n개선된 프롬프트 생성:")
        print(f"  - 작업 경로: {new_prompt_path}")
        print(f"  - 공식 경로: {official_path}")
        
        return official_path
    
    def _build_improved_prompt(self, current_content: str, insights: Dict, 
                              evaluation_results: Dict, version: str) -> str:
        """prompt-engineering-guide.md 원칙에 따른 프롬프트 구성"""
        
        # 성공/실패 사례 수집
        success_examples = self._collect_examples(evaluation_results, "success")
        failure_examples = self._collect_examples(evaluation_results, "failure")
        
        prompt = f"""# 경마 삼복연승 예측 프롬프트 {version}

<context>
한국 경마 데이터를 분석하여 1-3위에 들어올 3마리를 예측하는 작업입니다.
이전 버전 성능: 평균 적중 {evaluation_results['average_correct_horses']:.1f}마리, 완전 적중률 {evaluation_results['success_rate']:.1f}%
</context>

<role>
당신은 10년 이상의 경험을 가진 한국 경마 예측 전문가입니다. 
통계적 분석과 경마 도메인 지식을 결합하여 정확한 예측을 제공합니다.
</role>

<task>
제공된 경주 데이터를 분석하여 1-3위에 들어올 가능성이 가장 높은 3마리를 예측하세요.
</task>

<requirements>
1. 기권/제외(win_odds=0) 말은 반드시 제외
2. enriched 데이터의 모든 정보 활용 (말/기수/조교사 상세정보)
3. 다음 요소들을 종합적으로 고려:
   - 배당률 (시장 평가)
   - 기수 승률 및 최근 성적
   - 말의 최근 입상률
   - 부담중량 변화
   - 경주 조건 적합성

{self._generate_improvement_rules(insights)}
</requirements>

<analysis_steps>
1. 유효한 출주마 확인 (win_odds > 0)
2. 각 말의 핵심 지표 추출:
   - 배당률 순위
   - 기수 승률 (jkDetail.winRate)
   - 말 입상률 (hrDetail.placeRate)
   - 최근 성적 트렌드
3. 복합 점수 계산:
   - 배당률 점수: 40%
   - 기수 성적: 30%
   - 말 성적: 30%
4. 상위 3마리 선정
5. 선정 근거 검증
</analysis_steps>

<output_format>
```json
{{
  "predicted": [출전번호1, 출전번호2, 출전번호3],
  "confidence": 60-90 사이의 신뢰도,
  "brief_reason": "핵심 선정 이유 (한글 20자 이내)"
}}
```
</output_format>

<examples>
{self._format_examples(success_examples, failure_examples)}
</examples>

<important_notes>
- 인기마(1-3위)를 무시하지 마세요. 통계적으로 50% 이상이 입상합니다.
- 데이터가 부족한 신마는 배당률을 더 신뢰하세요.
- 극단적인 비인기마(10위 이하)는 특별한 이유가 없다면 피하세요.
</important_notes>
"""
        
        return prompt
    
    def _generate_improvement_rules(self, insights: Dict) -> str:
        """인사이트 기반 개선 규칙 생성"""
        rules = []
        
        # 약점 기반 규칙
        for weakness in insights.get("weaknesses", []):
            if "인기" in weakness and "놓침" in weakness:
                rules.append("4. 인기 1-3위 말은 특별한 결격 사유가 없는 한 포함")
            elif "기수승률" in weakness:
                rules.append("5. 기수 승률 15% 이상인 말 우선 고려")
        
        # 추천사항 기반 규칙
        for rec in insights.get("recommendations", []):
            if "비인기마 선택 기준 강화" in rec:
                rules.append("6. 배당률 8위 이하는 명확한 강점이 있을 때만 선택")
        
        return "\n".join(rules) if rules else ""
    
    def _collect_examples(self, evaluation_results: Dict, example_type: str) -> List[Dict]:
        """성공/실패 사례 수집"""
        examples = []
        
        for race in evaluation_results.get("detailed_results", []):
            # 예측이 없거나 reward가 없는 경우 건너뛰기
            if race.get("prediction") is None or "reward" not in race or "correct_count" not in race["reward"]:
                continue
                
            if example_type == "success" and race["reward"]["correct_count"] == 3:
                examples.append({
                    "race_id": race["race_id"],
                    "predicted": race["predicted"],
                    "actual": race["actual"],
                    "reason": race.get("brief_reason", "")
                })
            elif example_type == "failure" and race["reward"]["correct_count"] == 0:
                examples.append({
                    "race_id": race["race_id"],
                    "predicted": race["predicted"],
                    "actual": race["actual"],
                    "reason": race.get("brief_reason", "")
                })
        
        return examples[:2]  # 각각 최대 2개씩
    
    def _format_examples(self, success_examples: List[Dict], failure_examples: List[Dict]) -> str:
        """예시 포맷팅"""
        formatted = "### 성공 사례\n"
        
        for ex in success_examples:
            formatted += f"""
입력: [경주 데이터]
출력: {{"predicted": {ex['predicted']}, "confidence": 85, "brief_reason": "{ex.get('reason', '인기마 중심 선택')}"}}
결과: ✅ 정답 {ex['actual']}
"""
        
        formatted += "\n### 실패 사례 (피해야 할 패턴)\n"
        
        for ex in failure_examples:
            formatted += f"""
입력: [경주 데이터]
출력: {{"predicted": {ex['predicted']}, "confidence": 70, "brief_reason": "{ex.get('reason', '고배당 도전')}"}}
결과: ❌ 정답 {ex['actual']} (분석: 인기마 무시)
"""
        
        return formatted
    
    def _create_filtered_evaluator(self, output_path: Path, date_filter: str):
        """날짜 필터가 적용된 평가 스크립트 생성"""
        # evaluate_prompt_v3.py 읽기
        with open("scripts/evaluation/evaluate_prompt_v3.py", 'r', encoding='utf-8') as f:
            content = f.read()
        
        # find_test_races 메서드 수정
        if date_filter != "all":
            # 날짜 필터 추가
            filter_code = f"""
        # 날짜 필터 적용
        enriched_files = [f for f in enriched_files if '/{date_filter}/' in f]
"""
            content = content.replace(
                'enriched_files = sorted(glob.glob(enriched_pattern))',
                f'enriched_files = sorted(glob.glob(enriched_pattern)){filter_code}'
            )
        
        # main 함수 수정 - test_limit를 None으로 설정
        new_main = '''def main():
    if len(sys.argv) < 3:
        print("Usage: python evaluate_prompt_filtered.py <prompt_version> <prompt_file> [max_workers]")
        sys.exit(1)
    
    prompt_version = sys.argv[1]
    prompt_file = sys.argv[2]
    max_workers = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    
    # 평가 실행
    evaluator = PromptEvaluatorV3(prompt_version, prompt_file)
    results = evaluator.evaluate_all_parallel(test_limit=None, max_workers=max_workers)


if __name__ == "__main__":
    main()'''
        
        # main 함수 전체를 교체
        content = re.sub(
            r'def main\(\):.*?if __name__ == "__main__":\s*main\(\)',
            new_main,
            content,
            flags=re.DOTALL
        )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def run_improvement_cycle(self, date_filter: str = "all", max_workers: int = 3):
        """전체 개선 사이클 실행"""
        current_prompt_path = self.base_prompt_path
        previous_results = None
        
        # 날짜 정보 출력
        if date_filter == "all":
            available_dates = self.get_available_dates()
            total_races = sum(self.count_races_by_date(d) for d in available_dates)
            print(f"=== 재귀적 프롬프트 개선 v4 시작 ===")
            print(f"기본 프롬프트: {self.base_prompt_path}")
            print(f"기본 버전: v{self.base_version}")
            print(f"최대 반복: {self.max_iterations}회")
            print(f"테스트 경주: 모든 경주 ({total_races}개)")
            print(f"사용 가능한 날짜: {', '.join(available_dates)}")
        else:
            race_count = self.count_races_by_date(date_filter)
            print(f"=== 재귀적 프롬프트 개선 v4 시작 ===")
            print(f"기본 프롬프트: {self.base_prompt_path}")
            print(f"기본 버전: v{self.base_version}")
            print(f"최대 반복: {self.max_iterations}회")
            print(f"테스트 날짜: {date_filter}")
            print(f"테스트 경주: {race_count}개")
        
        print(f"병렬 처리: {max_workers}개")
        print("=" * 60)
        
        for iteration in range(self.max_iterations):
            # 버전 생성
            major_version = int(float(self.base_version)) + 1
            version = f"v{major_version}.{iteration}"
            
            print(f"\n\n{'='*60}")
            print(f"Iteration {iteration+1}/{self.max_iterations} - {version}")
            print(f"{'='*60}")
            
            # 1. 현재 프롬프트 평가
            evaluation_results = self.run_evaluation_with_date(
                version, 
                str(current_prompt_path), 
                date_filter,
                max_workers
            )
            
            if not evaluation_results:
                print("평가 실패, 중단")
                break
            
            # 2. 개별 경주 상세 분석
            print("\n📊 개별 경주 분석 중...")
            individual_analyses = []
            
            for race_result in evaluation_results.get("detailed_results", []):
                # enriched 데이터 로드 (가능한 경우)
                race_data = self._load_race_data(race_result["race_id"])
                
                analysis = self.analyze_individual_race(race_result, race_data)
                # 오류가 있는 경주는 분석에서 제외
                if "error" not in analysis:
                    individual_analyses.append(analysis)
            
            # 3. 통합 복기 및 인사이트 도출
            print("\n🔍 이터레이션 복기 중...")
            insights = self.integrate_iteration_results(evaluation_results, individual_analyses)
            
            # 4. 결과 출력
            print(f"\n📊 성능 요약:")
            print(f"  - 평가 경주 수: {evaluation_results['total_races']}개")
            print(f"  - 완전 적중률: {evaluation_results['success_rate']:.1f}%")
            print(f"  - 평균 적중 말: {evaluation_results['average_correct_horses']:.2f}/3")
            
            print(f"\n💪 강점:")
            for strength in insights["strengths"][:3]:
                print(f"  - {strength}")
            
            print(f"\n⚠️ 약점:")
            for weakness in insights["weaknesses"][:3]:
                print(f"  - {weakness}")
            
            print(f"\n💡 권고사항:")
            for rec in insights["recommendations"][:3]:
                print(f"  - {rec}")
            
            # 5. 이력 저장
            self.iteration_history.append({
                "iteration": iteration + 1,
                "version": version,
                "prompt_path": str(current_prompt_path),
                "results": evaluation_results,
                "insights": insights,
                "individual_analyses": individual_analyses,
                "date_filter": date_filter
            })
            
            # 6. 목표 달성 확인
            if evaluation_results['success_rate'] >= 70:
                print(f"\n🎯 목표 달성! (적중률 70% 이상)")
                break
            
            # 7. 개선 정체 확인
            if previous_results:
                improvement = evaluation_results['success_rate'] - previous_results['success_rate']
                if improvement < 1.0 and iteration >= 2:
                    print(f"\n⚠️ 개선 정체 (개선폭 {improvement:.1f}%p)")
                    print("충분한 시도 후 정체, 종료")
                    break
            
            # 8. 다음 반복을 위한 개선
            if iteration < self.max_iterations - 1:
                print(f"\n🔧 프롬프트 개선 중...")
                
                # 새 버전 생성
                new_version = f"v{major_version}.{iteration+1}"
                new_prompt_path = self.create_improved_prompt(
                    current_prompt_path,
                    insights,
                    new_version,
                    evaluation_results
                )
                
                current_prompt_path = new_prompt_path
                previous_results = evaluation_results
                
                # 다음 반복 전 대기
                print(f"\n⏳ 10초 후 다음 반복 시작...")
                time.sleep(10)
        
        # 최종 보고서 생성
        self.generate_final_report()
    
    def _load_race_data(self, race_id: str) -> Optional[Dict]:
        """경주 ID로 enriched 데이터 로드"""
        try:
            # race_id 형식: race_1_20250601_3
            parts = race_id.split('_')
            date = parts[2]
            race_no = parts[3]
            
            # enriched 파일 찾기
            pattern = f"data/races/*/*/*/{date}/*/*{race_id}*enriched.json"
            files = list(Path(".").glob(pattern))
            
            if files:
                with open(files[0], 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # API 응답에서 실제 데이터 추출
                    if 'response' in data and 'body' in data['response']:
                        items = data['response']['body']['items']['item']
                        return {"horses": items if isinstance(items, list) else [items]}
            
        except Exception as e:
            print(f"경주 데이터 로드 오류 ({race_id}): {e}")
        
        return None
    
    def generate_final_report(self):
        """최종 개선 보고서 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.working_dir / f"improvement_report_{timestamp}.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# 프롬프트 재귀 개선 보고서 v4\n\n")
            f.write(f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"기본 프롬프트: {self.base_prompt_path}\n")
            f.write(f"총 반복: {len(self.iteration_history)}회\n")
            
            if self.iteration_history:
                f.write(f"테스트 조건: {self.iteration_history[0]['date_filter']}\n\n")
            
            # 성능 변화 표
            f.write("## 성능 변화 추이\n\n")
            f.write("| Iteration | Version | 경주 수 | 적중률 | 평균 적중 | 주요 개선사항 |\n")
            f.write("|-----------|---------|---------|--------|----------|---------------|\n")
            
            for history in self.iteration_history:
                results = history["results"]
                insights = history["insights"]
                main_improvement = insights["recommendations"][0] if insights["recommendations"] else "없음"
                
                f.write(f"| {history['iteration']} | {history['version']} | "
                       f"{results['total_races']} | "
                       f"{results['success_rate']:.1f}% | "
                       f"{results['average_correct_horses']:.2f} | "
                       f"{main_improvement} |\n")
            
            # 상세 인사이트
            f.write("\n## 각 이터레이션 상세 분석\n")
            for history in self.iteration_history:
                f.write(f"\n### {history['version']}\n")
                
                insights = history["insights"]
                f.write("\n**강점:**\n")
                for strength in insights["strengths"]:
                    f.write(f"- {strength}\n")
                
                f.write("\n**약점:**\n")
                for weakness in insights["weaknesses"]:
                    f.write(f"- {weakness}\n")
                
                f.write("\n**주요 패턴:**\n")
                if "common_miss_patterns" in insights["patterns"]:
                    for pattern, count in list(insights["patterns"]["common_miss_patterns"].items())[:3]:
                        f.write(f"- {pattern}: {count}회\n")
            
            # 결론
            f.write("\n## 결론\n\n")
            
            if self.iteration_history:
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
                
                # 핵심 교훈
                f.write("\n### 핵심 교훈\n")
                all_recommendations = set()
                for history in self.iteration_history:
                    all_recommendations.update(history["insights"]["recommendations"])
                
                for rec in list(all_recommendations)[:5]:
                    f.write(f"- {rec}\n")
        
        print(f"\n\n📄 최종 보고서 생성: {report_path}")
        
        # 최적 프롬프트를 공식 위치에 복사
        if self.iteration_history:
            best_iteration = max(self.iteration_history, 
                               key=lambda x: (x["results"]["success_rate"], 
                                            x["results"]["average_correct_horses"]))
            best_prompt = Path(best_iteration['prompt_path'])
            if best_prompt.exists():
                final_prompt = Path("prompts") / f"prediction-template-optimized-v4.md"
                subprocess.run(['cp', str(best_prompt), str(final_prompt)])
                print(f"🏆 최적화된 프롬프트 저장: {final_prompt}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python recursive_prompt_improvement_v4.py <base_prompt_file> [date_filter] [max_iterations] [max_workers]")
        print("\nExamples:")
        print("  모든 경주: python recursive_prompt_improvement_v4.py prompts/base-prompt.md all 5 3")
        print("  특정 날짜: python recursive_prompt_improvement_v4.py prompts/base-prompt.md 20250601 5 3")
        print("\n사용 가능한 날짜:")
        
        # 사용 가능한 날짜 표시
        improver = RecursivePromptImproverV4("dummy")
        dates = improver.get_available_dates()
        for date in dates:
            count = improver.count_races_by_date(date)
            print(f"  - {date}: {count}개 경주")
        
        sys.exit(1)
    
    base_prompt = sys.argv[1]
    date_filter = sys.argv[2] if len(sys.argv) > 2 else "all"
    max_iterations = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    max_workers = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    
    # 파일 존재 확인
    if not Path(base_prompt).exists():
        print(f"Error: 프롬프트 파일을 찾을 수 없습니다: {base_prompt}")
        sys.exit(1)
    
    # 재귀 개선 실행
    improver = RecursivePromptImproverV4(base_prompt, max_iterations)
    improver.run_improvement_cycle(date_filter, max_workers)


if __name__ == "__main__":
    main()