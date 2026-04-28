import json

from torino.claude_client import ask_claude
from torino.models import TriageIssue

CLASSIFICATION_SCHEMA = {
    "severity": "Critical | Important | Moderate | Low",
    "severity_reasoning": "brief reasoning",
    "priority": "Critical | Major | Normal | Minor",
    "priority_reasoning": "brief reasoning",
    "component": "single component from the provided list",
    "component_reasoning": "brief reasoning",
    "is_regression": "Yes | No",
    "regression_reasoning": "brief reasoning",
    "is_security": True,
    "labels": ["list of applicable labels"],
    "need_info_from": "JIRA username or null",
    "need_info_reasoning": "what info is missing, if any",
    "summary": "one-sentence triage assessment",
}


def _build_prompt(issue: TriageIssue, components: list[str]) -> str:
    component_list = ", ".join(components)
    current_component = issue.components[0] if issue.components else "not set"
    schema_str = json.dumps(CLASSIFICATION_SCHEMA, indent=2)

    return f"""You are a triage analyst for Red Hat Satellite, a systems management product.
Your job is to classify a newly filed JIRA issue for Program Triage.

The issue must have exactly one component. Choose the single most appropriate one from this list:
{component_list}

Current field values (may be incomplete or wrong):
- Component: {current_component}
- Priority: {issue.priority or "not set"}
- Severity: {issue.severity or "not set"}
- Regression field: {issue.regression or "not set"}
- Regression from description: {issue.regression_from_description or "not mentioned"}
- Labels: {", ".join(issue.labels) or "none"}
- Reporter: {issue.reporter or "unknown"}

Issue key: {issue.key}
Type: {issue.issue_type}
Summary: {issue.summary}

Description:
{issue.description or "(empty)"}

Instructions:
- Assess severity and priority based on the impact described.
- If the reporter says it's a regression, trust them unless the description contradicts it.
- Only set need_info_from to a JIRA username (typically the reporter: {issue.reporter}) if the description is truly too vague to proceed with triage. Prefer to work with what's available.
- For labels, only suggest labels that clearly apply: patch (reporter provided code), easy-fix (trivial fix), user-experience (usability), AutomationBlocker, UpgradeBlocker.
- If the issue involves authentication bypass, data exposure, privilege escalation, or similar, mark is_security as true.

Respond with ONLY a JSON object matching this schema, no other text:
{schema_str}"""


def classify_issue(issue: TriageIssue, components: list[str]) -> dict:
    prompt = _build_prompt(issue, components)
    result_text = ask_claude(prompt)

    if "```" in result_text:
        result_text = result_text.split("```")[1]
        if result_text.startswith("json"):
            result_text = result_text[4:]
        result_text = result_text.strip()

    return json.loads(result_text)
