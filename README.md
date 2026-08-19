# Reconciliation Agent

这是财务对账 C 表项目的空骨架。

两份业务规则仍然保留为实现依据：

- `docs/财务对账表制表逻辑通用指南.md`
- `docs/财务对账表C表制作与反向核查强制规则.md`

当前已清理掉原有 `agent/` 实现、LLM 适配层、工作流和相关测试，后续可以按规则文档重新从头实现。

建议的重建顺序：

1. 先补 `agent/domain`。
2. 再补 `agent/core` 的确定性 Excel 处理。
3. 然后补工作流、验收与 CLI。
4. 最后再接 LLM 门面和 provider 适配。
