#!/usr/bin/env python3
"""
프롬프트 재귀 개선을 위한 평가 시스템 v2
- enriched 데이터 사용
- 병렬 처리 지원
- 향상된 에러 분석
- Claude CLI를 통한 예측 실행
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import glob
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from collections import defaultdict

# subprocess는 이미 import되어 있음

class PromptEvaluatorV2:
    def __init__(self, prompt_version: str, prompt_path: str):
        self.prompt_version = prompt_version
        self.prompt_path = prompt_path
        self.results_dir = Path("data/prompt_evaluation")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.api_lock = threading.Semaphore(3)  # API 동시 호출 제한
        self.error_stats = defaultdict(int)  # 에러 통계
        
    def find_test_races(self, limit: int = None) -> List[Dict[str, Path]]:
        """테스트할 경주 파일 찾기 (enriched 데이터 우선)"""
        race_files = []
        
        # enriched 파일 찾기
        enriched_pattern = "data/races/*/*/*/*/*_enriched.json"
        enriched_files = sorted(glob.glob(enriched_pattern))
        
        for enriched_file in enriched_files:
            # 해당 경주의 결과 파일이 있는지 확인
            path_parts = enriched_file.split('/')
            # race_1_20250608_1_enriched.json -> race_1
            race_prefix = '_'.join(path_parts[-1].split('_')[0:2])
            race_date = path_parts[-1].split('_')[2]
            race_no = path_parts[-1].split('_')[3].replace('_enriched.json', '')
            
            # meet 정보 추출 (경로에서)
            meet = path_parts[-2]  # seoul, jeju, busan 등
            meet_map = {'seoul': '서울', 'jeju': '제주', 'busan': '부산경남'}
            
            race_files.append({
                'enriched_file': Path(enriched_file),
                'race_id': f"{race_prefix}_{race_date}_{race_no}",
                'race_date': race_date,
                'race_no': race_no,
                'meet': meet_map.get(meet, '서울')
            })
        
        if limit:
            race_files = race_files[:limit]
            
        print(f"테스트할 경주: {len(race_files)}개 (enriched 데이터)")
        return race_files
    
    def load_race_data(self, race_info: Dict) -> Optional[Dict]:
        """enriched 파일에서 경주 데이터 로드"""
        try:
            with open(race_info['enriched_file'], 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # API 응답 형식에서 실제 데이터 추출
            if 'response' in data and 'body' in data['response']:
                items = data['response']['body']['items']['item']
                
                # 데이터 정리
                horses = []
                for item in items:
                    # 기권/제외 말 필터링
                    if item.get('winOdds', 999) == 0:
                        print(f"  - {item['chulNo']}번 {item['hrName']} 기권/제외 - 스킵")
                        continue
                    
                    horse = {
                        'chulNo': item['chulNo'],
                        'hrName': item['hrName'],
                        'hrNo': item['hrNo'],
                        'jkName': item['jkName'],
                        'jkNo': item['jkNo'],
                        'trName': item['trName'],
                        'trNo': item['trNo'],
                        'wgBudam': item['wgBudam'],
                        'winOdds': item['winOdds'],
                        'plcOdds': item['plcOdds'],
                        'rating': item.get('rating', 0),
                        'rank': item.get('rank', ''),
                        'age': item.get('age', 0),
                        'sex': item.get('sex', ''),
                        # 보강된 데이터 추가
                        'hrDetail': item.get('hrDetail', {}),
                        'jkDetail': item.get('jkDetail', {}),
                        'trDetail': item.get('trDetail', {})
                    }
                    
                    # 결과 필드 제거 (예측용)
                    if 'ord' in horse:
                        del horse['ord']
                    if 'rcTime' in horse:
                        del horse['rcTime']
                    
                    horses.append(horse)
                
                # 경주 정보 구성
                race_data = {
                    'raceInfo': {
                        'rcDate': items[0]['rcDate'],
                        'rcNo': items[0]['rcNo'],
                        'rcName': items[0].get('rcName', ''),
                        'rcDist': items[0]['rcDist'],
                        'track': items[0].get('track', ''),
                        'weather': items[0].get('weather', ''),
                        'ageCond': items[0].get('ageCond', ''),
                        'budam': items[0].get('budam', ''),
                        'meet': items[0]['meet']
                    },
                    'horses': horses
                }
                
                return race_data
            
            return None
            
        except Exception as e:
            print(f"데이터 로드 오류: {e}")
            return None
    
    def run_prediction_with_retry(self, race_data: Dict, race_id: str, max_retries: int = 1) -> Tuple[Optional[Dict], str]:
        """재시도 기능이 있는 예측 실행"""
        for attempt in range(max_retries + 1):
            result, error_type = self._run_single_prediction(race_data, race_id)
            if result is not None:
                return result, error_type
            
            if attempt < max_retries:
                print(f"  재시도 {attempt + 1}/{max_retries}...")
                time.sleep(2)
        
        return None, error_type
    
    def _run_single_prediction(self, race_data: Dict, race_id: str) -> Tuple[Optional[Dict], str]:
        """단일 예측 실행"""
        error_type = "success"
        start_time = time.time()
        
        # 프롬프트 읽기
        with open(self.prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
        
        # 프롬프트 구성
        prompt = f"""{prompt_template}

경주 데이터:
```json
{json.dumps(race_data, ensure_ascii=False, indent=2)}
```

다음 JSON 형식으로 예측 결과를 제공하세요:
{{
  "selected_horses": [
    {{"chulNo": 번호, "hrName": "말이름"}},
    {{"chulNo": 번호, "hrName": "말이름"}},
    {{"chulNo": 번호, "hrName": "말이름"}}
  ],
  "confidence": 70,
  "reasoning": "1위 인기마 포함, 기수 성적 우수"
}}"""
        
        try:
            # Claude CLI 실행
            with self.api_lock:  # API 동시 호출 제한
                cmd = ['claude', '-p', prompt]
                result = subprocess.run(cmd, 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=120)
            
            execution_time = time.time() - start_time
            
            if result.returncode != 0:
                error_type = "claude_error"
                self.error_stats[error_type] += 1
                print(f"Error running claude: {result.stderr}")
                return None, error_type
            
            # 결과 파싱
            output = result.stdout.strip()
            
            # JSON 부분만 추출
            import re
            
            # 패턴 1: 코드블록 내 JSON
            code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', output, re.DOTALL)
            if code_block_match:
                try:
                    prediction = json.loads(code_block_match.group(1))
                    prediction['execution_time'] = execution_time
                    return prediction, error_type
                except:
                    error_type = "json_parse_error"
            
            # 패턴 2: 일반 JSON
            json_match = re.search(r'\{.*\}', output, re.DOTALL)
            if json_match:
                try:
                    prediction = json.loads(json_match.group())
                    prediction['execution_time'] = execution_time
                    return prediction, error_type
                except:
                    error_type = "json_parse_error"
            
            self.error_stats[error_type] += 1
            print(f"Failed to parse prediction: {output[:200]}...")
            return None, error_type
                
        except subprocess.TimeoutExpired:
            error_type = "timeout"
            self.error_stats[error_type] += 1
            print(f"Timeout for race {race_id}")
            return None, error_type
        except Exception as e:
            error_type = "unknown_error"
            self.error_stats[error_type] += 1
            print(f"Error predicting race {race_id}: {e}")
            return None, error_type
    
    def extract_actual_result(self, race_info: Dict) -> List[int]:
        """캐시된 1-3위 결과 파일에서 실제 결과 추출"""
        try:
            # race_info에서 필요한 정보 추출
            meet = race_info.get('meet', '서울')
            rc_date = race_info['race_date']
            rc_no = race_info['race_no']
            
            # 1-3위 결과 파일 경로
            cache_file = Path(f"data/cache/results/top3_{rc_date}_{meet}_{rc_no}.json")
            
            # 캐시 파일이 있으면 읽기
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    top3 = json.load(f)  # [1위번호, 2위번호, 3위번호]
                return top3
            
            # 캐시가 없으면 API를 통해 가져오기 (Node.js 사용)
            print(f"  결과 캐시 없음. API로 가져오기: {meet} {rc_date} {rc_no}경주")
            cmd = ['node', 'scripts/fetch_and_save_results.js', meet, rc_date, str(rc_no)]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    # 저장된 파일 다시 읽기
                    if cache_file.exists():
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            top3 = json.load(f)
                        return top3
                else:
                    print(f"  API 호출 실패: {result.stderr}")
            except subprocess.TimeoutExpired:
                print(f"  API 호출 타임아웃")
                
            return []
                
        except Exception as e:
            print(f"  결과 추출 오류: {e}")
            return []
    
    def calculate_reward(self, predicted: List[int], actual: List[int]) -> Dict:
        """보상함수 계산"""
        if not actual:  # 실제 결과가 없는 경우
            return {
                "correct_count": 0,
                "base_score": 0,
                "bonus": 0,
                "total_score": 0,
                "hit_rate": 0,
                "status": "no_result"
            }
        
        # 적중 개수
        correct_count = len(set(predicted) & set(actual))
        
        # 기본 점수
        base_score = correct_count * 33.33
        
        # 보너스 (3마리 모두 적중)
        if correct_count == 3:
            bonus = 10
        else:
            bonus = 0
        
        total_score = base_score + bonus
        
        return {
            "correct_count": correct_count,
            "base_score": base_score,
            "bonus": bonus,
            "total_score": total_score,
            "hit_rate": correct_count / 3 * 100,
            "status": "evaluated"
        }
    
    def analyze_prediction_patterns(self, results: List[Dict]) -> Dict:
        """예측 패턴 분석"""
        patterns = {
            "popularity_distribution": defaultdict(int),
            "confidence_vs_accuracy": [],
            "execution_times": [],
            "error_distribution": dict(self.error_stats)
        }
        
        for result in results:
            if result.get("prediction"):
                # 실행 시간 수집
                if 'execution_time' in result['prediction']:
                    patterns['execution_times'].append(result['prediction']['execution_time'])
                
                # 신뢰도와 정확도 관계
                if result['reward']['status'] == 'evaluated':
                    patterns['confidence_vs_accuracy'].append({
                        'confidence': result['prediction'].get('confidence', 0),
                        'hit_rate': result['reward']['hit_rate']
                    })
        
        # 평균 계산
        if patterns['execution_times']:
            patterns['avg_execution_time'] = sum(patterns['execution_times']) / len(patterns['execution_times'])
        else:
            patterns['avg_execution_time'] = 0
        
        return patterns
    
    def evaluate_all_parallel(self, test_limit: int = 10, max_workers: int = 3):
        """병렬 처리로 전체 평가 실행"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 테스트 레이스 찾기
        test_races = self.find_test_races(limit=test_limit)
        
        results = []
        total_races = len(test_races)
        successful_predictions = 0
        total_correct_horses = 0
        
        print(f"\n{self.prompt_version} 평가 시작 (병렬 처리)...")
        print(f"테스트 경주 수: {total_races}")
        print(f"동시 실행 수: {max_workers}")
        print("-" * 60)
        
        # 병렬 처리
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 작업 제출
            future_to_race = {}
            for race_info in test_races:
                race_data = self.load_race_data(race_info)
                if race_data:
                    future = executor.submit(
                        self.process_single_race, 
                        race_info, 
                        race_data
                    )
                    future_to_race[future] = race_info
            
            # 결과 수집
            for i, future in enumerate(as_completed(future_to_race)):
                race_info = future_to_race[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        
                        # 통계 업데이트
                        if result['prediction'] is not None:
                            if result['reward']['correct_count'] == 3:
                                successful_predictions += 1
                            total_correct_horses += result['reward']['correct_count']
                        
                        print(f"[{i+1}/{total_races}] {race_info['race_id']} 완료")
                        
                except Exception as e:
                    print(f"Error processing {race_info['race_id']}: {e}")
        
        # 패턴 분석
        patterns = self.analyze_prediction_patterns(results)
        
        # 전체 요약
        valid_results = [r for r in results if r['prediction'] is not None]
        summary = {
            "prompt_version": self.prompt_version,
            "test_date": timestamp,
            "total_races": total_races,
            "valid_predictions": len(valid_results),
            "successful_predictions": successful_predictions,
            "success_rate": successful_predictions / len(valid_results) * 100 if valid_results else 0,
            "average_correct_horses": total_correct_horses / len(valid_results) if valid_results else 0,
            "total_correct_horses": total_correct_horses,
            "error_stats": dict(self.error_stats),
            "execution_patterns": patterns,
            "detailed_results": results
        }
        
        # 결과 저장
        output_file = self.results_dir / f"evaluation_{self.prompt_version}_{timestamp}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        # 결과 출력
        self.print_summary(summary, output_file)
        
        return summary
    
    def process_single_race(self, race_info: Dict, race_data: Dict) -> Optional[Dict]:
        """단일 경주 처리"""
        race_id = race_info['race_id']
        
        # 예측 실행 (재시도 포함)
        prediction, error_type = self.run_prediction_with_retry(race_data, race_id)
        
        if prediction is None:
            return {
                "race_id": race_id,
                "prediction": None,
                "error_type": error_type,
                "reward": {"status": "error"}
            }
        
        # 예측 결과 추출
        predicted_horses = [h["chulNo"] for h in prediction["selected_horses"]]
        
        # 실제 결과 추출
        actual_result = self.extract_actual_result(race_info)
        
        # 보상 계산
        reward = self.calculate_reward(predicted_horses, actual_result)
        
        return {
            "race_id": race_id,
            "predicted": predicted_horses,
            "actual": actual_result,
            "reward": reward,
            "confidence": prediction.get("confidence", 0),
            "reasoning": prediction.get("reasoning", ""),
            "execution_time": prediction.get("execution_time", 0),
            "prediction": prediction,
            "error_type": error_type
        }
    
    def print_summary(self, summary: Dict, output_file: Path):
        """요약 결과 출력"""
        print("\n" + "=" * 60)
        print(f"평가 완료!")
        print(f"프롬프트 버전: {summary['prompt_version']}")
        print(f"전체 경주: {summary['total_races']}")
        print(f"유효 예측: {summary['valid_predictions']}")
        
        if summary['valid_predictions'] > 0:
            print(f"완전 적중: {summary['successful_predictions']} ({summary['success_rate']:.1f}%)")
            print(f"평균 적중 말 수: {summary['average_correct_horses']:.2f}")
        
        print(f"\n에러 통계:")
        for error_type, count in summary['error_stats'].items():
            print(f"  - {error_type}: {count}건")
        
        if summary['execution_patterns'].get('avg_execution_time'):
            print(f"\n평균 실행 시간: {summary['execution_patterns']['avg_execution_time']:.1f}초")
        
        print(f"\n결과 저장: {output_file}")
    
    def generate_improvement_suggestions(self, evaluation_results: Dict) -> List[str]:
        """평가 결과를 바탕으로 개선 제안 생성"""
        suggestions = []
        
        # 에러율 기반 제안
        total_attempts = evaluation_results["total_races"]
        error_rate = (total_attempts - evaluation_results["valid_predictions"]) / total_attempts * 100
        
        if error_rate > 20:
            suggestions.append(f"높은 에러율 ({error_rate:.1f}%) - 프롬프트 형식이나 길이 조정 필요")
        
        # 에러 타입별 제안
        error_stats = evaluation_results["error_stats"]
        if error_stats.get("timeout", 0) > 2:
            suggestions.append("타임아웃 빈발 - 프롬프트 간소화 또는 응답 형식 단순화 필요")
        
        if error_stats.get("json_parse_error", 0) > 2:
            suggestions.append("JSON 파싱 오류 빈발 - 출력 형식 예시를 더 명확히 제시")
        
        # 성공률 기반 제안
        if evaluation_results["valid_predictions"] > 0:
            success_rate = evaluation_results["success_rate"]
            if success_rate < 10:
                suggestions.append("낮은 성공률 - 보강된 데이터(혈통, 기수/조교사 성적) 활용 강화")
            elif success_rate < 20:
                suggestions.append("개선 여지 있음 - 가중치 조정 및 세부 로직 최적화")
        
        return suggestions


def main():
    if len(sys.argv) < 3:
        print("Usage: python evaluate_prompt_v2.py <prompt_version> <prompt_file> [test_limit] [max_workers]")
        print("Example: python evaluate_prompt_v2.py v10.0 prompts/prediction-template-v10.0.md 30 3")
        sys.exit(1)
    
    prompt_version = sys.argv[1]
    prompt_file = sys.argv[2]
    test_limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    max_workers = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    
    # 평가 실행
    evaluator = PromptEvaluatorV2(prompt_version, prompt_file)
    results = evaluator.evaluate_all_parallel(test_limit=test_limit, max_workers=max_workers)
    
    # 개선 제안
    suggestions = evaluator.generate_improvement_suggestions(results)
    if suggestions:
        print("\n개선 제안:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"{i}. {suggestion}")


if __name__ == "__main__":
    main()