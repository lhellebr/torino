import json
from unittest.mock import patch

from torino.agents.debate import _format_issue_context, _parse_json, run_debate
from torino.models import TriageIssue
from torino.triage.validators import Check


def _make_issue():
    return TriageIssue(
        key="SAT-99999",
        summary="Test issue",
        description="Something is broken",
        issue_type="Bug",
        status="New",
        priority="Undefined",
        severity=None,
        components=["Authentication"],
        labels=[],
        fix_versions=[],
        affects_versions=[],
        regression=None,
        regression_from_description="Yes",
        reporter="testuser",
        assignee=None,
        url="https://example.atlassian.net/browse/SAT-99999",
    )


SAMPLE_ASSESSMENT = {
    "severity": "Important",
    "severity_reasoning": "Auth issue",
    "priority": "Major",
    "priority_reasoning": "Regression",
    "component": "Authentication",
    "component_reasoning": "Auth related",
    "is_regression": "Yes",
    "regression_reasoning": "Reporter says so",
    "is_security": False,
    "labels": [],
    "need_info_from": None,
    "need_info_reasoning": "",
    "summary": "Auth regression",
}

SAMPLE_SYNTHESIS = {
    **SAMPLE_ASSESSMENT,
    "disagreements": [],
    "jira_comment": "This issue was triaged by an AI-assisted tool (Torino). Auth regression.",
}


class TestParseJson:
    def test_plain_json(self):
        result = _parse_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_in_code_fence(self):
        text = '```json\n{"key": "value"}\n```'
        result = _parse_json(text)
        assert result == {"key": "value"}

    def test_json_in_bare_code_fence(self):
        text = '```\n{"key": "value"}\n```'
        result = _parse_json(text)
        assert result == {"key": "value"}


class TestFormatIssueContext:
    def test_contains_issue_fields(self):
        issue = _make_issue()
        checks = [
            Check("Priority", "missing", "Priority not set"),
            Check("Component", "ok", "Authentication"),
        ]
        context = _format_issue_context(issue, checks, ["Authentication", "Hosts"])

        assert "SAT-99999" in context
        assert "Test issue" in context
        assert "Authentication" in context
        assert "[MISSING] Priority" in context
        assert "[OK] Component" in context
        assert "Hosts" in context
        assert "New" in context
        assert "testuser" in context
        assert "unassigned" in context

    def test_contains_version_fields(self):
        issue = _make_issue()
        issue.affects_versions = ["6.14.0", "6.15.0"]
        issue.fix_versions = ["6.16.0"]
        context = _format_issue_context(issue, [], ["Authentication"])

        assert "6.14.0" in context
        assert "6.15.0" in context
        assert "6.16.0" in context

    def test_empty_versions(self):
        issue = _make_issue()
        context = _format_issue_context(issue, [], ["Authentication"])
        assert "Affects versions: none" in context
        assert "Fix versions: none" in context

    def test_empty_components(self):
        issue = _make_issue()
        issue.components = []
        context = _format_issue_context(issue, [], ["Authentication"])
        assert "not set" in context


class TestRunDebate:
    @patch("torino.agents.debate.ask_claude")
    def test_full_debate_flow(self, mock_claude):
        mock_claude.return_value = json.dumps(SAMPLE_ASSESSMENT)

        def synthesis_response(prompt, **kwargs):
            if "moderator" in prompt.lower() or "synthesizing" in prompt.lower():
                return json.dumps(SAMPLE_SYNTHESIS)
            return json.dumps(SAMPLE_ASSESSMENT)

        mock_claude.side_effect = synthesis_response

        issue = _make_issue()
        checks = [Check("Priority", "missing", "Priority not set")]
        components = ["Authentication", "Hosts"]

        result = run_debate(issue, checks, components)

        assert result["severity"] == "Important"
        assert result["component"] == "Authentication"
        assert result["is_regression"] == "Yes"
        assert "round1" in result
        assert "round2" in result
        assert len(result["round1"]) == 4
        assert len(result["round2"]) == 4

    @patch("torino.agents.debate.ask_claude")
    def test_debate_calls_claude_9_times(self, mock_claude):
        mock_claude.return_value = json.dumps(SAMPLE_ASSESSMENT)

        issue = _make_issue()
        checks = []
        components = ["Authentication"]

        run_debate(issue, checks, components)

        # 4 round1 + 4 round2 + 1 synthesis = 9
        assert mock_claude.call_count == 9

    @patch("torino.agents.debate.ask_claude")
    def test_round1_uses_allowed_tools(self, mock_claude):
        mock_claude.return_value = json.dumps(SAMPLE_ASSESSMENT)

        issue = _make_issue()
        run_debate(issue, [], ["Authentication"])

        round1_calls = mock_claude.call_args_list[:4]
        tools_used = [call.kwargs.get("allowed_tools") for call in round1_calls]
        assert ["WebSearch", "Bash"] in tools_used
        assert ["WebSearch", "WebFetch"] in tools_used

    @patch("torino.agents.debate.ask_claude")
    def test_on_update_called(self, mock_claude):
        mock_claude.return_value = json.dumps(SAMPLE_ASSESSMENT)

        messages = []
        issue = _make_issue()
        run_debate(issue, [], ["Authentication"], on_update=messages.append)

        assert any("Round 1" in m for m in messages)
        assert any("Round 2" in m for m in messages)
        assert any("Round 3" in m for m in messages)

    @patch("torino.agents.debate.ask_claude")
    def test_result_includes_jira_comment(self, mock_claude):
        mock_claude.return_value = json.dumps(SAMPLE_SYNTHESIS)

        issue = _make_issue()
        result = run_debate(issue, [], ["Authentication"])

        assert "jira_comment" in result
        assert "Torino" in result["jira_comment"]
