"""暴露给编排层的类型化工具结果模型。"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """通用工具结果封装。"""

    ok: bool
    name: str
    message: str
    artifacts: list[Path] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def success(
        cls,
        name: str,
        message: str,
        *,
        artifacts: list[Path] | None = None,
        data: dict[str, Any] | None = None,
    ) -> "ToolResult":
        return cls(ok=True, name=name, message=message, artifacts=artifacts or [], data=data or {})

    @classmethod
    def failure(cls, name: str, message: str, *, data: dict[str, Any] | None = None) -> "ToolResult":
        return cls(ok=False, name=name, message=message, data=data or {})
