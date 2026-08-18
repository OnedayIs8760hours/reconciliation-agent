# Agent Implementation Blueprint

## 目标

构建一个“财务对账 C 表生成与反向核查 Agent”。Agent 的职责不是让 LLM 直接改 Excel，而是让 LLM 编排一组确定性工具，完成：

1. 从 A 表完整复制生成 C 表。
2. 按 A 表原始业务口径逐行匹配 B 表系统入库/出库记录。
3. 将 B 表追溯字段写入 C 表。
4. 对 B 表本月记录做反向覆盖核查。
5. 对 C 未承接的 B 表记录在 B 表副本中标注缺失。
6. 交付前运行强制验收。

## 分层设计

### LLM 编排层

- 文件：`agent/llm.py`
- 作用：提供 provider-neutral 的 LLM 编排门面，解释计划、读取确定性工具结果、给出修复建议。
- 兼容入口：`ClaudeReconciliationAgent` 继续保留，默认使用 Anthropic/Claude，避免既有导入失效。
- 边界：不得凭空改写 Excel；不得绕过验收失败；不得把 provider 特有参数扩散到工作流。

### 模型 Provider 适配层

- 目录：`agent/llm_providers/`
- 作用：把不同模型供应商的 SDK/HTTP 调用统一成 `complete(prompt, max_tokens)` 接口。
- 支持：
  - `anthropic`：官方 Anthropic SDK，默认 `claude-opus-5`。
  - `openai`：官方 OpenAI SDK，默认 `gpt-4.1`。
  - `deepseek`：OpenAI-compatible 接口，默认 `deepseek-chat`。
  - `qwen`：DashScope OpenAI-compatible 接口，默认 `qwen-plus`。
  - `ollama`：本地 HTTP `/api/chat`，默认 `qwen2.5`。
- 配置：由 `agent/domain/config.py` 中的 `LLMConfig` 统一承载 provider、model、base URL、API key 环境变量、超时和重试参数。
- 密钥：只从环境变量读取，不在代码或文档中硬编码。

### Workflow 层

- 文件：`agent/workflows/c_table_workflow.py`
- 作用：把工具串成可审计流水线。

顺序：

1. 识别 A/B 表。
2. 提取 A/B 记录。
3. 从 A 表复制生成 C 表初稿。
4. 匹配 A 派生 C 行与 B 表记录。
5. 写入 C 表追溯字段。
6. 做 B 表本月反向核查。
7. 标注 B 表缺失记录。
8. 调整公式、列宽、视图。
9. 运行交付验收并输出报告。

### 确定性 Core 工具层

- `file_detector.py`：识别文件角色，`台州*` 视为 B 表。
- `workbook_loader.py`：统一 openpyxl 读写。
- `normalizer.py`：日期、金额、规格标准化。
- `record_extractor.py`：抽取 A/B 域模型。
- `c_table_builder.py`：复制 A 表生成 C 表，追加追溯列。
- `matcher.py`：正数走 B 入库 K:M，负数走 B 出库 N:P。
- `c_table_match_writer.py`：写入匹配结果并支持多行展开。
- `reverse_verifier.py`：核查 B 表本月记录覆盖状态。
- `missing_marker.py`：标注未被 C 表承接的 B 表记录。
- `formula_manager.py`：检查公式错误和金额显示风险。
- `view_manager.py`：交付视图重置到 A1，冻结首行。

## 强制业务规则

### A/C 口径

C 表必须从 A 表完整复制生成。原始业务列的数量、单价、金额不能被 B 表覆盖。多行展开时，新插入行的 A 表业务列应为空，只保留 B 表追溯字段。

### 匹配方向

- A/C 数量为正：匹配 B 表入库数量、入库成本单价、入库成本金额。
- A/C 数量为负：匹配 B 表出库数量、出库成本单价、出库成本金额，数量按绝对值比较。
- 零数量、零金额、补发件：不能忽略，必须进入复核状态或缺失标注。

### 多行匹配

当一个 A/C 行对应多条 B 表记录时，必须展开成多行，每条 B 表记录保留自己的行号、单据号、货品编号、规格、数量、单价、金额。不能只写合计。

### B 表本月反向核查

每条本月 B 表记录必须处于以下状态之一：

- 已承接：追溯字段已写入 C 表。
- 已标注缺失：在 B 表副本中明确标注。
- 人工排除：有人工排除依据。

不允许存在未覆盖记录。

## 交付验收

交付前必须通过：

- A/C 原始业务数量合计一致。
- A/C 原始业务金额合计一致。
- B 表本月覆盖方程成立。
- 公式错误为 0。
- 金额区域无 `########` 显示。
- C 表打开视图复位到 A1 并冻结表头。

验收失败时，CLI 返回非 0 状态码。
