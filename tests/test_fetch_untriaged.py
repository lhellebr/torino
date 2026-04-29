from unittest.mock import MagicMock, patch

from torino.jira_client import fetch_untriaged, FIELD_NEED_INFO_FROM


class _FakeResultList(list):
    def __init__(self, items, total):
        super().__init__(items)
        self.total = total


class TestFetchUntriaged:
    def test_jql_excludes_triaged_label(self):
        client = MagicMock()
        client.search_issues.return_value = _FakeResultList([], 0)

        fetch_untriaged(client, "SAT", "https://example.atlassian.net")

        jql = client.search_issues.call_args_list[0][0][0]
        assert "labels not in (triaged)" in jql

    def test_jql_includes_empty_labels(self):
        client = MagicMock()
        client.search_issues.return_value = _FakeResultList([], 0)

        fetch_untriaged(client, "SAT", "https://example.atlassian.net")

        jql = client.search_issues.call_args_list[0][0][0]
        assert "labels is EMPTY" in jql

    def test_jql_excludes_closed(self):
        client = MagicMock()
        client.search_issues.return_value = _FakeResultList([], 0)

        fetch_untriaged(client, "SAT", "https://example.atlassian.net")

        jql = client.search_issues.call_args_list[0][0][0]
        assert "status != Closed" in jql

    def test_jql_excludes_needinfo(self):
        client = MagicMock()
        client.search_issues.return_value = _FakeResultList([], 0)

        fetch_untriaged(client, "SAT", "https://example.atlassian.net")

        jql = client.search_issues.call_args_list[0][0][0]
        assert FIELD_NEED_INFO_FROM in jql
        assert "is EMPTY" in jql

    def test_jql_orders_by_created_desc(self):
        client = MagicMock()
        client.search_issues.return_value = _FakeResultList([], 0)

        fetch_untriaged(client, "SAT", "https://example.atlassian.net")

        jql = client.search_issues.call_args_list[0][0][0]
        assert "ORDER BY created DESC" in jql

    def test_respects_limit(self):
        client = MagicMock()
        client.search_issues.return_value = _FakeResultList([], 0)

        fetch_untriaged(client, "SAT", "https://example.atlassian.net", limit=10)

        data_call = client.search_issues.call_args_list[1]
        assert data_call.kwargs["maxResults"] == 10

    def test_default_limit_is_5(self):
        client = MagicMock()
        client.search_issues.return_value = _FakeResultList([], 0)

        fetch_untriaged(client, "SAT", "https://example.atlassian.net")

        data_call = client.search_issues.call_args_list[1]
        assert data_call.kwargs["maxResults"] == 5

    def test_returns_total_count(self):
        client = MagicMock()
        client.search_issues.side_effect = [
            _FakeResultList([], 42),
            _FakeResultList([], 5),
        ]

        items, total = fetch_untriaged(client, "SAT", "https://example.atlassian.net")

        assert total == 42

    def test_uses_project_parameter(self):
        client = MagicMock()
        client.search_issues.return_value = _FakeResultList([], 0)

        fetch_untriaged(client, "MYPROJ", "https://example.atlassian.net")

        jql = client.search_issues.call_args_list[0][0][0]
        assert "project = MYPROJ" in jql
