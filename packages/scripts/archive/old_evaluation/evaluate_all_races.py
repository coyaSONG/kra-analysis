#!/usr/bin/env python3
"""
전체 수집된 경주에 대한 프롬프트 평가
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


class FullEvaluator:
    def __init__(self, prompt_version: str, prompt_path: str):
        self.prompt_version = prompt_version
        self.prompt_path = prompt_path
        self.results_dir = Path("data/full_evaluation")
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def find_all_result_files(self) -> list[Path]:
        """모든 결과 파일 찾기"""
        result_files = []
        for month_dir in Path("data/raw/results/2025").iterdir():
            if month_dir.is_dir():
                files = sorted(month_dir.glob("race_*.json"))
                result_files.extend(files)

        print(f"총 {len(result_files)}개 경주 파일 발견")
        return result_files

    def prepare_race_data(self, result_file: Path) -> dict:
        """결과 파일에서 예측용 데이터 생성 (결과 제거)"""
        try:
            with open(result_file, encoding="utf-8") as f:
                data = json.load(f)

            # 결과 정보 제거
            prediction_data = {"race_info": data["race_info"].copy(), "horses": []}

            # 결과 필드 제거
            for horse in data["horses"]:
                horse_data = horse.copy()
                # 결과 관련 필드 제거
                for field in ["result", "ord", "rc_time", "win_odds", "plc_odds"]:
                    if field in horse_data:
                        del horse_data[field]
                prediction_data["horses"].append(horse_data)

            return prediction_data
        except Exception as e:
            print(f"Error preparing {result_file}: {e}")
            return None

    def run_prediction_batch(self, race_files: list[Path], batch_size: int = 10):
        """배치로 예측 실행"""
        total_races = 0
        successful_predictions = 0
        total_correct_horses = 0
        partial_correct_1 = 0  # 1마리 적중
        partial_correct_2 = 0  # 2마리 적중

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 진행 상황 파일
        progress_file = self.results_dir / f"progress_{timestamp}.json"
        results_file = (
            self.results_dir / f"full_evaluation_{self.prompt_version}_{timestamp}.json"
        )

        all_results = []

        # 프롬프트 읽기
        with open(self.prompt_path, encoding="utf-8") as f:
            prompt_template = f.read()

        print(f"\n전체 평가 시작: {len(race_files)}개 경주")
        print("=" * 60)

        for i in range(0, len(race_files), batch_size):
            batch = race_files[i : i + batch_size]
            batch_results = []

            print(
                f"\n배치 {i // batch_size + 1}/{(len(race_files) - 1) // batch_size + 1} 처리 중..."
            )

            for j, result_file in enumerate(batch):
                race_id = result_file.stem
                current_idx = i + j + 1

                print(
                    f"[{current_idx}/{len(race_files)}] {race_id} ", end="", flush=True
                )

                # 예측용 데이터 준비
                race_data = self.prepare_race_data(result_file)
                if not race_data:
                    print("❌ (데이터 오류)")
                    continue

                # 간소화된 프롬프트 구성
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
  "reasoning": "간단한 이유"
}}"""

                try:
                    # Claude CLI 실행
                    cmd = ["claude", "-p", prompt]
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=120
                    )

                    if result.returncode != 0:
                        print("❌ (CLI 오류)")
                        continue

                    # 결과 파싱
                    output = result.stdout.strip()
                    import re

                    # 패턴 1: 코드블록 내 JSON
                    code_block_match = re.search(
                        r"```(?:json)?\s*(\{.*?\})\s*```", output, re.DOTALL
                    )
                    if code_block_match:
                        try:
                            prediction = json.loads(code_block_match.group(1))
                        except Exception:
                            print("❌ (파싱 오류)")
                            continue
                    else:
                        # 패턴 2: 일반 JSON
                        json_match = re.search(r"\{.*\}", output, re.DOTALL)
                        if json_match:
                            try:
                                prediction = json.loads(json_match.group())
                            except Exception:
                                print("❌ (파싱 오류)")
                                continue
                        else:
                            print("❌ (파싱 오류)")
                            continue

                    # 실제 결과 추출
                    with open(result_file, encoding="utf-8") as f:
                        full_data = json.load(f)

                    actual_result = []
                    for horse in full_data["horses"]:
                        if "result" in horse and 1 <= horse["result"]["ord"] <= 3:
                            actual_result.append(
                                (horse["result"]["ord"], horse["chul_no"])
                            )
                    actual_result.sort()
                    actual_nums = [x[1] for x in actual_result[:3]]

                    # 예측 결과 추출
                    predicted_horses = [
                        h["chul_no"] for h in prediction["selected_horses"]
                    ]

                    # 평가
                    correct_count = len(set(predicted_horses) & set(actual_nums))
                    total_races += 1
                    total_correct_horses += correct_count

                    if correct_count == 3:
                        successful_predictions += 1
                        print("✅ (3/3)")
                    elif correct_count == 2:
                        partial_correct_2 += 1
                        print("⚡ (2/3)")
                    elif correct_count == 1:
                        partial_correct_1 += 1
                        print("💫 (1/3)")
                    else:
                        print("❌ (0/3)")

                    # 결과 저장
                    batch_results.append(
                        {
                            "race_id": race_id,
                            "predicted": predicted_horses,
                            "actual": actual_nums,
                            "correct_count": correct_count,
                            "confidence": prediction.get("confidence", 0),
                        }
                    )

                except subprocess.TimeoutExpired:
                    print("⏱️  (타임아웃)")
                except Exception as e:
                    print(f"❌ ({type(e).__name__})")

                # API 제한 대응
                time.sleep(2)

            # 배치 결과 저장
            all_results.extend(batch_results)

            # 중간 진행 상황 저장
            progress = {
                "current_batch": i // batch_size + 1,
                "total_batches": (len(race_files) - 1) // batch_size + 1,
                "processed_races": total_races,
                "successful_predictions": successful_predictions,
                "partial_2": partial_correct_2,
                "partial_1": partial_correct_1,
                "current_success_rate": (
                    successful_predictions / total_races * 100 if total_races > 0 else 0
                ),
            }

            with open(progress_file, "w", encoding="utf-8") as f:
                json.dump(progress, f, ensure_ascii=False, indent=2)

            print(
                f"\n현재까지: {total_races}경주 처리, {successful_predictions}회 완전적중 ({progress['current_success_rate']:.1f}%)"
            )

            # 배치 간 휴식
            if i + batch_size < len(race_files):
                print("다음 배치 준비 중...")
                time.sleep(5)

        # 최종 결과 정리
        summary = {
            "prompt_version": self.prompt_version,
            "evaluation_date": timestamp,
            "total_races": total_races,
            "total_files": len(race_files),
            "successful_predictions": successful_predictions,
            "partial_correct_2": partial_correct_2,
            "partial_correct_1": partial_correct_1,
            "no_correct": total_races
            - successful_predictions
            - partial_correct_2
            - partial_correct_1,
            "success_rate": (
                successful_predictions / total_races * 100 if total_races > 0 else 0
            ),
            "average_correct_horses": (
                total_correct_horses / total_races if total_races > 0 else 0
            ),
            "total_correct_horses": total_correct_horses,
            "detailed_results": all_results,
        }

        # 결과 저장
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        # 요약 보고서 생성
        report_file = self.results_dir / f"summary_report_{timestamp}.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# 전체 경주 평가 보고서\n\n")
            f.write(
                f"- **평가 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            f.write(f"- **프롬프트 버전**: {self.prompt_version}\n")
            f.write(f"- **전체 경주 파일**: {len(race_files)}개\n")
            f.write(f"- **성공적으로 처리**: {total_races}개\n\n")
            f.write("## 적중 통계\n\n")
            f.write("| 구분 | 경주 수 | 비율 |\n")
            f.write("|------|---------|------|\n")
            f.write(
                f"| 완전 적중 (3/3) | {successful_predictions} | {successful_predictions / total_races * 100:.1f}% |\n"
            )
            f.write(
                f"| 2마리 적중 (2/3) | {partial_correct_2} | {partial_correct_2 / total_races * 100:.1f}% |\n"
            )
            f.write(
                f"| 1마리 적중 (1/3) | {partial_correct_1} | {partial_correct_1 / total_races * 100:.1f}% |\n"
            )
            f.write(
                f"| 미적중 (0/3) | {total_races - successful_predictions - partial_correct_2 - partial_correct_1} | {(total_races - successful_predictions - partial_correct_2 - partial_correct_1) / total_races * 100:.1f}% |\n"
            )
            f.write(
                f"\n**평균 적중 말 수**: {summary['average_correct_horses']:.2f}/3\n"
            )

        print("\n" + "=" * 60)
        print("전체 평가 완료!")
        print(f"결과 파일: {results_file}")
        print(f"요약 보고서: {report_file}")

        return summary


def main():
    if len(sys.argv) < 3:
        print("Usage: python evaluate_all_races.py <prompt_version> <prompt_file>")
        print(
            "Example: python evaluate_all_races.py v2.1-optimized prompts/prediction-template-optimized.md"
        )
        sys.exit(1)

    prompt_version = sys.argv[1]
    prompt_file = sys.argv[2]

    # 전체 평가 실행
    evaluator = FullEvaluator(prompt_version, prompt_file)
    race_files = evaluator.find_all_result_files()

    # 확인
    print(f"\n전체 {len(race_files)}개 경주를 평가하시겠습니까?")
    print(f"예상 소요 시간: 약 {len(race_files) * 3 / 60:.1f}시간")
    response = input("계속하시겠습니까? (y/n): ")

    if response.lower() != "y":
        print("평가를 취소했습니다.")
        return

    # 평가 실행
    evaluator.run_prediction_batch(race_files, batch_size=10)


if __name__ == "__main__":
    main()
