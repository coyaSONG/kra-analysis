#!/usr/bin/env python3
"""
프롬프트 재귀 개선을 위한 평가 시스템 v3
- Claude CLI 헤드리스 모드 (구독 플랜 활용)
- JSON 응답 파싱 (코드블록 + regex fallback)
- 향상된 안정성
"""

import argparse
import json
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
from evaluation.data_loading import RaceEvaluationDataLoader
from evaluation.ensemble import SelfConsistencyEnsemble
from evaluation.leakage_checks import check_detailed_results_for_leakage
from evaluation.metrics import (
    compute_prediction_quality_metrics,
    is_ordered_topk_exact_match,
    is_unordered_topk_exact_match,
)
from evaluation.mlflow_tracker import ExperimentTracker
from evaluation.prediction_service import (
    build_prediction_prompt,
    finalize_prediction_payload,
    normalize_prediction_payload,
    parse_prediction_output,
)
from evaluation.report_schema import build_report_v2, validate_report_v2
from shared.claude_client import ClaudeClient
from shared.db_client import RaceDBClient
from shared.llm_client import LLMClient
from shared.prediction_input_schema import (
    build_alternative_ranking_dataset_metadata,
    validate_alternative_ranking_dataset_metadata,
)


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
        with_past_stats: bool = False,
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
        self.ensemble = (
            SelfConsistencyEnsemble(k=ensemble_k) if ensemble_k > 1 else None
        )
        self.with_past_stats = with_past_stats

        # DB 클라이언트
        self.db_client = RaceDBClient()
        self.data_loader = RaceEvaluationDataLoader(
            self.db_client, with_past_stats=with_past_stats
        )

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

    def _build_dataset_metadata(
        self, races: list[dict[str, Any]], *, limit: int | None
    ) -> dict[str, Any]:
        if hasattr(self.data_loader, "build_dataset_metadata"):
            metadata = self.data_loader.build_dataset_metadata(races, limit=limit)
            if isinstance(metadata, dict):
                return validate_alternative_ranking_dataset_metadata(metadata)
        return build_alternative_ranking_dataset_metadata(
            source=type(self.db_client).__name__,
            dataset_name="live_db_evaluation",
            requested_limit=limit,
            race_ids=[
                str(race.get("race_id")) for race in races if race.get("race_id")
            ],
            with_past_stats=self.with_past_stats,
        )

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

    @staticmethod
    def _default_fallback_meta() -> dict[str, Any]:
        return {
            "available": False,
            "applied": False,
            "reason_code": None,
            "reason": None,
            "source": None,
            "details": None,
        }

    def _aggregate_member_fallback_meta(
        self, predictions: list[dict[str, Any]], *, source: str
    ) -> dict[str, Any]:
        metas: list[dict[str, Any]] = []
        for prediction in predictions:
            raw_meta = prediction.get("fallback_meta")
            if isinstance(raw_meta, dict):
                metas.append(raw_meta)

        if not metas:
            return self._default_fallback_meta()

        available_count = sum(1 for meta in metas if bool(meta.get("available")))
        applied_count = sum(1 for meta in metas if bool(meta.get("applied")))
        reason_codes = sorted(
            {
                str(meta.get("reason_code"))
                for meta in metas
                if meta.get("reason_code") is not None
            }
        )
        details = {
            "member_count": len(metas),
            "available_count": available_count,
            "applied_count": applied_count,
            "reason_codes": reason_codes,
        }

        if applied_count == 0:
            return {
                "available": available_count > 0,
                "applied": False,
                "reason_code": None,
                "reason": None,
                "source": source,
                "details": details,
            }

        return {
            "available": True,
            "applied": True,
            "reason_code": "AGGREGATED_MEMBER_FALLBACK",
            "reason": f"{applied_count}/{len(metas)} member predictions used fallback ranking.",
            "source": source,
            "details": details,
        }

    def find_test_races(self, limit: int = None) -> list[dict[str, Any]]:
        """DB에서 수집 완료된 경주 찾기"""
        return self.data_loader.find_test_races(limit=limit)

    def load_race_data(self, race_info: dict) -> dict | None:
        """DB에서 경주 데이터 로드"""
        return self.data_loader.load_race_data(race_info)

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
        prompt = build_prediction_prompt(prompt_template, race_data)

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
            prediction = parse_prediction_output(
                response_text,
                execution_time,
                race_data=race_data,
            )
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

        merged = normalize_prediction_payload(
            {
                "selected_horses": [{"chulNo": no} for no in aggregated["predicted"]],
                "predicted": aggregated["predicted"],
                "confidence": aggregated["confidence"],
                "reasoning": predictions[0].get("reasoning", ""),
                "fallback_meta": self._aggregate_member_fallback_meta(
                    predictions, source="self_consistency_ensemble"
                ),
            },
            execution_time=sum(
                float(prediction.get("execution_time", 0.0))
                for prediction in predictions
            ),
            race_data=race_data,
        )
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
        """CLI 응답 텍스트에서 JSON 파싱 (기존 호환용 래퍼)"""
        return parse_prediction_output(output, execution_time)

    def _parse_regular_output(self, output: str, execution_time: float) -> dict | None:
        """일반 텍스트 출력 파싱 (폴백) - 가장 바깥쪽 JSON 매칭"""
        return parse_prediction_output(output, execution_time)

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

        prompt = build_prediction_prompt(prompt_template, race_data)

        # Jury 심의: 모든 모델에 동일 프롬프트 병렬 전송
        verdict = self.jury.deliberate(prompt, timeout=3000)

        if not verdict.quorum_reached:
            print(
                f"[Jury] quorum 미달 ({len(verdict.successful_responses)}/{len(verdict.responses)}) for {race_id}"
            )
            # fallback: 성공한 응답이 1개라도 있으면 단독 사용
            if verdict.successful_responses:
                resp = verdict.successful_responses[0]
                parsed = (
                    parse_prediction_output(resp.text, 0, race_data=race_data)
                    if resp.text
                    else None
                )
                if parsed:
                    execution_time = time.time() - start_time
                    parsed = normalize_prediction_payload(
                        parsed,
                        execution_time,
                        race_data=race_data,
                    )
                    if "selected_horses" in parsed:
                        return parsed, "success"
            return None, "jury_quorum_failed"

        # 각 성공 응답에서 예측 JSON 파싱
        model_predictions: dict[str, dict] = {}
        parsed_predictions: list[dict[str, Any]] = []
        for resp in verdict.successful_responses:
            if not resp.text:
                continue

            parsed = parse_prediction_output(resp.text, 0, race_data=race_data)

            if parsed:
                parsed_predictions.append(parsed)
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
            if parsed_predictions:
                # 1개만 성공한 경우 단독 사용
                execution_time = time.time() - start_time
                return (
                    normalize_prediction_payload(
                        parsed_predictions[0],
                        execution_time,
                        race_data=race_data,
                    ),
                    "success",
                )
            return None, "jury_parse_failed"

        # 앙상블 집계
        aggregation = self.jury_ensemble.aggregate(model_predictions)
        execution_time = time.time() - start_time

        result = normalize_prediction_payload(
            {
                "selected_horses": [{"chulNo": no} for no in aggregation.predicted],
                "predicted": aggregation.predicted,
                "confidence": aggregation.confidence,
                "fallback_meta": self._aggregate_member_fallback_meta(
                    parsed_predictions, source="jury_ensemble"
                ),
            },
            execution_time,
            race_data=race_data,
        )
        result["jury_meta"] = {
            "model_predictions": aggregation.model_predictions,
            "vote_counts": aggregation.vote_counts,
            "agreement_level": aggregation.agreement_level,
            "agreement_score": aggregation.agreement_score,
            "consistency_score": aggregation.consistency_score,
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
                "unordered_top3_exact_match": False,
                "ordered_top3_exact_match": False,
                "base_score": 0,
                "bonus": 0,
                "total_score": 0,
                "hit_rate": 0,
                "status": "no_result",
            }

        predicted_top3 = predicted[:3]
        actual_top3 = actual[:3]

        # 적중 개수는 상위 3두만 기준으로 계산
        correct_count = len(set(predicted_top3) & set(actual_top3))
        exact_match = is_unordered_topk_exact_match(predicted_top3, actual_top3)
        ordered_exact_match = is_ordered_topk_exact_match(predicted_top3, actual_top3)

        # 기본 점수
        base_score = correct_count * 33.33

        # 보너스 (3마리 모두 적중)
        bonus = 10 if exact_match else 0

        total_score = base_score + bonus

        return {
            "correct_count": correct_count,
            "unordered_top3_exact_match": exact_match,
            "ordered_top3_exact_match": ordered_exact_match,
            "base_score": base_score,
            "bonus": bonus,
            "total_score": total_score,
            "hit_rate": correct_count / 3 * 100,
            "status": "evaluated",
        }

    def _convert_race_data_for_v5(self, race_data: dict) -> dict:
        """v5 insight_analyzer 호환 형식으로 race_data 변환"""
        return self.data_loader.build_v5_race_data(race_data)

    def _build_error_result(
        self,
        race_id: str,
        error_type: str,
        race_data: dict[str, Any] | None = None,
        prediction: dict[str, Any] | None = None,
        actual: list[int] | None = None,
        reward: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        v5_race_data = (
            self._convert_race_data_for_v5(race_data)
            if race_data is not None
            else {"entries": [], "race_info": {}}
        )
        predicted_horses: list[int] = []
        if prediction is not None:
            raw_selected_horses = prediction.get("selected_horses") or []
            if isinstance(raw_selected_horses, list):
                predicted_horses = [
                    int(horse["chulNo"])
                    for horse in raw_selected_horses
                    if isinstance(horse, dict) and "chulNo" in horse
                ]

            if not predicted_horses:
                raw_predicted = (
                    prediction.get("predicted") or prediction.get("top3") or []
                )
                if isinstance(raw_predicted, list):
                    predicted_horses = [
                        int(chul_no)
                        for chul_no in raw_predicted
                        if isinstance(chul_no, int) or str(chul_no).isdigit()
                    ]

        return {
            "race_id": race_id,
            "top3": predicted_horses,
            "predicted": predicted_horses,
            "actual": actual or [],
            "fallback_used": bool(
                prediction and prediction.get("fallback_used", False)
            ),
            "fallback_reason_code": prediction.get("fallback_reason_code")
            if prediction
            else None,
            "fallback_reason": prediction.get("fallback_reason")
            if prediction
            else None,
            "fallback_meta": prediction.get(
                "fallback_meta", self._default_fallback_meta()
            )
            if prediction
            else self._default_fallback_meta(),
            "prediction": prediction,
            "error_type": error_type,
            "reward": reward or {"status": "error", "correct_count": 0},
            "hit": False,
            "ordered_hit": False,
            "confidence": prediction.get("confidence", 0) if prediction else 0,
            "reasoning": prediction.get("reasoning", "") if prediction else "",
            "execution_time": prediction.get("execution_time", 0) if prediction else 0,
            "race_data": v5_race_data,
        }

    def process_single_race(self, race_info: dict, race_data: dict) -> dict | None:
        """단일 경주 처리"""
        race_id = race_info["race_id"]

        # v5 호환 race_data 변환
        v5_race_data = self._convert_race_data_for_v5(race_data)

        # 예측 실행 (재시도 포함)
        prediction, error_type = self.run_prediction_with_retry(race_data, race_id)

        if prediction is None:
            return self._build_error_result(
                race_id=race_id,
                error_type=error_type,
                race_data=race_data,
            )

        finalized_prediction = finalize_prediction_payload(
            prediction,
            race_data=race_data,
            execution_time=float(prediction.get("execution_time", 0.0)),
        )
        if finalized_prediction is None:
            return self._build_error_result(
                race_id=race_id,
                error_type="prediction_output_contract_error",
                race_data=race_data,
            )
        prediction = finalized_prediction

        # 예측 결과 추출
        predicted_horses = [h["chulNo"] for h in prediction["selected_horses"]]

        # 실제 결과 추출
        actual_result = self.extract_actual_result(race_info)

        # 보상 계산
        try:
            reward = self.calculate_reward(predicted_horses, actual_result)
        except Exception as e:
            print(f"  점수 산출 오류: {race_id} - {e}")
            return self._build_error_result(
                race_id=race_id,
                error_type="score_error",
                race_data=race_data,
                prediction=prediction,
                actual=actual_result,
                reward={
                    "correct_count": 0,
                    "unordered_top3_exact_match": False,
                    "ordered_top3_exact_match": False,
                    "base_score": 0,
                    "bonus": 0,
                    "total_score": 0,
                    "hit_rate": 0,
                    "status": "score_fallback",
                },
            )

        return {
            "race_id": race_id,
            "top3": predicted_horses,
            "predicted": predicted_horses,
            "actual": actual_result,
            "reward": reward,
            "hit": reward.get("unordered_top3_exact_match", False),
            "ordered_hit": reward.get("ordered_top3_exact_match", False),
            "confidence": prediction.get("confidence", 0),
            "reasoning": prediction.get("reasoning", ""),
            "execution_time": prediction.get("execution_time", 0),
            "fallback_used": bool(prediction.get("fallback_used", False)),
            "fallback_reason_code": prediction.get("fallback_reason_code"),
            "fallback_reason": prediction.get("fallback_reason"),
            "fallback_meta": prediction.get(
                "fallback_meta", self._default_fallback_meta()
            ),
            "prediction": prediction,
            "error_type": error_type,
            "race_data": v5_race_data,
        }

    def evaluate_all_parallel(self, test_limit: int = 10, max_workers: int = 3):
        """병렬 처리로 전체 평가 실행"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 테스트 레이스 찾기
        test_races = self.find_test_races(limit=test_limit)
        dataset_metadata = self._build_dataset_metadata(test_races, limit=test_limit)

        results = []
        total_races = len(test_races)

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
                else:
                    self.error_stats["data_load_error"] += 1
                    result = self._build_error_result(
                        race_id=race_info["race_id"],
                        error_type="data_load_error",
                    )
                    results.append(result)
                    completed_count += 1
                    print(
                        f"[{completed_count}/{total_races}] ✗ {race_info['race_id']} - 에러: data_load_error | 진행률: {completed_count / total_races * 100:.1f}%"
                    )

            # 결과 수집
            for _i, future in enumerate(as_completed(future_to_race)):
                race_info = future_to_race[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)

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
        successful_predictions = sum(1 for r in results if r.get("hit"))
        total_correct_horses = sum(
            int((r.get("reward") or {}).get("correct_count", 0)) for r in results
        )
        summary: dict[str, Any] = {
            "prompt_version": self.prompt_version,
            "test_date": timestamp,
            "total_races": total_races,
            "valid_predictions": len(valid_results),
            "successful_predictions": successful_predictions,
            "success_rate": (
                successful_predictions / total_races * 100 if total_races else 0
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
            "dataset_metadata": dataset_metadata,
            "feature_schema_version": dataset_metadata.get(
                "feature_schema_version", "unknown"
            ),
        }

        metrics_v2 = compute_prediction_quality_metrics(
            detailed_results=results,
            topk_values=self.topk_values,
            ece_bins=self.ece_bins,
            defer_threshold=self.defer_threshold,
            reference_race_ids=dataset_metadata.get("race_ids"),
        )
        metrics_v2["json_valid_rate"] = (
            len(valid_results) / total_races if total_races > 0 else 0.0
        )
        summary["metrics_v2"] = metrics_v2

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
                "dataset_metadata": dataset_metadata,
                "feature_schema_version": dataset_metadata.get(
                    "feature_schema_version", "unknown"
                ),
            },
        )
        schema_valid, schema_errors = validate_report_v2(report_v2)
        report_v2["schema_valid"] = schema_valid
        report_v2["schema_errors"] = schema_errors

        # MLflow experiment tracking
        try:
            self.tracker.start_run(
                run_name=f"{self.prompt_version}_{timestamp}",
                tags={"prompt_version": self.prompt_version},
            )

            self.tracker.log_params(
                {
                    "prompt_version": self.prompt_version,
                    "prompt_path": str(self.prompt_path),
                    "total_races": total_races,
                    "max_workers": max_workers,
                    "model": "claude-opus-4-20250918",
                    "feature_schema_version": dataset_metadata.get(
                        "feature_schema_version", "unknown"
                    ),
                    "dataset_race_count": dataset_metadata.get("race_count", 0),
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
                    "ordered_race_hit_rate": metrics_v2.get(
                        "ordered_race_hit_rate", 0.0
                    ),
                }
            )

            self.tracker.log_artifact(str(self.prompt_path))
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
            print(
                f"  - prediction_coverage: "
                f"{metrics_v2.get('prediction_coverage', 0.0):.4f} "
                f"({metrics_v2.get('predicted_race_count', 0)} / "
                f"{metrics_v2.get('expected_race_count', 0)})"
            )
            print(
                f"  - missing_predictions: "
                f"{metrics_v2.get('missing_prediction_count', 0)}"
            )
            print(
                f"  - race_hit_rate: {metrics_v2.get('race_hit_rate', 0.0):.4f} "
                f"({metrics_v2.get('race_hit_count', 0)} / {summary['total_races']})"
            )
            print(
                f"  - ordered_race_hit_rate: "
                f"{metrics_v2.get('ordered_race_hit_rate', 0.0):.4f} "
                f"({metrics_v2.get('ordered_race_hit_count', 0)} / {summary['total_races']})"
            )
            missing_prediction_race_ids = metrics_v2.get(
                "missing_prediction_race_ids", []
            )
            if missing_prediction_race_ids:
                print(
                    "  - missing_prediction_race_ids: "
                    + ", ".join(str(race_id) for race_id in missing_prediction_race_ids)
                )

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
        "--with-past-stats",
        action="store_true",
        default=False,
        help="최근 top3 과거 성적 피처를 추가하여 평가 (A/B 테스트용)",
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
        with_past_stats=args.with_past_stats,
    )
    _results = evaluator.evaluate_all_parallel(
        test_limit=args.test_limit,
        max_workers=args.max_workers,
    )


if __name__ == "__main__":
    main()
