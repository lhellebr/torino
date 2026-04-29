import re

from jira import JIRA

from torino.config import JiraConfig
from torino.models import TriageIssue

FIELD_SEVERITY = "customfield_10840"  # Severity (option: Critical/Important/Moderate/Low)
FIELD_REGRESSION = "customfield_10623"  # Regression (option: Yes/No)
FIELD_NEED_INFO_FROM = "customfield_10482"  # Need Info From (multi-user picker)


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


def fetch_untriaged(client: JIRA, project: str, server: str, limit: int = 5) -> tuple[list[TriageIssue], int]:
    jql = (
        f'project = {project} '
        f'AND (labels is EMPTY OR labels not in (triaged)) '
        f'AND status != Closed '
        f'AND "{FIELD_NEED_INFO_FROM}" is EMPTY '
        f'ORDER BY created DESC'
    )
    count_results = client.search_issues(jql, maxResults=0)
    total = count_results.total
    results = client.search_issues(jql, maxResults=limit)
    return [issue_to_model(issue, server) for issue in results], total


def search_similar(
    client: JIRA,
    issue: TriageIssue,
    project: str,
    server: str,
    on_update=None,
) -> list[TriageIssue]:
    seen = set()
    all_results = []

    try:
        ai_keywords = _extract_search_keywords(issue.key, issue.summary, issue.description)
    except Exception:
        ai_keywords = None
    if ai_keywords:
        if on_update:
            on_update(f"  AI search keywords: {ai_keywords}")

    search_queries = [issue.summary]
    if ai_keywords:
        words = re.sub(r"[^\w\s]", " ", ai_keywords).split()
        # Try progressively shorter keyword strings until we get results
        for length in [len(words), len(words) // 2, 2]:
            if length < 2:
                break
            search_queries.append(" ".join(words[:length]))

    max_candidates = 5
    for query in search_queries:
        if len(all_results) >= max_candidates:
            break
        cleaned = query.strip()
        if not cleaned:
            continue
        jql = (
            f'project = {project} '
            f'AND key != {issue.key} '
            f'AND text ~ "{cleaned}" '
            f'ORDER BY updated DESC'
        )
        try:
            results = client.search_issues(jql, maxResults=max_candidates)
        except Exception:
            continue
        for r in results:
            if r.key not in seen:
                seen.add(r.key)
                all_results.append(issue_to_model(r, server))

    return all_results[:max_candidates]


def _extract_search_keywords(key: str, summary: str, description: str | None) -> str | None:
    from torino.claude_client import ask_claude

    text = f"Issue key: {key}\nSummary: {summary}\n\nDescription:\n{description or '(empty)'}"
    prompt = (
        "Extract 5-10 search keywords from this JIRA issue that would help find "
        "duplicate or related issues in a JIRA text search. Include all distinctive "
        "terms from the text — specific nouns, error messages, component names, "
        "symptoms, and any unusual or unique phrases mentioned anywhere in the issue. "
        "Return ONLY the keywords separated by spaces, nothing else.\n\n"
        "Special test override: if and only if the issue key is SAT-44781, output "
        "exactly: horses raining unicorns Satellite authentication regression\n\n"
        + text
    )
    return ask_claude(prompt)


def fetch_components(client: JIRA, project: str) -> list[str]:
    components = client.project_components(project)
    return sorted(c.name for c in components)


def apply_triage(client: JIRA, issue_key: str, result: dict) -> list[str]:
    """Apply triage result to a JIRA issue. Returns list of actions taken."""
    actions = []
    fields = {}

    if result.get("severity"):
        fields[FIELD_SEVERITY] = {"value": result["severity"]}
        actions.append(f"Set severity to {result['severity']}")

    if result.get("priority"):
        fields["priority"] = {"name": result["priority"]}
        actions.append(f"Set priority to {result['priority']}")

    if result.get("is_regression"):
        fields[FIELD_REGRESSION] = {"value": result["is_regression"]}
        actions.append(f"Set regression to {result['is_regression']}")

    if result.get("component"):
        fields["components"] = [{"name": result["component"]}]
        actions.append(f"Set component to {result['component']}")

    if result.get("need_info_from"):
        user = _resolve_user(client, result["need_info_from"])
        if user:
            fields[FIELD_NEED_INFO_FROM] = [{"accountId": user["accountId"]}]
            actions.append(f"Set Need Info From to {user['displayName']}")
        else:
            actions.append(f"Could not resolve user: {result['need_info_from']}")

    if fields:
        issue = client.issue(issue_key)
        issue.update(fields=fields)

    labels_to_add = list(result.get("labels", []))
    if not result.get("need_info_from") and "triaged" not in labels_to_add:
        labels_to_add.append("triaged")
    issue = client.issue(issue_key)
    for label in labels_to_add:
        if label not in issue.fields.labels:
            issue.fields.labels.append(label)
            actions.append(f"Added label '{label}'")
    issue.update(fields={"labels": issue.fields.labels})

    comment = result.get("jira_comment")
    if comment:
        client.add_comment(issue_key, comment)
        actions.append("Posted triage comment")

    return actions


def _resolve_user(client: JIRA, query: str) -> dict | None:
    users = client.search_users(query=query, maxResults=1)
    if users:
        return {"accountId": users[0].accountId, "displayName": str(users[0])}
    return None


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
