"""对账运行的命令行入口。"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from agent.workflows.c_table_workflow import CTableWorkflow
from agent.domain.config import LLMConfig, ReconciliationRunConfig

app = typer.Typer(help="Generate and verify finance reconciliation C tables.")
console = Console()


@app.command("run")
def run(
    a_table: Path = typer.Option(..., help="Path to A table workbook."),
    b_table: Path = typer.Option(..., help="Path to B table workbook."),
    month: str = typer.Option(..., help="Reconciliation month, e.g. 2026-07."),
    output_dir: Path = typer.Option(Path("outputs"), help="Directory for generated files."),
    company: str = typer.Option("default", help="Company rule profile."),
    llm_provider: str = typer.Option("anthropic", help="LLM provider."),
    llm_model: Optional[str] = typer.Option(None, help="LLM model name."),
    llm_base_url: Optional[str] = typer.Option(None, help="LLM provider base URL."),
    llm_api_key_env: Optional[str] = typer.Option(None, help="Environment variable containing the LLM API key."),
) -> None:
    """运行完整的 C 表工作流，包括强制验证。"""
    config = ReconciliationRunConfig(
        a_table_path=a_table,
        b_table_path=b_table,
        reconciliation_month=month,
        output_dir=output_dir,
        company_profile=company,
        llm=LLMConfig(
            provider=llm_provider,
            model=llm_model,
            base_url=llm_base_url,
            api_key_env=llm_api_key_env,
        ),
    )
    result = CTableWorkflow(config).run()
    console.print(result.to_display())
    raise typer.Exit(code=0 if result.accepted else 1)


if __name__ == "__main__":
    app()
