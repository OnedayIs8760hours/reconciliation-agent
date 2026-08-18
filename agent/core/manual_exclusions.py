"""反向验证的手工排除处理。"""

from pathlib import Path

from pydantic import BaseModel, Field


class ManualExclusion(BaseModel):
    """一条手工批准的 B 表行排除项。"""

    b_row_number: int
    reason: str
    approved_by: str | None = None
    evidence: str | None = None


class ManualExclusionRegistry(BaseModel):
    """可满足反向验证覆盖要求的排除项集合。"""

    exclusions: list[ManualExclusion] = Field(default_factory=list)

    @property
    def rows(self) -> set[int]:
        return {item.b_row_number for item in self.exclusions}

    @classmethod
    def empty(cls) -> "ManualExclusionRegistry":
        return cls()

    @classmethod
    def from_text_file(cls, path: Path | None) -> "ManualExclusionRegistry":
        """从换行文本文件加载简单的行号排除项。

        格式：每个非注释行以 B 表行号开头，后面可跟一个
        用逗号分隔的可选原因。
        """
        if path is None or not path.exists():
            return cls.empty()
        exclusions: list[ManualExclusion] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            row_text, _, reason = stripped.partition(",")
            exclusions.append(ManualExclusion(b_row_number=int(row_text), reason=reason.strip()))
        return cls(exclusions=exclusions)
