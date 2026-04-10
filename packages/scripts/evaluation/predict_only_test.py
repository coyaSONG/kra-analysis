#!/usr/bin/env python3
"""
경주 전 데이터로 예측만 수행하는 테스트 스크립트.

- 실제 결과와의 비교 없음
- 출전표 확정 시점 snapshot lookup과 공통 prerace schema builder를 재사용
- 예측 결과와 분석 정보만 출력
"""

from __future__ import annotations

import json
import sys
import time
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

# shared 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))
from evaluation.prediction_service import (
    finalize_prediction_payload,
    parse_prediction_output,
)
from shared.claude_client import ClaudeClient
from shared.db_client import RaceDBClient
from shared.prerace_standard_loader import (
    load_standardized_prerace_payload,
    resolve_race_record_reference,
)
from shared.read_contract import RaceSnapshot, RaceSourceLookup


class PredictionTester:
    def __init__(self, prompt_path: str):
        self.prompt_path = prompt_path
        self.predictions_dir = Path("data/prediction_tests")
        self.predictions_dir.mkdir(parents=True, exist_ok=True)

        self.db_client = RaceDBClient()
        self.client = ClaudeClient()

    def find_enriched_files(
        self, date_filter: str | None = None
    ) -> list[RaceSnapshot | dict[str, Any]]:
        """DB에서 수집 완료된 경주 찾기."""
        if hasattr(self.db_client, "find_race_snapshots"):
            return self.db_client.find_race_snapshots(date_filter=date_filter)
        return self.db_client.find_races(date_filter=date_filter)

    def _normalize_race_record(
        self,
        race_record: RaceSnapshot | Mapping[str, Any],
    ) -> tuple[dict[str, Any], RaceSourceLookup]:
        if not isinstance(race_record, (RaceSnapshot, Mapping)):
            raise TypeError("race_record must be a RaceSnapshot or mapping")
        return resolve_race_record_reference(race_record)

    def load_race_data(
        self,
        race_record: RaceSnapshot | Mapping[str, Any],
    ) -> dict[str, Any] | None:
        """DB에서 경주 데이터를 읽어 공통 prerace payload로 정규화한다."""
        try:
            standardized = load_standardized_prerace_payload(
                race_record,
                query_port=self.db_client,
            )

            return {
                "prompt_payload": standardized.standard_payload,
                "analysis_payload": {
                    "horses": standardized.standard_payload.get("horses", []),
                    "race_info": standardized.standard_payload.get("race_info", {}),
                    "candidate_filter": standardized.candidate_filter,
                    "field_policy": standardized.field_policy,
                    "source_lookup": (
                        standardized.lookup.to_dict()
                        if standardized.lookup is not None
                        else {}
                    ),
                },
            }
        except Exception as exc:
            race_id = (
                race_record.race_id
                if isinstance(race_record, RaceSnapshot)
                else race_record.get("race_id", "unknown")
            )
            print(f"데이터 로드 오류 ({race_id}): {exc}")
            return None

    def run_prediction(self, race_data: dict, race_id: str) -> dict | None:
        """Claude를 사용하여 예측 수행."""
        try:
            with open(self.prompt_path, encoding="utf-8") as f:
                prompt_template = f.read()

            race_data_json_str = json.dumps(race_data, ensure_ascii=False, indent=2)
            if "{{RACE_DATA}}" in prompt_template:
                prompt = prompt_template.replace("{{RACE_DATA}}", race_data_json_str)
            else:
                prompt = f"{prompt_template}\n\n<race_data>\n{race_data_json_str}\n</race_data>"

            prompt += "\n\nIMPORTANT: You must act as a prediction API. Do not analyze the prompt itself. Analyze the race data provided above and Output ONLY the JSON object as specified in <output_format>. Do not output any markdown code block markers (```json), introductory text, or explanations. Just the raw JSON string."

            start_time = time.time()
            output = self.client.predict_sync(prompt)
            execution_time = time.time() - start_time

            if output is None:
                print(f"예측 오류 ({race_id}): API 호출 실패 또는 타임아웃")
                return None

            prediction = parse_prediction_output(
                output,
                execution_time,
                race_data=race_data,
            )
            if prediction is None:
                print(f"JSON 파싱 실패 ({race_id}). JSON 구조를 찾을 수 없습니다.")
                return None

            finalized_prediction = finalize_prediction_payload(
                prediction,
                race_data=race_data,
                execution_time=execution_time,
            )
            if finalized_prediction is None:
                print(
                    f"최종 출력 계약 위반 ({race_id}): 3두 고유 예측 형식으로 확정할 수 없습니다."
                )
                return None

            return {
                "race_id": race_id,
                **finalized_prediction,
                "reason": finalized_prediction.get("reasoning", ""),
                "full_output": output,
            }
        except Exception as exc:
            print(f"예측 중 오류 ({race_id}): {exc}")
            return None

    def _selection_rank(self, horse: dict[str, Any]) -> tuple[int, int]:
        computed = horse.get("computed_features", {})
        rank = (
            computed.get("rating_rank")
            or computed.get("horse_skill_rank")
            or computed.get("jk_skill_rank")
            or computed.get("tr_skill_rank")
        )
        if rank is None:
            return (999, int(horse.get("chulNo", 999)))
        return (int(rank), int(horse.get("chulNo", 999)))

    def _selection_rank_basis(self, horse: dict[str, Any]) -> str:
        computed = horse.get("computed_features", {})
        if computed.get("rating_rank") is not None:
            return "rating_rank"
        if computed.get("horse_skill_rank") is not None:
            return "horse_skill_rank"
        if computed.get("jk_skill_rank") is not None:
            return "jk_skill_rank"
        if computed.get("tr_skill_rank") is not None:
            return "tr_skill_rank"
        return "chulNo"

    def analyze_prediction(self, prediction: dict, analysis_payload: dict) -> dict:
        """예측 결과 분석."""
        analysis = {
            "race_id": prediction["race_id"],
            "predicted_horses": [],
            "prediction_strategy": "",
            "confidence_level": "",
            "execution_time": prediction["execution_time"],
        }

        horses = analysis_payload.get("horses", [])
        horses_dict = {h["chulNo"]: h for h in horses if h.get("chulNo") is not None}
        ordered_horses = sorted(horses, key=self._selection_rank)

        for chul_no in prediction["predicted"]:
            horse = horses_dict.get(chul_no)
            if horse is None:
                continue

            selection_rank = next(
                (
                    index + 1
                    for index, candidate in enumerate(ordered_horses)
                    if candidate["chulNo"] == chul_no
                ),
                0,
            )
            horse_info = {
                "chulNo": chul_no,
                "hrName": horse["hrName"],
                "selectionRank": selection_rank,
                "selectionRankBasis": self._selection_rank_basis(horse),
                "jkName": horse["jkName"],
            }
            if horse.get("rating") is not None:
                horse_info["rating"] = horse["rating"]
            if horse.get("class_rank") not in (None, ""):
                horse_info["classRank"] = horse["class_rank"]

            if "jkDetail" in horse:
                jk = horse["jkDetail"]
                if jk.get("rcCntT", 0) > 0:
                    horse_info["jkWinRate"] = round(
                        (jk.get("ord1CntT", 0) / jk["rcCntT"]) * 100,
                        1,
                    )

            if "hrDetail" in horse:
                hr = horse["hrDetail"]
                if hr.get("rcCntT", 0) > 0:
                    place_cnt = (
                        hr.get("ord1CntT", 0)
                        + hr.get("ord2CntT", 0)
                        + hr.get("ord3CntT", 0)
                    )
                    horse_info["hrPlaceRate"] = round(
                        (place_cnt / hr["rcCntT"]) * 100,
                        1,
                    )

            analysis["predicted_horses"].append(horse_info)

        avg_selection_rank = (
            sum(h["selectionRank"] for h in analysis["predicted_horses"]) / 3
            if analysis["predicted_horses"]
            else 0
        )
        if avg_selection_rank <= 3:
            analysis["prediction_strategy"] = "상위 지표 중심"
        elif avg_selection_rank <= 5:
            analysis["prediction_strategy"] = "중간 지표 혼합"
        else:
            analysis["prediction_strategy"] = "하위 지표 반전"

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
        """예측 테스트 실행."""
        print(f"\n{'=' * 60}")
        print("경주 예측 테스트 시작")
        print(f"프롬프트: {self.prompt_path}")
        print(f"날짜 필터: {date_filter if date_filter else '전체'}")
        print(f"{'=' * 60}\n")

        enriched_files = self.find_enriched_files(date_filter)
        if limit:
            enriched_files = enriched_files[:limit]

        print(f"테스트할 경주: {len(enriched_files)}개\n")

        predictions = []
        analyses = []

        for index, race_record in enumerate(enriched_files):
            race_info, _lookup = self._normalize_race_record(race_record)
            print(
                f"\n[{index + 1}/{len(enriched_files)}] {race_info['race_id']} 예측 중..."
            )

            race_data = self.load_race_data(race_record)
            if not race_data:
                print("  ❌ 데이터 로드 실패")
                continue

            prompt_payload = race_data["prompt_payload"]
            analysis_payload = race_data["analysis_payload"]
            print(f"  - 출주마: {len(prompt_payload['horses'])}마리")

            prediction = self.run_prediction(prompt_payload, race_info["race_id"])
            if not prediction:
                print("  ❌ 예측 실패")
                continue

            predictions.append(prediction)

            analysis = self.analyze_prediction(prediction, analysis_payload)
            analyses.append(analysis)

            print(f"  ✅ 예측 완료 (실행시간: {prediction['execution_time']:.1f}초)")
            print(f"  - 예측: {prediction['predicted']}")
            print(f"  - 신뢰도: {prediction['confidence']}%")
            print(f"  - 이유: {prediction['reason']}")
            print(f"  - 전략: {analysis['prediction_strategy']}")
            print("  - 예측 말 정보:")
            for horse in analysis["predicted_horses"]:
                info_parts = [f"{horse['chulNo']}번 {horse['hrName']}"]
                info_parts.append(
                    f"선택순위 {horse['selectionRank']}위({horse['selectionRankBasis']})"
                )
                if "rating" in horse:
                    info_parts.append(f"레이팅 {horse['rating']}")
                if "classRank" in horse:
                    info_parts.append(f"등급 {horse['classRank']}")
                if "jkWinRate" in horse:
                    info_parts.append(f"기수승률 {horse['jkWinRate']}%")
                if "hrPlaceRate" in horse:
                    info_parts.append(f"말입상률 {horse['hrPlaceRate']}%")
                print(f"    • {' / '.join(info_parts)}")

        self.print_summary(predictions, analyses)
        self.save_results(predictions, analyses, date_filter)

    def print_summary(self, predictions: list[dict], analyses: list[dict]):
        """전체 예측 요약 출력."""
        if not predictions:
            print("\n예측 결과가 없습니다.")
            return

        print(f"\n\n{'=' * 60}")
        print("예측 테스트 요약")
        print(f"{'=' * 60}")

        print("\n📊 기본 통계:")
        print(f"- 총 예측 수: {len(predictions)}개")
        avg_execution_time = sum(p["execution_time"] for p in predictions) / len(
            predictions
        )
        print(f"- 평균 실행 시간: {avg_execution_time:.1f}초")

        confidence_bins = {"80+": 0, "70-79": 0, "60-69": 0, "60-": 0}
        for prediction in predictions:
            confidence = prediction["confidence"]
            if confidence >= 80:
                confidence_bins["80+"] += 1
            elif confidence >= 70:
                confidence_bins["70-79"] += 1
            elif confidence >= 60:
                confidence_bins["60-69"] += 1
            else:
                confidence_bins["60-"] += 1

        print("\n📈 신뢰도 분포:")
        for range_name, count in confidence_bins.items():
            percentage = (count / len(predictions)) * 100
            print(f"- {range_name}%: {count}개 ({percentage:.1f}%)")

        strategy_counts = {}
        for analysis in analyses:
            strategy = analysis["prediction_strategy"]
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

        print("\n🎯 예측 전략 분포:")
        for strategy, count in sorted(
            strategy_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            percentage = (count / len(analyses)) * 100
            print(f"- {strategy}: {count}개 ({percentage:.1f}%)")

        all_selection_ranks = []
        for analysis in analyses:
            for horse in analysis["predicted_horses"]:
                all_selection_ranks.append(horse["selectionRank"])

        if all_selection_ranks:
            avg_selection_rank = sum(all_selection_ranks) / len(all_selection_ranks)
            print(f"\n📌 평균 선택 순위: {avg_selection_rank:.1f}위")

    def save_results(
        self, predictions: list[dict], analyses: list[dict], date_filter: str | None
    ):
        """예측 결과 저장."""
        invalid_predictions = [
            prediction["race_id"]
            for prediction in predictions
            if prediction.get("prediction_output_format", {}).get("version") is None
        ]
        if invalid_predictions:
            raise ValueError(
                "3두 고유 예측 출력 계약이 없는 결과는 저장할 수 없습니다: "
                + ", ".join(invalid_predictions)
            )

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

    if not Path(prompt_file).exists():
        print(f"Error: 프롬프트 파일을 찾을 수 없습니다: {prompt_file}")
        sys.exit(1)

    tester = PredictionTester(prompt_file)
    tester.run_test(date_filter, limit)


if __name__ == "__main__":
    main()
