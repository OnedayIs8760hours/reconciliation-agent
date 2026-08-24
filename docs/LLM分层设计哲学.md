# LLM Provider、Domain 与 Agent 门面的设计哲学

本文整理当前项目中 `agent/domain`、`agent/llm_providers` 和 `agent/llm.py` 三部分的设计思想。它们共同解决一个问题：**让财务对账 Agent 可以通过统一入口使用不同模型供应商，同时不让业务流程被具体 SDK、HTTP 接口、模型参数和密钥管理细节污染。**

## 一、总体设计目标

当前 LLM 相关代码不是简单地把 Claude、OpenAI、Ollama 的调用代码堆在一起，而是拆成三层：

```text
业务调用方 / Workflow / CLI
        ↓
agent/llm.py
统一 LLM Agent 门面
        ↓
agent/llm_providers/factory.py
根据 provider 动态选择适配器
        ↓
agent/llm_providers/*.py
具体供应商 SDK / HTTP 适配
        ↓
Anthropic / OpenAI / DeepSeek / Qwen / Ollama
```

同时，配置模型放在：

```text
agent/domain/config.py
```

它负责定义哪些 provider 合法、有哪些通用配置字段、默认值如何校验。

这个设计的核心思想是：

1. **业务层不关心具体模型供应商。**
2. **具体供应商差异被封装在 adapter 内部。**
3. **配置先变成强类型对象，再进入工厂函数。**
4. **Agent 只调用统一的 `complete()` 方法。**
5. **LLM 不直接操作 Excel，只负责解释、建议和编排。**

---

## 二、`agent/domain` 的设计哲学

### 1. Domain 层是什么

`agent/domain` 是领域模型层。

在当前 LLM 架构里，主要文件是：

```text
agent/domain/config.py
```

它定义：

```python
LLMProviderName = Literal["anthropic", "openai", "deepseek", "qwen", "ollama"]
```

和：

```python
class LLMConfig(BaseModel):
    ...
```

### 2. 为什么 provider 名字要放在 domain 里

因为 provider 名字不是某一个 adapter 自己的私有信息，而是整个 Agent 系统都要认同的公共概念。

比如这些地方都会用到 provider：

- CLI 参数：用户传入 `--llm-provider openai`
- Agent 初始化：`ReconciliationLLMAgent(provider="openai")`
- factory 分发：根据 provider 创建对应 adapter
- response 返回：`LLMResponse(provider="openai")`
- 日志、审计、成本统计：记录本次到底用了哪个模型供应商

所以 provider 名字应该集中定义，而不是散落在多个文件里写字符串。

### 3. `LLMConfig` 的意义

`LLMConfig` 是模型调用的统一配置对象。

它把这些参数集中管理：

```python
provider
model
base_url
api_key_env
timeout_seconds
max_retries
```

这样做有几个好处：

#### 统一入口

调用方只需要创建一个配置对象：

```python
LLMConfig(provider="deepseek")
```

不用自己知道 DeepSeek 默认模型、base URL、环境变量名。

#### 强类型校验

非法 provider 会被 Pydantic 拦住。

比如：

```python
LLMConfig(provider="unknown")
```

这不应该进入后续模型调用流程。

#### 避免配置散落

如果没有 `LLMConfig`，代码里可能到处都是：

```python
provider = "openai"
model = "gpt-4.1"
api_key_env = "OPENAI_API_KEY"
```

后续维护时很容易出错。

### 4. Domain 层的哲学总结

`agent/domain` 的设计哲学是：

> **先把系统认可的业务概念和配置概念定义成强类型对象，再让其他层基于这些对象协作。**

它不是负责调用模型的地方，而是负责定义“这个系统允许怎么配置模型”。

---

## 三、`agent/llm_providers` 的设计哲学

### 1. Provider 层是什么

`agent/llm_providers` 是模型供应商适配层。

它的职责是：

> **屏蔽不同模型供应商之间的 SDK、HTTP API、参数格式、响应格式差异，对上层统一暴露 `complete(prompt, max_tokens)`。**

当前目录大致包含：

```text
agent/llm_providers/
├── base.py
├── factory.py
├── anthropic_adapter.py
├── openai_adapter.py
├── openai_compatible_adapter.py
├── ollama_adapter.py
└── __init__.py
```

### 2. `base.py` 的意义

`base.py` 定义公共约定：

```python
@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    provider: LLMProviderName
```

和：

```python
class LLMProviderAdapter(Protocol):
    provider: LLMProviderName
    model: str

    def complete(self, prompt: str, max_tokens: int = 1024) -> LLMResponse:
        ...
```

也就是说，只要一个 adapter 有：

```text
provider
model
complete()
```

它就符合系统对模型供应商适配器的最低要求。

### 3. 为什么需要 `LLMResponse`

不同供应商返回结构不一样。

Anthropic 可能返回 content blocks：

```python
response.content
```

OpenAI 返回：

```python
response.choices[0].message.content
```

Ollama 返回：

```python
body["message"]["content"]
```

或者：

```python
body["response"]
```

如果上层业务代码直接解析这些返回值，就会变得非常混乱。

所以 adapter 内部负责解析供应商原始响应，然后统一返回：

```python
LLMResponse(
    text="模型生成的文本",
    model="实际使用的模型名",
    provider="实际供应商",
)
```

上层只使用 `response.text`，不关心供应商原始结构。

### 4. 为什么需要 adapter

每个 provider 的调用方式都不同。

#### Anthropic

使用：

```python
self.client.messages.create(...)
```

而且可以带 Claude 专属参数：

```python
thinking={"type": "adaptive"}
```

#### OpenAI

使用：

```python
self.client.chat.completions.create(...)
```

不能传 Claude 的 `thinking` 参数。

#### DeepSeek / Qwen

它们可以复用 OpenAI-compatible 接口形式，但是：

- provider 名字不同
- model 默认值不同
- base URL 不同
- API key 环境变量不同

#### Ollama

它不走 OpenAI SDK，而是本地 HTTP：

```text
POST http://localhost:11434/api/chat
```

并且 `max_tokens` 要映射成：

```python
options.num_predict
```

如果没有 adapter，业务层就必须写很多分支：

```python
if provider == "anthropic":
    ...
elif provider == "openai":
    ...
elif provider == "ollama":
    ...
```

这样会导致业务代码越来越脏。

adapter 的设计就是为了把这些差异关在各自文件里。

### 5. `factory.py` 的意义

`factory.py` 是模型适配器工厂。

它做两件事：

#### 第一件事：补全默认配置

例如用户只传：

```python
LLMConfig(provider="qwen")
```

factory 会补全成类似：

```python
provider = "qwen"
model = "qwen-plus"
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
api_key_env = "DASHSCOPE_API_KEY"
```

这里用到：

```python
config.model_copy(update={...})
```

它的意思是：复制一个新的配置对象，并在新对象上补全默认字段，不直接修改原始 config。

#### 第二件事：根据 provider 创建 adapter

例如：

```python
if config.provider == "anthropic":
    return AnthropicAdapter(...)
if config.provider == "openai":
    return OpenAIAdapter(...)
if config.provider in {"deepseek", "qwen"}:
    return OpenAICompatibleAdapter(...)
if config.provider == "ollama":
    return OllamaAdapter(...)
```

这样 `agent/llm.py` 不需要知道具体创建逻辑。

### 6. `OpenAICompatibleAdapter` 的意义

DeepSeek、Qwen 这类服务虽然不是 OpenAI，但接口形式和 OpenAI Chat Completions 很像。

所以没有必要重复写：

```python
client.chat.completions.create(...)
```

它们可以继承 `OpenAIAdapter`，只替换：

```python
provider
model
base_url
api_key_env
```

这体现的是复用思想：

> **协议兼容的 provider，不重复造轮子；只在配置上区分供应商。**

### 7. Provider 层的哲学总结

`agent/llm_providers` 的设计哲学是：

> **把所有模型供应商差异都封装在适配器层，对业务层只暴露统一协议。**

这样后续新增 provider 时，主要新增 adapter 和 factory 分支，不需要大改 Agent 或 Workflow。

---

## 四、`agent/llm.py` 的设计哲学

### 1. `llm.py` 是什么

`agent/llm.py` 是 LLM Agent 门面层。

核心类是：

```python
ReconciliationLLMAgent
```

它是业务调用方真正接触的入口。

调用方可以这样使用：

```python
agent = ReconciliationLLMAgent(provider="openai")
response = agent.complete("请解释这个对账计划")
```

也可以：

```python
agent = ReconciliationLLMAgent(provider="ollama", model="qwen2.5")
```

### 2. 为什么 `llm.py` 不直接调用 OpenAI 或 Anthropic

如果 `llm.py` 直接写 SDK 调用，会变成这样：

```python
if self.provider == "anthropic":
    self.client.messages.create(...)
elif self.provider == "openai":
    self.client.chat.completions.create(...)
elif self.provider == "ollama":
    httpx.post(...)
```

这样 `llm.py` 就会知道太多底层细节。

而当前设计是：

```python
self.adapter = build_llm_adapter(config)
```

然后只调用：

```python
self.adapter.complete(prompt, max_tokens=max_tokens)
```

这样 `llm.py` 只关心“我要让模型完成一次文本生成”，不关心“这个模型到底通过哪个 SDK 调用”。

### 3. `ReconciliationLLMAgent` 的职责边界

`ReconciliationLLMAgent` 不是万能类。

它不应该负责：

- 读取 Excel
- 修改 Excel
- 匹配 A/B 表记录
- 写入 C 表
- 标注 B 表缺失
- 校验公式
- 保存文件

这些都应该由确定性 core/tools/workflow 层负责。

它应该负责：

- 接收 provider/model 等 LLM 配置
- 构建对应 adapter
- 提供统一 `complete()` 方法
- 组织和模型交互的业务 prompt
- 解释计划
- 根据验收失败报告提出修复建议

### 4. 为什么有 `ClaudeReconciliationAgent`

当前主类已经是 provider-neutral：

```python
ReconciliationLLMAgent(provider="anthropic")
ReconciliationLLMAgent(provider="openai")
ReconciliationLLMAgent(provider="ollama")
```

但旧代码可能已经使用：

```python
ClaudeReconciliationAgent
```

如果直接删除，会导致旧导入失败。

所以保留：

```python
class ClaudeReconciliationAgent(ReconciliationLLMAgent):
    ...
```

它默认设置：

```python
provider = "anthropic"
```

这是一种兼容设计：

> **新架构支持多 provider，同时不破坏旧调用方式。**

### 5. 为什么 Agent 支持注入 adapter

`ReconciliationLLMAgent` 里有：

```python
adapter: LLMProviderAdapter | None = None
```

这是为了测试和扩展。

测试时不应该真的调用 OpenAI 或 Claude，所以可以注入 fake adapter：

```python
agent = ReconciliationLLMAgent(adapter=FakeAdapter())
```

这样测试只验证 Agent 是否正确调用 adapter，不访问外部网络。

这体现的是依赖注入思想：

> **外部依赖可以被替换，这样代码更容易测试，也更容易接入上层已有 client。**

### 6. `llm.py` 的哲学总结

`agent/llm.py` 的设计哲学是：

> **为业务层提供一个稳定、简单、provider-neutral 的 LLM 使用入口，把复杂的模型选择和调用细节交给下层 adapter/factory。**

---

## 五、三层之间的关系

可以把这三层理解成：

```text
agent/domain
定义规则：允许哪些 provider？配置字段有哪些？

agent/llm_providers
执行适配：不同 provider 怎么调用？怎么把响应转成统一格式？

agent/llm.py
业务门面：调用方怎么用一个统一 Agent 发起 LLM 请求？
```

更直观地说：

```text
Domain 是说明书
Factory 是调度员
Adapter 是翻译官
LLM Agent 是前台入口
```

- Domain：规定合法配置。
- Factory：根据配置选择正确 adapter。
- Adapter：把统一请求翻译成各供应商 API。
- LLM Agent：给业务代码一个简单入口。

---

## 六、为什么这是比直接写 if/else 更好的设计

### 直接写法的问题

如果所有逻辑都写在一个类里，代码可能变成：

```python
class ReconciliationLLMAgent:
    def complete(self, prompt):
        if self.provider == "anthropic":
            ...
        elif self.provider == "openai":
            ...
        elif self.provider == "deepseek":
            ...
        elif self.provider == "qwen":
            ...
        elif self.provider == "ollama":
            ...
```

短期看简单，长期会有问题：

1. 一个类越来越大。
2. provider 参数互相污染。
3. 测试困难。
4. 新增 provider 要改主业务类。
5. 响应格式解析散落在业务代码里。
6. 密钥、base URL、默认模型难以统一维护。

### 当前写法的优势

当前设计把责任拆开：

```text
LLMConfig 负责配置
factory 负责选择
adapter 负责调用
LLM Agent 负责业务入口
```

这样每一层都比较清楚。

新增一个 provider 时，理想情况下只需要：

1. 在 `LLMProviderName` 里加名字。
2. 在 factory 默认配置里加模型、base URL、API key env。
3. 新增或复用一个 adapter。
4. 加测试。

业务层基本不用改。

---

## 七、当前架构成熟度

当前设计可以理解为：

> **企业级架构骨架 / 工程化 MVP，而不是完整企业生产级闭环。**

它已经具备：

- 分层清晰
- provider-neutral 门面
- adapter pattern
- factory pattern
- 强类型配置
- 密钥不硬编码
- fake client 可测试
- provider 响应统一封装
- Claude 专属参数隔离
- OpenAI-compatible provider 复用
- Ollama 本地模型适配

但如果要进一步达到更完整的企业生产级，还可以继续补：

1. 统一日志与链路追踪。
2. LLM 请求审计记录。
3. token 使用量和成本统计。
4. 更细的错误类型，例如鉴权失败、限流、超时、模型不可用。
5. fallback 策略，例如 OpenAI 失败后切换备用 provider。
6. prompt 模板管理和版本管理。
7. 敏感财务数据脱敏策略。
8. provider 调用速率限制。
9. 配置从环境变量、YAML、TOML 或 secrets manager 加载。
10. 更严格的运行时 adapter 校验。

---

## 八、最终总结

当前 `domain + llm_providers + llm.py` 的整体设计哲学是：

> **用 Domain 定义配置边界，用 Factory 动态选择模型供应商，用 Adapter 屏蔽供应商差异，用 LLM Agent 给业务流程提供稳定入口。**

它的核心价值不是“少写几行代码”，而是：

1. 后续新增模型供应商更容易。
2. 业务流程不被 SDK 细节污染。
3. 测试时可以替换真实模型调用。
4. 不同供应商响应可以统一处理。
5. 财务对账核心流程仍保持确定性和可审计。
