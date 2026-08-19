# 财务对账智能体 MVP 设计文档

> 目标：先完成一个最简单、稳定、可运行的财务对账智能体。  
> 第一版不追求“智能”，而是追求“流程明确、结果稳定、可核查”。

---

## 1. 项目目标

用户上传两张 Excel：

- **A 表**：客户、供应商或业务侧提供的原始对账底稿。
- **B 表**：系统导出的出入库明细，通常文件名以“台州”开头。

系统自动完成：

```text
A 表
  ↓
生成 C 表底稿
  ↓
C 表匹配 B 表
  ↓
B 表反向核查 C 表
  ↓
生成核查报告
  ↓
通过核查
  ↓
输出 C 表 + 标记后的 B 表 + 核查结果
```

核心原则：

```text
生成 C 表 ≠ 对账完成

只有核查通过，才算完成。
```

---

# 2. MVP 范围

第一版只实现以下能力：

1. 上传 A 表、B 表。
2. 选择对账月份。
3. 自动识别 A/B 文件。
4. 根据 A 表生成 C 表。
5. 根据 C 表记录匹配 B 表。
6. 支持正数入库、负数出库匹配。
7. 支持单行和多行匹配。
8. 保留完整 B 表追溯字段。
9. 反向检查 B 表本月记录是否全部被处理。
10. 检查 A/C 数量和金额是否一致。
11. 检查 Excel 公式错误。
12. 输出：
    - C 表
    - 标记后的 B 表
    - 核查报告

第一版暂时不做：

- RAG
- 向量数据库
- 多 Agent
- 长期记忆
- 聊天式多轮操作
- 自动学习新规则
- 复杂人工审批流
- 规则管理后台
- 多租户
- 权限系统
- 工作流编排平台

---

# 3. 系统整体架构

```text
┌──────────── 前端 ────────────┐
│                              │
│  上传 A 表                   │
│  上传 B 表                   │
│  选择对账月份                │
│                              │
│       [开始对账]             │
│                              │
│  执行状态                    │
│  ✓ 文件解析                  │
│  ✓ C 表生成                  │
│  ✓ 数据匹配                  │
│  ✓ 反向核查                  │
│                              │
│  [下载 C 表]                 │
│  [下载标记后的 B 表]         │
│  [查看核查报告]              │
│                              │
└─────────────┬────────────────┘
              │
              │ HTTP
              ▼
┌──────── FastAPI 后端 ────────┐
│                              │
│ ReconciliationAgent          │
│                              │
│   ├─ inspect_excel()         │
│   ├─ generate_c_table()      │
│   ├─ match_c_with_b()        │
│   └─ verify_reconciliation() │
│                              │
└─────────────┬────────────────┘
              │
              ▼
┌────── Excel Engine ──────────┐
│                              │
│ Python                       │
│ openpyxl                     │
│ pandas（可选）               │
│ 自定义匹配算法               │
│                              │
│ 真正负责 Excel 操作          │
│                              │
└──────────────────────────────┘
```

---

# 4. 核心设计原则

## 4.1 LLM 不直接操作 Excel

LLM 只负责：

```text
现在进行到哪一步
下一步应该调用什么工具
工具执行结果是否正常
核查是否通过
失败后应该返回什么信息
```

LLM 不负责：

```text
直接读取几千行 Excel 后推理
直接计算金额
直接插入 Excel 行
直接修改公式
直接判断所有匹配关系
```

这些确定性工作全部交给 Python。

---

## 4.2 业务规则写进 Python

例如：

```text
数量 > 0 → 匹配 B 表入库 K-M

数量 < 0 → 匹配 B 表出库 N-P

出库数量比较使用绝对值

多条 B 表记录必须展开

零金额不能自动忽略

B 表本月记录必须全部被：
已承接 / 已标注缺失 / 人工排除
```

这些规则不应该每次让 LLM 推理。

应该固定到：

```text
matcher.py
verifier.py
normalizer.py
```

---

# 5. Agent 职责

MVP 中 Agent 只负责流程调度。

整体流程：

```text
用户上传文件
      ↓
inspect_excel
      ↓
generate_c_table
      ↓
match_c_with_b
      ↓
verify_reconciliation
      ↓
核查通过？
   ┌──┴──┐
   │     │
  是     否
   │     │
输出文件  返回失败原因
```

Agent 不允许跳过最终核查。

---

# 6. Agent System Prompt

第一版不需要把完整业务 MD 全部放进 Prompt。

可以使用下面这个最小 Prompt：

```text
你是一个财务对账流程智能体。

用户会提供两张 Excel：

A表：
业务方提供的原始对账表。

B表：
系统导出的出入库明细。
文件名通常以“台州”开头。

你的任务不是直接修改 Excel，而是调用 Excel 工具完成对账。

必须严格按照以下顺序执行：

1. 检查 A 表和 B 表。
2. 调用 generate_c_table，根据 A 表生成 C 表底稿。
3. 调用 match_c_with_b，将 B 表记录匹配到 C 表。
4. 调用 verify_reconciliation，对 A、B、C 进行最终核查。

任何情况下都不能跳过第 4 步。

只有当 verify_reconciliation 返回 passed=true 时，
才能认为任务完成。

如果核查失败：
不得告诉用户“对账完成”，
而应该返回核查失败原因。
```

---

# 7. Excel 工具设计

MVP 只提供四个工具。

---

## 7.1 inspect_excel

### 功能

检查：

- Excel 是否能正常打开。
- 工作表是否存在。
- A 表是否存在基础业务数据。
- B 表是否包含必要字段。
- 对账月份是否合法。
- 文件是否符合当前 MVP 支持范围。

### 接口

```python
inspect_excel(
    a_file: str,
    b_file: str,
    month: str
)
```

### 返回示例

```json
{
  "a": {
    "sheet": "Sheet1",
    "rows": 544,
    "columns": 7
  },
  "b": {
    "sheet": "Sheet1",
    "rows": 1200,
    "columns": 16
  },
  "month": "2026-07",
  "valid": true
}
```

如果文件异常：

```json
{
  "valid": false,
  "errors": [
    "B表缺少系统出入库时间字段"
  ]
}
```

---

# 8. generate_c_table

## 8.1 功能

根据 A 表完整生成 C 表底稿。

处理流程：

```text
复制 A 表
    ↓
取消合并单元格
    ↓
日期向下填充
    ↓
日期格式标准化
    ↓
清除原始底色
    ↓
保留原业务字段
    ↓
追加 B 表追溯字段
    ↓
生成 C.xlsx
```

---

## 8.2 接口

```python
generate_c_table(
    a_file: str
)
```

---

## 8.3 返回

```json
{
  "success": true,
  "c_file": "/tasks/REC202608190001/C.xlsx",
  "original_rows": 541
}
```

---

# 9. C 表新增字段

建议追加：

```text
匹配状态
匹配依据
B表行号
匹配方向
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

其中：

```text
匹配方向 =
入库
出库
```

---

# 10. match_c_with_b

这是 MVP 最核心的 Excel 工具。

## 10.1 接口

```python
match_c_with_b(
    c_file: str,
    b_file: str,
    month: str
)
```

---

# 11. 正负数匹配

## 11.1 正数

```text
C 表数量 > 0
```

匹配：

```text
B 表 K：入库数量
B 表 L：入库成本单价
B 表 M：入库成本金额
```

匹配方向：

```text
入库
```

---

## 11.2 负数

```text
C 表数量 < 0
```

匹配：

```text
B 表 N：出库数量
B 表 O：出库成本单价
B 表 P：出库成本金额
```

匹配方向：

```text
出库
```

比较时：

```text
abs(C数量) == B出库数量

abs(C金额) == B出库金额
```

---

# 12. B 表追溯字段

匹配成功后必须保留：

```text
仓库
系统出入库时间
单据编号
货品编号
货品名称
规格
数量
单价
金额
```

不能只保留：

```text
数量
单价
金额
```

否则人工无法反查系统记录。

---

# 13. 匹配算法

建议核心类：

```python
class ReconciliationMatcher:

    def match(self, c_row, b_rows):

        if c_row.quantity > 0:
            return self.match_inbound(c_row, b_rows)

        if c_row.quantity < 0:
            return self.match_outbound(c_row, b_rows)

        return self.match_zero(c_row, b_rows)
```

---

# 14. 匹配层级

建议按照以下优先级执行。

## Level 1：严格单行匹配

```text
日期一致
+
规格一致
+
数量一致
+
单价一致
```

状态：

```text
已匹配
```

---

## Level 2：辅助字段严格匹配

```text
日期
+
货品编号
+
规格
+
数量
+
单价
```

状态：

```text
已匹配
```

---

## Level 3：多行匹配

一条 C 表记录对应多条 B 表记录。

例如：

```text
C数量 = 462

B记录1 = 449
B记录2 = 13

449 + 13 = 462
```

匹配成功。

---

# 15. 多行匹配展开

不能：

```text
把 B 表两行合计后，只写到 C 表一行。
```

必须：

```text
B 表匹配几行
C 表就展开几行
```

例如：

```text
C原始行
   ├─ B记录1
   ├─ B记录2
   └─ B记录3
```

其中新增行：

```text
A 表原始业务字段为空
```

只填写：

```text
匹配状态
匹配依据
B表行号
匹配方向
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

这样不会破坏 A 表业务口径。

---

# 16. 需要复核的匹配

如果：

```text
数量一致
单价一致
核心业务字段能够对应
```

但是日期不同：

```text
已匹配/日期需复核
```

规格不同：

```text
已匹配/规格需复核
```

日期和规格都不同：

```text
已匹配/日期规格需复核
```

如果数量无法对应：

```text
未匹配
```

不能标记成已匹配。

---

# 17. 零数量 / 零金额

不能自动忽略。

例如：

```text
补发件
免费配件
补数
零金额入库
```

如果 B 表存在系统记录，仍然需要处理。

可标记：

```text
零金额需复核

补发件需复核
```

---

# 18. verify_reconciliation

生成 C 表之后必须进行最终核查。

接口：

```python
verify_reconciliation(
    a_file: str,
    b_file: str,
    c_file: str,
    month: str
)
```

---

# 19. A → C 核查

检查：

```text
A 表原始业务数量合计
=
C 表原始业务数量合计
```

同时：

```text
A 表原始业务金额合计
=
C 表原始业务金额合计
```

要求：

```text
quantity_diff = 0

amount_diff = 0
```

---

# 20. B → C 反向核查

例如当前对账月份：

```text
2026-07
```

只检查：

```text
B表系统出入库时间属于 2026-07
```

B 表每条本月系统记录必须属于：

```text
已承接
```

或者：

```text
已标注缺失
```

或者：

```text
人工排除
```

不允许出现：

```text
既没有进入 C 表
也没有被标记
```

---

# 21. B 表缺失标记

如果 B 表本月记录没有被 C 表承接：

在 B 表右侧追加：

```text
C表缺失标注
缺失类型
缺失匹配依据
标注说明
```

示例：

```text
C表缺失标注：C表缺失

缺失类型：入库缺失

缺失匹配依据：
B表本月记录未在C表中找到
```

---

# 22. Excel 公式核查

扫描：

```text
#REF!
#DIV/0!
#VALUE!
#NAME?
#N/A
```

要求：

```text
formula_errors = 0
```

---

# 23. 合计公式核查

C 表插入多行之后，需要重新确定合计行。

例如：

```text
原 A 表：

G545 = SUM(G4:G544)
```

插行以后：

```text
C 表合计行变成 G571
```

必须：

```text
G571 = SUM(G4:G570)
```

不能继续使用：

```text
SUM(G4:G544)
```

---

# 24. verify 返回结构

建议统一返回：

```json
{
  "passed": true,

  "a_c_check": {
    "quantity_a": 52310,
    "quantity_c": 52310,
    "quantity_diff": 0,

    "amount_a": 838293.52,
    "amount_c": 838293.52,
    "amount_diff": 0
  },

  "b_coverage": {
    "current_month_rows": 831,
    "matched": 790,
    "missing_marked": 41,
    "excluded": 0,
    "unexplained": 0
  },

  "excel_check": {
    "formula_errors": 0
  }
}
```

---

# 25. Agent 最终判断

Agent 只需要判断：

```python
if verify_result["passed"]:
    return success
else:
    return failed
```

---

## 成功

```json
{
  "status": "SUCCESS",
  "message": "对账完成",
  "c_file": "...",
  "marked_b_file": "...",
  "report": "..."
}
```

---

## 失败

例如：

```json
{
  "status": "FAILED",
  "message": "对账核查未通过",
  "errors": [
    "A/C金额差异120元",
    "存在3条B表记录未承接且未标记"
  ]
}
```

---

# 26. 后端 API

MVP 只需要四组 API。

---

## 26.1 上传文件

```http
POST /api/reconciliation/upload
```

参数：

```text
a_file
b_file
```

返回：

```json
{
  "task_id": "REC202608190001"
}
```

---

## 26.2 开始对账

```http
POST /api/reconciliation/{task_id}/run
```

请求：

```json
{
  "month": "2026-07"
}
```

---

## 26.3 获取任务状态

```http
GET /api/reconciliation/{task_id}
```

返回：

```json
{
  "task_id": "REC202608190001",
  "status": "VERIFYING",
  "progress": 80
}
```

---

## 26.4 下载文件

```http
GET /api/reconciliation/{task_id}/download/c
```

```http
GET /api/reconciliation/{task_id}/download/b
```

也可以增加：

```http
GET /api/reconciliation/{task_id}/report
```

---

# 27. 任务状态

```text
UPLOADED

INSPECTING

GENERATING

MATCHING

VERIFYING

SUCCESS

FAILED
```

前端根据这些状态展示执行进度。

---

# 28. 数据库设计

MVP 可以直接使用 SQLite。

表：

```text
reconciliation_task
```

字段：

```text
id

a_file_path

b_file_path

month

status

c_file_path

marked_b_file_path

verify_result

error_message

created_at

finished_at
```

---

# 29. 前端页面

MVP 不需要聊天页面。

只做一个对账页面。

```text
              财务智能对账


A表：

[ 选择文件 ]

芳华7月.xlsx


B表：

[ 选择文件 ]

台州市芳华塑料制品厂.xlsx


对账月份：

[ 2026-07 ▼ ]


        [ 开始智能对账 ]


────────────────────────


执行进度：

✓ 文件检查

✓ 生成C表

✓ C/B匹配

✓ B表反向核查


────────────────────────


核查结果：

A/C数量差额：0

A/C金额差额：0

B本月记录：831

已承接：790

缺失标记：41

未解释：0


最终状态：

✓ 核查通过


[ 下载 C 表 ]

[ 下载标记 B 表 ]
```

---

# 30. 前端组件

```text
Reconciliation.vue

├── FileUpload.vue
├── MonthSelector.vue
├── TaskProgress.vue
├── VerifyResult.vue
└── DownloadResult.vue
```

---

# 31. 项目结构

```text
reconciliation-agent/

├── backend/
│
│   ├── app/
│   │
│   ├── main.py
│   │
│   ├── api/
│   │   └── reconciliation.py
│   │
│   ├── agent/
│   │   ├── reconciliation_agent.py
│   │   └── prompt.py
│   │
│   ├── tools/
│   │   ├── inspect_excel.py
│   │   ├── generate_c.py
│   │   ├── match_b.py
│   │   └── verify.py
│   │
│   ├── excel/
│   │   ├── reader.py
│   │   ├── writer.py
│   │   ├── matcher.py
│   │   ├── normalizer.py
│   │   └── verifier.py
│   │
│   ├── models/
│   │   ├── task.py
│   │   └── result.py
│   │
│   ├── db/
│   │   └── database.py
│   │
│   └── storage/
│       └── tasks/
│
└── frontend/
    │
    └── src/
        ├── views/
        │   └── Reconciliation.vue
        │
        ├── api/
        │   └── reconciliation.ts
        │
        └── components/
            ├── FileUpload.vue
            ├── MonthSelector.vue
            ├── TaskProgress.vue
            ├── VerifyResult.vue
            └── DownloadResult.vue
```

---

# 32. matcher.py 建议结构

```python
class ReconciliationMatcher:

    def match(self, c_row, b_rows):
        pass

    def match_inbound(self, c_row, b_rows):
        pass

    def match_outbound(self, c_row, b_rows):
        pass

    def match_zero(self, c_row, b_rows):
        pass

    def find_exact_match(self, c_row, b_rows):
        pass

    def find_multi_row_match(self, c_row, b_rows):
        pass

    def find_date_review_match(self, c_row, b_rows):
        pass

    def find_spec_review_match(self, c_row, b_rows):
        pass
```

---

# 33. verifier.py 建议结构

```python
class ReconciliationVerifier:

    def verify(self, a_file, b_file, c_file, month):
        pass

    def verify_a_c_quantity(self):
        pass

    def verify_a_c_amount(self):
        pass

    def verify_b_coverage(self):
        pass

    def verify_formula_errors(self):
        pass

    def verify_total_formula(self):
        pass

    def verify_excel_view(self):
        pass
```

---

# 34. 第一版主流程

即使暂时不使用 LangGraph，也可以先写成普通 Python：

```python
async def reconcile(a_file, b_file, month):

    inspect_result = inspect_excel(
        a_file=a_file,
        b_file=b_file,
        month=month
    )

    if not inspect_result["valid"]:
        return {
            "status": "FAILED",
            "errors": inspect_result["errors"]
        }

    c_result = generate_c_table(
        a_file=a_file
    )

    match_result = match_c_with_b(
        c_file=c_result["c_file"],
        b_file=b_file,
        month=month
    )

    verify_result = verify_reconciliation(
        a_file=a_file,
        b_file=b_file,
        c_file=match_result["c_file"],
        month=month
    )

    if not verify_result["passed"]:
        return {
            "status": "FAILED",
            "report": verify_result
        }

    return {
        "status": "SUCCESS",
        "c_file": match_result["c_file"],
        "marked_b_file": verify_result["marked_b_file"],
        "report": verify_result
    }
```

---

# 35. LangGraph MVP

如果希望使用 LangGraph，可以只设计四个节点。

```text
START

  ↓

inspect

  ↓

generate_c

  ↓

match_b

  ↓

verify

  ↓

SUCCESS / FAILED

  ↓

END
```

State：

```python
class ReconciliationState(TypedDict):

    task_id: str

    a_file: str
    b_file: str
    c_file: str | None

    month: str

    status: str

    inspect_result: dict | None
    match_result: dict | None
    verify_result: dict | None

    errors: list[str]
```

第一版甚至不需要复杂 LLM 决策节点。

LangGraph 主要用于：

```text
控制流程

保存状态

控制失败分支

方便未来扩展
```

---

# 36. MD 文档在系统里的定位

原来的业务规则 MD 不应该一直作为完整 Prompt 塞给 LLM。

应该逐渐拆成：

```text
业务规则文档
        ↓
规则实现
        ↓
Python
```

结构：

```text
                    Agent Prompt
                         │
                  只保存流程职责
                         │
                         ▼
                    Python规则
                         │
        ┌────────────────┼───────────────┐
        ▼                ▼               ▼
   正负数规则        多行规则       反向核查规则
        │                │               │
        └────────────────┼───────────────┘
                         ▼
                       Excel
```

MD 的主要作用：

```text
业务规范

开发依据

测试依据

验收依据
```

而不是：

```text
每一次都全部发送给 LLM
```

---

# 37. MVP 技术栈

## 前端

```text
Vue 3
TypeScript
Element Plus
Axios
```

## 后端

```text
FastAPI
Pydantic
SQLAlchemy
```

## Agent

第一阶段：

```text
普通 Python Workflow
```

或者：

```text
LangGraph
```

## Excel

```text
openpyxl
```

必要时增加：

```text
pandas
```

## 数据库

```text
SQLite
```

后续可切换：

```text
PostgreSQL
```

## 文件存储

```text
backend/storage/tasks/{task_id}/
```

例如：

```text
storage/tasks/REC202608190001/

├── A.xlsx
├── B.xlsx
├── C.xlsx
├── B_marked.xlsx
└── report.json
```

---

# 38. MVP 第一阶段文件限制

第一版建议只支持：

```text
.xlsx
```

暂时不支持：

```text
.xls
xlsb
csv
```

等核心逻辑稳定以后，再增加文件适配层。

---

# 39. MVP 验收标准

一个任务必须同时满足：

## A 表

```text
原始 A 表未被修改
```

## C 表

```text
从 A 表完整复制生成
```

```text
日期已正确填充
```

```text
正数正确匹配 B 入库
```

```text
负数正确匹配 B 出库
```

```text
多行匹配已逐行展开
```

```text
B 表追溯字段完整
```

## A/C 核查

```text
A数量 = C原始数量
```

```text
A金额 = C原始金额
```

要求：

```text
差额 = 0
```

## B 表反向核查

```text
B本月记录数
=
C已承接
+
B已标注缺失
+
人工排除
```

要求：

```text
unexplained = 0
```

## Excel 核查

```text
#REF! = 0
#DIV/0! = 0
#VALUE! = 0
#NAME? = 0
#N/A = 0
```

## 最终结果

```text
verify.passed == true
```

才能：

```text
status = SUCCESS
```

---

# 40. MVP 最核心目标

第一版最终只验证一件事情：

> 用户上传 A 表 + B 表，点击一次按钮，系统能够稳定生成 C 表、标记 B 表缺失记录，并完成 A/C 口径核查与 B 表本月反向核查。

最终闭环：

```text
上传

↓

自动处理

↓

自动生成

↓

自动核查

↓

结果通过

↓

下载
```

而不是追求：

```text
Agent 看起来有多聪明
```

优先追求：

```text
同一输入
+
同一规则
=
同一输出
```

---

# 41. 后续演进方向

MVP 稳定以后，再逐步增加：

```text
Phase 2

不同 A 表结构自动识别
```

```text
Phase 3

公司 / 供应商匹配策略
```

```text
Phase 4

规则配置系统
```

```text
Phase 5

人工复核工作台
```

```text
Phase 6

LLM 解释异常原因
```

```text
Phase 7

规则学习 / 历史案例知识库
```

最终形成：

```text
Excel 对账引擎
        +
规则引擎
        +
Agent 调度层
        +
人工复核系统
```

但 MVP 阶段只需要：

```text
Excel 对账引擎
+
简单流程 Agent
+
一个上传页面
+
一个核查结果页面
```
