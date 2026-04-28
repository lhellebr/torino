from dataclasses import dataclass

from torino.models import TriageIssue


@dataclass
class Check:
    field: str
    status: str  # "ok", "missing", "warning"
    message: str


def validate_issue(issue: TriageIssue) -> list[Check]:
    checks = []
    checks.append(_check_summary(issue))
    checks.append(_check_priority(issue))
    checks.append(_check_severity(issue))
    checks.append(_check_components(issue))
    checks.append(_check_regression(issue))
    checks.extend(_check_description(issue))
    checks.extend(_check_labels(issue))
    return checks


def _check_summary(issue: TriageIssue) -> Check:
    if not issue.summary or not issue.summary.strip():
        return Check("Summary", "missing", "Summary is empty")
    return Check("Summary", "ok", issue.summary)


def _check_priority(issue: TriageIssue) -> Check:
    if not issue.priority or issue.priority.lower() in ("undefined", "none"):
        return Check("Priority", "missing", "Priority not set")
    return Check("Priority", "ok", issue.priority)


def _check_severity(issue: TriageIssue) -> Check:
    if not issue.severity:
        return Check("Severity", "missing", "Severity not set")
    return Check("Severity", "ok", issue.severity)


def _check_components(issue: TriageIssue) -> Check:
    if not issue.components:
        return Check("Component", "missing", "No component assigned")
    return Check("Component", "ok", ", ".join(issue.components))


def _check_regression(issue: TriageIssue) -> Check:
    if issue.regression:
        return Check("Regression", "ok", issue.regression)
    if issue.regression_from_description:
        return Check(
            "Regression", "warning",
            f"Field not set, but description says: {issue.regression_from_description}",
        )
    return Check("Regression", "missing", "Regression not set and not found in description")


TEMPLATE_SECTIONS = [
    "Description of problem",
    "How reproducible",
    "Is this issue a regression from an earlier version",
    "Steps to Reproduce",
    "Actual behavior",
    "Expected behavior",
]


def _check_description(issue: TriageIssue) -> list[Check]:
    if not issue.description or not issue.description.strip():
        return [Check("Description", "missing", "Description is empty")]

    checks = []
    for section in TEMPLATE_SECTIONS:
        marker = f"*{section}"
        idx = issue.description.find(marker)
        if idx == -1:
            checks.append(Check("Description", "warning", f"Missing section: {section}"))
            continue

        end_marker = issue.description.find("*", idx + len(marker))
        if end_marker == -1:
            continue
        next_section = issue.description.find("\n*", end_marker)
        if next_section == -1:
            content = issue.description[end_marker + 1:]
        else:
            content = issue.description[end_marker + 1:next_section]

        content = content.strip().strip(":").strip()
        if not content:
            checks.append(Check("Description", "warning", f"Section is empty: {section}"))

    if not checks:
        checks.append(Check("Description", "ok", "All template sections present"))

    return checks


def _check_labels(issue: TriageIssue) -> list[Check]:
    checks = []
    if "triaged" in issue.labels:
        checks.append(Check("Labels", "warning", "Already has 'triaged' label"))
    if "NEEDINFO" in issue.labels:
        checks.append(Check("Labels", "warning", "Has NEEDINFO — should be skipped"))
    return checks
