"""
LLM Jury 오케스트레이터

여러 LLM CLI 클라이언트를 병렬로 호출하여 결과를 수집하고
quorum(정족수) 기반으로 유효성을 판단합니다.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from .llm_client import LLMClient, LLMResponse


@dataclass
class JuryVerdict:
    """Jury 심의 결과"""

    responses: list[LLMResponse] = field(default_factory=list)
    successful_responses: list[LLMResponse] = field(default_factory=list)
    failed_responses: list[LLMResponse] = field(default_factory=list)

    @property
    def quorum_reached(self) -> bool:
        """정족수(2개 이상 성공) 도달 여부"""
        return len(self.successful_responses) >= 2

    @property
    def agreement_ratio(self) -> float:
        """성공 응답 비율 (0.0 ~ 1.0)"""
        if not self.responses:
            return 0.0
        return len(self.successful_responses) / len(self.responses)


class LLMJury:
    """LLM Jury: 여러 모델을 병렬로 호출하여 심의

    3개 모델(Claude, Codex, Gemini)에 동일한 프롬프트를 보내고
    결과를 JuryVerdict로 집계합니다.
    """

    def __init__(self, clients: list[LLMClient]):
        if not clients:
            raise ValueError("At least one LLMClient is required")
        self.clients = clients

    def deliberate(self, prompt: str, timeout: float = 3000, **kwargs) -> JuryVerdict:
        """모든 클라이언트에 동일 프롬프트를 병렬 전송하고 결과를 집계.

        Args:
            prompt: 전송할 프롬프트
            timeout: 각 클라이언트 타임아웃(초)

        Returns:
            JuryVerdict: 전체 응답, 성공/실패 구분, quorum 여부
        """
        verdict = JuryVerdict()

        with ThreadPoolExecutor(max_workers=len(self.clients)) as executor:
            future_to_client = {
                executor.submit(
                    client.predict_sync, prompt, timeout=timeout, **kwargs
                ): client
                for client in self.clients
            }

            for future in as_completed(future_to_client):
                try:
                    response = future.result()
                    verdict.responses.append(response)
                    if response.success:
                        verdict.successful_responses.append(response)
                    else:
                        verdict.failed_responses.append(response)
                except Exception as e:
                    client = future_to_client[future]
                    error_response = LLMResponse(
                        text=None,
                        model_name=client.model_name,
                        success=False,
                        error=f"Future exception: {e}",
                    )
                    verdict.responses.append(error_response)
                    verdict.failed_responses.append(error_response)

        return verdict
