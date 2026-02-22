#!/usr/bin/env python3
"""
프롬프트 재귀 개선을 위한 평가 시스템 v3
- Claude CLI 헤드리스 모드 (구독 플랜 활용)
- JSON 응답 파싱 (코드블록 + regex fallback)
- 향상된 안정성
"""

import argparse
import json
import re
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

# shared 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))
from evaluation.ensemble import SelfConsistencyEnsemble
from evaluation.leakage_checks import check_detailed_results_for_leakage
from evaluation.metrics import compute_prediction_quality_metrics
from evaluation.mlflow_tracker import ExperimentTracker
from evaluation.report_schema import build_report_v2, validate_report_v2
from evaluation.run_metadata import build_run_metadata
from feature_engineering import compute_race_features
from shared.claude_client import ClaudeClient
from shared.data_adapter import convert_basic_data_to_enriched_format
from shared.db_client import RaceDBClient
from shared.llm_client import LLMClient


class PromptEvaluatorV3:
    def __init__(
        self,
        prompt_version: str,
        prompt_path: str,
        topk_values: tuple[int, ...] = (1, 3),
        ece_bins: int = 10,
        asof_check: str = "on",
        report_format: str = "v2",
        metrics_profile: str = "rpi_v1",
        defer_threshold: float | None = None,
        ensemble_k: int = 1,
        jury_enabled: bool = False,
        jury_models: list[str] | None = None,
        jury_weights: dict[str, float] | None = None,
        data_snapshot_id: str = "db_latest",
        seed: int = 42,
        mode: str = "evaluation",
    ):
        self.prompt_version = prompt_version
        self.prompt_path = prompt_path
        self.results_dir = Path("data/prompt_evaluation")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.api_lock = threading.Semaphore(3)  # API 동시 호출 제한
        self.error_stats = defaultdict(int)  # 에러 통계
        self.topk_values = topk_values
        self.ece_bins = ece_bins
        self.asof_check = asof_check
        self.report_format = report_format
        self.metrics_profile = metrics_profile
        self.defer_threshold = defer_threshold
        self.ensemble_k = ensemble_k
        self.data_snapshot_id = data_snapshot_id
        self.seed = seed
        self.mode = mode
        self.ensemble = (
            SelfConsistencyEnsemble(k=ensemble_k) if ensemble_k > 1 else None
        )

        # DB 클라이언트
        self.db_client = RaceDBClient()

        # Claude CLI 클라이언트 (구독 플랜)
        self.client = ClaudeClient()

        # MLflow experiment tracker
        self.tracker = ExperimentTracker()

        # LLM Jury 설정
        self.jury_enabled = jury_enabled
        self.jury = None
        self.jury_ensemble = None

        if jury_enabled:
            self._init_jury(jury_models or ["claude", "codex", "gemini"], jury_weights)

    def _init_jury(
        self, model_names: list[str], weights: dict[str, float] | None = None
    ) -> None:
        """LLM Jury 초기화: 지정된 모델 클라이언트 생성 + Jury + Ensemble"""
        from evaluation.jury_ensemble import JuryEnsemble
        from shared.llm_client import CodexClient, GeminiClient
        from shared.llm_jury import LLMJury

        clients: list[LLMClient] = []
        for name in model_names:
            if name == "claude":
                clients.append(self.client)  # 기존 ClaudeClient 재사용
            elif name == "codex":
                clients.append(CodexClient())
            elif name == "gemini":
                clients.append(GeminiClient())

        if clients:
            self.jury = LLMJury(clients)
            self.jury_ensemble = JuryEnsemble(model_weights=weights)

    def find_test_races(self, limit: int = None) -> list[dict[str, Any]]:
        """DB에서 수집 완료된 경주 찾기"""
        races = self.db_client.find_races(limit=limit)
        print(f"테스트할 경주: {len(races)}개 (DB 데이터)")
        return races

    def load_race_data(self, race_info: dict) -> dict | None:
        """DB에서 경주 데이터 로드"""
        try:
            basic_data = self.db_client.load_race_basic_data(race_info["race_id"])
            if not basic_data:
                return None

            # DB 데이터를 평가 스크립트 호환 포맷으로 변환
            data = convert_basic_data_to_enriched_format(basic_data)
            if not data:
                return None

            # API 응답 형식에서 실제 데이터 추출
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
                    "wgBudam": item.get("wgBudam", 0),
                    "winOdds": item["winOdds"],
                    "plcOdds": item.get("plcOdds", 0),
                    "rating": item.get("rating", 0),
                    "rank": item.get("rank", ""),
                    "age": item.get("age", 0),
                    "sex": item.get("sex", ""),
                    # 보강된 데이터
                    "hrDetail": item.get("hrDetail", {}),
                    "jkDetail": item.get("jkDetail", {}),
                    "trDetail": item.get("trDetail", {}),
                }

                horses.append(horse)

            # Feature Engineering: 파생 피처 계산
            horses = compute_race_features(horses)

            # 경주 정보 구성
            race_data = {
                "raceInfo": {
                    "rcDate": items[0]["rcDate"],
                    "rcNo": items[0]["rcNo"],
                    "rcName": items[0].get("rcName", ""),
                    "rcDist": items[0]["rcDist"],
                    "track": items[0].get("track", ""),
                    "weather": items[0].get("weather", ""),
                    "meet": items[0]["meet"],
                },
                "horses": horses,
            }

            return race_data

        except Exception as e:
            print(f"데이터 로드 오류: {e}")
            return None

    def run_claude_prediction(
        self, race_data: dict, race_id: str
    ) -> tuple[dict | None, str]:
        """Anthropic SDK를 통한 예측 실행"""
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
            # Claude CLI를 통한 예측 호출 (Opus 모델, 구독 플랜)
            with self.api_lock:
                response_text = self.client.predict_sync_compat(
                    prompt,
                    model="opus",
                    max_tokens=4096,
                    timeout=3000,
                )

            execution_time = time.time() - start_time

            if response_text is None:
                error_type = "claude_error"
                self.error_stats[error_type] += 1
                print(f"Claude API 호출 실패 (race {race_id})")
                return None, error_type

            # 응답 텍스트에서 JSON 파싱
            prediction = self._parse_stream_json(response_text, execution_time)
            if prediction:
                return prediction, error_type

            # 파싱 실패 시 일반 출력으로 시도
            prediction = self._parse_regular_output(response_text, execution_time)
            if prediction:
                return prediction, error_type

            error_type = "json_parse_error"
            self.error_stats[error_type] += 1
            return None, error_type

        except Exception as e:
            error_type = "unknown_error"
            self.error_stats[error_type] += 1
            print(f"Error predicting race {race_id}: {e}")
            return None, error_type

    def run_ensemble_prediction(
        self, race_data: dict, race_id: str
    ) -> tuple[dict | None, str]:
        """Run K predictions and aggregate via ensemble."""
        if self.ensemble is None or self.ensemble_k <= 1:
            return self.run_claude_prediction(race_data, race_id)

        predictions = []
        last_error = "success"

        for _i in range(self.ensemble_k):
            result, error_type = self.run_claude_prediction(race_data, race_id)
            if result is not None:
                predictions.append(result)
            else:
                last_error = error_type

        if not predictions:
            return None, last_error

        # Extract predicted horse numbers from each prediction for aggregation
        pred_dicts = []
        for p in predictions:
            predicted = [h["chulNo"] for h in p.get("selected_horses", [])]
            pred_dicts.append(
                {
                    "predicted": predicted,
                    "confidence": p.get("confidence", 50),
                }
            )

        # Aggregate
        aggregated = self.ensemble.aggregate_predictions(pred_dicts)

        # Build result dict matching expected format
        merged = predictions[0].copy()  # Use first as base
        merged["selected_horses"] = [{"chulNo": no} for no in aggregated["predicted"]]
        merged["predicted"] = aggregated["predicted"]
        merged["confidence"] = aggregated["confidence"]
        merged["ensemble_meta"] = {
            "k": self.ensemble_k,
            "collected": len(predictions),
            "consistency_score": aggregated["consistency_score"],
            "vote_counts": aggregated["vote_counts"],
        }

        # Check abstain
        if self.ensemble.should_abstain(aggregated["consistency_score"]):
            merged["low_confidence"] = True

        return merged, "success"

    def _parse_stream_json(self, output: str, execution_time: float) -> dict | None:
        """CLI 응답 텍스트에서 JSON 파싱 (직접 JSON 또는 코드블록)"""
        try:
            # 1. 응답 전체가 직접 JSON인 경우
            try:
                data = json.loads(output.strip())
                if isinstance(data, dict):
                    if "selected_horses" in data or "predicted" in data:
                        data["execution_time"] = execution_time
                        if "predicted" in data and "selected_horses" not in data:
                            data["selected_horses"] = [
                                {"chulNo": no} for no in data["predicted"]
                            ]
                        return data
            except json.JSONDecodeError:
                pass

            # 2. 코드블록 내 JSON 추출 시도
            code_block_match = re.search(
                r"```(?:json)?\s*(\{.*?\})\s*```", output, re.DOTALL
            )
            if code_block_match:
                try:
                    prediction = json.loads(code_block_match.group(1))
                    prediction["execution_time"] = execution_time
                    if "selected_horses" not in prediction:
                        if "predicted" in prediction:
                            prediction["selected_horses"] = [
                                {"chulNo": no} for no in prediction["predicted"]
                            ]
                        elif "prediction" in prediction:
                            prediction["selected_horses"] = [
                                {"chulNo": no} for no in prediction["prediction"]
                            ]
                    return prediction
                except json.JSONDecodeError:
                    pass

            # 3. 코드블록 없으면 직접 JSON 추출 시도
            json_match = re.search(
                r'\{[^{}]*"(?:selected_horses|predicted|prediction)"[^{}]*\}',
                output,
                re.DOTALL,
            )
            if json_match:
                try:
                    prediction = json.loads(json_match.group())
                    prediction["execution_time"] = execution_time
                    if "selected_horses" not in prediction:
                        if "predicted" in prediction:
                            prediction["selected_horses"] = [
                                {"chulNo": no} for no in prediction["predicted"]
                            ]
                        elif "prediction" in prediction:
                            prediction["selected_horses"] = [
                                {"chulNo": no} for no in prediction["prediction"]
                            ]
                    return prediction
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            print(f"JSON 파싱 오류: {e}")

        return None

    def _parse_regular_output(self, output: str, execution_time: float) -> dict | None:
        """일반 텍스트 출력 파싱 (폴백) - 가장 바깥쪽 JSON 매칭"""
        try:
            # 코드블록 내 JSON
            code_block_match = re.search(
                r"```(?:json)?\s*(\{.*?\})\s*```", output, re.DOTALL
            )
            if code_block_match:
                try:
                    prediction = json.loads(code_block_match.group(1))
                    prediction["execution_time"] = execution_time
                    # predicted 또는 prediction 필드를 selected_horses로 변환
                    if "selected_horses" not in prediction:
                        if "predicted" in prediction:
                            prediction["selected_horses"] = [
                                {"chulNo": no} for no in prediction["predicted"]
                            ]
                        elif "prediction" in prediction:
                            prediction["selected_horses"] = [
                                {"chulNo": no} for no in prediction["prediction"]
                            ]
                    return prediction
                except Exception:
                    pass

            # 일반 JSON (selected_horses, predicted 또는 prediction)
            json_match = re.search(
                r'\{.*"(?:selected_horses|predicted|prediction)".*?\}',
                output,
                re.DOTALL,
            )
            if json_match:
                try:
                    prediction = json.loads(json_match.group())
                    prediction["execution_time"] = execution_time
                    # predicted 또는 prediction 필드를 selected_horses로 변환
                    if "selected_horses" not in prediction:
                        if "predicted" in prediction:
                            prediction["selected_horses"] = [
                                {"chulNo": no} for no in prediction["predicted"]
                            ]
                        elif "prediction" in prediction:
                            prediction["selected_horses"] = [
                                {"chulNo": no} for no in prediction["prediction"]
                            ]
                    return prediction
                except Exception:
                    pass

        except Exception as e:
            print(f"Regular 파싱 오류: {e}")

        return None

    def run_jury_prediction(
        self, race_data: dict, race_id: str
    ) -> tuple[dict | None, str]:
        """LLM Jury를 통한 예측 실행: 3개 모델 병렬 호출 → 가중 투표 집계"""
        if not self.jury or not self.jury_ensemble:
            return self.run_claude_prediction(race_data, race_id)

        start_time = time.time()

        # 프롬프트 읽기
        with open(self.prompt_path, encoding="utf-8") as f:
            prompt_template = f.read()

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

        # Jury 심의: 모든 모델에 동일 프롬프트 병렬 전송
        verdict = self.jury.deliberate(prompt, timeout=3000)

        if not verdict.quorum_reached:
            print(
                f"[Jury] quorum 미달 ({len(verdict.successful_responses)}/{len(verdict.responses)}) for {race_id}"
            )
            # fallback: 성공한 응답이 1개라도 있으면 단독 사용
            if verdict.successful_responses:
                resp = verdict.successful_responses[0]
                parsed = LLMClient.parse_json(resp.text) if resp.text else None
                if parsed:
                    execution_time = time.time() - start_time
                    parsed["execution_time"] = execution_time
                    if "selected_horses" not in parsed and "predicted" in parsed:
                        parsed["selected_horses"] = [
                            {"chulNo": no} for no in parsed["predicted"]
                        ]
                    if "selected_horses" in parsed:
                        return parsed, "success"
            return None, "jury_quorum_failed"

        # 각 성공 응답에서 예측 JSON 파싱
        model_predictions: dict[str, dict] = {}
        for resp in verdict.successful_responses:
            if not resp.text:
                continue

            parsed = LLMClient.parse_json(resp.text)
            if not parsed:
                # 기존 파싱 폴백
                parsed = self._parse_stream_json(resp.text, 0)

            if parsed:
                predicted = []
                if "selected_horses" in parsed:
                    predicted = [h["chulNo"] for h in parsed["selected_horses"]]
                elif "predicted" in parsed:
                    predicted = parsed["predicted"]
                elif "prediction" in parsed:
                    predicted = parsed["prediction"]

                if predicted:
                    model_predictions[resp.model_name] = {
                        "predicted": predicted[:3],
                        "confidence": parsed.get("confidence", 50),
                    }

        if len(model_predictions) < 2:
            # 파싱 가능한 응답이 2개 미만
            if model_predictions:
                # 1개만 성공한 경우 단독 사용
                single = next(iter(model_predictions.values()))
                execution_time = time.time() - start_time
                result = {
                    "selected_horses": [{"chulNo": no} for no in single["predicted"]],
                    "predicted": single["predicted"],
                    "confidence": single["confidence"],
                    "execution_time": execution_time,
                }
                return result, "success"
            return None, "jury_parse_failed"

        # 앙상블 집계
        aggregation = self.jury_ensemble.aggregate(model_predictions)
        execution_time = time.time() - start_time

        result = {
            "selected_horses": [{"chulNo": no} for no in aggregation.predicted],
            "predicted": aggregation.predicted,
            "confidence": aggregation.confidence,
            "execution_time": execution_time,
            "jury_meta": {
                "model_predictions": aggregation.model_predictions,
                "vote_counts": aggregation.vote_counts,
                "agreement_level": aggregation.agreement_level,
                "agreement_score": aggregation.agreement_score,
                "consistency_score": aggregation.consistency_score,
            },
        }

        return result, "success"

    def run_prediction_with_retry(
        self, race_data: dict, race_id: str, max_retries: int = 1
    ) -> tuple[dict | None, str]:
        """재시도 기능이 있는 예측 실행"""
        for attempt in range(max_retries + 1):
            if self.jury_enabled:
                result, error_type = self.run_jury_prediction(race_data, race_id)
            else:
                result, error_type = self.run_ensemble_prediction(race_data, race_id)

            if result is not None:
                return result, error_type

            if attempt < max_retries and error_type != "timeout":
                print(f"  재시도 {attempt + 1}/{max_retries}...")
                time.sleep(2)

        return None, error_type

    def extract_actual_result(self, race_info: dict) -> list[int]:
        """DB에서 경주 결과 (1-3위) 추출"""
        try:
            result = self.db_client.get_race_result(race_info["race_id"])
            if not result:
                print(f"  결과 없음: {race_info['race_id']} (DB에 result_data 미수집)")
            return result
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
                "status": "no_result",
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
            "status": "evaluated",
        }

    def _convert_race_data_for_v5(self, race_data: dict) -> dict:
        """v5 insight_analyzer 호환 형식으로 race_data 변환"""
        entries = []
        for horse in race_data.get("horses", []):
            entries.append(
                {
                    "horse_no": horse.get("chulNo"),
                    "win_odds": horse.get("winOdds", 0),
                    "jockey_name": horse.get("jkName", ""),
                    "jockey_winrate": horse.get("jkDetail", {}).get("winRate", 0),
                    "horse_name": horse.get("hrName", ""),
                    "horse_record": horse.get("hrDetail", {}),
                }
            )
        return {
            "entries": entries,
            "race_info": race_data.get("raceInfo", {}),
        }

    def process_single_race(self, race_info: dict, race_data: dict) -> dict | None:
        """단일 경주 처리"""
        race_id = race_info["race_id"]

        # v5 호환 race_data 변환
        v5_race_data = self._convert_race_data_for_v5(race_data)

        # 예측 실행 (재시도 포함)
        prediction, error_type = self.run_prediction_with_retry(race_data, race_id)

        if prediction is None:
            return {
                "race_id": race_id,
                "prediction": None,
                "error_type": error_type,
                "reward": {"status": "error"},
                "race_data": v5_race_data,
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
            "error_type": error_type,
            "race_data": v5_race_data,
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

        print(f"\n{self.prompt_version} 평가 시작 (Anthropic SDK)...")
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
                        self.process_single_race, race_info, race_data
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
                            pred_str = (
                                f"[{','.join(map(str, predicted))}]"
                                if predicted
                                else "[?]"
                            )
                            actual_str = (
                                f"[{','.join(map(str, actual))}]" if actual else "[?]"
                            )

                            print(
                                f"[{completed_count}/{total_races}] {status} {race_info['race_id']} - 적중: {correct}/3 ({hit_rate:.0f}%) | 예측: {pred_str} → 실제: {actual_str} | 진행률: {completed_count / total_races * 100:.1f}% | ETA: {eta:.0f}초"
                            )
                        else:
                            print(
                                f"[{completed_count}/{total_races}] {status} {race_info['race_id']} - 에러: {result.get('error_type', 'unknown')} | 진행률: {completed_count / total_races * 100:.1f}%"
                            )

                except Exception as e:
                    print(f"Error processing {race_info['race_id']}: {e}")

        # 전체 요약
        valid_results = [r for r in results if r["prediction"] is not None]
        summary: dict[str, Any] = {
            "prompt_version": self.prompt_version,
            "test_date": timestamp,
            "total_races": total_races,
            "valid_predictions": len(valid_results),
            "successful_predictions": successful_predictions,
            "success_rate": (
                successful_predictions / len(valid_results) * 100
                if valid_results
                else 0
            ),
            "average_correct_horses": (
                total_correct_horses / len(valid_results) if valid_results else 0
            ),
            "total_correct_horses": total_correct_horses,
            "error_stats": dict(self.error_stats),
            "avg_execution_time": (
                sum(r["execution_time"] for r in valid_results) / len(valid_results)
                if valid_results
                else 0
            ),
            "detailed_results": results,
        }
        run_metadata = build_run_metadata(
            prompt_version=self.prompt_version,
            dataset_id=self.data_snapshot_id,
            mode=self.mode,
            seed=self.seed,
            extra={
                "max_workers": max_workers,
                "test_limit": test_limit,
            },
        )
        summary["run_metadata"] = run_metadata

        metrics_v2 = compute_prediction_quality_metrics(
            detailed_results=results,
            topk_values=self.topk_values,
            ece_bins=self.ece_bins,
            defer_threshold=self.defer_threshold,
        )
        metrics_v2["json_valid_rate"] = (
            len(valid_results) / total_races if total_races > 0 else 0.0
        )

        if self.asof_check == "on":
            leakage_check = check_detailed_results_for_leakage(results)
        else:
            leakage_check = {
                "passed": True,
                "issues": [],
                "checked_races": len(results),
            }

        report_v2 = build_report_v2(
            prompt_version=self.prompt_version,
            summary=summary,
            metrics=metrics_v2,
            leakage=leakage_check,
            promotion_context={
                "selection_gate": "strict",
                "metrics_profile": self.metrics_profile,
            },
        )
        schema_valid, schema_errors = validate_report_v2(report_v2)
        report_v2["schema_valid"] = schema_valid
        report_v2["schema_errors"] = schema_errors
        report_v2["run_metadata"] = run_metadata

        # MLflow experiment tracking
        try:
            self.tracker.start_run(
                run_name=f"{self.prompt_version}_{timestamp}",
                tags={
                    "prompt_version": self.prompt_version,
                    "mode": self.mode,
                    "data_snapshot_id": self.data_snapshot_id,
                },
            )

            self.tracker.log_params(
                {
                    "prompt_version": self.prompt_version,
                    "prompt_path": str(self.prompt_path),
                    "total_races": total_races,
                    "max_workers": max_workers,
                    "model": "claude-opus-4-20250918",
                    "data_snapshot_id": self.data_snapshot_id,
                    "seed": self.seed,
                    "mode": self.mode,
                }
            )

            self.tracker.log_metrics(
                {
                    "success_rate": summary["success_rate"],
                    "average_correct_horses": summary["average_correct_horses"],
                    "total_races": float(summary["total_races"]),
                    "valid_predictions": float(summary["valid_predictions"]),
                    "successful_predictions": float(summary["successful_predictions"]),
                    "total_correct_horses": float(summary["total_correct_horses"]),
                    "avg_execution_time": summary["avg_execution_time"],
                    "log_loss": metrics_v2["log_loss"],
                    "brier": metrics_v2["brier"],
                    "ece": metrics_v2["ece"],
                    "top3": metrics_v2["topk"].get("top_3", 0.0),
                    "avg_roi": metrics_v2["roi"].get("avg_roi", 0.0),
                    "coverage": metrics_v2["coverage"],
                }
            )

            self.tracker.log_artifact(str(self.prompt_path))
            self.tracker.log_run_metadata(
                run_metadata=run_metadata,
                artifact_name=f"run_metadata_{self.prompt_version}_{timestamp}.json",
                local_output_dir=self.results_dir,
            )
        finally:
            self.tracker.end_run()

        # 결과 저장
        output_file = (
            self.results_dir / f"evaluation_{self.prompt_version}_{timestamp}.json"
        )
        with open(output_file, "w", encoding="utf-8") as f:
            if self.report_format == "v2":
                json.dump(report_v2, f, ensure_ascii=False, indent=2)
            else:
                json.dump(summary, f, ensure_ascii=False, indent=2)

        # 결과 출력
        self.print_summary(
            report_v2 if self.report_format == "v2" else summary, output_file
        )

        return report_v2 if self.report_format == "v2" else summary

    def print_summary(self, summary: dict, output_file: Path):
        """요약 결과 출력"""
        print("\n" + "=" * 60)
        print("평가 완료!")
        print(f"프롬프트 버전: {summary['prompt_version']}")
        print(f"전체 경주: {summary['total_races']}")
        print(f"유효 예측: {summary['valid_predictions']}")

        if summary["valid_predictions"] > 0:
            print(
                f"완전 적중: {summary['successful_predictions']} ({summary['success_rate']:.1f}%)"
            )
            print(f"평균 적중 말 수: {summary['average_correct_horses']:.2f}")
            print(f"평균 실행 시간: {summary['avg_execution_time']:.1f}초")

        print("\n에러 통계:")
        for error_type, count in summary["error_stats"].items():
            print(f"  - {error_type}: {count}건")

        metrics_v2 = summary.get("metrics_v2")
        if metrics_v2:
            print("\n품질 지표(v2):")
            print(f"  - log_loss: {metrics_v2.get('log_loss', 0.0):.4f}")
            print(f"  - brier: {metrics_v2.get('brier', 0.0):.4f}")
            print(f"  - ece: {metrics_v2.get('ece', 0.0):.4f}")
            print(f"  - top3: {metrics_v2.get('topk', {}).get('top_3', 0.0):.4f}")
            print(f"  - avg_roi: {metrics_v2.get('roi', {}).get('avg_roi', 0.0):.4f}")
            print(f"  - coverage: {metrics_v2.get('coverage', 0.0):.4f}")

        leakage_check = summary.get("leakage_check")
        if leakage_check:
            print(f"\n누수 검사: {'PASS' if leakage_check.get('passed') else 'FAIL'}")
            if leakage_check.get("issues"):
                print(f"  - issues: {len(leakage_check['issues'])}")

        print(f"\n결과 저장: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="프롬프트 평가 시스템 v3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python evaluate_prompt_v3.py v10.0 prompts/prediction-template-v10.0.md 30 3 --report-format v2 --asof-check on --topk 1,3
        """,
    )
    parser.add_argument("prompt_version", help="프롬프트 버전")
    parser.add_argument("prompt_file", help="프롬프트 파일 경로")
    parser.add_argument(
        "test_limit",
        nargs="?",
        default=10,
        type=int,
        help="평가 경주 수 (기본값: 10)",
    )
    parser.add_argument(
        "max_workers",
        nargs="?",
        default=3,
        type=int,
        help="병렬 작업 수 (기본값: 3)",
    )
    parser.add_argument(
        "--report-format",
        choices=["v1", "v2"],
        default="v2",
        help="결과 리포트 포맷 (기본값: v2)",
    )
    parser.add_argument(
        "--asof-check",
        choices=["on", "off"],
        default="on",
        help="누수(as-of) 검사 on/off (기본값: on)",
    )
    parser.add_argument(
        "--topk",
        default="1,3",
        help="Top-k 지표 목록 (예: 1,3,5)",
    )
    parser.add_argument(
        "--metrics-profile",
        choices=["rpi_v1"],
        default="rpi_v1",
        help="지표 프로파일 (기본값: rpi_v1)",
    )
    parser.add_argument(
        "--defer-threshold",
        type=float,
        default=None,
        help="디퍼 임계값 (0~1, 미지정 시 비활성)",
    )
    parser.add_argument(
        "--ensemble-k",
        type=int,
        default=1,
        help="앙상블 예측 수 (1=단일 예측, 기본값: 1)",
    )
    parser.add_argument(
        "--jury",
        action="store_true",
        default=False,
        help="LLM Jury 모드 활성화 (Claude + Codex + Gemini 앙상블)",
    )
    parser.add_argument(
        "--jury-models",
        type=str,
        default="claude,codex,gemini",
        help="Jury에 참여할 모델 목록 (쉼표 구분, 기본값: claude,codex,gemini)",
    )
    parser.add_argument(
        "--jury-weights",
        type=str,
        default=None,
        help="Jury 모델별 가중치 (예: claude=1.0,codex=0.8,gemini=0.9)",
    )
    parser.add_argument(
        "--data-snapshot-id",
        type=str,
        default="db_latest",
        help="평가 데이터 스냅샷 식별자 (기본값: db_latest)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="재현성 시드 (기본값: 42)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="evaluation",
        help="실행 모드 메타데이터 값 (기본값: evaluation)",
    )

    args = parser.parse_args()

    topk_values = tuple(
        int(token.strip()) for token in args.topk.split(",") if token.strip()
    )
    if not topk_values:
        topk_values = (1, 3)

    # Jury 가중치 파싱
    jury_weights = None
    if args.jury_weights:
        jury_weights = {}
        for pair in args.jury_weights.split(","):
            k, v = pair.split("=")
            jury_weights[k.strip()] = float(v.strip())

    # Jury 모델 목록 파싱
    jury_models = [m.strip() for m in args.jury_models.split(",") if m.strip()]

    evaluator = PromptEvaluatorV3(
        prompt_version=args.prompt_version,
        prompt_path=args.prompt_file,
        topk_values=topk_values,
        asof_check=args.asof_check,
        report_format=args.report_format,
        metrics_profile=args.metrics_profile,
        defer_threshold=args.defer_threshold,
        ensemble_k=args.ensemble_k,
        jury_enabled=args.jury,
        jury_models=jury_models,
        jury_weights=jury_weights,
        data_snapshot_id=args.data_snapshot_id,
        seed=args.seed,
        mode=args.mode,
    )
    _results = evaluator.evaluate_all_parallel(
        test_limit=args.test_limit,
        max_workers=args.max_workers,
    )


if __name__ == "__main__":
    main()
