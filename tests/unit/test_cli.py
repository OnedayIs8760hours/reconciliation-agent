"""CLI 冒烟测试。"""

from typer.testing import CliRunner

from agent.cli import app


def test_cli_help() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "run" in result.output
    assert "llm-provider" in result.output
