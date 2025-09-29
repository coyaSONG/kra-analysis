#!/usr/bin/env python3
"""
프롬프트 재귀 개선을 위한 평가 시스템
- Claude CLI를 통한 예측 실행
- 실제 결과와 비교
- 보상함수 기반 평가
- 개선 방향 도출
"""

import glob
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


class PromptEvaluator:
    def __init__(self, prompt_version: str, prompt_path: str):
        self.prompt_version = prompt_version
        self.prompt_path = prompt_path
        self.results_dir = Path("data/prompt_evaluation")
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def find_test_races(self, limit: int = None) -> list[Path]:
        """테스트할 경주 파일 찾기 (결과가 있는 경주만)"""
        # 2025년 5-6월 경주 결과 파일들
        result_files = []
        for month in ["05", "06"]:
            pattern = f"data/raw/results/2025/{month}/race_*.json"
            files = sorted(glob.glob(pattern))
            result_files.extend(files)

        if limit:
            result_files = result_files[:limit]

        print(f"테스트할 경주: {len(result_files)}개")
        return [Path(f) for f in result_files]

    def prepare_race_data(self, result_file: Path) -> dict | None:
        """결과 파일에서 예측용 데이터 생성 (결과 제거)"""
        with open(result_file, encoding="utf-8") as f:
            data = json.load(f)

        # 결과 정보 제거
        prediction_data = {"race_info": data["race_info"].copy(), "horses": []}

        # 결과 필드 제거 및 기권/제외 말 필터링
        for horse in data["horses"]:
            # 기권/제외 말 스킵 (win_odds가 0인 경우)
            if horse.get("win_odds", 999) == 0:
                print(f"  - {horse['chul_no']}번 {horse['hr_name']} 기권/제외 - 스킵")
                continue

            horse_data = horse.copy()
            # 결과 관련 필드 제거
            if "result" in horse_data:
                del horse_data["result"]
            if "ord" in horse_data:
                del horse_data["ord"]
            if "rc_time" in horse_data:
                del horse_data["rc_time"]
            # win_odds와 plc_odds는 예측에 필요하므로 제거하지 않음

            prediction_data["horses"].append(horse_data)

        return prediction_data

    def run_prediction(self, race_data: dict, race_id: str) -> dict | None:
        """Claude CLI를 통해 예측 실행"""
        # 임시 파일에 race data 저장
        temp_file = f"/tmp/race_{race_id}.json"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(race_data, f, ensure_ascii=False, indent=2)

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
    {{"chul_no": 번호, "hr_name": "말이름"}},
    {{"chul_no": 번호, "hr_name": "말이름"}},
    {{"chul_no": 번호, "hr_name": "말이름"}}
  ],
  "confidence": 70,
  "reasoning": "1위 인기마 포함, 기수 성적 우수"
}}"""

        try:
            # Claude CLI 실행
            cmd = ["claude", "-p", prompt]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode != 0:
                print(f"Error running claude: {result.stderr}")
                return None

            # 결과 파싱
            output = result.stdout.strip()

            # JSON 부분만 추출 (여러 패턴 시도)
            import re

            # 패턴 1: 코드블록 내 JSON
            code_block_match = re.search(
                r"```(?:json)?\s*(\{.*?\})\s*```", output, re.DOTALL
            )
            if code_block_match:
                try:
                    prediction = json.loads(code_block_match.group(1))
                    return prediction
                except Exception:
                    pass

            # 패턴 2: 일반 JSON
            json_match = re.search(r"\{.*\}", output, re.DOTALL)
            if json_match:
                try:
                    prediction = json.loads(json_match.group())
                    return prediction
                except Exception:
                    pass

            print(f"Failed to parse prediction: {output[:200]}...")
            return None

        except subprocess.TimeoutExpired:
            print(f"Timeout for race {race_id}")
            return None
        except Exception as e:
            print(f"Error predicting race {race_id}: {e}")
            return None
        finally:
            # 임시 파일 삭제
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def extract_actual_result(self, result_file: Path) -> list[int]:
        """실제 결과에서 1-3위 말 번호 추출"""
        with open(result_file, encoding="utf-8") as f:
            data = json.load(f)

        # 결과가 있는 말들을 순위별로 정렬
        horses_with_result = []
        for horse in data["horses"]:
            if "result" in horse and horse["result"].get("ord"):
                horses_with_result.append(
                    {"chul_no": horse["chul_no"], "ord": horse["result"]["ord"]}
                )

        # 순위별 정렬
        horses_with_result.sort(key=lambda x: x["ord"])

        # 1-3위 말 번호 반환
        top3 = [h["chul_no"] for h in horses_with_result[:3]]
        return top3

    def calculate_reward(self, predicted: list[int], actual: list[int]) -> dict:
        """보상함수 계산"""
        # 적중 개수
        correct_count = len(set(predicted) & set(actual))

        # 기본 점수
        base_score = correct_count * 33.33  # 각 말당 33.33점

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
        }

    def analyze_failure(
        self,
        race_data: dict,
        predicted: list[int],
        actual: list[int],
        result_file: Path,
    ) -> dict:
        """실패 원인 분석"""
        with open(result_file, encoding="utf-8") as f:
            full_data = json.load(f)

        # 놓친 말들 분석
        missed_horses = set(actual) - set(predicted)
        missed_analysis = []

        for chul_no in missed_horses:
            horse = next(
                (h for h in full_data["horses"] if h["chul_no"] == chul_no), None
            )
            if horse:
                # 인기도 확인 (배당률 기반)
                all_odds = [
                    (h["chul_no"], h.get("win_odds", 999))
                    for h in full_data["horses"]
                    if h.get("win_odds")
                ]
                all_odds.sort(key=lambda x: x[1])
                popularity_rank = next(
                    (i + 1 for i, (no, _) in enumerate(all_odds) if no == chul_no), -1
                )

                missed_analysis.append(
                    {
                        "chul_no": chul_no,
                        "hr_name": horse["hr_name"],
                        "popularity_rank": popularity_rank,
                        "data_count": len(horse.get("recent_records", [])),
                        "actual_position": actual.index(chul_no) + 1,
                    }
                )

        # 잘못 선택한 말들 분석
        wrong_horses = set(predicted) - set(actual)
        wrong_analysis = []

        for chul_no in wrong_horses:
            horse = next(
                (h for h in full_data["horses"] if h["chul_no"] == chul_no), None
            )
            if horse and "result" in horse:
                wrong_analysis.append(
                    {
                        "chul_no": chul_no,
                        "hr_name": horse["hr_name"],
                        "predicted_reason": "분석 필요",
                        "actual_position": horse["result"].get("ord", 99),
                    }
                )

        return {"missed_horses": missed_analysis, "wrong_horses": wrong_analysis}

    def evaluate_all(self, test_limit: int = 10):
        """전체 평가 프로세스 실행"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 테스트 레이스 찾기
        test_races = self.find_test_races(limit=test_limit)

        results = []
        total_races = len(test_races)
        successful_predictions = 0
        total_correct_horses = 0

        print(f"\n{self.prompt_version} 평가 시작...")
        print(f"테스트 경주 수: {total_races}")
        print("-" * 60)

        for i, result_file in enumerate(test_races):
            # 경주 ID 생성
            race_id = result_file.stem
            print(f"\n[{i+1}/{total_races}] {race_id} 처리 중...")

            # 예측용 데이터 준비
            race_data = self.prepare_race_data(result_file)
            if not race_data:
                continue

            # 예측 실행
            prediction = self.run_prediction(race_data, race_id)
            if not prediction:
                continue

            # 실제 결과 추출
            actual_result = self.extract_actual_result(result_file)

            # 예측 결과 추출
            predicted_horses = [h["chul_no"] for h in prediction["selected_horses"]]

            # 보상 계산
            reward = self.calculate_reward(predicted_horses, actual_result)

            # 실패 분석
            if reward["correct_count"] < 3:
                failure_analysis = self.analyze_failure(
                    race_data, predicted_horses, actual_result, result_file
                )
            else:
                failure_analysis = None

            # 결과 저장
            result = {
                "race_id": race_id,
                "predicted": predicted_horses,
                "actual": actual_result,
                "reward": reward,
                "confidence": prediction.get("confidence", 0),
                "reasoning": prediction.get("reasoning", ""),
                "failure_analysis": failure_analysis,
            }

            results.append(result)

            # 통계 업데이트
            if reward["correct_count"] == 3:
                successful_predictions += 1
            total_correct_horses += reward["correct_count"]

            print(f"  예측: {predicted_horses}")
            print(f"  실제: {actual_result}")
            print(f"  적중: {reward['correct_count']}/3 ({reward['hit_rate']:.1f}%)")

            # API 제한 대응
            time.sleep(5)

        # 전체 요약
        summary = {
            "prompt_version": self.prompt_version,
            "test_date": timestamp,
            "total_races": total_races,
            "successful_predictions": successful_predictions,
            "success_rate": (
                successful_predictions / total_races * 100 if total_races > 0 else 0
            ),
            "average_correct_horses": (
                total_correct_horses / total_races if total_races > 0 else 0
            ),
            "total_correct_horses": total_correct_horses,
            "detailed_results": results,
        }

        # 결과 저장
        output_file = (
            self.results_dir / f"evaluation_{self.prompt_version}_{timestamp}.json"
        )
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print("\n" + "=" * 60)
        print("평가 완료!")
        print(f"전체 경주: {total_races}")
        print(f"완전 적중: {successful_predictions} ({summary['success_rate']:.1f}%)")
        print(f"평균 적중 말 수: {summary['average_correct_horses']:.2f}")
        print(f"결과 저장: {output_file}")

        return summary

    def generate_improvement_suggestions(self, evaluation_results: dict) -> list[str]:
        """평가 결과를 바탕으로 개선 제안 생성"""
        suggestions = []

        # 공통 실패 패턴 분석
        missed_patterns = {
            "high_popularity_missed": 0,
            "low_data_missed": 0,
            "weight_change_missed": 0,
        }

        for result in evaluation_results["detailed_results"]:
            if result["failure_analysis"]:
                for missed in result["failure_analysis"]["missed_horses"]:
                    if missed["popularity_rank"] <= 3:
                        missed_patterns["high_popularity_missed"] += 1
                    if missed["data_count"] < 3:
                        missed_patterns["low_data_missed"] += 1

        # 패턴별 제안
        if missed_patterns["high_popularity_missed"] > 3:
            suggestions.append(
                "인기마(1-3위) 배제 기준이 너무 엄격함. 시장 평가 가중치 추가 상향 필요"
            )

        if missed_patterns["low_data_missed"] > 2:
            suggestions.append(
                "데이터 부족 말 평가 로직 개선 필요. C그룹 가중치 조정 검토"
            )

        # 성공률 기반 제안
        if evaluation_results["success_rate"] < 10:
            suggestions.append(
                "전반적인 접근 방식 재검토 필요. Few-shot 예시 추가 확대"
            )
        elif evaluation_results["success_rate"] < 20:
            suggestions.append("세부 조정 필요. 보정 요소 가중치 미세 조정")

        return suggestions


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: python evaluate_prompt.py <prompt_version> <prompt_file> [test_limit]"
        )
        print(
            "Example: python evaluate_prompt.py v2.0 prompts/prediction-template-v2.0.md 10"
        )
        sys.exit(1)

    prompt_version = sys.argv[1]
    prompt_file = sys.argv[2]
    test_limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10

    # 평가 실행
    evaluator = PromptEvaluator(prompt_version, prompt_file)
    results = evaluator.evaluate_all(test_limit=test_limit)

    # 개선 제안
    suggestions = evaluator.generate_improvement_suggestions(results)
    if suggestions:
        print("\n개선 제안:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"{i}. {suggestion}")


if __name__ == "__main__":
    main()
