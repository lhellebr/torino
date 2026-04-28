from pathlib import Path
from textwrap import dedent

import pytest

from torino.config import load_config, DEFAULT_MODEL


def test_load_config_from_file(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(dedent("""\
        jira:
          server: https://example.atlassian.net
          email: user@example.com
          api_token: secret123
        claude:
          vertex_project_id: my-project
          vertex_region: us-east1
    """))
    config = load_config(cfg_file)

    assert config.jira.server == "https://example.atlassian.net"
    assert config.jira.email == "user@example.com"
    assert config.jira.api_token == "secret123"
    assert config.claude.vertex_project_id == "my-project"
    assert config.claude.vertex_region == "us-east1"
    assert config.claude.model == DEFAULT_MODEL


def test_load_config_defaults(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(dedent("""\
        jira:
          server: https://example.atlassian.net
          email: user@example.com
          api_token: secret123
        claude:
          vertex_project_id: my-project
    """))
    config = load_config(cfg_file)

    assert config.claude.vertex_region == "global"
    assert config.claude.model == DEFAULT_MODEL


def test_load_config_missing_file():
    with pytest.raises(SystemExit, match="Config file not found"):
        load_config(Path("/nonexistent/config.yaml"))


def test_load_config_missing_jira_field(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(dedent("""\
        jira:
          server: https://example.atlassian.net
        claude:
          vertex_project_id: my-project
    """))
    with pytest.raises(KeyError):
        load_config(cfg_file)
