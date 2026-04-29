from types import SimpleNamespace
from unittest.mock import MagicMock, call

import pytest

from torino.jira_client import apply_triage, FIELD_SEVERITY, FIELD_REGRESSION, FIELD_NEED_INFO_FROM


def _mock_client(existing_labels=None):
    client = MagicMock()
    issue = MagicMock()
    issue.fields.labels = list(existing_labels or [])
    client.issue.return_value = issue
    return client, issue


class TestApplyTriage:
    def test_sets_severity(self):
        client, issue = _mock_client()
        result = {"severity": "Important"}

        actions = apply_triage(client, "SAT-99999", result)

        update_call = issue.update.call_args_list[0]
        fields = update_call.kwargs["fields"]
        assert fields[FIELD_SEVERITY] == {"value": "Important"}
        assert any("severity" in a.lower() for a in actions)

    def test_sets_priority(self):
        client, issue = _mock_client()
        result = {"priority": "Major"}

        actions = apply_triage(client, "SAT-99999", result)

        update_call = issue.update.call_args_list[0]
        fields = update_call.kwargs["fields"]
        assert fields["priority"] == {"name": "Major"}

    def test_sets_regression(self):
        client, issue = _mock_client()
        result = {"is_regression": "Yes"}

        actions = apply_triage(client, "SAT-99999", result)

        update_call = issue.update.call_args_list[0]
        fields = update_call.kwargs["fields"]
        assert fields[FIELD_REGRESSION] == {"value": "Yes"}

    def test_sets_component(self):
        client, issue = _mock_client()
        result = {"component": "Authentication"}

        actions = apply_triage(client, "SAT-99999", result)

        update_call = issue.update.call_args_list[0]
        fields = update_call.kwargs["fields"]
        assert fields["components"] == [{"name": "Authentication"}]

    def test_sets_need_info_from(self):
        client, issue = _mock_client()
        mock_user = MagicMock()
        mock_user.accountId = "abc123"
        mock_user.__str__ = lambda s: "John Doe"
        client.search_users.return_value = [mock_user]
        result = {"need_info_from": "jdoe"}

        actions = apply_triage(client, "SAT-99999", result)

        client.search_users.assert_called_once_with(query="jdoe", maxResults=1)
        update_call = issue.update.call_args_list[0]
        fields = update_call.kwargs["fields"]
        assert fields[FIELD_NEED_INFO_FROM] == [{"accountId": "abc123"}]
        assert any("Need Info From" in a for a in actions)

    def test_need_info_skips_triaged_label(self):
        client, issue = _mock_client()
        mock_user = MagicMock()
        mock_user.accountId = "abc123"
        mock_user.__str__ = lambda s: "John Doe"
        client.search_users.return_value = [mock_user]
        result = {"need_info_from": "jdoe"}

        actions = apply_triage(client, "SAT-99999", result)

        assert "triaged" not in issue.fields.labels

    def test_need_info_from_user_not_found(self):
        client, issue = _mock_client()
        client.search_users.return_value = []
        result = {"need_info_from": "nonexistent"}

        actions = apply_triage(client, "SAT-99999", result)

        assert any("Could not resolve" in a for a in actions)

    def test_adds_triaged_label(self):
        client, issue = _mock_client()
        result = {}

        actions = apply_triage(client, "SAT-99999", result)

        assert "triaged" in issue.fields.labels
        assert any("triaged" in a for a in actions)

    def test_triaged_added_even_when_agents_omit_it(self):
        client, issue = _mock_client()
        result = {"labels": ["Security", "Regression"]}

        actions = apply_triage(client, "SAT-99999", result)

        assert "triaged" in issue.fields.labels
        assert "Security" in issue.fields.labels
        assert "Regression" in issue.fields.labels

    def test_adds_suggested_labels(self):
        client, issue = _mock_client()
        result = {"labels": ["easy-fix", "user-experience"]}

        actions = apply_triage(client, "SAT-99999", result)

        assert "easy-fix" in issue.fields.labels
        assert "user-experience" in issue.fields.labels
        assert "triaged" in issue.fields.labels

    def test_does_not_duplicate_existing_labels(self):
        client, issue = _mock_client(existing_labels=["triaged"])
        result = {"labels": ["triaged"]}

        actions = apply_triage(client, "SAT-99999", result)

        assert issue.fields.labels.count("triaged") == 1
        assert not any("Added label 'triaged'" in a for a in actions)

    def test_posts_jira_comment(self):
        client, issue = _mock_client()
        result = {"jira_comment": "This issue was triaged by an AI-assisted tool (Torino)."}

        actions = apply_triage(client, "SAT-99999", result)

        client.add_comment.assert_called_once_with(
            "SAT-99999",
            "This issue was triaged by an AI-assisted tool (Torino).",
        )
        assert any("comment" in a.lower() for a in actions)

    def test_no_comment_when_absent(self):
        client, issue = _mock_client()
        result = {}

        apply_triage(client, "SAT-99999", result)

        client.add_comment.assert_not_called()

    def test_empty_result_still_adds_triaged(self):
        client, issue = _mock_client()
        result = {}

        actions = apply_triage(client, "SAT-99999", result)

        assert "triaged" in issue.fields.labels

    def test_all_fields_at_once(self):
        client, issue = _mock_client()
        result = {
            "severity": "Critical",
            "priority": "Critical",
            "is_regression": "Yes",
            "component": "Security",
            "need_info_from": "jdoe",
            "labels": ["patch"],
            "jira_comment": "Triaged.",
        }

        actions = apply_triage(client, "SAT-99999", result)

        assert len(actions) >= 7
