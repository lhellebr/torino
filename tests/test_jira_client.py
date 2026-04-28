from types import SimpleNamespace

import pytest

from torino.jira_client import (
    _option_str,
    _parse_regression_from_description,
    issue_to_model,
)


class _StrObj:
    """Mimics JIRA objects that return a name from str()."""
    def __init__(self, name):
        self._name = name
    def __str__(self):
        return self._name


class TestOptionStr:
    def test_none(self):
        assert _option_str(None) is None

    def test_plain_string(self):
        assert _option_str("Critical") == "Critical"

    def test_object_with_value(self):
        obj = SimpleNamespace(value="Yes")
        assert _option_str(obj) == "Yes"


class TestParseRegressionFromDescription:
    def test_yes(self):
        desc = (
            "*Description of problem:*\n"
            "Something broke\n\n"
            "*Is this issue a regression from an earlier version:*\n"
            " Yes\n\n"
            "*Steps to Reproduce:*\n"
        )
        assert _parse_regression_from_description(desc) == "Yes"

    def test_no(self):
        desc = (
            "*Is this issue a regression from an earlier version:*\n"
            " No\n"
        )
        assert _parse_regression_from_description(desc) == "No"

    def test_freeform_text(self):
        desc = (
            "*Is this issue a regression from an earlier version:*\n"
            " Yes, since 6.14.0\n"
        )
        assert _parse_regression_from_description(desc) == "Yes, since 6.14.0"

    def test_missing_section(self):
        desc = "*Description of problem:*\nSomething broke\n"
        assert _parse_regression_from_description(desc) is None

    def test_none_description(self):
        assert _parse_regression_from_description(None) is None

    def test_empty_description(self):
        assert _parse_regression_from_description("") is None


def _make_jira_issue(overrides=None):
    defaults = {
        "summary": "Test issue",
        "description": "*Description of problem:*\nTest\n",
        "issuetype": _StrObj("Bug"),
        "status": _StrObj("New"),
        "priority": _StrObj("Major"),
        "components": [SimpleNamespace(name="Authentication")],
        "labels": ["triaged"],
        "fixVersions": [SimpleNamespace(name="6.15.0")],
        "versions": [SimpleNamespace(name="6.14.0")],
        "reporter": _StrObj("testuser"),
        "assignee": None,
        "customfield_10840": SimpleNamespace(value="Important"),
        "customfield_10623": SimpleNamespace(value="Yes"),
    }
    if overrides:
        defaults.update(overrides)
    fields = SimpleNamespace(**defaults)
    return SimpleNamespace(key="SAT-99999", fields=fields)


class TestIssueToModel:
    def test_basic_mapping(self):
        issue = _make_jira_issue()
        model = issue_to_model(issue, "https://example.atlassian.net")

        assert model.key == "SAT-99999"
        assert model.summary == "Test issue"
        assert model.issue_type == "Bug"
        assert model.status == "New"
        assert model.priority == "Major"
        assert model.severity == "Important"
        assert model.components == ["Authentication"]
        assert model.labels == ["triaged"]
        assert model.fix_versions == ["6.15.0"]
        assert model.affects_versions == ["6.14.0"]
        assert model.regression == "Yes"
        assert model.reporter == "testuser"
        assert model.assignee is None
        assert model.url == "https://example.atlassian.net/browse/SAT-99999"

    def test_missing_optional_fields(self):
        issue = _make_jira_issue({
            "priority": None,
            "components": None,
            "labels": None,
            "fixVersions": None,
            "versions": None,
            "customfield_10840": None,
            "customfield_10623": None,
        })
        model = issue_to_model(issue, "https://example.atlassian.net")

        assert model.priority is None
        assert model.severity is None
        assert model.components == []
        assert model.labels == []
        assert model.fix_versions == []
        assert model.affects_versions == []
        assert model.regression is None
