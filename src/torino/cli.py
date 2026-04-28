from pathlib import Path

import click

from torino.config import load_config


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
    else:
        click.echo("Program Triage mode — not yet implemented.")
