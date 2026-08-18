# Reconciliation Agent

面向财务对账 C 表生成的 Agent 项目结构。

核心原则：

1. C 表必须从 A 表完整复制生成，不能破坏 A 表口径。
2. C 表必须按正负数分别匹配 B 表入库/出库字段。
3. 多行匹配必须逐行展开，不能只写合计。
4. B 表本月系统记录必须全部被 C 表承接、被 B 表标注缺失，或被人工排除。
5. 交付前必须运行强制核查；核查不通过不交付。

## 安装

```bash
python -m pip install -e .[dev]
```

## 运行

```bash
reconcile-c-table run \
  --a-table path/to/A.xlsx \
  --b-table path/to/台州B.xlsx \
  --month 2026-07 \
  --output-dir outputs
```

## 模型供应商

LLM 层只用于解释运行计划和根据验收失败报告提出修复建议；Excel 读写、匹配、反向核查和交付验收仍由确定性 Python 工具执行。

默认使用 Anthropic/Claude，也可以通过 CLI 切换供应商：

```bash
reconcile-c-table run \
  --a-table path/to/A.xlsx \
  --b-table path/to/台州B.xlsx \
  --month 2026-07 \
  --llm-provider deepseek \
  --llm-model deepseek-chat
```

支持的供应商和默认密钥环境变量：

| Provider | 默认模型 | 默认环境变量 | 说明 |
| --- | --- | --- | --- |
| `anthropic` | `claude-opus-5` | `ANTHROPIC_API_KEY` | 使用官方 Anthropic SDK。 |
| `openai` | `gpt-4.1` | `OPENAI_API_KEY` | 使用官方 OpenAI SDK。 |
| `deepseek` | `deepseek-chat` | `DEEPSEEK_API_KEY` | 通过 OpenAI-compatible 接口接入。 |
| `qwen` | `qwen-plus` | `DASHSCOPE_API_KEY` | 通过 DashScope OpenAI-compatible 接口接入。 |
| `ollama` | `qwen2.5` | 无 | 默认访问本地 `http://localhost:11434`。 |

可选参数：

- `--llm-provider`：选择 `anthropic`、`openai`、`deepseek`、`qwen`、`ollama`。
- `--llm-model`：覆盖默认模型。
- `--llm-base-url`：覆盖 provider 默认 base URL。
- `--llm-api-key-env`：指定读取 API key 的环境变量名。

## 结构

- `agent/domain`：领域模型、状态、表结构定义。
- `agent/core`：确定性 Excel 处理工具。
- `agent/workflows`：端到端 C 表工作流。
- `agent/verification`：强制交付验收。
- `agent/reporting`：审计报告。
- `agent/tools`：暴露给 LLM 编排层的工具外观。
- `agent/llm_providers`：Claude、OpenAI、DeepSeek、Qwen、Ollama 模型适配器。
- `agent/rules`：公司规则配置。
- `docs/agent-implementation-blueprint.md`：完整实现蓝图。
