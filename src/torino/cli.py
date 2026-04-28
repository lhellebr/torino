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
@click.pass_context
def triage(ctx, issues, project, team_triage):
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
        items = fetch_untriaged(client, project, config.jira.server)

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

    from torino.jira_client import fetch_components
    from torino.triage.classifier import classify_issue

    click.echo(f"Fetching components for {project}...")
    components = fetch_components(client, project)

    for item in items:
        click.echo(f"\nClassifying {item.key} via Claude Code...")
        result = classify_issue(item, components)
        _display_classification(item, result)


def _display_classification(issue: TriageIssue, result: dict):
    click.echo(click.style(f"\n  AI Classification for {issue.key}:", bold=True))
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

    need_info = result.get("need_info_from")
    if need_info:
        click.echo(click.style(f"    Need info from: {need_info}", fg="yellow"))
        click.echo(f"      → {result.get('need_info_reasoning', '')}")
