"""工作簿文件检测工具。"""

from pathlib import Path

from agent.domain.records import WorkbookIdentity
from agent.domain.schemas import WorkbookKind


class WorkbookDetector:
    """在运行开始前识别 A/B/C 工作簿角色。"""

    def identify(self, path: Path) -> WorkbookIdentity:
        """根据文件名约定尽力返回工作簿身份。"""
        name = path.name
        reasons: list[str] = []
        if name.startswith("台州"):
            reasons.append("文件名以“台州”开头，按规则识别为 B 表")
            return WorkbookIdentity(
                path=path,
                kind=WorkbookKind.B_TABLE.value,
                confidence=0.95,
                reasons=reasons,
            )
        if "C表" in name or "C 表" in name:
            reasons.append("文件名包含 C 表标识")
            return WorkbookIdentity(
                path=path,
                kind=WorkbookKind.C_TABLE.value,
                confidence=0.85,
                reasons=reasons,
            )
        reasons.append("非台州系统导出文件，默认按 A 表业务来源处理")
        return WorkbookIdentity(
            path=path,
            kind=WorkbookKind.A_TABLE.value,
            confidence=0.70,
            reasons=reasons,
        )

    def assert_expected(self, path: Path, expected: WorkbookKind) -> WorkbookIdentity:
        """识别工作簿；如果其明显与预期角色冲突，则抛出异常。"""
        identity = self.identify(path)
        if identity.kind != expected.value and identity.confidence >= 0.9:
            raise ValueError(f"{path} 被识别为 {identity.kind}，不是期望的 {expected.value}")
        return identity
