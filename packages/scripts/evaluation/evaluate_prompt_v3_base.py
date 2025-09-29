#!/usr/bin/env python3
"""
프롬프트 평가 시스템 v3 - base-prompt용 수정 버전
- predicted 필드를 처리하도록 수정
- selected_horses 대신 predicted 사용
"""

import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path


class PromptEvaluatorV3Base:
    def __init__(self, prompt_version: str, prompt_path: str):
        self.prompt_version = prompt_version
        self.prompt_path = Path(prompt_path)
        self.results_dir = Path("data/prompt_evaluation")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.error_stats = {}

        # Claude Code 환경 설정
        self.env = {
            **os.environ,
            "BASH_DEFAULT_TIMEOUT_MS": "120000",  # 2분
            "BASH_MAX_TIMEOUT_MS": "300000",     # 5분
            "CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR": "true",
            "DISABLE_INTERLEAVED_THINKING": "true"
        }

    def find_test_races(self, limit: int = 10) -> list[dict[str, any]]:
        """테스트할 경주 찾기 (enriched 데이터 우선)"""
        test_races = []
        cache_dir = Path("data/cache/results")

        # enriched 파일 찾기
        enriched_files = list(Path("data/races").glob("*/*/*/*/*_enriched.json"))

        for enriched_file in sorted(enriched_files)[:limit*2]:
            try:
                path_parts = enriched_file.parts
                filename = path_parts[-1]

                # 파일명에서 정보 추출
                race_prefix = "_".join(filename.split("_")[0:2])
                race_date = filename.split("_")[2]
                race_no = filename.split("_")[3].replace("_enriched.json", "")

                # meet 정보 추출
                meet = path_parts[-2]
                meet_map = {"seoul": "서울", "jeju": "제주", "busan": "부산경남"}

                # 해당하는 결과 파일 확인
                result_file = cache_dir / f"top3_{race_date}_{meet_map.get(meet, "서울")}_{race_no}.json"

                if result_file.exists():
                    test_races.append({
                        "race_id": f"{race_prefix}_{race_date}_{race_no}",
                        "enriched_file": enriched_file,
                        "result_file": result_file,
                        "race_date": race_date,
                        "race_no": race_no,
                        "meet": meet_map.get(meet, "서울")
                    })

                    if len(test_races) >= limit:
                        break

            except Exception:
                continue

        print(f"테스트할 경주: {len(test_races)}개 (enriched 데이터)")
        return test_races

    def load_race_data(self, enriched_file: Path) -> dict | None:
        """enriched 파일에서 경주 데이터 로드"""
        try:
            with open(enriched_file, encoding="utf-8") as f:
                data = json.load(f)

            # API 응답 형식에서 실제 데이터 추출
            if "response" in data and "body" in data["response"]:
                items = data["response"]["body"]["items"]["item"]

                # 리스트가 아닌 경우 리스트로 변환
                if not isinstance(items, list):
                    items = [items]

                # 기권/제외 말 필터링 (winOdds가 0인 경우)
                valid_items = [item for item in items if item.get("winOdds", 0) > 0]

                if not valid_items:
                    return None

                # 데이터 구조 재구성
                race_data = {
                    "meet": valid_items[0].get("meet", ""),
                    "rcDate": valid_items[0].get("rcDate", ""),
                    "rcNo": valid_items[0].get("rcNo", ""),
                    "horses": []
                }

                for item in valid_items:
                    horse = {
                        "chulNo": item["chulNo"],
                        "hrName": item["hrName"],
                        "hrNo": item["hrNo"],
                        "jkName": item["jkName"],
                        "jkNo": item["jkNo"],
                        "trName": item["trName"],
                        "trNo": item["trNo"],
                        "winOdds": item["winOdds"],
                        "budam": item.get("budam", 0),
                        "age": item.get("age", ""),
                        "sex": item.get("sex", ""),
                        "rank": item.get("rank", ""),
                        "rating": item.get("rating", ""),
                        "jkWeight": item.get("jkWeight", ""),
                        "diffUnit": item.get("diffUnit", ""),
                        "prizeCond": item.get("prizeCond", "")
                    }

                    # enriched 데이터 추가
                    if "hrDetail" in item:
                        horse["hrDetail"] = item["hrDetail"]
                    if "jkDetail" in item:
                        horse["jkDetail"] = item["jkDetail"]
                    if "trDetail" in item:
                        horse["trDetail"] = item["trDetail"]

                    race_data["horses"].append(horse)

                return race_data

            return None

        except Exception as e:
            print(f"데이터 로드 오류: {e}")
            return None

    def run_claude_prediction(self, race_data: dict, race_id: str) -> tuple[dict | None, str]:
        """Claude를 사용하여 예측 수행"""
        try:
            # 프롬프트 읽기
            with open(self.prompt_path, encoding="utf-8") as f:
                prompt_template = f.read()

            # 데이터를 프롬프트에 포함
            prompt = f"{prompt_template}\n\n제공된 경주 데이터:\n```json\n{json.dumps(race_data, ensure_ascii=False, indent=2)}\n```"

            # Claude Code CLI 명령 구성
            cmd = [
                "claude",
                "-p",
                prompt
            ]

            start_time = time.time()

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180,  # 3분 타임아웃
                env=self.env
            )

            execution_time = time.time() - start_time

            if result.returncode != 0:
                print(f"Error running Claude for race {race_id}: {result.stderr[:200]}")
                error_type = "claude_error"
                self.error_stats[error_type] = self.error_stats.get(error_type, 0) + 1
                return None, error_type

            # 응답 파싱
            try:
                parsed = self._parse_stream_json(result.stdout, execution_time)
                if parsed:
                    return parsed, "success"

                # 폴백: 일반 출력 파싱
                parsed = self._parse_regular_output(result.stdout, execution_time)
                if parsed:
                    return parsed, "success"

                print(f"Failed to parse JSON for race {race_id}")
                error_type = "json_parse_error"
                self.error_stats[error_type] = self.error_stats.get(error_type, 0) + 1
                return None, error_type

            except Exception as e:
                print(f"Error processing {race_id}: {e}")
                error_type = "json_parse_error"
                self.error_stats[error_type] = self.error_stats.get(error_type, 0) + 1
                return None, error_type

        except subprocess.TimeoutExpired:
            error_type = "timeout"
            self.error_stats[error_type] = self.error_stats.get(error_type, 0) + 1
            print(f"Timeout for race {race_id}")
            return None, error_type
        except Exception as e:
            error_type = "unknown_error"
            self.error_stats[error_type] = self.error_stats.get(error_type, 0) + 1
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
                    content = None

                    if isinstance(data, dict):
                        # 직접 JSON 응답인 경우
                        if "predicted" in data:
                            data["execution_time"] = execution_time
                            return data

                        # stream 형식인 경우
                        if "type" in data and data["type"] == "message":
                            content = data.get("content", "")
                        elif "content" in data:
                            content = data["content"]
                        elif "text" in data:
                            content = data["text"]

                    if content:
                        # content에서 JSON 추출
                        json_match = re.search(r'\{.*"predicted".*?\}', content, re.DOTALL)
                        if json_match:
                            prediction = json.loads(json_match.group())
                            prediction["execution_time"] = execution_time
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
                    return prediction
                except Exception:
                    pass

            # 일반 JSON
            json_match = re.search(r'\{.*"predicted".*?\}', output, re.DOTALL)
            if json_match:
                try:
                    prediction = json.loads(json_match.group())
                    prediction["execution_time"] = execution_time
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
            result_file = race_info["result_file"]
            if result_file.exists():
                with open(result_file, encoding="utf-8") as f:
                    return json.load(f)

            # 결과 파일이 없으면 API 호출 시도
            cmd = [
                "node", "scripts/race_collector/get_race_result.js",
                race_info["race_date"], race_info["meet"], race_info["race_no"]
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                cache_file = Path(f"data/cache/results/top3_{race_info["race_date"]}_{race_info["meet"]}_{race_info["race_no"]}.json")
                if cache_file.exists():
                    with open(cache_file, encoding="utf-8") as f:
                        return json.load(f)

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

        # 예측 결과 추출 - predicted 필드 사용
        predicted_horses = prediction.get("predicted", [])

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
            "brief_reason": prediction.get("brief_reason", ""),
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

        # 병렬 처리
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 작업 제출
            future_to_race = {}
            for race_info in test_races:
                race_data = self.load_race_data(race_info["enriched_file"])
                if race_data:
                    future = executor.submit(self.process_single_race, race_info, race_data)
                    future_to_race[future] = race_info

            # 결과 수집
            completed = 0
            for future in as_completed(future_to_race):
                race_info = future_to_race[future]
                completed += 1

                try:
                    result = future.result()
                    if result and result.get("prediction") is not None:
                        results.append(result)

                        # 통계 업데이트
                        if result["reward"]["status"] == "evaluated":
                            correct = result["reward"]["correct_count"]
                            hit_rate = result["reward"]["hit_rate"]
                            predicted = result.get("predicted", [])
                            actual = result.get("actual", [])

                            # 예측과 실제 결과를 문자열로 포맷
                            pred_str = f"[{",".join(map(str, predicted))}]" if predicted else "[?]"
                            actual_str = f"[{",".join(map(str, actual))}]" if actual else "[?]"

                            if result["reward"]["correct_count"] == 3:
                                successful_predictions += 1
                                print(f"[{completed}/{total_races}] ✓ {race_info["race_id"]} - 적중: {correct}/3 ({hit_rate:.0f}%) | 예측: {pred_str} → 실제: {actual_str}")
                            else:
                                print(f"[{completed}/{total_races}] ✗ {race_info["race_id"]} - 적중: {correct}/3 ({hit_rate:.0f}%) | 예측: {pred_str} → 실제: {actual_str}")
                            total_correct_horses += result["reward"]["correct_count"]
                        else:
                            print(f"[{completed}/{total_races}] ? {race_info["race_id"]} (결과 없음)")
                    else:
                        print(f"[{completed}/{total_races}] ✗ {race_info["race_id"]} 오류")

                except Exception as e:
                    print(f"[{completed}/{total_races}] ✗ {race_info["race_id"]} 처리 중 오류: {e}")

        # 최종 통계
        valid_predictions = len([r for r in results if r.get("prediction") is not None])
        avg_correct_horses = total_correct_horses / valid_predictions if valid_predictions > 0 else 0
        success_rate = (successful_predictions / valid_predictions * 100) if valid_predictions > 0 else 0

        print("\n" + "=" * 60)
        print("평가 완료!")
        print(f"프롬프트 버전: {self.prompt_version}")
        print(f"전체 경주: {total_races}")
        print(f"유효 예측: {valid_predictions}")
        print(f"완전 적중: {successful_predictions} ({success_rate:.1f}%)")
        print(f"평균 적중 말 수: {avg_correct_horses:.2f}")

        # 실행 시간 통계
        execution_times = [r["execution_time"] for r in results if r.get("execution_time", 0) > 0]
        if execution_times:
            avg_execution_time = sum(execution_times) / len(execution_times)
            print(f"평균 실행 시간: {avg_execution_time:.1f}초")

        # 에러 통계
        if self.error_stats:
            print("\n에러 통계:")
            for error_type, count in self.error_stats.items():
                print(f"  - {error_type}: {count}건")

        # 결과 저장
        evaluation_result = {
            "prompt_version": self.prompt_version,
            "test_date": timestamp,
            "total_races": total_races,
            "valid_predictions": valid_predictions,
            "successful_predictions": successful_predictions,
            "success_rate": success_rate,
            "average_correct_horses": avg_correct_horses,
            "total_correct_horses": total_correct_horses,
            "error_stats": self.error_stats,
            "avg_execution_time": sum(execution_times) / len(execution_times) if execution_times else 0,
            "detailed_results": results
        }

        output_file = self.results_dir / f"evaluation_{self.prompt_version}_{timestamp}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(evaluation_result, f, ensure_ascii=False, indent=2)

        print(f"\n결과 저장: {output_file}")

        return evaluation_result


def main():
    if len(sys.argv) < 3:
        print("Usage: python evaluate_prompt_v3_base.py <prompt_version> <prompt_file> [test_limit] [max_workers]")
        print("Example: python evaluate_prompt_v3_base.py v1.0 prompts/base-prompt-v1.0.md 10 3")
        sys.exit(1)

    prompt_version = sys.argv[1]
    prompt_file = sys.argv[2]
    test_limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    max_workers = int(sys.argv[4]) if len(sys.argv) > 4 else 3

    # 파일 존재 확인
    if not Path(prompt_file).exists():
        print(f"Error: 프롬프트 파일을 찾을 수 없습니다: {prompt_file}")
        sys.exit(1)

    # 평가 실행
    evaluator = PromptEvaluatorV3Base(prompt_version, prompt_file)
    evaluator.evaluate_all_parallel(test_limit, max_workers)


if __name__ == "__main__":
    main()
