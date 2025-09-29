#!/usr/bin/env python3
"""
프롬프트 재귀 개선을 위한 평가 시스템 v3
- Claude Code CLI를 더 효율적으로 활용
- stream-json 출력 형식 사용
- 향상된 안정성
"""

import glob
import json
import os
import re
import subprocess
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path


class PromptEvaluatorV3:
    def __init__(self, prompt_version: str, prompt_path: str):
        self.prompt_version = prompt_version
        self.prompt_path = prompt_path
        self.results_dir = Path("data/prompt_evaluation")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.api_lock = threading.Semaphore(3)  # API 동시 호출 제한
        self.error_stats = defaultdict(int)  # 에러 통계

        # Claude Code 환경 설정
        self.claude_env = {
            **os.environ,
            "BASH_DEFAULT_TIMEOUT_MS": "120000",
            "BASH_MAX_TIMEOUT_MS": "300000",
            "CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR": "true",
            "DISABLE_INTERLEAVED_THINKING": "true"  # 더 빠른 응답
        }

    def find_test_races(self, limit: int = None) -> list[dict[str, any]]:
        """테스트할 경주 파일 찾기 (enriched 데이터)"""
        race_files = []

        # enriched 파일 찾기
        enriched_pattern = "data/races/*/*/*/*/*_enriched.json"
        enriched_files = sorted(glob.glob(enriched_pattern))

        for enriched_file in enriched_files:
            path_parts = enriched_file.split("/")
            # race_1_20250608_1_enriched.json -> 정보 추출
            filename = path_parts[-1]
            race_prefix = "_".join(filename.split("_")[0:2])
            race_date = filename.split("_")[2]
            race_no = filename.split("_")[3].replace("_enriched.json", "")

            # meet 정보 추출
            meet = path_parts[-2]  # seoul, jeju, busan 등
            meet_map = {"seoul": "서울", "jeju": "제주", "busan": "부산경남"}

            race_files.append({
                "enriched_file": Path(enriched_file),
                "race_id": f"{race_prefix}_{race_date}_{race_no}",
                "race_date": race_date,
                "race_no": race_no,
                "meet": meet_map.get(meet, "서울")
            })

        if limit:
            race_files = race_files[:limit]

        print(f"테스트할 경주: {len(race_files)}개 (enriched 데이터)")
        return race_files

    def load_race_data(self, race_info: dict) -> dict | None:
        """enriched 파일에서 경주 데이터 로드"""
        try:
            with open(race_info["enriched_file"], encoding="utf-8") as f:
                data = json.load(f)

            # API 응답 형식에서 실제 데이터 추출
            if "response" in data and "body" in data["response"]:
                items = data["response"]["body"]["items"]["item"]

                # 데이터 정리
                horses = []
                for item in items:
                    # 기권/제외 말 필터링
                    if item.get("winOdds", 999) == 0:
                        continue

                    horse = {
                        "chulNo": item["chulNo"],
                        "hrName": item["hrName"],
                        "hrNo": item["hrNo"],
                        "jkName": item["jkName"],
                        "jkNo": item["jkNo"],
                        "trName": item["trName"],
                        "trNo": item["trNo"],
                        "wgBudam": item["wgBudam"],
                        "winOdds": item["winOdds"],
                        "plcOdds": item["plcOdds"],
                        "rating": item.get("rating", 0),
                        "rank": item.get("rank", ""),
                        "age": item.get("age", 0),
                        "sex": item.get("sex", ""),
                        # 보강된 데이터
                        "hrDetail": item.get("hrDetail", {}),
                        "jkDetail": item.get("jkDetail", {}),
                        "trDetail": item.get("trDetail", {})
                    }

                    horses.append(horse)

                # 경주 정보 구성
                race_data = {
                    "raceInfo": {
                        "rcDate": items[0]["rcDate"],
                        "rcNo": items[0]["rcNo"],
                        "rcName": items[0].get("rcName", ""),
                        "rcDist": items[0]["rcDist"],
                        "track": items[0].get("track", ""),
                        "weather": items[0].get("weather", ""),
                        "meet": items[0]["meet"]
                    },
                    "horses": horses
                }

                return race_data

            return None

        except Exception as e:
            print(f"데이터 로드 오류: {e}")
            return None

    def run_claude_prediction(self, race_data: dict, race_id: str) -> tuple[dict | None, str]:
        """Claude Code CLI를 통한 예측 실행 (stream-json 사용)"""
        error_type = "success"
        start_time = time.time()

        # 프롬프트 읽기
        with open(self.prompt_path, encoding="utf-8") as f:
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
            # Claude Code 실행 (stream-json 형식)
            with self.api_lock:
                cmd = [
                    "claude",
                    "-p",
                    prompt
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=3000,
                    env=self.claude_env
                )

            execution_time = time.time() - start_time

            if result.returncode != 0:
                error_type = "claude_error"
                self.error_stats[error_type] += 1
                print(f"Claude 오류: {result.stderr[:200]}")
                return None, error_type

            # stream-json 출력 파싱
            prediction = self._parse_stream_json(result.stdout, execution_time)
            if prediction:
                return prediction, error_type

            # 파싱 실패 시 일반 출력으로 시도
            prediction = self._parse_regular_output(result.stdout, execution_time)
            if prediction:
                return prediction, error_type

            error_type = "json_parse_error"
            self.error_stats[error_type] += 1
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

    def _parse_stream_json(self, output: str, execution_time: float) -> dict | None:
        """stream-json 형식 파싱"""
        try:
            for line in output.strip().split("\n"):
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    # 다양한 형식 처리
                    content = None

                    if isinstance(data, dict):
                        # 직접 JSON 응답인 경우
                        if "selected_horses" in data or "predicted" in data:
                            data["execution_time"] = execution_time
                            # predicted를 selected_horses로 변환
                            if "predicted" in data and "selected_horses" not in data:
                                data["selected_horses"] = [{"chulNo": no} for no in data["predicted"]]
                            return data

                        # stream 형식인 경우
                        if "type" in data and data["type"] == "message":
                            content = data.get("content", "")
                        elif "content" in data:
                            content = data["content"]
                        elif "text" in data:
                            content = data["text"]

                    if content:
                        # content에서 JSON 추출 (selected_horses 또는 predicted)
                        json_match = re.search(r'\{.*"(?:selected_horses|predicted)".*?\}', content, re.DOTALL)
                        if json_match:
                            prediction = json.loads(json_match.group())
                            prediction["execution_time"] = execution_time
                            # predicted를 selected_horses로 변환
                            if "predicted" in prediction and "selected_horses" not in prediction:
                                prediction["selected_horses"] = [{"chulNo": no} for no in prediction["predicted"]]
                            return prediction

                except json.JSONDecodeError:
                    continue

        except Exception as e:
            print(f"Stream JSON 파싱 오류: {e}")

        return None

    def _parse_regular_output(self, output: str, execution_time: float) -> dict | None:
        """일반 출력 파싱 (폴백)"""
        try:
            # 코드블록 내 JSON
            code_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", output, re.DOTALL)
            if code_block_match:
                try:
                    prediction = json.loads(code_block_match.group(1))
                    prediction["execution_time"] = execution_time
                    # predicted를 selected_horses로 변환
                    if "predicted" in prediction and "selected_horses" not in prediction:
                        prediction["selected_horses"] = [{"chulNo": no} for no in prediction["predicted"]]
                    return prediction
                except Exception:
                    pass

            # 일반 JSON (selected_horses 또는 predicted)
            json_match = re.search(r'\{.*"(?:selected_horses|predicted)".*?\}', output, re.DOTALL)
            if json_match:
                try:
                    prediction = json.loads(json_match.group())
                    prediction["execution_time"] = execution_time
                    # predicted를 selected_horses로 변환
                    if "predicted" in prediction and "selected_horses" not in prediction:
                        prediction["selected_horses"] = [{"chulNo": no} for no in prediction["predicted"]]
                    return prediction
                except Exception:
                    pass

        except Exception as e:
            print(f"Regular 파싱 오류: {e}")

        return None

    def run_prediction_with_retry(self, race_data: dict, race_id: str, max_retries: int = 1) -> tuple[dict | None, str]:
        """재시도 기능이 있는 예측 실행"""
        for attempt in range(max_retries + 1):
            result, error_type = self.run_claude_prediction(race_data, race_id)
            if result is not None:
                return result, error_type

            if attempt < max_retries and error_type != "timeout":
                print(f"  재시도 {attempt + 1}/{max_retries}...")
                time.sleep(2)

        return None, error_type

    def extract_actual_result(self, race_info: dict) -> list[int]:
        """캐시된 1-3위 결과 파일에서 실제 결과 추출"""
        try:
            meet = race_info.get("meet", "서울")
            rc_date = race_info["race_date"]
            rc_no = race_info["race_no"]

            # 1-3위 결과 파일 경로
            cache_file = Path(f"data/cache/results/top3_{rc_date}_{meet}_{rc_no}.json")

            # 캐시 파일이 있으면 읽기
            if cache_file.exists():
                with open(cache_file, encoding="utf-8") as f:
                    top3 = json.load(f)
                return top3

            # 캐시가 없으면 API를 통해 가져오기
            print(f"  결과 캐시 없음. API로 가져오기: {meet} {rc_date} {rc_no}경주")
            cmd = ["node", "scripts/fetch_and_save_results.js", meet, rc_date, str(rc_no)]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0 and cache_file.exists():
                    with open(cache_file, encoding="utf-8") as f:
                        top3 = json.load(f)
                    return top3
            except Exception:
                pass

            return []

        except Exception as e:
            print(f"  결과 추출 오류: {e}")
            return []

    def calculate_reward(self, predicted: list[int], actual: list[int]) -> dict:
        """보상함수 계산"""
        if not actual:
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
        bonus = 10 if correct_count == 3 else 0

        total_score = base_score + bonus

        return {
            "correct_count": correct_count,
            "base_score": base_score,
            "bonus": bonus,
            "total_score": total_score,
            "hit_rate": correct_count / 3 * 100,
            "status": "evaluated"
        }

    def process_single_race(self, race_info: dict, race_data: dict) -> dict | None:
        """단일 경주 처리"""
        race_id = race_info["race_id"]

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

    def evaluate_all_parallel(self, test_limit: int = 10, max_workers: int = 3):
        """병렬 처리로 전체 평가 실행"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 테스트 레이스 찾기
        test_races = self.find_test_races(limit=test_limit)

        results = []
        total_races = len(test_races)
        successful_predictions = 0
        total_correct_horses = 0

        print(f"\n{self.prompt_version} 평가 시작 (Claude Code CLI + stream-json)...")
        print(f"테스트 경주 수: {total_races}")
        print(f"동시 실행 수: {max_workers}")
        print("-" * 60)

        # 진행 상황 추적 변수
        start_time = time.time()
        completed_count = 0

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
            for _i, future in enumerate(as_completed(future_to_race)):
                race_info = future_to_race[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)

                        # 통계 업데이트
                        if result["prediction"] is not None:
                            if result["reward"]["correct_count"] == 3:
                                successful_predictions += 1
                            total_correct_horses += result["reward"]["correct_count"]

                        completed_count += 1
                        elapsed = time.time() - start_time
                        avg_time = elapsed / completed_count
                        eta = avg_time * (total_races - completed_count)

                        status = "✓" if result["prediction"] else "✗"
                        if result["prediction"]:
                            correct = result["reward"]["correct_count"]
                            hit_rate = result["reward"]["hit_rate"]
                            predicted = result.get("predicted", [])
                            actual = result.get("actual", [])

                            # 예측과 실제 결과를 문자열로 포맷
                            pred_str = f"[{",".join(map(str, predicted))}]" if predicted else "[?]"
                            actual_str = f"[{",".join(map(str, actual))}]" if actual else "[?]"

                            print(f"[{completed_count}/{total_races}] {status} {race_info["race_id"]} - 적중: {correct}/3 ({hit_rate:.0f}%) | 예측: {pred_str} → 실제: {actual_str} | 진행률: {completed_count/total_races*100:.1f}% | ETA: {eta:.0f}초")
                        else:
                            print(f"[{completed_count}/{total_races}] {status} {race_info["race_id"]} - 에러: {result.get("error_type", "unknown")} | 진행률: {completed_count/total_races*100:.1f}%")

                except Exception as e:
                    print(f"Error processing {race_info["race_id"]}: {e}")

        # 전체 요약
        valid_results = [r for r in results if r["prediction"] is not None]
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
            "avg_execution_time": sum(r["execution_time"] for r in valid_results) / len(valid_results) if valid_results else 0,
            "detailed_results": results
        }

        # 결과 저장
        output_file = self.results_dir / f"evaluation_{self.prompt_version}_{timestamp}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        # 결과 출력
        self.print_summary(summary, output_file)

        return summary

    def print_summary(self, summary: dict, output_file: Path):
        """요약 결과 출력"""
        print("\n" + "=" * 60)
        print("평가 완료!")
        print(f"프롬프트 버전: {summary["prompt_version"]}")
        print(f"전체 경주: {summary["total_races"]}")
        print(f"유효 예측: {summary["valid_predictions"]}")

        if summary["valid_predictions"] > 0:
            print(f"완전 적중: {summary["successful_predictions"]} ({summary["success_rate"]:.1f}%)")
            print(f"평균 적중 말 수: {summary["average_correct_horses"]:.2f}")
            print(f"평균 실행 시간: {summary["avg_execution_time"]:.1f}초")

        print("\n에러 통계:")
        for error_type, count in summary["error_stats"].items():
            print(f"  - {error_type}: {count}건")

        print(f"\n결과 저장: {output_file}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python evaluate_prompt_v3.py <prompt_version> <prompt_file> [test_limit] [max_workers]")
        print("Example: python evaluate_prompt_v3.py v10.0 prompts/prediction-template-v10.0.md 30 3")
        sys.exit(1)

    prompt_version = sys.argv[1]
    prompt_file = sys.argv[2]
    test_limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    max_workers = int(sys.argv[4]) if len(sys.argv) > 4 else 3

    # 평가 실행
    evaluator = PromptEvaluatorV3(prompt_version, prompt_file)
    _results = evaluator.evaluate_all_parallel(test_limit=test_limit, max_workers=max_workers)


if __name__ == "__main__":
    main()
