"""
Claude CLI 기반 클라이언트 (구독 플랜 활용)
- subprocess를 통한 claude -p 헤드리스 모드 호출
- Max 구독 플랜 사용량 소비 (API KEY 불필요)
- 동시성 제한 (Semaphore)
- JSON 응답 파싱 (코드블록 + regex fallback)
- LLMClient ABC 상속
"""

from __future__ import annotations

import json
import os

from .llm_client import LLMClient


class ClaudeClient(LLMClient):
    """Claude CLI 헤드리스 모드 래퍼 클라이언트 (구독 플랜 전용)

    LLMClient ABC를 상속하면서 기존 인터페이스도 유지합니다.
    """

    def __init__(self, max_concurrency: int = 3):
        super().__init__(model_name="claude", max_concurrency=max_concurrency)

    def _build_env(self) -> dict[str, str]:
        """Claude CLI 환경 변수 구성."""
        env = {**os.environ, "DISABLE_INTERLEAVED_THINKING": "true"}
        env.pop("CLAUDECODE", None)
        return env

    def _build_command(self, prompt: str, **kwargs) -> list[str]:
        model = kwargs.get("model", "opus")
        return [
            "claude",
            "-p",
            prompt,
            "--model",
            model,
            "--output-format",
            "json",
            "--max-turns",
            "1",
        ]

    def _extract_text(self, stdout: str) -> str | None:
        """Claude CLI JSON 출력에서 실제 텍스트 추출.

        --output-format json: {"type":"result","result":"..."} 형태
        """
        if not stdout or not stdout.strip():
            return None

        try:
            cli_response = json.loads(stdout)
            if isinstance(cli_response, dict) and "result" in cli_response:
                return cli_response["result"]
        except json.JSONDecodeError:
            pass

        return stdout.strip() if stdout.strip() else None

    # ------------------------------------------------------------------
    # 하위 호환 인터페이스
    # ------------------------------------------------------------------
    def predict_sync_compat(
        self,
        prompt: str,
        model: str = "opus",
        max_tokens: int = 8192,
        timeout: float = 3000,
    ) -> str | None:
        """기존 코드 호환용 동기 예측 호출. 성공 시 응답 텍스트, 실패 시 None.

        내부적으로 LLMClient.predict_sync()를 사용합니다.
        """
        response = self.predict_sync(prompt, timeout=timeout, model=model)
        return response.text if response.success else None
