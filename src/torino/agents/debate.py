import json

from torino.claude_client import ask_claude
from torino.models import TriageIssue
from torino.triage.validators import Check
from torino.agents.roles import (
    ISSUE_CONTEXT,
    AGENT_ROLES,
    ROUND1_SUFFIX,
    DEBATE_PROMPT,
    SYNTHESIS_PROMPT,
    ASSESSMENT_SCHEMA,
)


def _format_issue_context(
    issue: TriageIssue,
    checks: list[Check],
    components: list[str],
) -> str:
    validation_lines = []
    for c in checks:
        validation_lines.append(f"  [{c.status.upper()}] {c.field}: {c.message}")

    return ISSUE_CONTEXT.format(
        key=issue.key,
        issue_type=issue.issue_type,
        summary=issue.summary,
        component=issue.components[0] if issue.components else "not set",
        priority=issue.priority or "not set",
        severity=issue.severity or "not set",
        regression=issue.regression or "not set",
        regression_from_description=issue.regression_from_description or "not mentioned",
        labels=", ".join(issue.labels) or "none",
        reporter=issue.reporter or "unknown",
        description=issue.description or "(empty)",
        validation="\n".join(validation_lines),
        components=", ".join(components),
    )


def _parse_json(text: str) -> dict:
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


def _run_round1(role: str, role_config: dict, issue_context: str, on_update=None) -> dict:
    if on_update:
        on_update(f"  Round 1: {role} is analyzing...")

    prompt = role_config["prompt"].format(issue_context=issue_context) + ROUND1_SUFFIX
    response = ask_claude(prompt, allowed_tools=role_config["tools"])
    return _parse_json(response)


def _run_debate_round(
    role: str,
    role_config: dict,
    own_assessment: dict,
    all_assessments: dict[str, dict],
    on_update=None,
) -> dict:
    if on_update:
        on_update(f"  Round 2: {role} is reviewing other assessments...")

    other_parts = []
    for other_role, assessment in all_assessments.items():
        if other_role != role:
            other_parts.append(f"--- {other_role} ---\n{json.dumps(assessment, indent=2)}")

    prompt = DEBATE_PROMPT.format(
        role=role,
        own_assessment=json.dumps(own_assessment, indent=2),
        other_assessments="\n\n".join(other_parts),
        schema=ASSESSMENT_SCHEMA,
    )
    response = ask_claude(prompt, allowed_tools=role_config["tools"])
    return _parse_json(response)


def _run_synthesis(issue_context: str, round2: dict[str, dict], on_update=None) -> dict:
    if on_update:
        on_update("  Round 3: Moderator is synthesizing consensus...")

    assessment_parts = []
    for role, assessment in round2.items():
        assessment_parts.append(
            f"--- {role} (final assessment) ---\n{json.dumps(assessment, indent=2)}"
        )

    prompt = SYNTHESIS_PROMPT.format(
        issue_context=issue_context,
        all_assessments="\n\n".join(assessment_parts),
    )
    response = ask_claude(prompt)
    return _parse_json(response)


def run_debate(
    issue: TriageIssue,
    checks: list[Check],
    components: list[str],
    on_update=None,
) -> dict:
    issue_context = _format_issue_context(issue, checks, components)

    round1 = {}
    for role, config in AGENT_ROLES.items():
        round1[role] = _run_round1(role, config, issue_context, on_update)

    round2 = {}
    for role, config in AGENT_ROLES.items():
        round2[role] = _run_debate_round(
            role, config, round1[role], round1, on_update,
        )

    return _run_synthesis(issue_context, round2, on_update)
