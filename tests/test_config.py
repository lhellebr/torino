from pathlib import Path
from textwrap import dedent

import pytest

from torino.config import load_config


def test_load_config_from_file(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(dedent("""\
        jira:
          server: https://example.atlassian.net
          email: user@example.com
          api_token: secret123
    """))
    config = load_config(cfg_file)

    assert config.jira.server == "https://example.atlassian.net"
    assert config.jira.email == "user@example.com"
    assert config.jira.api_token == "secret123"


def test_load_config_missing_file():
    with pytest.raises(SystemExit, match="Config file not found"):
        load_config(Path("/nonexistent/config.yaml"))


def test_load_config_missing_jira_field(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(dedent("""\
        jira:
          server: https://example.atlassian.net
    """))
    with pytest.raises(KeyError):
        load_config(cfg_file)
