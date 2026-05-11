# WebGalAgent

多智能体协作工作流框架 — 让多个 AI Agent 以不同角色协同完成复杂任务。

## 项目简介

WebGalAgent 是一个通用的多智能体协作框架。核心思路是将复杂任务拆解为多个子任务，分配给不同角色的智能体（Agent），通过工作流（Workflow）编排它们的协作方式，最终汇聚结果。

### 核心概念

| 概念 | 说明 |
|------|------|
| **Agent** | 自主智能体，拥有独立记忆、系统提示词和运行逻辑 |
| **Message** | 智能体之间的通信单元，包含类型、发送方、接收方和内容 |
| **Workflow** | 工作流模式，定义智能体之间的协作顺序和消息流转方式 |
| **Memory** | 智能体的记忆系统，存储对话历史 |
| **Knowledge** | 知识库，存储角色、设定等参考信息，供智能体运行时查询 |
| **Tool** | 工具，扩展智能体的能力（如文件读写） |

### 内置角色

| 角色 | 职责 |
|------|------|
| **Director** | 导演 — 接收高层需求，分解为子任务，协调整体流程 |
| **Writer** | 创作者 — 根据任务生成结构化内容 |
| **Artist** | 创意专家 — 生成视觉描述和创意提示词 |
| **Reviewer** | 审核员 — 评估输出质量，给出改进建议和评分 |

### 内置工作流

| 模式 | 说明 |
|------|------|
| **SequentialWorkflow** | 顺序流水线 — 智能体按固定顺序依次执行，前一个的输出作为后一个的输入 |
| **DebateWorkflow** | 辩论迭代 — 创作者与审核员交替执行，直到质量评分达到阈值或达到最大迭代次数 |

---

## 环境要求

- **Python** ≥ 3.12
- **包管理**: [hatch](https://hatch.pypa.io/) 或 pip
- **LLM API**: OpenAI 兼容接口（OpenAI / Azure / 本地模型等）

---

## 安装

### 1. 克隆项目

```bash
git clone <repo-url>
cd WebGalAgent
```

### 2. 创建虚拟环境并安装依赖

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev]"
```

### 3. 配置环境变量

复制示例文件并填入你的 API Key：

```bash
cp .env.example .env
```

编辑 `.env`：

```env
LLM_API_KEY=sk-your-api-key-here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o
```

---

## 快速开始

### 顺序流水线

```python
import asyncio
from webgal_agent.agents import DirectorAgent, WriterAgent
from webgal_agent.core.agent import AgentConfig
from webgal_agent.core.message import Message, MessageType
from webgal_agent.workflows import SequentialWorkflow


async def main():
    # 创建智能体
    director = DirectorAgent()
    writer = WriterAgent()

    # 组建顺序工作流
    workflow = SequentialWorkflow(
        agents={"director": director, "writer": writer},
        order=["director", "writer"],
    )

    # 发起任务
    initial = Message(
        type=MessageType.TASK,
        sender="user",
        receiver="director",
        content="请帮我写一个关于时间旅行的短故事",
    )

    result = await workflow.execute(initial)

    # 查看结果
    for msg in result.messages:
        print(f"[{msg.sender} → {msg.receiver}] {msg.content}")


asyncio.run(main())
```

### 辩论迭代（创作者 + 审核员）

```python
from webgal_agent.agents import WriterAgent, ReviewerAgent
from webgal_agent.workflows import DebateWorkflow


async def main():
    writer = WriterAgent()
    reviewer = ReviewerAgent()

    workflow = DebateWorkflow(
        agents={"writer": writer, "reviewer": reviewer},
        creator="writer",
        reviewer="reviewer",
        max_iterations=3,
        threshold=0.8,  # 审核评分 ≥ 0.8 即通过
    )

    initial = Message(
        type=MessageType.TASK,
        sender="user",
        receiver="writer",
        content="写一段产品介绍文案",
    )

    result = await workflow.execute(initial)
    print(f"成功: {result.success}, 迭代次数: {result.metadata.get('iterations')}")
```

---

## 知识库

知识库用于存储角色信息、世界观、设定等参考资料，智能体运行时可以查询。

### 目录结构

```
data/knowledge/
├── characters/          # 角色信息
│   ├── 主角.md
│   └── 伙伴A.md
└── settings/            # 世界设定
    ├── 世界观.md
    └── 主场景.md
```

### 文件格式

每个知识条目是一个 Markdown 文件，顶部用 YAML Frontmatter 存储元数据，正文为自由格式的 Markdown：

```markdown
---
category: character
tags: [protagonist, human]
title: Alice
---

# Alice

## 基本信息
- 年龄：18
- 性别：女

## 性格
勇敢、善良、略带倔强

## 背景
来自边境小镇的冒险者……
```

### 加载与查询

```python
from webgal_agent.knowledge import FileKnowledgeStore

# 加载知识库
store = FileKnowledgeStore("data/knowledge")

# 按类别查询
characters = store.query(category="character")

# 按标签查询
protagonists = store.query(tags=["protagonist"])

# 关键词搜索
results = store.query(keyword="Alice")

# 获取条目内容（可直接放入 LLM prompt）
for entry in characters:
    print(entry.full_content())

# 热更新（修改文件后重新加载）
store.reload()
```

### 新增知识条目

在 `data/knowledge/` 下的任意子目录中新建 `.md` 文件即可。目录结构自由组织，`FileKnowledgeStore` 会递归扫描所有 `.md` 文件。

---

## 项目结构

```
WebGalAgent/
├── pyproject.toml              # 项目配置 & 依赖
├── configs/
│   └── default.yaml            # 默认配置文件
├── data/
│   └── knowledge/              # 知识库（Markdown + Frontmatter）
│       ├── characters/
│       └── settings/
├── src/webgal_agent/
│   ├── __init__.py
│   ├── core/                   # 核心抽象层
│   │   ├── agent.py            #   Agent 基类 & 状态机
│   │   ├── message.py          #   消息模型 & 消息类型
│   │   ├── workflow.py         #   Workflow 基类 & 执行结果
│   │   ├── memory.py           #   记忆抽象 & 内存实现
│   │   └── context.py          #   跨 Agent 共享上下文
│   ├── agents/                 # 具体智能体实现
│   │   ├── director.py         #   导演
│   │   ├── writer.py           #   创作者
│   │   ├── artist.py           #   创意专家
│   │   └── reviewer.py          #   审核员
│   ├── workflows/              # 工作流模式
│   │   ├── sequential.py       #   顺序流水线
│   │   └── debate.py           #   辩论迭代
│   ├── knowledge/              # 知识库
│   │   ├── models.py           #   知识条目模型
│   │   └── store.py            #   存储抽象 & 文件加载
│   ├── tools/                  # 工具扩展
│   │   ├── base.py             #   Tool 基类
│   │   └── file_ops.py         #   文件读写工具
│   ├── config/                 # 配置管理
│   │   └── settings.py         #   pydantic-settings 配置
│   └── utils/
│       └── logging.py          #   日志配置（rich）
└── tests/                      # 测试
    ├── conftest.py
    └── core/
        ├── test_agent.py
        ├── test_message.py
        └── test_workflow.py
```

---

## 配置说明

### 环境变量

所有配置均可通过环境变量覆盖，支持 `.env` 文件：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WEBGAL_DEBUG` | `false` | 调试模式 |
| `WEBGAL_PROJECT_DIR` | `.` | 项目目录 |
| `LLM_PROVIDER` | `openai` | LLM 提供商 |
| `LLM_MODEL` | `gpt-4o` | 模型名称 |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | API 地址 |
| `LLM_API_KEY` | - | API 密钥 |
| `LLM_TEMPERATURE` | `0.7` | 生成温度 |
| `LLM_MAX_TOKENS` | `4096` | 最大 Token 数 |

### YAML 配置文件

参考 `configs/default.yaml`，可按需修改各智能体使用的模型和工作流参数。

---

## 自定义扩展

### 创建自定义智能体

继承 `Agent` 基类，实现 `system_prompt()` 和 `run()` 方法：

```python
from webgal_agent.core.agent import Agent, AgentConfig
from webgal_agent.core.message import Message, MessageType


class TranslatorAgent(Agent):
    def __init__(self) -> None:
        super().__init__(config=AgentConfig(
            name="translator",
            description="Translation agent",
        ))

    def system_prompt(self) -> str:
        return "你是一个专业翻译，将内容翻译为指定语言。"

    async def run(self, message: Message) -> Message:
        # 接入 LLM 进行实际翻译
        ...
        return message.reply(content="翻译结果...", msg_type=MessageType.RESULT)
```

### 创建自定义工作流

继承 `Workflow` 基类，实现 `execute()` 方法：

```python
from webgal_agent.core.workflow import Workflow, WorkflowResult


class ParallelWorkflow(Workflow):
    """并行执行多个智能体，汇总结果。"""

    async def execute(self, initial_message: Message) -> WorkflowResult:
        import asyncio

        tasks = [
            agent.handle(initial_message)
            for agent in self.agents.values()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        messages = []
        errors = []
        for r in results:
            if isinstance(r, Exception):
                errors.append(str(r))
            else:
                messages.append(r)

        return WorkflowResult(success=len(errors) == 0, messages=messages, errors=errors)
```

### 创建自定义工具

继承 `Tool` 基类：

```python
from webgal_agent.tools.base import Tool, ToolResult


class SearchTool(Tool):
    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Search the web for information."

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        # 实现搜索逻辑
        return ToolResult(success=True, output="搜索结果...")
```

---

## 运行测试

```bash
pytest -v
```

---

## 技术栈

- **Python** 3.12+
- **Pydantic** v2 — 数据模型 & 校验
- **pydantic-settings** — 配置管理（环境变量 / .env）
- **PyYAML** — YAML 解析
- **OpenAI SDK** — LLM 调用
- **httpx** — 异步 HTTP 客户端
- **Rich** — 终端美化输出
- **pytest + pytest-asyncio** — 异步测试

---

## 许可证

MIT
