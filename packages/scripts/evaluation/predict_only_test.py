#!/usr/bin/env python3
"""
경주 전 데이터로 예측만 수행하는 테스트 스크립트
- 실제 결과와의 비교 없음
- enriched 데이터를 사용하여 예측 수행
- 예측 결과와 분석 정보만 출력
"""
from __future__ import annotations

import glob
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# shared 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))
from feature_engineering import compute_race_features
from shared.claude_client import ClaudeClient


class PredictionTester:
    def __init__(self, prompt_path: str):
        self.prompt_path = prompt_path
        self.predictions_dir = Path("data/prediction_tests")
        self.predictions_dir.mkdir(parents=True, exist_ok=True)

        # Claude CLI 클라이언트 (구독 플랜)
        self.client = ClaudeClient()

    def find_enriched_files(
        self, date_filter: str | None = None
    ) -> list[dict[str, any]]:
        """enriched 파일 찾기"""
        enriched_files = []

        if date_filter and date_filter != "all":
            pattern = f"data/races/*/*/{date_filter}/*/*_enriched.json"
        else:
            pattern = "data/races/*/*/*/*/*_enriched.json"

        files = sorted(glob.glob(pattern))

        for file in files:
            path_parts = file.split("/")
            filename = path_parts[-1]

            # 파일명에서 정보 추출
            race_prefix = "_".join(filename.split("_")[0:2])
            race_date = filename.split("_")[2]
            race_no = filename.split("_")[3].replace("_enriched.json", "")

            # meet 정보 추출
            meet = path_parts[-2]
            meet_map = {"seoul": "서울", "jeju": "제주", "busan": "부산경남"}

            enriched_files.append(
                {
                    "file_path": Path(file),
                    "race_id": f"{race_prefix}_{race_date}_{race_no}",
                    "race_date": race_date,
                    "race_no": race_no,
                    "meet": meet_map.get(meet, "서울"),
                }
            )

        return enriched_files

    def load_race_data(self, file_info: dict) -> dict | None:
        """enriched 파일에서 경주 데이터 로드"""
        try:
            with open(file_info["file_path"], encoding="utf-8") as f:
                data = json.load(f)

            # API 응답 형식에서 실제 데이터 추출
            if "response" in data and "body" in data["response"]:
                items = data["response"]["body"]["items"]["item"]

                # 데이터 정리 및 필터링
                horses = []
                for item in items:
                    # 기권/제외 말 필터링
                    if item.get("winOdds", 999) == 0:
                        continue

                    # wgHr 파싱: "470(+5)" 형태에서 숫자만 추출
                    wgHr_str = item.get("wgHr", "")
                    wgHr_match = re.match(r"(\d+)", wgHr_str)
                    wgHr_value = int(wgHr_match.group(1)) if wgHr_match else None

                    horse = {
                        "chulNo": item["chulNo"],
                        "hrName": item["hrName"],
                        "hrNo": item["hrNo"],
                        "jkName": item["jkName"],
                        "jkNo": item["jkNo"],
                        "trName": item["trName"],
                        "trNo": item["trNo"],
                        "winOdds": item["winOdds"],
                        "plcOdds": item.get("plcOdds"),
                        "budam": item.get("budam", ""), # '핸디캡' 등의 문자열
                        "wgBudam": item.get("wgBudam"), # 숫자 값 (52.0 등)
                        "wgHr": wgHr_value, # 파싱된 숫자 값
                        "age": item.get("age"),
                        "sex": item.get("sex", ""),
                        "rank": item.get("rank", ""), # '국5등급' 등
                        "rating": item.get("rating"),
                        "rcDist": item.get("rcDist"), # 경주거리 추가
                        "ilsu": item.get("ilsu"), # 장기휴양 리스크 계산을 위한 일수 추가
                        # 기타 필요한 데이터 추가 (예: 구간 기록 등)
                        "se_3cAccTime": item.get("se_3cAccTime"),
                        "se_4cAccTime": item.get("se_4cAccTime"),
                        "sj_3cOrd": item.get("sj_3cOrd"),
                        "sj_4cOrd": item.get("sjS1fOrd"),
                        "seS1fAccTime": item.get("seS1fAccTime"),
                        "sjS1fOrd": item.get("sjS1fOrd"),
                        "seG1fAccTime": item.get("seG1fAccTime"),
                        "sjG1fOrd": item.get("sjG1fOrd"),
                    }

                    # enriched 데이터 추가
                    if "hrDetail" in item:
                        horse["hrDetail"] = item["hrDetail"]
                    if "jkDetail" in item:
                        horse["jkDetail"] = item["jkDetail"]
                    if "trDetail" in item:
                        horse["trDetail"] = item["trDetail"]

                    horses.append(horse)

                # Feature Engineering: 파생 피처 계산
                horses = compute_race_features(horses)

                # raceInfo 추출 (첫 번째 말의 공통 정보 사용)
                first_horse_item = items[0] if items else {}
                race_distance = first_horse_item.get("rcDist") # rcDist에서 경주거리 가져오기

                return {
                    "meet": file_info["meet"],
                    "rcDate": file_info["race_date"],
                    "rcNo": file_info["race_no"],
                    "horses": horses,
                    "raceInfo": {
                        "distance": race_distance,
                        "grade": first_horse_item.get("rank", ""), # 등급 추가
                        "track": first_horse_item.get("track", ""),
                        "weather": first_horse_item.get("weather", ""),
                        "budam": first_horse_item.get("budam", ""), # 부담조건 추가
                    },
                }

            return None
        except Exception as e:
            print(f"데이터 로드 오류 ({file_info['race_id']}): {e}")
            return None

    def run_prediction(self, race_data: dict, race_id: str) -> dict | None:
        """Claude를 사용하여 예측 수행"""
        try:
            # 프롬프트 읽기
            with open(self.prompt_path, encoding="utf-8") as f:
                prompt_template = f.read()

            # 데이터를 프롬프트에 포함
            # {{RACE_DATA}} 플레이스홀더가 있으면 대체하고, 없으면 뒤에 추가
            race_data_json_str = json.dumps(race_data, ensure_ascii=False, indent=2)

            if "{{RACE_DATA}}" in prompt_template:
                prompt = prompt_template.replace("{{RACE_DATA}}", race_data_json_str)
            else:
                prompt = f"{prompt_template}\n\n<race_data>\n{race_data_json_str}\n</race_data>"

            # 클로드에게 명확하게 JSON만 출력하도록 지시 (프롬프트 최하단에 배치)
            prompt += "\n\nIMPORTANT: You must act as a prediction API. Do not analyze the prompt itself. Analyze the race data provided above and Output ONLY the JSON object as specified in <output_format>. Do not output any markdown code block markers (```json), introductory text, or explanations. Just the raw JSON string."

            start_time = time.time()

            # Claude CLI를 통한 예측 호출 (구독 플랜)
            output = self.client.predict_sync(prompt)

            execution_time = time.time() - start_time

            if output is None:
                print(f"예측 오류 ({race_id}): API 호출 실패 또는 타임아웃")
                return None

            # 응답 파싱
            try:
                # JSON 블록 추출 시도 (유연하게)
                # 1. 마크다운 코드 블록 확인
                json_match = re.search(r"```json\s*(\{.*?\})\s*```", output, re.DOTALL)

                # 2. 코드 블록 없으면 가장 바깥쪽 중괄호 쌍 찾기
                if not json_match:
                    json_match = re.search(r"(\{.*\})", output, re.DOTALL)

                if json_match:
                    json_str = json_match.group(1)
                    prediction_data = json.loads(json_str)

                    # `predicted` 필드가 최상위에 없으면 trifecta_picks.primary에서 가져옴 (하위 호환성)
                    predicted_list = prediction_data.get("predicted", prediction_data.get("trifecta_picks", {}).get("primary", []))

                    return {
                        "race_id": race_id,
                        "predicted": predicted_list,
                        "confidence": prediction_data.get("trifecta_picks", {}).get("confidence", 0),
                        "reason": prediction_data.get("analysis_summary", ""),
                        "execution_time": execution_time,
                        "full_output": output,
                    }
                else:
                    print(f"JSON 파싱 실패 ({race_id}). JSON 구조를 찾을 수 없습니다.")
                    return None

            except json.JSONDecodeError as e:
                print(f"JSON 디코딩 오류 ({race_id}): {e}")
                return None

        except Exception as e:
            print(f"예측 중 오류 ({race_id}): {e}")
            return None

    def analyze_prediction(self, prediction: dict, race_data: dict) -> dict:
        """예측 결과 분석"""
        analysis = {
            "race_id": prediction["race_id"],
            "predicted_horses": [],
            "prediction_strategy": "",
            "confidence_level": "",
            "execution_time": prediction["execution_time"],
        }

        # 예측한 말들의 정보 수집
        horses_dict = {h["chulNo"]: h for h in race_data["horses"]}

        for chul_no in prediction["predicted"]:
            if chul_no in horses_dict:
                horse = horses_dict[chul_no]

                # 배당률 순위 계산
                sorted_horses = sorted(race_data["horses"], key=lambda x: x["winOdds"])
                odds_rank = next(
                    (
                        i + 1
                        for i, h in enumerate(sorted_horses)
                        if h["chulNo"] == chul_no
                    ),
                    0,
                )

                horse_info = {
                    "chulNo": chul_no,
                    "hrName": horse["hrName"],
                    "winOdds": horse["winOdds"],
                    "oddsRank": odds_rank,
                    "jkName": horse["jkName"],
                }

                # 기수 승률 추가
                if "jkDetail" in horse:
                    jk = horse["jkDetail"]
                    if jk.get("rcCntT", 0) > 0:
                        horse_info["jkWinRate"] = round(
                            (jk.get("ord1CntT", 0) / jk["rcCntT"]) * 100, 1
                        )

                # 말 입상률 추가
                if "hrDetail" in horse:
                    hr = horse["hrDetail"]
                    if hr.get("rcCntT", 0) > 0:
                        place_cnt = (
                            hr.get("ord1CntT", 0)
                            + hr.get("ord2CntT", 0)
                            + hr.get("ord3CntT", 0)
                        )
                        horse_info["hrPlaceRate"] = round(
                            (place_cnt / hr["rcCntT"]) * 100, 1
                        )

                analysis["predicted_horses"].append(horse_info)

        # 예측 전략 분석
        avg_odds_rank = sum(h["oddsRank"] for h in analysis["predicted_horses"]) / 3
        if avg_odds_rank <= 3:
            analysis["prediction_strategy"] = "인기마 중심"
        elif avg_odds_rank <= 5:
            analysis["prediction_strategy"] = "중간 배당"
        else:
            analysis["prediction_strategy"] = "고배당 도전"

        # 신뢰도 수준
        confidence = prediction["confidence"]
        if confidence >= 80:
            analysis["confidence_level"] = "매우 높음"
        elif confidence >= 70:
            analysis["confidence_level"] = "높음"
        elif confidence >= 60:
            analysis["confidence_level"] = "보통"
        else:
            analysis["confidence_level"] = "낮음"

        return analysis

    def run_test(self, date_filter: str | None = None, limit: int | None = None):
        """예측 테스트 실행"""
        print(f"\n{'='*60}")
        print("경주 예측 테스트 시작")
        print(f"프롬프트: {self.prompt_path}")
        print(f"날짜 필터: {date_filter if date_filter else '전체'}")
        print(f"{'='*60}\n")

        # enriched 파일 찾기
        enriched_files = self.find_enriched_files(date_filter)

        if limit:
            enriched_files = enriched_files[:limit]

        print(f"테스트할 경주: {len(enriched_files)}개\n")

        predictions = []
        analyses = []

        for i, file_info in enumerate(enriched_files):
            print(f"\n[{i+1}/{len(enriched_files)}] {file_info['race_id']} 예측 중...")

            # 경주 데이터 로드
            race_data = self.load_race_data(file_info)
            if not race_data:
                print("  ❌ 데이터 로드 실패")
                continue

            print(f"  - 출주마: {len(race_data['horses'])}마리")

            # 예측 수행
            prediction = self.run_prediction(race_data, file_info["race_id"])
            if not prediction:
                print("  ❌ 예측 실패")
                continue

            predictions.append(prediction)

            # 예측 분석
            analysis = self.analyze_prediction(prediction, race_data)
            analyses.append(analysis)

            # 결과 출력
            print(f"  ✅ 예측 완료 (실행시간: {prediction['execution_time']:.1f}초)")
            print(f"  - 예측: {prediction['predicted']}")
            print(f"  - 신뢰도: {prediction['confidence']}%")
            print(f"  - 이유: {prediction['reason']}")
            print(f"  - 전략: {analysis['prediction_strategy']}")

            # 예측한 말들 정보
            print("  - 예측 말 정보:")
            for horse in analysis["predicted_horses"]:
                info_parts = [f"{horse['chulNo']}번 {horse['hrName']}"]
                info_parts.append(
                    f"배당률 {horse['oddsRank']}위({horse['winOdds']:.1f})"
                )
                if "jkWinRate" in horse:
                    info_parts.append(f"기수승률 {horse['jkWinRate']}%")
                if "hrPlaceRate" in horse:
                    info_parts.append(f"말입상률 {horse['hrPlaceRate']}%")
                print(f"    • {' / '.join(info_parts)}")

        # 전체 통계
        self.print_summary(predictions, analyses)

        # 결과 저장
        self.save_results(predictions, analyses, date_filter)

    def print_summary(self, predictions: list[dict], analyses: list[dict]):
        """전체 예측 요약 출력"""
        if not predictions:
            print("\n예측 결과가 없습니다.")
            return

        print(f"\n\n{'='*60}")
        print("예측 테스트 요약")
        print(f"{'='*60}")

        print("\n📊 기본 통계:")
        print(f"- 총 예측 수: {len(predictions)}개")
        avg_execution_time = sum(p["execution_time"] for p in predictions) / len(
            predictions
        )
        print(f"- 평균 실행 시간: {avg_execution_time:.1f}초")

        # 신뢰도 분포
        confidence_bins = {"80+": 0, "70-79": 0, "60-69": 0, "60-": 0}
        for p in predictions:
            conf = p["confidence"]
            if conf >= 80:
                confidence_bins["80+"] += 1
            elif conf >= 70:
                confidence_bins["70-79"] += 1
            elif conf >= 60:
                confidence_bins["60-69"] += 1
            else:
                confidence_bins["60-"] += 1

        print("\n📈 신뢰도 분포:")
        for range_name, count in confidence_bins.items():
            percentage = (count / len(predictions)) * 100
            print(f"- {range_name}%: {count}개 ({percentage:.1f}%)")

        # 전략 분포
        strategy_counts = {}
        for a in analyses:
            strategy = a["prediction_strategy"]
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

        print("\n🎯 예측 전략 분포:")
        for strategy, count in sorted(
            strategy_counts.items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (count / len(analyses)) * 100
            print(f"- {strategy}: {count}개 ({percentage:.1f}%)")

        # 평균 배당률 순위
        all_odds_ranks = []
        for a in analyses:
            for h in a["predicted_horses"]:
                all_odds_ranks.append(h["oddsRank"])

        if all_odds_ranks:
            avg_odds_rank = sum(all_odds_ranks) / len(all_odds_ranks)
            print(f"\n💰 평균 선택 배당률 순위: {avg_odds_rank:.1f}위")

    def save_results(
        self, predictions: list[dict], analyses: list[dict], date_filter: str | None
    ):
        """예측 결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = (
            f"prediction_test_{date_filter if date_filter else 'all'}_{timestamp}.json"
        )
        filepath = self.predictions_dir / filename

        results = {
            "test_info": {
                "prompt_path": str(self.prompt_path),
                "test_date": datetime.now().isoformat(),
                "date_filter": date_filter,
                "total_predictions": len(predictions),
            },
            "predictions": predictions,
            "analyses": analyses,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n📄 결과 저장: {filepath}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python predict_only_test.py <prompt_file> [date_filter] [limit]")
        print("\nExamples:")
        print("  모든 경주: python predict_only_test.py prompts/base-prompt-v1.0.md")
        print(
            "  특정 날짜: python predict_only_test.py prompts/base-prompt-v1.0.md 20250601"
        )
        print(
            "  개수 제한: python predict_only_test.py prompts/base-prompt-v1.0.md all 10"
        )
        sys.exit(1)

    prompt_file = sys.argv[1]
    date_filter = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "all" else None
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else None

    # 파일 존재 확인
    if not Path(prompt_file).exists():
        print(f"Error: 프롬프트 파일을 찾을 수 없습니다: {prompt_file}")
        sys.exit(1)

    # 테스터 실행
    tester = PredictionTester(prompt_file)
    tester.run_test(date_filter, limit)


if __name__ == "__main__":
    main()
