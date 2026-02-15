"""
Claude CLI 기반 클라이언트 (구독 플랜 활용)
- subprocess를 통한 claude -p 헤드리스 모드 호출
- Max 구독 플랜 사용량 소비 (API KEY 불필요)
- 동시성 제한 (Semaphore)
- JSON 응답 파싱 (코드블록 + regex fallback)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import threading


class ClaudeClient:
    """Claude CLI 헤드리스 모드 래퍼 클라이언트 (구독 플랜 전용)"""

    def __init__(self, max_concurrency: int = 3):
        self._semaphore = threading.Semaphore(max_concurrency)
        # Claude CLI 환경 설정
        env = {**os.environ, "DISABLE_INTERLEAVED_THINKING": "true"}
        # 중첩 세션 차단 우회 (Claude Code 내부에서 실행 시)
        env.pop("CLAUDECODE", None)
        self._env = env

    def predict_sync(
        self,
        prompt: str,
        model: str = "opus",
        max_tokens: int = 8192,
        timeout: float = 3000,
    ) -> str | None:
        """동기 예측 호출. 성공 시 응답 텍스트, 실패 시 None 반환.

        Claude CLI 헤드리스 모드를 사용하여 구독 플랜 사용량을 소비합니다.
        """
        cmd = [
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

        with self._semaphore:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env=self._env,
                )

                if result.returncode != 0:
                    stderr_preview = result.stderr[:300] if result.stderr else "N/A"
                    print(
                        f"[ClaudeClient] CLI 오류 (code={result.returncode}): {stderr_preview}"
                    )
                    return None

                # --output-format json의 경우 {"type":"result","result":"..."} 형태
                output = result.stdout
                if not output or not output.strip():
                    print("[ClaudeClient] 빈 응답")
                    return None

                # Claude CLI JSON 출력에서 실제 텍스트 추출
                try:
                    cli_response = json.loads(output)
                    if isinstance(cli_response, dict) and "result" in cli_response:
                        return cli_response["result"]
                except json.JSONDecodeError:
                    pass

                # JSON 래핑이 아닌 경우 원시 출력 반환
                return output

            except subprocess.TimeoutExpired:
                print(f"[ClaudeClient] 타임아웃 ({timeout}s)")
                return None
            except FileNotFoundError:
                print(
                    "[ClaudeClient] 'claude' CLI를 찾을 수 없습니다. Claude Code가 설치되어 있는지 확인하세요."
                )
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
