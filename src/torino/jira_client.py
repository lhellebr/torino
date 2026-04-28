import re

from jira import JIRA

from torino.config import JiraConfig
from torino.models import TriageIssue

FIELD_SEVERITY = "customfield_10840"
FIELD_REGRESSION = "customfield_10623"


def connect(config: JiraConfig) -> JIRA:
    return JIRA(server=config.server, basic_auth=(config.email, config.api_token))


def _option_str(val) -> str | None:
    if val is None:
        return None
    if hasattr(val, "value"):
        return str(val.value)
    return str(val)


def issue_to_model(issue, server: str) -> TriageIssue:
    fields = issue.fields

    return TriageIssue(
        key=issue.key,
        summary=fields.summary or "",
        description=fields.description,
        issue_type=str(fields.issuetype),
        status=str(fields.status),
        priority=str(fields.priority) if fields.priority else None,
        severity=_option_str(getattr(fields, FIELD_SEVERITY, None)),
        components=[c.name for c in (fields.components or [])],
        labels=list(fields.labels or []),
        fix_versions=[v.name for v in (fields.fixVersions or [])],
        affects_versions=[v.name for v in (fields.versions or [])],
        regression=_option_str(getattr(fields, FIELD_REGRESSION, None)),
        regression_from_description=_parse_regression_from_description(fields.description),
        reporter=str(fields.reporter) if fields.reporter else None,
        assignee=str(fields.assignee) if fields.assignee else None,
        url=f"{server}/browse/{issue.key}",
    )


def fetch_issues(client: JIRA, keys: list[str], server: str) -> list[TriageIssue]:
    issues = []
    for key in keys:
        issue = client.issue(key)
        issues.append(issue_to_model(issue, server))
    return issues


def fetch_untriaged(client: JIRA, project: str, server: str) -> list[TriageIssue]:
    jql = (
        f'project = {project} '
        f'AND labels not in (triaged) '
        f'AND status != Closed '
        f'AND labels not in (NEEDINFO) '
        f'ORDER BY created DESC'
    )
    results = client.search_issues(jql, maxResults=50)
    return [issue_to_model(issue, server) for issue in results]


def fetch_components(client: JIRA, project: str) -> list[str]:
    components = client.project_components(project)
    return sorted(c.name for c in components)


def _parse_regression_from_description(description: str | None) -> str | None:
    if not description:
        return None
    match = re.search(
        r"\*Is this issue a regression[^*]*\*[:\s]*\n\s*(.+)",
        description,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()
    return None
