# WebGalAgent

多智能体协作工作流框架 — 让多个 AI Agent 以不同角色协同完成视觉小说剧本创作。

## 项目简介

WebGalAgent 是一个面向视觉小说（Visual Novel）创作的多智能体协作框架。核心思路是将剧本创作流程拆解为三个阶段，分别由不同角色的智能体完成，通过 Pipeline 工作流串联执行，最终输出 WebGal 引擎可识别的脚本。

### 核心概念

| 概念 | 说明 |
|------|------|
| **Agent** | 自主智能体，拥有独立记忆、系统提示词和运行逻辑 |
| **Message** | 智能体之间的通信单元，包含类型、发送方、接收方和内容 |
| **Workflow** | 工作流模式，定义智能体之间的协作顺序和消息流转方式 |
| **Memory** | 智能体的记忆系统，存储对话历史 |
| **Knowledge** | 知识库，存储角色、设定、技能等参考信息，按需提供给对应智能体 |
| **Tool** | 工具，扩展智能体的能力（如文件读写） |

### 内置智能体

| 角色 | 职责 |
|------|------|
| **OutlineWriter** (A) | 剧本大纲编写者 — 根据用户输入和知识库，编写包含场景的大纲 |
| **ScriptWriter** (B) | 剧本编写者 — 根据大纲和知识库，将每个场景扩展为描写和对话 |
| **ScriptConverter** (C) | 脚本转换者 — 根据剧本和知识库，转换为 WebGal 引擎可执行的脚本 |

### 工作流

**PipelineWorkflow**：三阶段顺序流水线 A → B → C，每个智能体接收用户输入 + 知识库 + 前序输出，依次执行。

---

## 环境要求

- **Python** ≥ 3.12
- **包管理**: [hatch](https://hatch.pypa.io/) 或 pip
- **LLM API**: OpenAI 兼容接口（OpenAI / DeepSeek / SiliconFlow / 本地模型等）

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

### 3. 配置提供商

编辑 `configs/providers.yaml`，填入你的 API Key 和模型配置：

```yaml
defaults: &defaults
  provider: openai
  model: deepseek-ai/DeepSeek-V4-Flash
  base_url: https://api.siliconflow.cn/v1
  api_key: "sk-your-api-key-here"
  temperature: 0.7
  max_tokens: 409600
  # reasoning_effort: high       # 可选：推理深度（low/medium/high），适用于 o1/o3 等推理模型
  # extra_body:                   # 可选：透传额外请求体（如 DeepSeek thinking 模式）
  #   thinking:
  #     type: enabled

outline_writer:
  <<: *defaults
script_writer:
  <<: *defaults
script_converter:
  <<: *defaults
```

### 4. 启动服务

```bash
python -m webgal_agent
```

访问 http://127.0.0.1:8000 即可打开 Web UI。

---

## 配置说明

### 配置文件结构

```
configs/
├── default.yaml       # 默认配置（应用、LLM、工作流、记忆）
├── providers.yaml     # 智能体提供商配置（模型、API Key、参数）
└── prompts.yaml       # 智能体提示词 & 知识需求配置
```

### prompts.yaml

每个智能体可配置 `system_prompt`（系统提示词）和 `knowledge`（知识需求）：

```yaml
outline_writer:
  knowledge:
    categories: [character, setting]
  system_prompt: |
    你是一位专业的视觉小说剧本大纲编写者……

script_converter:
  knowledge:
    categories: [reference, setting]
    tags: [webgal]
  system_prompt: |
    你是一位专业的视觉小说脚本转换者……
```

`knowledge` 中的 `categories` 和 `tags` 用于控制该智能体接收哪些知识条目（并集匹配），未配置则加载全部。

### providers.yaml

每个智能体可独立配置 LLM 提供商，使用 YAML anchor 实现继承：

```yaml
defaults: &defaults
  provider: openai
  model: gpt-4o
  base_url: https://api.openai.com/v1
  api_key: "sk-..."
  temperature: 0.7
  max_tokens: 4096
  # 可选参数：
  # reasoning_effort: high     # 推理深度，适用 o1/o3/o4-mini 等推理模型
  # extra_body:                # 透传额外请求体（如 DeepSeek thinking）
  #   thinking:
  #     type: enabled

outline_writer:
  <<: *defaults       # 继承 defaults，可按需覆盖

script_converter:
  <<: *defaults
  extra_body:         # 可按智能体覆盖，如为脚本转换开启 thinking
    thinking:
      type: enabled
```

### 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--host` | `127.0.0.1` | 绑定地址 |
| `--port` | `8000` | 绑定端口 |
| `--reload` | `false` | 启用自动重载 |
| `--knowledge-dir` | `data/knowledge` | 知识库目录 |
| `--providers-path` | `configs/providers.yaml` | 提供商配置文件路径 |

---

## 知识库

知识库用于存储角色信息、世界观、技能文档等参考资料，智能体运行时按配置需求查询。

### 目录结构

```
data/knowledge/
├── characters/          # 角色信息
│   ├── 千早愛音.md
│   └── 長崎素世.md
├── settings/            # 世界设定
│   └── BanG_Dream_MyGO世界观.md
└── skills/              # 技能文档
    └── webgal_script_syntax.md
```

### 文件格式

每个知识条目是一个 Markdown 文件，顶部用 YAML Frontmatter 存储元数据：

```markdown
---
category: character
tags: [protagonist, guitarist]
title: 千早愛音
---

# 千早愛音

## 基本信息
- 年龄：16
- 学校：月之森女子学园

## 性格
开朗活泼、有点冒失……
```

**分类 (category)** 的可选值：

| 分类 | 说明 |
|------|------|
| `character` | 角色信息 |
| `setting` | 世界观设定 |
| `plot` | 剧情参考 |
| `reference` | 参考文档（如技能语法） |
| `custom` | 自定义 |

### 智能体知识需求

在 `configs/prompts.yaml` 中为每个智能体配置需要的知识类别和标签：

```yaml
outline_writer:
  knowledge:
    categories: [character, setting]    # 只接收角色和设定类知识

script_converter:
  knowledge:
    categories: [reference, setting]    # 接收参考文档和设定
    tags: [webgal]                      # 接收含 webgal 标签的知识
```

运行时，系统会根据配置自动筛选知识条目，只将相关内容注入对应智能体的上下文，避免无关信息浪费 token。

### 新增知识条目

在 `data/knowledge/` 下的任意子目录中新建 `.md` 文件即可。目录结构自由组织，`FileKnowledgeStore` 会递归扫描所有 `.md` 文件。

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/knowledge` | 列出知识条目，支持 `?category=`、`?keyword=`、`?tags=` 筛选 |
| GET | `/api/knowledge/categories` | 获取所有分类 |
| GET | `/api/knowledge/tags` | 获取所有标签 |
| GET | `/api/knowledge/agent-requirements` | 获取各智能体的知识需求配置 |
| GET | `/api/knowledge/{id}` | 获取单条知识 |
| POST | `/api/knowledge/reload` | 从磁盘重新加载知识库 |

---

## 项目结构

```
WebGalAgent/
├── pyproject.toml                  # 项目配置 & 依赖
├── configs/
│   ├── default.yaml                # 默认配置
│   ├── providers.yaml              # 智能体提供商配置
│   └── prompts.yaml                # 智能体提示词 & 知识需求
├── data/
│   └── knowledge/                  # 知识库（Markdown + Frontmatter）
│       ├── characters/
│       ├── settings/
│       └── skills/
├── src/webgal_agent/
│   ├── __init__.py
│   ├── __main__.py                 # CLI 入口（启动 Web 服务）
│   ├── core/                       # 核心抽象层
│   │   ├── agent.py                #   Agent 基类 & 状态机
│   │   ├── message.py              #   消息模型 & 消息类型
│   │   ├── workflow.py             #   Workflow 基类 & 执行结果
│   │   ├── memory.py               #   记忆抽象 & 内存实现
│   │   └── context.py              #   跨 Agent 共享上下文
│   ├── agents/                     # 具体智能体实现
│   │   ├── outline_writer.py       #   A: 剧本大纲编写
│   │   ├── script_writer.py        #   B: 章节剧本生成
│   │   └── script_converter.py     #   C: WebGal 脚本转换
│   ├── workflows/                  # 工作流模式
│   │   └── pipeline.py             #   Pipeline 顺序流水线
│   ├── knowledge/                  # 知识库
│   │   ├── models.py               #   知识条目模型 & 分类枚举
│   │   └── store.py                #   存储抽象 & 文件加载
│   ├── api/                        # FastAPI Web 层
│   │   ├── app.py                  #   应用工厂
│   │   ├── models.py               #   API 响应模型
│   │   ├── task_manager.py         #   任务管理器（编排 Agent & 知识注入）
│   │   ├── routes/                 #   REST API 路由
│   │   └── static/                 #   前端静态文件（HTML/CSS/JS）
│   ├── tools/                      # 工具扩展
│   │   ├── base.py                 #   Tool 基类
│   │   ├── file_ops.py             #   文件读写工具（ReadFile / WriteResult）
│   │   ├── asset_query.py          #   素材查询工具（按类型列出可用文件）
│   │   ├── read_model.py           #   Live2D 模型读取（提取 motions / expressions）
│   │   └── _paths.py               #   路径解析辅助
│   ├── config/                     # 配置管理
│   │   ├── settings.py             #   pydantic-settings 配置
│   │   └── provider_manager.py     #   提供商配置管理器
│   └── utils/
│       └── logging.py              #   日志配置（Rich）
└── tests/                          # 测试
    ├── conftest.py
    └── core/
        ├── test_agent.py
        ├── test_message.py
        └── test_workflow.py
```

---

## 自定义扩展

### 创建自定义智能体

继承 `Agent` 基类，实现 `system_prompt()` 和 `run()` 方法：

```python
from webgal_agent.core.agent import Agent, AgentConfig
from webgal_agent.core.message import Message, MessageType


class CustomAgent(Agent):
    def __init__(self, config: AgentConfig, system_prompt: str = "") -> None:
        super().__init__(config=config)
        self._custom_prompt = system_prompt

    def system_prompt(self) -> str:
        return self._custom_prompt or "你是一个自定义智能体。"

    async def run(self, message: Message) -> Message:
        # 接入 LLM 进行实际处理
        ...
        return message.reply(content="处理结果...", msg_type=MessageType.RESULT)
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
- **FastAPI + Uvicorn** — Web API & 服务
- **httpx** — 异步 HTTP 客户端
- **Rich** — 终端美化输出
- **pytest + pytest-asyncio** — 异步测试

---

## 许可证

MIT
