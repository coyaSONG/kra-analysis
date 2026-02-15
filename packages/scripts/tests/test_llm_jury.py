"""LLMJury 단위 테스트"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.llm_client import LLMClient, LLMResponse
from shared.llm_jury import JuryVerdict, LLMJury


# ---------------------------------------------------------------------------
# MockClient: LLMClient를 상속하여 테스트용 구현
# ---------------------------------------------------------------------------
class MockClient(LLMClient):
    """테스트용 Mock LLM 클라이언트"""

    def __init__(self, name: str, response_text: str | None, success: bool = True):
        super().__init__(model_name=name, max_concurrency=1)
        self._response_text = response_text
        self._success = success

    def _build_command(self, prompt: str, **kwargs) -> list[str]:
        return ["echo", "mock"]

    def predict_sync(self, prompt: str, timeout: float = 3000, **kwargs) -> LLMResponse:
        return LLMResponse(
            text=self._response_text,
            model_name=self.model_name,
            success=self._success,
            error=None if self._success else "mock error",
            latency_seconds=0.1,
        )


# ---------------------------------------------------------------------------
# JuryVerdict
# ---------------------------------------------------------------------------
class TestJuryVerdict:
    def test_empty_verdict(self):
        v = JuryVerdict()
        assert v.quorum_reached is False
        assert v.agreement_ratio == 0.0

    def test_quorum_reached_with_two_successes(self):
        v = JuryVerdict()
        v.responses = [
            LLMResponse(text="a", model_name="m1", success=True),
            LLMResponse(text="b", model_name="m2", success=True),
        ]
        v.successful_responses = v.responses.copy()
        assert v.quorum_reached is True
        assert v.agreement_ratio == 1.0

    def test_quorum_not_reached_with_one_success(self):
        v = JuryVerdict()
        ok = LLMResponse(text="a", model_name="m1", success=True)
        fail = LLMResponse(text=None, model_name="m2", success=False)
        v.responses = [ok, fail]
        v.successful_responses = [ok]
        v.failed_responses = [fail]
        assert v.quorum_reached is False
        assert v.agreement_ratio == 0.5


# ---------------------------------------------------------------------------
# LLMJury
# ---------------------------------------------------------------------------
class TestLLMJury:
    def test_empty_clients_raises(self):
        with pytest.raises(ValueError):
            LLMJury([])

    def test_all_success(self):
        clients = [
            MockClient("claude", '{"predicted": [1, 2, 3]}'),
            MockClient("codex", '{"predicted": [1, 3, 5]}'),
            MockClient("gemini", '{"predicted": [2, 3, 4]}'),
        ]
        jury = LLMJury(clients)
        verdict = jury.deliberate("test prompt", timeout=10)

        assert len(verdict.responses) == 3
        assert len(verdict.successful_responses) == 3
        assert len(verdict.failed_responses) == 0
        assert verdict.quorum_reached is True
        assert verdict.agreement_ratio == 1.0

    def test_partial_failure(self):
        clients = [
            MockClient("claude", '{"predicted": [1, 2, 3]}'),
            MockClient("codex", None, success=False),
            MockClient("gemini", '{"predicted": [2, 3, 4]}'),
        ]
        jury = LLMJury(clients)
        verdict = jury.deliberate("test prompt", timeout=10)

        assert len(verdict.responses) == 3
        assert len(verdict.successful_responses) == 2
        assert len(verdict.failed_responses) == 1
        assert verdict.quorum_reached is True

    def test_total_failure(self):
        clients = [
            MockClient("claude", None, success=False),
            MockClient("codex", None, success=False),
            MockClient("gemini", None, success=False),
        ]
        jury = LLMJury(clients)
        verdict = jury.deliberate("test prompt", timeout=10)

        assert len(verdict.successful_responses) == 0
        assert verdict.quorum_reached is False

    def test_single_client(self):
        clients = [MockClient("claude", "response")]
        jury = LLMJury(clients)
        verdict = jury.deliberate("test", timeout=10)

        assert len(verdict.responses) == 1
        assert verdict.quorum_reached is False  # 1 < 2

    def test_two_clients_both_succeed(self):
        clients = [
            MockClient("claude", "a"),
            MockClient("codex", "b"),
        ]
        jury = LLMJury(clients)
        verdict = jury.deliberate("test", timeout=10)
        assert verdict.quorum_reached is True
