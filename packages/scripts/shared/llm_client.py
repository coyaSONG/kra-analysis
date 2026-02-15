"""
LLM CLI 클라이언트 추상화 계층

구독 기반 CLI 도구(Claude, Codex, Gemini)를 통합하는 추상 베이스 클래스와
각 CLI의 구체적 구현을 제공합니다.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """LLM 호출 응답을 표현하는 데이터 클래스"""

    text: str | None
    model_name: str
    success: bool
    error: str | None = None
    latency_seconds: float = 0.0
    raw_output: str | None = None


class LLMClient(ABC):
    """LLM CLI 클라이언트 추상 베이스 클래스

    각 CLI 도구(claude, codex, gemini)는 이 ABC를 상속하여
    동일한 인터페이스로 호출할 수 있습니다.
    """

    def __init__(self, model_name: str, max_concurrency: int = 3):
        self.model_name = model_name
        self._semaphore = threading.Semaphore(max_concurrency)
        self._env = self._build_env()

    def _build_env(self) -> dict[str, str]:
        """서브프로세스용 환경 변수 구성. 기본: CLAUDECODE 제거."""
        env = {**os.environ}
        env.pop("CLAUDECODE", None)
        return env

    @abstractmethod
    def _build_command(self, prompt: str, **kwargs) -> list[str]:
        """CLI 호출 명령어 리스트를 생성한다."""

    def _extract_text(self, stdout: str) -> str | None:
        """CLI stdout에서 응답 텍스트를 추출한다. 기본 구현: 원시 출력 반환."""
        return stdout.strip() if stdout and stdout.strip() else None

    def _get_stdin(self) -> int | None:
        """subprocess의 stdin 설정. 기본: None (inherit)."""
        return None

    def predict_sync(self, prompt: str, timeout: float = 3000, **kwargs) -> LLMResponse:
        """동기 예측 호출.

        semaphore로 동시성 제한, subprocess.run으로 CLI 호출,
        timeout/error 처리를 수행하고 LLMResponse를 반환합니다.
        """
        cmd = self._build_command(prompt, **kwargs)
        start = time.time()

        with self._semaphore:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env=self._env,
                    stdin=self._get_stdin(),
                )

                latency = time.time() - start

                if result.returncode != 0:
                    stderr_preview = result.stderr[:300] if result.stderr else "N/A"
                    return LLMResponse(
                        text=None,
                        model_name=self.model_name,
                        success=False,
                        error=f"CLI error (code={result.returncode}): {stderr_preview}",
                        latency_seconds=latency,
                        raw_output=result.stdout,
                    )

                text = self._extract_text(result.stdout)
                if text is None:
                    return LLMResponse(
                        text=None,
                        model_name=self.model_name,
                        success=False,
                        error="Empty response",
                        latency_seconds=latency,
                        raw_output=result.stdout,
                    )

                return LLMResponse(
                    text=text,
                    model_name=self.model_name,
                    success=True,
                    latency_seconds=latency,
                    raw_output=result.stdout,
                )

            except subprocess.TimeoutExpired:
                return LLMResponse(
                    text=None,
                    model_name=self.model_name,
                    success=False,
                    error=f"Timeout ({timeout}s)",
                    latency_seconds=time.time() - start,
                )

            except FileNotFoundError:
                return LLMResponse(
                    text=None,
                    model_name=self.model_name,
                    success=False,
                    error=f"CLI not found for {self.model_name}",
                    latency_seconds=time.time() - start,
                )

            except Exception as e:
                return LLMResponse(
                    text=None,
                    model_name=self.model_name,
                    success=False,
                    error=f"Unexpected error: {e}",
                    latency_seconds=time.time() - start,
                )

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


class CodexClient(LLMClient):
    """OpenAI Codex CLI 클라이언트 (codex exec)"""

    def __init__(self, max_concurrency: int = 3):
        super().__init__(model_name="codex", max_concurrency=max_concurrency)

    def _build_command(self, prompt: str, **kwargs) -> list[str]:
        return [
            "codex",
            "exec",
            prompt,
            "--full-auto",
            "--json",
            "--skip-git-repo-check",
        ]

    def _extract_text(self, stdout: str) -> str | None:
        """Codex JSON 출력에서 텍스트 추출.

        codex exec --json 출력 형식:
        {"items": [{"type": "message", "content": "..."}]}
        """
        if not stdout or not stdout.strip():
            return None

        try:
            data = json.loads(stdout)
            # codex exec --json 응답 형식
            if isinstance(data, dict):
                # items 배열에서 message 타입의 content 추출
                items = data.get("items", [])
                texts = []
                for item in items:
                    if item.get("type") == "message":
                        content = item.get("content", "")
                        if isinstance(content, list):
                            for block in content:
                                if (
                                    isinstance(block, dict)
                                    and block.get("type") == "output_text"
                                ):
                                    texts.append(block.get("text", ""))
                        elif isinstance(content, str):
                            texts.append(content)
                if texts:
                    return "\n".join(texts)

                # 단순 result 필드
                if "result" in data:
                    return data["result"]
        except json.JSONDecodeError:
            pass

        # JSON 파싱 실패 시 원시 출력
        return stdout.strip() if stdout.strip() else None


class GeminiClient(LLMClient):
    """Google Gemini CLI 클라이언트 (gemini -p)"""

    def __init__(self, max_concurrency: int = 3):
        super().__init__(model_name="gemini", max_concurrency=max_concurrency)

    def _build_command(self, prompt: str, **kwargs) -> list[str]:
        return [
            "gemini",
            "-p",
            prompt,
        ]

    def _get_stdin(self) -> int:
        """Gemini CLI hang 방지를 위해 stdin을 DEVNULL로 설정."""
        return subprocess.DEVNULL

    def _extract_text(self, stdout: str) -> str | None:
        """Gemini CLI 출력에서 텍스트 추출.

        gemini -p는 일반 텍스트 또는 JSON을 출력합니다.
        """
        if not stdout or not stdout.strip():
            return None

        # JSON 응답인 경우 텍스트 추출 시도
        try:
            data = json.loads(stdout)
            if isinstance(data, dict):
                if "result" in data:
                    return data["result"]
                if "text" in data:
                    return data["text"]
                if "response" in data:
                    return data["response"]
        except json.JSONDecodeError:
            pass

        # 일반 텍스트 출력
        return stdout.strip()
