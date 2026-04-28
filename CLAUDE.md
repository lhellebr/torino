# Torino

Multi-agentic JIRA triage tool for Red Hat Satellite.

## Build & run

```bash
pip install -e ".[dev]"
torino triage              # find untriaged issues
torino triage SAT-12345    # triage specific issues
```

## Test

```bash
pytest
```

## Architecture

- `src/torino/cli.py` — Click CLI entrypoint
- `src/torino/config.py` — YAML config loader
- `src/torino/models.py` — TriageIssue dataclass
- `src/torino/jira_client.py` — JIRA connection and query logic
- `src/torino/agents/` — AI agent personas (QE, PO, Developer)
- `src/torino/triage/` — Triage logic (validation, classification, duplicate detection)

## Conventions

- Python 3.10+, type hints throughout
- Claude via Vertex AI (`AnthropicVertex` client), not direct Anthropic API
- Default model: claude-opus-4-6-20250527
- Confirm-then-apply: never write to JIRA without user confirmation
- Focus is Program Triage; Team Triage only with --team-triage flag
