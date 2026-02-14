"""
Anthropic SDK 기반 Claude 클라이언트
- subprocess.run(["claude", ...]) 대신 anthropic Python SDK 직접 사용
- 동시성 제한 (Semaphore)
- JSON 응답 파싱 (regex fallback 포함)
"""
from __future__ import annotations

import json
import os
import re
import threading

import anthropic
from dotenv import load_dotenv

# 프로젝트 루트 및 scripts 디렉토리의 .env 파일 로드
load_dotenv()
load_dotenv(
    os.path.join(os.path.dirname(__file__), os.pardir, ".env"),
    override=True,
)


class ClaudeClient:
    """Anthropic Messages API 래퍼 클라이언트"""

    def __init__(self, max_concurrency: int = 3):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다. "
                ".env 파일 또는 환경변수를 확인하세요."
            )
        self._client = anthropic.Anthropic(api_key=api_key)
        self._semaphore = threading.Semaphore(max_concurrency)

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def predict_sync(
        self,
        prompt: str,
        model: str = "claude-sonnet-4-5-20250929",
        max_tokens: int = 8192,
        timeout: float = 300.0,
    ) -> str | None:
        """동기 예측 호출. 성공 시 응답 텍스트, 실패 시 None 반환."""
        with self._semaphore:
            try:
                response = self._client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                    timeout=timeout,
                )
                return response.content[0].text
            except anthropic.APITimeoutError:
                print(f"[ClaudeClient] API 타임아웃 ({timeout}s)")
                return None
            except anthropic.APIStatusError as e:
                print(f"[ClaudeClient] API 오류: {e.status_code} - {e.message}")
                return None
            except anthropic.APIError as e:
                print(f"[ClaudeClient] API 오류: {e}")
                return None
            except Exception as e:
                print(f"[ClaudeClient] 예기치 않은 오류: {e}")
                return None

    # ------------------------------------------------------------------
    # JSON 파싱 유틸리티
    # ------------------------------------------------------------------
    @staticmethod
    def parse_json(text: str) -> dict | None:
        """응답 텍스트에서 JSON 객체를 추출한다.

        1) ```json ... ``` 코드블록 우선
        2) 가장 바깥쪽 { ... } 매칭
        """
        if not text:
            return None

        # 1. 마크다운 코드블록
        m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        # 2. 가장 바깥쪽 중괄호
        m = re.search(r"(\{.*\})", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        return None
