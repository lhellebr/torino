# Torino

Multi-agentic JIRA triage tool for Red Hat Satellite. Automates the Program Triage process using Claude AI agents that debate as QE, Product Owner, and Developer.

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

Edit `config.yaml` with your credentials:
- **JIRA token**: personal access token for issues.redhat.com
- **Vertex AI**: GCP project ID (requires `gcloud auth application-default login`)

### Google Cloud authentication

```bash
gcloud auth application-default login
```

## Usage

```bash
# Triage specific issues
torino triage SAT-12345 SAT-12346

# Find and triage all untriaged issues
torino triage

# Team Triage mode (optional)
torino triage --team-triage
```
