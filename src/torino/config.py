from dataclasses import dataclass
from pathlib import Path

import yaml


DEFAULT_MODEL = "claude-opus-4-6-20250527"


@dataclass
class JiraConfig:
    server: str
    email: str
    api_token: str


@dataclass
class ClaudeConfig:
    vertex_project_id: str
    vertex_region: str = "global"
    model: str = DEFAULT_MODEL


@dataclass
class Config:
    jira: JiraConfig
    claude: ClaudeConfig


def load_config(path: Path | None = None) -> Config:
    if path is None:
        path = Path("config.yaml")
    if not path.exists():
        raise SystemExit(
            f"Config file not found: {path}\n"
            "Copy config.example.yaml to config.yaml and fill in your credentials."
        )
    with open(path) as f:
        raw = yaml.safe_load(f)

    jira_raw = raw.get("jira", {})
    claude_raw = raw.get("claude", {})

    return Config(
        jira=JiraConfig(
            server=jira_raw["server"],
            email=jira_raw["email"],
            api_token=jira_raw["api_token"],
        ),
        claude=ClaudeConfig(
            vertex_project_id=claude_raw["vertex_project_id"],
            vertex_region=claude_raw.get("vertex_region", "global"),
            model=claude_raw.get("model", DEFAULT_MODEL),
        ),
    )
