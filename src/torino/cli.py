from pathlib import Path

import click

from torino.config import load_config
from torino.models import TriageIssue


@click.group()
@click.option(
    "--config", "config_path",
    type=click.Path(path_type=Path),
    default="config.yaml",
    help="Path to config file.",
)
@click.pass_context
def main(ctx, config_path):
    """Torino — multi-agentic JIRA triage tool for Red Hat Satellite."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path


@main.command()
@click.argument("issues", nargs=-1)
@click.option("--project", default="SAT", help="JIRA project key (default: SAT)")
@click.option("--team-triage", is_flag=True, help="Run Team Triage instead of Program Triage")
@click.option("--quick", is_flag=True, help="Use single-agent classifier instead of full debate")
@click.option("--verbose", "-v", is_flag=True, help="Show each agent's assessment during the debate")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt and apply changes immediately")
@click.option("--limit", default=5, help="Max untriaged issues to fetch (default: 5)")
@click.pass_context
def triage(ctx, issues, project, team_triage, quick, verbose, yes, limit):
    """Triage JIRA issues.

    Pass issue keys (e.g. SAT-12345) to triage specific issues,
    or run with no arguments to find all untriaged issues.
    """
    config = load_config(ctx.obj["config_path"])

    from torino.jira_client import connect, fetch_issues, fetch_untriaged

    click.echo("Connecting to JIRA...")
    client = connect(config.jira)

    if issues:
        click.echo(f"Fetching {len(issues)} issue(s)...")
        items = fetch_issues(client, list(issues), config.jira.server)
    else:
        click.echo(f"Searching for untriaged issues in {project}...")
        items, total = fetch_untriaged(client, project, config.jira.server, limit=limit)
        if total > limit:
            click.echo(click.style(
                f"  Warning: showing {limit} of {total} untriaged issues. "
                f"Use --limit to increase.",
                fg="yellow",
            ))

    if not items:
        click.echo("No issues to triage.")
        return

    from torino.triage.validators import validate_issue

    click.echo(f"Found {len(items)} issue(s) to triage:\n")
    for item in items:
        click.echo(f"  {item.key}: {item.summary}")
        checks = validate_issue(item)
        for check in checks:
            if check.status == "ok":
                tag = click.style("[OK]     ", fg="green")
            elif check.status == "warning":
                tag = click.style("[WARNING]", fg="yellow")
            else:
                tag = click.style("[MISSING]", fg="red")
            click.echo(f"    {tag} {check.field}: {check.message}")
        click.echo()

    if team_triage:
        click.echo("Team Triage mode — not yet implemented.")
        return

    from torino.jira_client import fetch_components, search_similar

    click.echo(f"Fetching components for {project}...")
    components = fetch_components(client, project)

    if quick:
        from torino.triage.classifier import classify_issue

        for item in items:
            click.echo(f"\nClassifying {item.key} via Claude Code...")
            result = classify_issue(item, components)
            _display_result(item, result)
            _confirm_and_apply(client, item, result, auto_yes=yes)
    else:
        from torino.agents.debate import run_debate

        for item in items:
            item_checks = validate_issue(item)
            click.echo(f"\nSearching for similar issues to {item.key}...")
            similar = search_similar(client, item, project, config.jira.server, on_update=click.echo)
            click.echo(f"  Found {len(similar)} candidate(s).")
            click.echo(click.style(f"\nStarting multi-agent debate for {item.key}...", bold=True))
            result = run_debate(
                item, item_checks, components,
                similar=similar,
                on_update=click.echo,
                on_assessment=_display_agent_assessment if verbose else None,
            )
            _display_result(item, result)
            _confirm_and_apply(client, item, result, auto_yes=yes)


def _display_agent_assessment(role: str, assessment: dict):
    click.echo(f"    {click.style(role, bold=True)}:")
    click.echo(f"      Severity: {assessment.get('severity')} — {assessment.get('severity_reasoning', '')}")
    click.echo(f"      Priority: {assessment.get('priority')} — {assessment.get('priority_reasoning', '')}")
    click.echo(f"      Component: {assessment.get('component')} — {assessment.get('component_reasoning', '')}")
    click.echo(f"      Regression: {assessment.get('is_regression')} — {assessment.get('regression_reasoning', '')}")
    click.echo(f"      Security: {'Yes' if assessment.get('is_security') else 'No'}")
    if assessment.get("need_info_from"):
        click.echo(f"      Need info from: {assessment['need_info_from']} — {assessment.get('need_info_reasoning', '')}")
    click.echo(f"      Summary: {assessment.get('summary', '')}")
    click.echo()



def _display_result(issue: TriageIssue, result: dict):
    click.echo(click.style(f"\n  Triage Result for {issue.key}:", bold=True))
    click.echo(f"  {result.get('summary', '')}\n")

    click.echo(f"    Severity:   {result['severity']}")
    click.echo(f"      → {result['severity_reasoning']}")
    click.echo(f"    Priority:   {result['priority']}")
    click.echo(f"      → {result['priority_reasoning']}")
    click.echo(f"    Component:  {result['component']}")
    click.echo(f"      → {result['component_reasoning']}")
    click.echo(f"    Regression: {result['is_regression']}")
    click.echo(f"      → {result['regression_reasoning']}")
    click.echo(f"    Security:   {'Yes' if result['is_security'] else 'No'}")

    if result.get("labels"):
        click.echo(f"    Labels:     {', '.join(result['labels'])}")

    if result.get("code_location"):
        click.echo(f"    Code:       {result['code_location']}")

    need_info = result.get("need_info_from")
    if need_info:
        click.echo(click.style(f"    Need info from: {need_info}", fg="yellow"))
        click.echo(f"      → {result.get('need_info_reasoning', '')}")

    disagreements = result.get("disagreements", [])
    if disagreements:
        click.echo(click.style("\n    Unresolved disagreements:", fg="yellow"))
        for d in disagreements:
            click.echo(f"      - {d}")

    jira_comment = result.get("jira_comment")
    if jira_comment:
        click.echo(click.style("\n    Suggested JIRA comment:", bold=True))
        click.echo(f"    {jira_comment}")


def _confirm_and_apply(client, issue: TriageIssue, result: dict, auto_yes: bool = False):
    from torino.jira_client import apply_triage

    duplicates = result.get("duplicates", [])
    if duplicates:
        click.echo(click.style("\n  POSSIBLE DUPLICATES — action required:", fg="red", bold=True))
        for dup in duplicates:
            click.echo(click.style(f"    {dup['key']}", fg="red", bold=True) + f": {dup['reasoning']}")

    click.echo()
    if not auto_yes and not click.confirm(f"  Apply these changes to {issue.key}?"):
        click.echo("  Skipped.")
        return

    try:
        actions = apply_triage(client, issue.key, result)
        click.echo(click.style(f"\n  Applied to {issue.key}:", fg="green"))
        for action in actions:
            click.echo(f"    - {action}")
    except Exception as e:
        click.echo(click.style(f"\n  Failed to apply: {e}", fg="red"))
