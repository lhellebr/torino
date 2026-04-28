import json
from unittest.mock import patch, MagicMock

import pytest

from torino.claude_client import ask_claude


class TestAskClaude:
    @patch("torino.claude_client.subprocess.run")
    def test_returns_result_text(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"result": "hello world"}),
        )
        result = ask_claude("say hi")
        assert result == "hello world"

    @patch("torino.claude_client.subprocess.run")
    def test_passes_prompt_via_stdin(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"result": "ok"}),
        )
        ask_claude("my prompt")
        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs["input"] == "my prompt"

    @patch("torino.claude_client.subprocess.run")
    def test_includes_allowed_tools(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"result": "ok"}),
        )
        ask_claude("prompt", allowed_tools=["WebSearch", "Bash"])
        cmd = mock_run.call_args[0][0]
        assert "--allowedTools" in cmd
        assert "WebSearch,Bash" in cmd

    @patch("torino.claude_client.subprocess.run")
    def test_no_allowed_tools_by_default(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"result": "ok"}),
        )
        ask_claude("prompt")
        cmd = mock_run.call_args[0][0]
        assert "--allowedTools" not in cmd

    @patch("torino.claude_client.subprocess.run")
    def test_raises_on_failure(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="something went wrong",
        )
        with pytest.raises(RuntimeError, match="something went wrong"):
            ask_claude("prompt")

    @patch("torino.claude_client.subprocess.run")
    def test_custom_timeout(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"result": "ok"}),
        )
        ask_claude("prompt", timeout=300)
        assert mock_run.call_args.kwargs["timeout"] == 300
