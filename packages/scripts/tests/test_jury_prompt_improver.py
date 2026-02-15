"""JuryPromptImprover 단위 테스트"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prompt_improvement.jury_prompt_improver import (
    JuryPromptImprover,
)
from shared.llm_client import LLMClient, LLMResponse
from shared.llm_jury import LLMJury


# ---------------------------------------------------------------------------
# MockClient
# ---------------------------------------------------------------------------
class MockClient(LLMClient):
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


def _make_structure():
    """테스트용 PromptStructure 생성"""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "prompt_improvement"))
    from v5_modules.prompt_parser import PromptStructure

    structure = PromptStructure(
        title="Test Prompt",
        version="v1.0",
    )
    structure.add_section("context", "경마 예측 시스템입니다.", order=0)
    structure.add_section("analysis_steps", "1. 기본 분석\n2. 상세 분석", order=1)
    structure.add_section("output_format", "JSON 형식으로 출력", order=2)
    return structure


def _make_modification_response(section: str, action: str, description: str) -> str:
    """수정안 JSON 응답 생성"""
    return json.dumps(
        {
            "modifications": [
                {
                    "section": section,
                    "action": action,
                    "description": description,
                    "content": f"개선된 {section} 내용",
                    "reasoning": "테스트 근거",
                    "priority": 3,
                }
            ]
        }
    )


class TestJuryPromptImproverConsensus:
    """2/3 이상 합의된 수정만 적용되는지 테스트"""

    def test_consensus_reached_two_models_agree(self):
        # claude와 codex가 동일 (section, action) 제안
        clients = [
            MockClient(
                "claude",
                _make_modification_response("analysis_steps", "modify", "분석 강화"),
            ),
            MockClient(
                "codex",
                _make_modification_response("analysis_steps", "modify", "분석 개선"),
            ),
            MockClient(
                "gemini",
                _make_modification_response("output_format", "modify", "출력 개선"),
            ),
        ]
        jury = LLMJury(clients)
        improver = JuryPromptImprover(jury=jury, min_consensus=2)

        structure = _make_structure()
        metrics = {"success_rate": 30.0, "avg_correct": 1.0, "total_races": 10}

        new_structure, changes = improver.improve_prompt(structure, [], metrics, "v1.1")

        # analysis_steps는 2개 모델 합의 → 적용
        assert len(changes) == 1
        assert changes[0].target_section == "analysis_steps"
        assert new_structure.version == "v1.1"

    def test_no_consensus_no_changes(self):
        # 3개 모델 모두 다른 (section, action) 제안
        clients = [
            MockClient(
                "claude",
                _make_modification_response("context", "modify", "컨텍스트 변경"),
            ),
            MockClient(
                "codex",
                _make_modification_response("analysis_steps", "modify", "분석 변경"),
            ),
            MockClient(
                "gemini",
                _make_modification_response("output_format", "modify", "출력 변경"),
            ),
        ]
        jury = LLMJury(clients)
        improver = JuryPromptImprover(jury=jury, min_consensus=2)

        structure = _make_structure()
        metrics = {"success_rate": 30.0, "avg_correct": 1.0, "total_races": 10}

        new_structure, changes = improver.improve_prompt(structure, [], metrics, "v1.1")

        # 합의 없음 → 변경 없음 (fallback 없음)
        assert len(changes) == 0

    def test_unanimous_consensus(self):
        # 3개 모델 모두 동일 (section, action) 제안
        clients = [
            MockClient(
                "claude", _make_modification_response("analysis_steps", "modify", "A")
            ),
            MockClient(
                "codex", _make_modification_response("analysis_steps", "modify", "B")
            ),
            MockClient(
                "gemini", _make_modification_response("analysis_steps", "modify", "C")
            ),
        ]
        jury = LLMJury(clients)
        improver = JuryPromptImprover(jury=jury, min_consensus=2)

        structure = _make_structure()
        metrics = {"success_rate": 30.0, "avg_correct": 1.0, "total_races": 10}

        new_structure, changes = improver.improve_prompt(structure, [], metrics, "v1.1")

        assert len(changes) == 1
        assert changes[0].target_section == "analysis_steps"


class TestJuryPromptImproverFallback:
    """모델 응답 부족 시 fallback 테스트"""

    def test_fallback_on_total_failure(self):
        clients = [
            MockClient("claude", None, success=False),
            MockClient("codex", None, success=False),
            MockClient("gemini", None, success=False),
        ]
        jury = LLMJury(clients)

        # Mock DynamicReconstructor
        mock_reconstructor = MagicMock()
        mock_structure = _make_structure()
        mock_structure.version = "v1.1"
        from v5_modules.common_types import Change

        mock_changes = [
            Change(
                change_type="modify",
                target_section="context",
                description="fallback change",
            )
        ]
        mock_reconstructor.reconstruct_prompt.return_value = (
            mock_structure,
            mock_changes,
        )

        # insight_analysis mock
        mock_insight = MagicMock()

        improver = JuryPromptImprover(
            jury=jury, fallback_reconstructor=mock_reconstructor, min_consensus=2
        )

        structure = _make_structure()
        metrics = {"success_rate": 30.0, "avg_correct": 1.0, "total_races": 10}

        new_structure, changes = improver.improve_prompt(
            structure, [], metrics, "v1.1", insight_analysis=mock_insight
        )

        # Fallback 호출 확인
        mock_reconstructor.reconstruct_prompt.assert_called_once()
        assert len(changes) == 1
        assert changes[0].description == "fallback change"

    def test_no_fallback_without_reconstructor(self):
        clients = [
            MockClient("claude", None, success=False),
            MockClient("codex", None, success=False),
            MockClient("gemini", None, success=False),
        ]
        jury = LLMJury(clients)
        improver = JuryPromptImprover(jury=jury, min_consensus=2)

        structure = _make_structure()
        metrics = {"success_rate": 30.0, "avg_correct": 1.0, "total_races": 10}

        new_structure, changes = improver.improve_prompt(structure, [], metrics, "v1.1")

        assert len(changes) == 0


class TestJuryPromptImproverActions:
    """add, modify, remove 액션 테스트"""

    def test_add_section(self):
        response = json.dumps(
            {
                "modifications": [
                    {
                        "section": "new_section",
                        "action": "add",
                        "description": "새 섹션 추가",
                        "content": "새 섹션 내용",
                        "reasoning": "추가 필요",
                        "priority": 1,
                    }
                ]
            }
        )
        clients = [
            MockClient("claude", response),
            MockClient("codex", response),
        ]
        jury = LLMJury(clients)
        improver = JuryPromptImprover(jury=jury, min_consensus=2)

        structure = _make_structure()
        metrics = {"success_rate": 30.0, "avg_correct": 1.0, "total_races": 10}

        new_structure, changes = improver.improve_prompt(structure, [], metrics, "v1.1")

        assert len(changes) == 1
        assert changes[0].change_type == "add"
        assert new_structure.get_section("new_section") is not None

    def test_remove_section(self):
        response = json.dumps(
            {
                "modifications": [
                    {
                        "section": "output_format",
                        "action": "remove",
                        "description": "출력 형식 제거",
                        "content": "",
                        "reasoning": "불필요",
                        "priority": 5,
                    }
                ]
            }
        )
        clients = [
            MockClient("claude", response),
            MockClient("codex", response),
        ]
        jury = LLMJury(clients)
        improver = JuryPromptImprover(jury=jury, min_consensus=2)

        structure = _make_structure()
        metrics = {"success_rate": 30.0, "avg_correct": 1.0, "total_races": 10}

        new_structure, changes = improver.improve_prompt(structure, [], metrics, "v1.1")

        assert len(changes) == 1
        assert changes[0].change_type == "remove"
        assert new_structure.get_section("output_format") is None


class TestPromptModificationParsing:
    """수정안 파싱 테스트"""

    def test_parse_valid_json(self):
        response = _make_modification_response("context", "modify", "test")
        clients = [MockClient("claude", response)]
        jury = LLMJury(clients)
        improver = JuryPromptImprover(jury=jury)

        mods = improver._parse_modifications(response, "claude")
        assert len(mods) == 1
        assert mods[0].section == "context"
        assert mods[0].action == "modify"
        assert mods[0].source_model == "claude"

    def test_parse_invalid_json(self):
        clients = [MockClient("claude", "not json at all")]
        jury = LLMJury(clients)
        improver = JuryPromptImprover(jury=jury)

        mods = improver._parse_modifications("not json", "claude")
        assert len(mods) == 0

    def test_parse_invalid_action(self):
        response = json.dumps(
            {
                "modifications": [
                    {
                        "section": "context",
                        "action": "invalid_action",
                        "description": "test",
                        "content": "test",
                        "reasoning": "test",
                        "priority": 5,
                    }
                ]
            }
        )
        clients = [MockClient("claude", response)]
        jury = LLMJury(clients)
        improver = JuryPromptImprover(jury=jury)

        mods = improver._parse_modifications(response, "claude")
        assert len(mods) == 0
