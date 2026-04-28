from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class JiraConfig:
    server: str
    email: str
    api_token: str


@dataclass
class Config:
    jira: JiraConfig


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

    return Config(
        jira=JiraConfig(
            server=jira_raw["server"],
            email=jira_raw["email"],
            api_token=jira_raw["api_token"],
        ),
    )
