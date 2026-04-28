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
- `src/torino/config.py` — YAML config loader (JIRA credentials only)
- `src/torino/models.py` — TriageIssue dataclass
- `src/torino/jira_client.py` — JIRA connection and query logic
- `src/torino/claude_client.py` — Claude Code CLI subprocess wrapper
- `src/torino/agents/` — AI agent personas (QE, PO, Developer)
- `src/torino/triage/validators.py` — Field validation (pure Python)
- `src/torino/triage/classifier.py` — AI-powered issue classification

## Conventions

- Python 3.10+, type hints throughout
- Claude via Claude Code CLI (`claude -p`), not direct Anthropic API
- An issue has exactly one component
- Confirm-then-apply: never write to JIRA without user confirmation
- Focus is Program Triage; Team Triage only with --team-triage flag
- Conservative with NEEDINFO — only when truly necessary
