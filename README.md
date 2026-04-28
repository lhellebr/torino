# Torino

Multi-agentic JIRA triage tool for Red Hat Satellite. Automates the Program Triage process using Claude AI agents that debate as QE, Product Owner, and Developer.

## Prerequisites

- Python 3.10+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and configured

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Configuration

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` with your JIRA credentials (email and API token).

Claude Code must be installed and authenticated separately (e.g. via Vertex AI with `gcloud auth`).

## Usage

```bash
# Triage specific issues
torino triage SAT-12345 SAT-12346

# Find and triage all untriaged issues
torino triage

# Team Triage mode (optional)
torino triage --team-triage
```
