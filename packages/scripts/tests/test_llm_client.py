"""LLMClient ABC, CodexClient, GeminiClient 단위 테스트"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.llm_client import (
    CodexClient,
    GeminiClient,
    LLMClient,
    LLMResponse,
)


# ---------------------------------------------------------------------------
# LLMResponse dataclass
# ---------------------------------------------------------------------------
class TestLLMResponse:
    def test_success_response(self):
        r = LLMResponse(text="hello", model_name="test", success=True)
        assert r.success is True
        assert r.text == "hello"
        assert r.error is None

    def test_failure_response(self):
        r = LLMResponse(text=None, model_name="test", success=False, error="timeout")
        assert r.success is False
        assert r.text is None
        assert r.error == "timeout"


# ---------------------------------------------------------------------------
# parse_json (static method on LLMClient)
# ---------------------------------------------------------------------------
class TestParseJson:
    def test_json_code_block(self):
        text = '```json\n{"selected_horses": [1, 2, 3]}\n```'
        result = LLMClient.parse_json(text)
        assert result == {"selected_horses": [1, 2, 3]}

    def test_raw_json(self):
        text = 'Some text {"key": "value"} more text'
        result = LLMClient.parse_json(text)
        assert result == {"key": "value"}

    def test_empty_input(self):
        assert LLMClient.parse_json("") is None
        assert LLMClient.parse_json(None) is None

    def test_no_json(self):
        assert LLMClient.parse_json("plain text without json") is None


# ---------------------------------------------------------------------------
# CodexClient
# ---------------------------------------------------------------------------
class TestCodexClient:
    def test_build_command(self):
        client = CodexClient(max_concurrency=1)
        cmd = client._build_command("test prompt")
        assert cmd == [
            "codex",
            "exec",
            "test prompt",
            "--full-auto",
            "--json",
            "--skip-git-repo-check",
        ]

    def test_extract_text_items_format(self):
        client = CodexClient()
        stdout = json.dumps(
            {
                "items": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "hello world"}],
                    }
                ]
            }
        )
        assert client._extract_text(stdout) == "hello world"

    def test_extract_text_result_field(self):
        client = CodexClient()
        stdout = json.dumps({"result": "test result"})
        assert client._extract_text(stdout) == "test result"

    def test_extract_text_plain(self):
        client = CodexClient()
        assert client._extract_text("plain output") == "plain output"

    def test_extract_text_empty(self):
        client = CodexClient()
        assert client._extract_text("") is None
        assert client._extract_text("   ") is None

    @patch("subprocess.run")
    def test_predict_sync_success(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"result": "prediction text"}),
            stderr="",
        )
        client = CodexClient(max_concurrency=1)
        resp = client.predict_sync("test prompt", timeout=10)
        assert resp.success is True
        assert resp.text == "prediction text"
        assert resp.model_name == "codex"

    @patch("subprocess.run")
    def test_predict_sync_cli_error(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error msg")
        client = CodexClient(max_concurrency=1)
        resp = client.predict_sync("test", timeout=10)
        assert resp.success is False
        assert "CLI error" in resp.error

    @patch(
        "subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="codex", timeout=5)
    )
    def test_predict_sync_timeout(self, mock_run):
        client = CodexClient(max_concurrency=1)
        resp = client.predict_sync("test", timeout=5)
        assert resp.success is False
        assert "Timeout" in resp.error

    @patch("subprocess.run", side_effect=FileNotFoundError())
    def test_predict_sync_not_found(self, mock_run):
        client = CodexClient(max_concurrency=1)
        resp = client.predict_sync("test", timeout=5)
        assert resp.success is False
        assert "CLI not found" in resp.error

    def test_env_no_claudecode(self):
        client = CodexClient()
        assert "CLAUDECODE" not in client._env


# ---------------------------------------------------------------------------
# GeminiClient
# ---------------------------------------------------------------------------
class TestGeminiClient:
    def test_build_command(self):
        client = GeminiClient(max_concurrency=1)
        cmd = client._build_command("test prompt")
        assert cmd == ["gemini", "-p", "test prompt"]

    def test_get_stdin_devnull(self):
        client = GeminiClient()
        assert client._get_stdin() == subprocess.DEVNULL

    def test_extract_text_json_result(self):
        client = GeminiClient()
        stdout = json.dumps({"result": "gemini answer"})
        assert client._extract_text(stdout) == "gemini answer"

    def test_extract_text_plain(self):
        client = GeminiClient()
        assert client._extract_text("plain gemini output") == "plain gemini output"

    def test_extract_text_empty(self):
        client = GeminiClient()
        assert client._extract_text("") is None

    @patch("subprocess.run")
    def test_predict_sync_success(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="gemini prediction", stderr=""
        )
        client = GeminiClient(max_concurrency=1)
        resp = client.predict_sync("test", timeout=10)
        assert resp.success is True
        assert resp.text == "gemini prediction"
        assert resp.model_name == "gemini"

    def test_env_no_claudecode(self):
        client = GeminiClient()
        assert "CLAUDECODE" not in client._env
