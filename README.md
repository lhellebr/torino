# Torino

Multi-agentic JIRA triage tool for Red Hat Satellite. Automates the Program Triage process using Claude AI agents (QE, Product Owner, Developer, Docs) that debate and reach consensus on issue classification.

## Prerequisites

- Python 3.10+
- Claude Code CLI installed and authenticated
- A JIRA Cloud account with API token

## Setup

### 1. Install Claude Code CLI

```bash
npm install -g @anthropic-ai/claude-code
```

Configure authentication for your environment (e.g. for Vertex AI):

```bash
export CLAUDE_CODE_USE_VERTEX=1
export CLOUD_ML_REGION=global
export ANTHROPIC_VERTEX_PROJECT_ID=your-gcp-project-id
gcloud auth application-default login
```

Verify it works:

```bash
claude --version
```

### 2. Clone and install Torino

```bash
git clone https://github.com/lhellebr/torino.git
cd torino
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 3. Configure JIRA credentials

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml`:

```yaml
jira:
  server: https://your-instance.atlassian.net
  email: your.email@example.com
  api_token: your-jira-api-token
```

To create a JIRA API token, go to https://id.atlassian.com/manage-profile/security/api-tokens

## Usage

```bash
# Triage specific issues
torino triage SAT-12345 SAT-12346

# Find and triage all untriaged issues (default: 5 newest)
torino triage

# Quick mode — single-agent classification, faster but less thorough
torino triage --quick SAT-12345

# Show each agent's assessment during the debate
torino triage -v SAT-12345

# Skip confirmation prompt and apply changes immediately
torino triage --yes SAT-12345

# Fetch more untriaged issues
torino triage --limit 20

# Use a different JIRA project
torino triage --project MYPROJ

# Combine options
torino triage --quick --yes --limit 10
```

## What it does

For each issue, Torino:

1. **Validates fields** — checks if summary, priority, severity, component, regression, and description sections are filled
2. **Searches for duplicates** — uses AI-extracted keywords to find similar issues in JIRA
3. **Runs a multi-agent debate** — four AI agents (QE, Product Owner, Developer, Docs) independently analyze the issue, then challenge each other's assessments
4. **Produces a consensus** — a moderator synthesizes the debate into a single recommendation with reasoning
5. **Applies to JIRA** (after confirmation) — sets severity, priority, component, regression, labels, Need Info From, and posts a triage comment

## Running tests

```bash
source .venv/bin/activate
pytest
```
