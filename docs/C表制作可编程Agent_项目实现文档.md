---
title: C表制作可编程Agent项目实现文档
date: 2026-08-20
status: implementation-plan
source: C:/Users/Woda/Documents/Obsidian Vault/个人知识库/C表制作可编程Agent项目计划书.md
---

# C表制作可编程Agent项目实现文档

## 1. 文档定位

本文档把《C表制作可编程Agent项目计划书》转成 `reconciliation-agent` 仓库内可执行的工程实现说明。

当前仓库状态：

- `agent/` 目录目前只有 `__init__.py`，核心 Agent、Excel 引擎、规则包和 CLI 尚未实现。
- `scripts/run_reconciliation.py` 已预留命令行入口，但引用的 `agent.cli` 还不存在。
- `backend/` 已有 FastAPI 基础结构，`backend/api/v1/reconciliation.py` 仍是占位接口。
- `frontend/` 已有 Vue 3 工作台界面和对账任务类型定义，可作为 MVP 前端基础。
- `docs/` 已有通用制表规则、C 表强制规则、MVP 设计文档和历史实现蓝图。

本文档不是业务规则全文复述，而是说明如何在当前仓库中落地一个可复跑、可审计、可验收的 C 表生成 Agent。

## 2. 实现目标

实现一个确定性 Python harness，由 Agent 或 API 编排完成以下闭环：

```text
接收 A 表、B 表、月份、输出目录
  ↓
加载内置规则包
  ↓
分析 A/B 工作簿真实结构
  ↓
以 A 表复制生成 C 表底稿
  ↓
解析 A 表明细和 B 表本月记录
  ↓
分层匹配 A/C 明细与 B 表记录
  ↓
写入匹配状态和 B 表追溯字段
  ↓
反向核查 B 表本月覆盖
  ↓
将 B 表未承接记录追加到 C 表末尾
  ↓
重写合计、视图和样式
  ↓
执行强制验收
  ↓
输出 C 表、JSON 报告和用户摘要
```

核心判断：

```text
生成 C 表 != 对账完成

只有强制验收通过，任务才能进入 SUCCESS。
```

## 3. 范围边界

### 3.1 本期纳入

- 从用户输入解析 A 表、B 表、对账月份、输出目录和覆盖项。
- 将规则文档萃取为 harness 内置规则，不要求每次运行传入 Markdown。
- 按真实 Excel 结构识别工作表、表头、明细区、合计行和关键字段。
- C 表必须从 A 表完整复制生成，保留左侧 A 表业务口径。
- 在 C 表右侧追加匹配状态、匹配依据、B 表行号、方向、差异字段和 B 表追溯字段。
- 支持入库、出库、金额差异、日期差异、规格差异、多行合计匹配和 B-only 追加。
- 执行 A/C 原始口径核查、B 表覆盖核查、B 行唯一性核查、公式错误核查和基础视觉核查。
- 输出结构化 JSON 报告，供 CLI、后端 API 和前端工作台复用。

### 3.2 暂不纳入

- 自动解释所有复杂会计业务含义。
- 直接修改原始 A 表或 B 表。
- OCR 识别图片版对账单。
- 自动登录 ERP 或财务系统拉取数据。
- 完整多租户、权限、审批流和规则后台。

## 4. 实现原则

1. LLM 不直接改 Excel。LLM 只负责解释、编排、异常建议和用户沟通，Excel 操作必须由确定性 Python 模块完成。
2. 规则内置并版本化。运行时加载 `RuleConfig`，报告必须输出规则包名称和版本。
3. 当前 Excel 结构优先。不得把示例文件名、固定列字母或历史案例结构当成默认事实。
4. A 表原始口径不可污染。C 表左侧 A 表业务列只来自 A 表；B 表只能写入追加追溯字段或 B-only 追加区。
5. B 表本月记录必须闭环。每条 B 表本月记录必须处于已承接、已追加、已标注缺失或人工排除之一。
6. 验收失败不得交付成功。CLI 返回非 0，API 状态为 `FAILED`，报告保留失败原因。

## 5. 目标目录结构

建议在当前仓库补齐以下结构：

```text
reconciliation-agent/
  agent/
    __init__.py
    cli.py
    domain/
      __init__.py
      config.py
      records.py
      results.py
      statuses.py
      workbook_profile.py
    rules/
      __init__.py
      c_table_default.py
      rule_provider.py
      rule_schema.py
    core/
      __init__.py
      input_resolver.py
      workbook_loader.py
      workbook_profiler.py
      normalizer.py
      a_parser.py
      b_parser.py
      c_workbook_builder.py
      matcher.py
      c_table_writer.py
      reverse_checker.py
      missing_resolver.py
      formula_manager.py
      view_manager.py
      renderer.py
    verification/
      __init__.py
      verifier.py
    reporting/
      __init__.py
      json_reporter.py
      markdown_reporter.py
    workflows/
      __init__.py
      c_table_workflow.py
  backend/
    api/v1/reconciliation.py
    services/
      reconciliation_service.py
    storage/
      tasks/
  tests/
    unit/
    integration/
    fixtures/
      zhenxiang_2026_06/
      huayue_2026_06/
  docs/
```

说明：

- `agent/core` 承担确定性 Excel 处理。
- `agent/workflows` 只编排步骤，不写复杂 Excel 细节。
- `agent/rules` 保存内置规则包和规则版本。
- `agent/verification` 是强制门禁。
- `backend/services` 复用同一个 workflow，不能重写一套对账逻辑。

## 6. 领域模型

### 6.1 RunContext

```python
class RunContext(BaseModel):
    run_id: str
    a_path: Path
    b_path: Path
    output_dir: Path
    output_path: Path
    report_path: Path
    reconcile_month: str
    user_overrides: dict[str, Any] = {}
```

约束：

- `reconcile_month` 使用 `YYYY-MM`。
- 原始 A/B 表只读。
- 输出必须写入任务目录或用户指定目录。

### 6.2 RuleConfig

```python
class RuleConfig(BaseModel):
    rule_pack: str = "c_table_default"
    rule_version: str
    copy_a_as_c: bool = True
    freeze_formula_cached_values: bool = True
    fill_down_merged_dates: bool = True
    compare_outbound_abs: bool = True
    preserve_b_trace_fields: bool = True
    allow_date_review_match: bool = True
    allow_spec_review_match: bool = True
    allow_amount_review_match: bool = True
    allow_multi_b_expand: bool = True
    allow_non_contiguous_multi_b_match: bool = True
    reverse_check_current_month_b: bool = True
    missing_b_policy: Literal["append_to_c_tail", "mark_b_sheet"] = "append_to_c_tail"
    force_a_c_total_check: bool = True
    force_b_coverage_check: bool = True
    force_formula_error_check: bool = True
    force_view_reset: bool = True
```

强制门禁不能被用户覆盖关闭：

- `force_a_c_total_check`
- `force_b_coverage_check`
- `force_formula_error_check`
- `reverse_check_current_month_b`

### 6.3 ADetailRow

```python
class ADetailRow(BaseModel):
    row: int
    date_key: str | tuple
    document_no: str | None = None
    item_code: str | None = None
    item_name: str | None = None
    spec_raw: str | None = None
    spec_key: str | None = None
    qty: Decimal
    price: Decimal | None = None
    amount: Decimal
    direction: Literal["入库", "出库", "待定"]
    raw_values: dict[str, Any] = {}
```

### 6.4 BRecord

```python
class BRecord(BaseModel):
    record_id: str
    row: int
    direction: Literal["入库", "出库"]
    warehouse: str | None = None
    system_time: datetime | str
    date_key: str | tuple
    document_no: str | None = None
    item_code: str | None = None
    item_name: str | None = None
    spec_raw: str | None = None
    spec_key: str | None = None
    qty: Decimal
    price: Decimal | None = None
    amount: Decimal
    raw_fields: dict[str, Any] = {}
```

`record_id` 必须使用 `row + direction`，因为同一 B 表行可能同时存在入库和出库。

### 6.5 MatchResult

```python
class MatchResult(BaseModel):
    a_row: int
    status: str
    basis: str
    b_record_ids: list[str] = []
    direction: str
    diff_qty: Decimal | None = None
    diff_amount: Decimal | None = None
    trace_records: list[BRecord] = []
```

约束：

- 只有成功承接的 BRecord 才能进入 `b_record_ids`。
- 数量或金额核心口径无法支撑时，不得输出 `已匹配/xxx需复核`。
- 多行匹配必须保留每条 BRecord 的独立追溯字段。

## 7. 端到端流程实现

### Step 0：InputResolver 创建运行上下文

文件：`agent/core/input_resolver.py`

职责：

- 规范化 A/B 表路径、输出目录和月份。
- 校验 A/B 文件存在且可读。
- 生成 `run_id` 和输出路径。
- 合并用户覆盖项，例如 `append_unmatched_b_to_c_tail = true`。

失败条件：

- 文件不存在。
- 月份无法确定。
- 输出目录不可写。

### Step 1：RuleProvider 加载内置规则

文件：

- `agent/rules/c_table_default.py`
- `agent/rules/rule_provider.py`
- `agent/rules/rule_schema.py`

职责：

- 加载默认规则、字段别名、金额容差、匹配优先级、颜色规则和缺失处理策略。
- 应用用户覆盖项。
- 拒绝关闭强制核查的覆盖项。
- 输出 `rule_version`。

当前计划书指定默认缺失策略为：

```text
missing_b_policy = append_to_c_tail
```

这与历史 MVP 文档中“标注 B 表缺失”的策略不同。实现时以当前计划书为准，同时保留 `mark_b_sheet` 扩展能力。

### Step 2：WorkbookProfiler 分析工作簿

文件：`agent/core/workbook_profiler.py`

职责：

- A/B 工作簿各读取两份：
  - `data_only=False`：结构、公式、样式。
  - `data_only=True`：公式缓存值和核查值。
- 识别工作表、表头行、明细起止行、合计行、关键字段列。
- 记录合并单元格、公式单元格、列宽、冻结窗格和筛选区域。
- B 表字段优先按真实表头识别，固定列字母只作为兜底别名。

关键字段：

- 仓库
- 系统出入库时间
- 单据编号
- 货品编号
- 货品名称
- 规格
- 入库数量、入库成本单价、入库成本金额
- 出库数量、出库成本单价、出库成本金额

### Step 3：CWorkbookBuilder 生成 C 表底稿

文件：`agent/core/c_workbook_builder.py`

职责：

- 从 A 表完整复制生成 C 表。
- 取消合并单元格，并向明细行填充合并区域值。
- 固化明细金额公式缓存值，避免后续插行破坏公式引用。
- 清除 A 表原底色，保留字体、边框、列宽和基础版式。
- 在右侧追加匹配字段和 B 表追溯字段。

追加字段建议：

```text
匹配状态
匹配依据
B表行号
匹配方向
差异数量
差异金额
仓库
系统出入库时间
单据编号
货品编号
货品名称
规格
B数量
B单价
B金额
```

### Step 4：AParser 解析 A 表明细

文件：`agent/core/a_parser.py`

职责：

- 只解析 A 表原始业务明细行。
- 排除标题行、小计行、合计行和 B-only 追加区。
- 将日期、规格、数量、单价、金额转为标准对象。
- 按数量正负生成方向：
  - `qty > 0`：入库
  - `qty < 0`：出库
  - `qty == 0`：待定，进入复核

### Step 5：BParser 解析 B 表记录

文件：`agent/core/b_parser.py`

职责：

- 按真实表头读取 B 表字段。
- 一行存在入库数量时生成一条入库 `BRecord`。
- 一行存在出库数量时生成一条出库 `BRecord`。
- 同一行同时有入库和出库时生成两条记录，使用 `row + direction` 唯一标识。
- 按系统出入库时间筛选当前对账月份。
- 零数量、零金额、补发件、空数量不能静默忽略。

### Step 6：Normalizer 与 MatchIndex

文件：

- `agent/core/normalizer.py`
- `agent/core/matcher.py`

职责：

- 文本去空格、全角半角归一、连接符归一和无意义后缀清理。
- 日期统一生成 `date_key`。
- 数量、单价、金额统一为 `Decimal`。
- 出库比较数量和金额时使用绝对值。
- 构建 B 表候选索引。

索引至少包括：

```text
direction + date_key + item_code + spec_key + qty + price
direction + date_key + spec_key + qty + price
direction + item_code + spec_key + qty + price
multi_candidate_pool
```

### Step 7：Matcher 分层匹配

文件：`agent/core/matcher.py`

匹配顺序：

1. 严格单行匹配。
2. 金额容差匹配，输出 `已匹配/金额需复核`。
3. 日期复核匹配，输出 `已匹配/日期需复核`。
4. 规格复核匹配，输出 `已匹配/规格需复核`。
5. 日期规格复核匹配，输出 `已匹配/日期规格需复核`。
6. 连续多行合计匹配。
7. 非连续多行合计匹配。
8. 近似候选记录，仅写候选依据，不占用 B 表记录。

禁止行为：

- 同一 B 表记录被多个 A 表明细承接。
- 数量或金额对不上仍标记为已匹配。
- 多行匹配只写合计，不展开 B 表明细。

### Step 8：CTableWriter 写入匹配结果

文件：`agent/core/c_table_writer.py`

职责：

- 写入匹配状态、匹配依据、B 表行号、方向、差异数量和差异金额。
- 写入完整 B 表追溯字段。
- 多行匹配时，在原 C 行下插入附加行。
- 插入行左侧 A 表原始业务列留空，只写匹配字段和 B 表追溯字段。
- 按状态设置颜色。

### Step 9：ReverseChecker 做 B 表本月覆盖核查

文件：`agent/core/reverse_checker.py`

职责：

- 只核查当前对账月份 B 表记录。
- 用 `record_id` 和追溯字段核对 C 表承接情况。
- 输出本月记录数、已承接数、缺失记录和人工排除记录。

覆盖等式：

```text
B 表本月记录数
= C 表已承接记录数
+ C 表末尾追加 B 未匹配记录数
+ B 表已标注缺失记录数
+ 人工排除记录数
```

### Step 10：MissingResolver 处理 B 表未承接记录

文件：`agent/core/missing_resolver.py`

默认策略：

```text
append_to_c_tail
```

处理方式：

- 在 C 表末尾创建 `B表未匹配追加区`。
- 左侧 A 表原始业务列留空。
- 写入 `B未匹配/追加`、B 表行号、方向、缺失依据和完整 B 表追溯字段。
- 对零金额、补发件、空数量记录写明复核类型。

保留扩展策略：

```text
mark_b_sheet
```

该策略在 B 表副本右侧追加缺失标注列，但不是本项目默认策略。

### Step 11：FormulaManager 和 ViewManager 重写交付状态

文件：

- `agent/core/formula_manager.py`
- `agent/core/view_manager.py`

职责：

- 全部插行和 B-only 追加完成后重新定位合计行。
- A 表原始业务数量、金额合计范围只覆盖 A 表原始明细区。
- B-only 追加区不得计入 A 表合计。
- 调整金额列宽，避免显示 `########`。
- 设置筛选、冻结窗格、`topLeftCell = A1`、`activeCell = A1`。

### Step 12：Verifier 强制验收

文件：`agent/verification/verifier.py`

验收项：

- A/C 原始业务数量合计差额为 0。
- A/C 原始业务金额合计差额为 0。
- B 表本月覆盖等式成立。
- B 表记录唯一性成立。
- 公式错误数量为 0。
- 金额列无 `########` 显示风险。
- 表头、状态列、追溯字段和追加区可读。

验收失败时：

- 不输出 `SUCCESS`。
- 报告中保留失败项和定位信息。
- CLI 返回非 0。

### Step 13：Reporter 输出交付报告

文件：

- `agent/reporting/json_reporter.py`
- `agent/reporting/markdown_reporter.py`

JSON 报告必须包含：

```json
{
  "status": "passed",
  "input": {
    "a_file": "",
    "b_file": "",
    "user_overrides": {}
  },
  "rules": {
    "rule_pack": "c_table_default",
    "rule_version": "",
    "override_applied": []
  },
  "profiles": {
    "a_sheet": "",
    "b_sheet": "",
    "a_detail_rows": 0,
    "b_records": 0
  },
  "matching": {
    "matched": 0,
    "unmatched_a_rows": 0,
    "appended_b_records": 0,
    "status_counts": {}
  },
  "verification": {
    "qty_diff": 0,
    "amount_diff": 0,
    "b_record_count": 0,
    "c_covered_b_rows": 0,
    "c_appended_b_rows": 0,
    "b_marked_missing_rows": 0,
    "manual_excluded_b_rows": 0,
    "formula_error_count": 0
  },
  "output": {
    "c_file": "",
    "report_file": ""
  }
}
```

## 8. Workflow 接口

文件：`agent/workflows/c_table_workflow.py`

建议提供同步接口，先保证 CLI 和 FastAPI 可直接复用：

```python
class CTableWorkflow:
    def run(self, request: ReconciliationRunRequest) -> RunReport:
        ...
```

`ReconciliationRunRequest`：

```python
class ReconciliationRunRequest(BaseModel):
    a_file: Path
    b_file: Path
    month: str | None = None
    output_dir: Path
    user_overrides: dict[str, Any] = {}
```

`RunReport`：

```python
class RunReport(BaseModel):
    status: Literal["passed", "failed"]
    run_id: str
    c_file: Path | None = None
    report_file: Path
    errors: list[str] = []
    verification: VerificationReport
```

## 9. CLI 实现

文件：`agent/cli.py`

命令：

```bash
python scripts/run_reconciliation.py \
  --a-file "C:/path/A.xlsx" \
  --b-file "C:/path/B.xlsx" \
  --month 2026-06 \
  --output-dir "S:/ai-agent/reconciliation-agent/outputs"
```

推荐参数：

```text
--a-file
--b-file
--month
--output-dir
--append-unmatched-b-to-c-tail
--rule-pack
--json
```

退出码：

- `0`：验收通过。
- `1`：验收失败或运行异常。

## 10. 后端 API 实现

当前 `backend/api/v1/reconciliation.py` 是占位接口，需要改成复用 workflow 的 API。

### 10.1 上传文件

```http
POST /api/v1/reconciliation/tasks
Content-Type: multipart/form-data
```

字段：

```text
a_file
b_file
month
append_unmatched_b_to_c_tail
```

返回：

```json
{
  "task_id": "REC202608200001",
  "status": "UPLOADED"
}
```

### 10.2 启动对账

```http
POST /api/v1/reconciliation/tasks/{task_id}/run
```

返回：

```json
{
  "task_id": "REC202608200001",
  "status": "PROCESSING"
}
```

MVP 可以先同步执行，后续再接后台任务队列。

### 10.3 查询任务

```http
GET /api/v1/reconciliation/tasks/{task_id}
```

返回字段应匹配前端 `ReconciliationTask` 类型：

- `status`
- `progressSteps`
- `progressDetail`
- `verifyMetrics`
- `coverage`
- `exceptions`
- `downloads`

### 10.4 下载结果

```http
GET /api/v1/reconciliation/tasks/{task_id}/download/c
GET /api/v1/reconciliation/tasks/{task_id}/download/report
```

如果保留 `mark_b_sheet` 扩展策略，可追加：

```http
GET /api/v1/reconciliation/tasks/{task_id}/download/b
```

## 11. 前端对接

现有前端类型文件：

```text
frontend/src/types/reconciliation.ts
```

后端返回状态需要与当前类型保持一致：

```text
UPLOADED
PROCESSING
GENERATING
MATCHING
VERIFYING
SUCCESS
FAILED
```

建议将 workflow 阶段映射为前端进度：

| Workflow 阶段 | 前端状态 | 进度 |
| --- | --- | ---: |
| input_resolved | PROCESSING | 10 |
| workbook_profiled | PROCESSING | 20 |
| c_draft_built | GENERATING | 35 |
| rows_parsed | MATCHING | 45 |
| matched | MATCHING | 65 |
| reverse_checked | VERIFYING | 80 |
| verified | VERIFYING | 95 |
| report_written | SUCCESS / FAILED | 100 |

异常记录 `exceptions` 可来自：

- A 表未匹配行。
- B 表未承接追加行。
- 零数量或零金额需复核记录。
- 日期、规格、金额复核状态记录。

## 12. 测试策略

### 12.1 单元测试

目录：`tests/unit`

优先覆盖：

- `RuleProvider`：强制规则不能被覆盖关闭。
- `Normalizer`：日期、规格、金额、全角半角和空格归一。
- `BParser`：同一行入库/出库拆成两条 `BRecord`。
- `Matcher`：严格匹配、金额复核、日期复核、规格复核、多行合计。
- `ReverseChecker`：覆盖等式、B 行唯一性。
- `MissingResolver`：B-only 追加区不污染 A 表合计。
- `Verifier`：任一强制项失败时整体失败。

### 12.2 集成测试

目录：`tests/integration`

固定两个回归样例：

- `6月甄享`：基础入库匹配、金额差异复核。
- `6月华悦`：复杂 A 表版式、入库出库并存、B 表未匹配追加。

每个样例需要固定：

```text
input/A.xlsx
input/B.xlsx
expected/report.json
```

验收断言：

- `status == passed`
- `qty_diff == 0`
- `amount_diff == 0`
- `formula_error_count == 0`
- `unexplained_b_records == 0`
- `duplicate_b_record_count == 0`

### 12.3 视觉检查

MVP 可先做程序化检查：

- 金额列宽足够。
- 表头非空。
- 匹配状态列存在。
- B-only 追加区标题存在。
- 打开视图为 A1。

后续再增加 Excel 渲染截图或 PDF 预览检查。

## 13. 实施里程碑

### M1：最小可用 harness

- [ ] 补齐 `agent/domain` 基础模型。
- [ ] 实现 `InputResolver` 和 `RuleProvider`。
- [ ] 实现 `WorkbookProfiler`。
- [ ] 实现基于真实表头的 `BParser`。
- [ ] 实现 `AParser` 基础明细识别。
- [ ] 实现从 A 表复制生成 C 表。
- [ ] 实现基础入库严格匹配。
- [ ] 输出 C 表和 JSON 验收报告。

### M2：完整匹配与反向覆盖

- [ ] 支持出库匹配和绝对值比较。
- [ ] 支持规格标准化。
- [ ] 支持日期显示口径解析。
- [ ] 支持金额、日期、规格复核状态。
- [ ] 支持连续多行和非连续多行合计匹配。
- [ ] 支持 B 表未匹配追加到 C 表末尾。
- [ ] 支持 B 行唯一性核查。

### M3：API 和前端闭环

- [ ] 后端上传任务落盘到 `backend/storage/tasks/{task_id}`。
- [ ] 后端调用 `CTableWorkflow`。
- [ ] 后端返回前端所需任务状态、覆盖统计、异常列表和下载链接。
- [ ] 前端接真实 API，替换 mock 数据。
- [ ] 下载 C 表和报告。

### M4：工程化交付

- [ ] 增加真实样例 integration tests。
- [ ] 增加运行日志和中间数据导出。
- [ ] 增加 Markdown 摘要报告。
- [ ] 增加视觉渲染核查。
- [ ] 增加规则版本变更记录。

## 14. 开发顺序建议

建议按以下顺序提交，降低返工：

1. 先实现 `domain + rules + input_resolver`，让所有模块共享同一套对象。
2. 再实现 `workbook_profiler + parser`，把 Excel 结构识别跑通。
3. 再实现 `c_workbook_builder`，保证 C 表能从 A 表复制生成。
4. 再实现 `matcher + c_table_writer`，只做严格单行匹配。
5. 再实现 `reverse_checker + missing_resolver + verifier`，形成验收闭环。
6. 最后接 CLI、FastAPI 和前端。

不要先接 LLM。LLM 门面应等确定性 workflow 可稳定运行后再加。

## 15. 当前文档与历史文档的关系

- `财务对账表制表逻辑通用指南.md`：业务口径来源。
- `财务对账表C表制作与反向核查强制规则.md`：强制验收和禁止行为来源。
- `财务对账智能体_MVP设计文档.md`：产品 MVP 和前后端交互参考。
- `agent-implementation-blueprint.md`：历史 Agent 分层蓝图。
- 本文档：面向当前仓库状态的实现落地说明。

实现时如果文档冲突，优先级为：

1. 用户当前明确要求。
2. 当前计划书和本文档。
3. 强制规则文档。
4. 通用制表规则文档。
5. 历史 MVP/蓝图文档。

## 16. 完成定义

项目实现达到以下状态，才算第一阶段完成：

- CLI 可运行一次完整对账任务。
- 输入 A/B 表和月份后能输出 C 表。
- B 表本月记录全部被承接、追加、标注或人工排除。
- A/C 原始业务数量和金额差额为 0。
- C 表无公式错误。
- JSON 报告包含规则版本、覆盖统计和验收结论。
- 失败任务不会被标记为成功。
- 至少一个真实案例作为 integration test 通过。
