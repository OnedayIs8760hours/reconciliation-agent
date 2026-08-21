"""命令行入口。"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from dotenv import load_dotenv

from agent.domain.config import ReconciliationRunRequest
from agent.workflows.c_table_workflow import CTableWorkflow

app = typer.Typer(help="财务对账 C 表制作 MVP")


@app.command()
def run(
    a_file: Path = typer.Option(..., "--a-file", exists=True, file_okay=True, dir_okay=False, help="A 表 .xlsx 文件"),
    b_file: Path = typer.Option(..., "--b-file", exists=True, file_okay=True, dir_okay=False, help="B 表 .xlsx 文件"),
    month: str = typer.Option(..., "--month", help="对账月份，格式 YYYY-MM"),
    output_dir: Path = typer.Option(Path("outputs"), "--output-dir", help="输出目录"),
    json_output: bool = typer.Option(False, "--json", help="以 JSON 输出运行结果"),
) -> None:
    load_dotenv()
    report = CTableWorkflow().run(
        ReconciliationRunRequest(a_file=a_file, b_file=b_file, month=month, output_dir=output_dir)
    )
    payload = report.model_dump(mode="json")
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"状态：{report.status}")
        typer.echo(f"C 表：{report.c_file}")
        typer.echo(f"报告：{report.report_file}")
        if report.summary:
            typer.echo(f"摘要：{report.summary}")
        for warning in report.warnings:
            typer.echo(f"警告：{warning}")
        for error in report.errors:
            typer.echo(f"错误：{error}")
    if report.status != "passed":
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
