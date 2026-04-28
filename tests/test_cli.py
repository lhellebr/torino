from click.testing import CliRunner

from torino.cli import main


def test_main_help():
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Torino" in result.output
    assert "triage" in result.output


def test_triage_help():
    result = CliRunner().invoke(main, ["triage", "--help"])
    assert result.exit_code == 0
    assert "--project" in result.output
    assert "--team-triage" in result.output


def test_triage_missing_config(tmp_path):
    result = CliRunner().invoke(
        main, ["--config", str(tmp_path / "nonexistent.yaml"), "triage"],
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "config" in result.output.lower()
