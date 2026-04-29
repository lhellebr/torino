import json
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from torino.jira_client import search_similar, _extract_search_keywords
from torino.models import TriageIssue


def _make_issue(**overrides):
    defaults = dict(
        key="SAT-99999",
        summary="Login fails after upgrade",
        description="Authentication broken after upgrading to 6.19",
        issue_type="Bug",
        status="New",
        priority="Major",
        severity=None,
        components=["Authentication"],
        labels=[],
        fix_versions=[],
        affects_versions=[],
        regression=None,
        regression_from_description=None,
        reporter="testuser",
        assignee=None,
        url="https://example.atlassian.net/browse/SAT-99999",
    )
    defaults.update(overrides)
    return TriageIssue(**defaults)


def _mock_jira_issue(key, summary):
    issue = MagicMock()
    issue.key = key
    issue.fields.summary = summary
    issue.fields.description = "some description"
    issue.fields.issuetype = SimpleNamespace(__str__=lambda s: "Bug")
    issue.fields.status = SimpleNamespace(__str__=lambda s: "Open")
    issue.fields.priority = SimpleNamespace(__str__=lambda s: "Major")
    issue.fields.components = []
    issue.fields.labels = []
    issue.fields.fixVersions = []
    issue.fields.versions = []
    issue.fields.reporter = SimpleNamespace(__str__=lambda s: "someone")
    issue.fields.assignee = None
    issue.fields.customfield_10840 = None
    issue.fields.customfield_10623 = None
    return issue


class TestExtractSearchKeywords:
    @patch("torino.claude_client.ask_claude")
    def test_returns_keywords(self, mock_claude):
        mock_claude.return_value = "login authentication password bypass"

        result = _extract_search_keywords("SAT-99999", "Login fails", "Auth broken")

        assert result == "login authentication password bypass"

    @patch("torino.claude_client.ask_claude")
    def test_passes_key_summary_description(self, mock_claude):
        mock_claude.return_value = "keywords"

        _extract_search_keywords("SAT-12345", "My summary", "My description")

        prompt = mock_claude.call_args[0][0]
        assert "SAT-12345" in prompt
        assert "My summary" in prompt
        assert "My description" in prompt

    @patch("torino.claude_client.ask_claude")
    def test_handles_none_description(self, mock_claude):
        mock_claude.return_value = "keywords"

        _extract_search_keywords("SAT-99999", "Summary", None)

        prompt = mock_claude.call_args[0][0]
        assert "(empty)" in prompt


class TestSearchSimilar:
    @patch("torino.jira_client._extract_search_keywords")
    def test_searches_by_summary_and_keywords(self, mock_keywords):
        mock_keywords.return_value = "auth login bypass"
        client = MagicMock()
        client.search_issues.return_value = []

        issue = _make_issue()
        search_similar(client, issue, "SAT", "https://example.atlassian.net")

        assert client.search_issues.call_count >= 2

    @patch("torino.jira_client._extract_search_keywords")
    def test_excludes_current_issue(self, mock_keywords):
        mock_keywords.return_value = "auth login"
        client = MagicMock()
        client.search_issues.return_value = []

        issue = _make_issue(key="SAT-99999")
        search_similar(client, issue, "SAT", "https://example.atlassian.net")

        for call in client.search_issues.call_args_list:
            jql = call[0][0]
            assert "key != SAT-99999" in jql

    @patch("torino.jira_client._extract_search_keywords")
    def test_max_5_candidates(self, mock_keywords):
        mock_keywords.return_value = "auth"
        client = MagicMock()
        results = [_mock_jira_issue(f"SAT-{i}", f"Issue {i}") for i in range(10)]
        client.search_issues.return_value = results

        issue = _make_issue()
        similar = search_similar(client, issue, "SAT", "https://example.atlassian.net")

        assert len(similar) <= 5

    @patch("torino.jira_client._extract_search_keywords")
    def test_deduplicates_results(self, mock_keywords):
        mock_keywords.return_value = "auth login"
        client = MagicMock()
        same_issue = _mock_jira_issue("SAT-11111", "Duplicate result")
        client.search_issues.return_value = [same_issue]

        issue = _make_issue()
        similar = search_similar(client, issue, "SAT", "https://example.atlassian.net")

        keys = [s.key for s in similar]
        assert keys.count("SAT-11111") == 1

    @patch("torino.jira_client._extract_search_keywords")
    def test_graceful_on_keyword_failure(self, mock_keywords):
        mock_keywords.side_effect = RuntimeError("Claude failed")
        client = MagicMock()
        client.search_issues.return_value = []

        issue = _make_issue()
        similar = search_similar(client, issue, "SAT", "https://example.atlassian.net")

        assert similar == []
        assert client.search_issues.call_count >= 1

    @patch("torino.jira_client._extract_search_keywords")
    def test_graceful_on_jql_error(self, mock_keywords):
        mock_keywords.return_value = "auth"
        client = MagicMock()
        client.search_issues.side_effect = Exception("JQL error")

        issue = _make_issue()
        similar = search_similar(client, issue, "SAT", "https://example.atlassian.net")

        assert similar == []

    @patch("torino.jira_client._extract_search_keywords")
    def test_on_update_shows_keywords(self, mock_keywords):
        mock_keywords.return_value = "auth login bypass"
        client = MagicMock()
        client.search_issues.return_value = []

        messages = []
        issue = _make_issue()
        search_similar(client, issue, "SAT", "https://example.atlassian.net", on_update=messages.append)

        assert any("auth login bypass" in m for m in messages)
