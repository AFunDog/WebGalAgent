# WebGalAgent 代码结构与可维护性优化方案

最后更新: 2026-05-18

本文档只讨论“不改变程序功能”的工程优化方向，目标是提升可读性、注释质量、模块边界清晰度、测试可维护性和文档一致性。所有建议均基于当前仓库真实代码状态整理，而不是抽象模板。

## 1. 当前代码结构概览

### 1.1 顶层目录职责

- `src/webgal_agent/core/`: 智能体基类、消息模型、记忆抽象
- `src/webgal_agent/agents/`: `outline_writer` / `script_writer` / `script_converter` 三个具体智能体
- `src/webgal_agent/api/`: FastAPI 应用、任务管理器、路由
- `src/webgal_agent/browser/`: Playwright/CDP 浏览器控制、录制 CLI、录制器
- `src/webgal_agent/knowledge/`: 知识库模型与文件存储
- `src/webgal_agent/tools/`: Agent 可调用工具
- `src/frontend/`: Vue 3 前端
- `tests/`: 后端与浏览器相关测试
- `docs/`: 路线图与工程说明

### 1.2 当前结构特点

- 分层总体清晰，目录命名直接，主流程容易理解。
- 浏览器录制子系统已经从 API 进程中隔离到 CLI 子进程，边界比很多早期原型项目更明确。
- 智能体流水线顺序固定，适合维护，但“固定顺序”相关规则目前散落在 `TaskManager` 和前端视图中。
- 文档总体在补齐，但“某些模块注释很充分，某些模块几乎只靠读代码理解”的不均衡比较明显。

### 1.3 当前需要重点关注的大文件

以下文件已经明显承担了过多职责，后续应优先做“拆分但不改行为”的整理：

- `src/webgal_agent/api/task_manager.py`，约 716 行
- `src/webgal_agent/browser/screencast.py`，约 535 行
- `src/frontend/src/views/PipelineView.vue`，约 527 行
- `src/webgal_agent/browser/demo.py`，约 484 行
- `src/webgal_agent/api/routes/record.py`，约 265 行

这类文件不是“必须重写”，但已经超过单文件易读阈值。后续增加功能时，理解成本和回归风险都会继续上升。

## 2. 当前可维护性问题分析

### 2.1 模块职责偏重

#### `TaskManager`

当前同时承担了：

- 配置读取
- 提示词加载
- 知识筛选
- Agent 构建
- 任务状态管理
- 任务持久化
- 工作流步骤编排
- token 汇总

这会带来两个问题：

- 单元测试难以聚焦，很多测试只能走“大而全”的集成路径。
- 小改动容易产生连锁影响，例如修改任务落盘格式时，可能顺带影响运行流程。

#### `browser/demo.py`

当前同时承担了：

- CLI 参数定义
- 页面导航演示
- WebGal 注入逻辑
- IndexedDB 配置修改逻辑
- 页面初始化时序控制
- 录制前准备
- JSON 输出模式适配

这导致“CLI 外壳”和“页面业务脚本”耦合过深。后续如果想单独测试注入逻辑、复用录制前准备步骤，成本会偏高。

#### `browser/screencast.py`

当前同时承担了：

- Screencast 帧接收
- 临时目录管理
- 停止条件轮询
- 音频采集
- 音频诊断
- WAV 写入
- FFmpeg 参数拼装与编码

功能集中是录制器的自然结果，但目前一个类里混合了“核心流程”“诊断工具”“底层编码细节”，阅读层次不够清楚。

#### `PipelineView.vue`

当前同时承担了：

- 新任务创建
- 起始步骤和依赖输入控制
- 当前任务展示
- 步骤执行与轮询
- 步骤结果编辑
- token 展示
- 大量页面样式

它已经接近“页面组件 + 状态机 + 局部 API 协调层”的混合体。继续堆功能会直接压缩可维护性。

### 2.2 重复逻辑与散落规则

已有一些规则同时存在于多个位置：

- 流水线步骤顺序和依赖：后端 `PIPELINE_ORDER` / `AGENT_PREV_DEPS`，前端 `pipelineSteps`
- 录制参数默认值：`record.yaml`、后端 `RecordConfigRequest`、前端类型与表单
- WebGal 录制流程约束：`demo.py`、`screencast.py`、`record.py`、`README`

这种重复并不一定立刻出错，但非常容易在后续调整时产生漂移。

### 2.3 注释与文档风格不统一

当前代码里已经存在两种风格：

- 比较好的风格：模块级 docstring、关键时序注释、限制条件说明
- 不足的风格：复杂函数缺少输入输出约束说明，前端局部状态和轮询机制几乎没有结构性注释

具体表现：

- Python 后端整体 docstring 基础不错，但不是每个“复杂决策点”都有注释。
- 前端逻辑说明偏少，状态变量命名虽然直观，但读者仍需自己推断交互状态机。
- 一些关键常量背后的业务理由未被集中解释，例如页面注入依赖的符号、步骤依赖关系、任务落盘格式。

### 2.4 配置与序列化边界不够集中

几个典型问题：

- `prompts.yaml` 被 `_load_prompts()` 和 `_load_knowledge_requirements()` 各读一次。
- 任务序列化 / 反序列化逻辑主要内嵌在 `TaskManager` 所在文件中。
- 录制默认配置读取逻辑内嵌在 `record.py`。
- 前端 `api/index.ts` 中接口返回结构直接手写，缺少更细的分组与错误抽象。

这些都不是功能错误，但会让配置格式调整、数据结构扩展、接口字段重命名的代价变高。

### 2.5 测试组织仍偏薄

当前测试目录已经覆盖了核心基础模块，但对以下区域仍不够友好：

- `TaskManager` 的状态流转与磁盘恢复
- `record.py` 的子进程协议
- `demo.py` 的参数校验与 JSON 输出契约
- `PipelineView.vue` 的交互状态

如果后续做“只重构不改功能”的整理，这些位置必须先补最小保护测试，否则重构风险会被放大。

## 3. 不改变功能的优化方案

### 3.1 代码结构优化

#### A. 拆分 `TaskManager`，保留对外接口不变

建议拆成以下几个内部模块：

- `task_state.py`: `TaskInfo`、状态枚举、序列化结构
- `task_storage.py`: `_save_task_to_disk()`、`_load_tasks_from_disk()`
- `task_context.py`: prompt 和 knowledge context 构建
- `task_factory.py`: Agent 构建、工具装配
- `task_manager.py`: 只保留编排入口和状态协调

收益：

- 降低单文件复杂度
- 让序列化和执行逻辑解耦
- 更容易给“任务恢复”“知识上下文构建”单独补测试

注意：

- 对外仍保留 `TaskManager` 类，避免影响 API 路由和前端契约。

#### B. 拆分 `browser/demo.py`

建议拆成：

- `browser/cli.py` 或 `browser/demo_cli.py`: 参数解析与命令入口
- `browser/webgal_injection.py`: 页面注入脚本与等待逻辑
- `browser/game_config.py`: IndexedDB 配置读写与回读验证
- `browser/record_session.py`: 录制前准备流程

收益：

- 让“CLI 壳层”和“浏览器行为逻辑”分离
- 更容易围绕注入脚本写局部验证
- 降低对长字符串 `page.evaluate("""...""")` 的阅读压力

#### C. 细化 `screencast.py`

建议按职责拆为：

- `screencast.py`: `ScreencastRecorder` 主流程
- `audio_capture.py`: PCM 拉取、WAV 写入、音频诊断
- `ffmpeg_encoder.py`: 输出格式与 FFmpeg 参数构造

如果暂时不想拆文件，至少先做类内私有方法分组和区域注释标准化。

#### D. 拆分 `PipelineView.vue`

建议拆成以下组件或 composable：

- `TaskCreatePanel.vue`
- `PipelineStepList.vue`
- `PipelineStepEditor.vue`
- `usePipelineTask.ts`

收益：

- 页面结构更接近设计语义
- 轮询、编辑、创建任务逻辑可以拆开测试
- 避免一个 SFC 同时承载模板、状态、样式和 API 编排

### 3.2 注释与文档优化

#### A. 建立统一注释标准

建议在仓库内统一以下原则：

- 模块级 docstring 说明“职责、边界、不做什么”
- 复杂函数 docstring 说明“输入、输出、关键约束”
- 非显而易见的时序逻辑前加 1 行短注释
- 避免描述性废话注释，如“给变量赋值”

适合补注释的高价值位置：

- `TaskManager` 的状态流转和落盘时机
- `demo.py` 中 `changeScene -> game_config -> toggleAuto -> hideInfo` 的时序原因
- `screencast.py` 中停止条件轮询和音频拉取并发策略
- 前端页面中的轮询生命周期与“跳步执行”依赖规则

#### B. 补充“架构说明型”文档，而不是只写接口说明

建议新增或维护以下文档：

- `docs/architecture-overview.md`: 后端、前端、browser 三大子系统边界
- `docs/task-pipeline.md`: 流水线步骤、依赖、任务状态、落盘格式
- `docs/recording-flow.md`: 录制前准备、注入、screencast、音频、子进程协议

这样能减少“必须打开 4 个源码文件才知道真实流程”的情况。

#### C. 将关键隐式约束转成显式清单

例如：

- `--duration 0` 必须配合 `--stop-on`
- `selector=auto` 先尝试 `#root` 再尝试 `canvas`
- `saveConfig()` 后不可立即访问同一 IndexedDB store
- Windows event loop policy 只能放入口点

这些规则现在分散在代码、README、AGENTS 中，建议集中成“约束清单”文档并在相关模块头部引用。

### 3.3 配置与常量整理

#### A. 集中定义工作流元数据

把下面这些内容合并到单个定义模块中：

- `PIPELINE_ORDER`
- agent 展示名 / 描述
- 前序依赖
- 前端页面的步骤标签

理想形式：

- 后端提供唯一结构化定义
- 前端直接消费 `/workflows/pipeline` 的步骤元信息，而不是重复写一份常量

如果暂时不动接口，也建议先在后端内部形成统一 `PipelineDefinition` 数据结构。

#### B. 合并 prompts 配置加载

当前 `prompts.yaml` 被读取两次，建议改为一次读取后拆分使用：

- `PromptConfigRepository`
- 或单个 `_load_prompt_config()` 返回结构化对象

收益：

- 减少重复 IO 与解析逻辑
- 减少同一个 YAML schema 在多个函数里各自解释

#### C. 收敛录制配置模型

建议统一以下来源：

- `src/configs/record.yaml`
- `RecordConfigRequest`
- 前端 `RecordConfig` 类型
- CLI 参数默认值

目标不是立刻“一个定义生成全部”，而是至少建立“谁是默认值来源、谁是传输契约来源”的明确规则。

### 3.4 前端可维护性优化

#### A. 抽象通用请求层

`src/frontend/src/api/index.ts` 当前是单文件集中导出，短期可用，但建议后续拆成：

- `api/request.ts`
- `api/tasks.ts`
- `api/providers.ts`
- `api/record.ts`
- `api/knowledge.ts`

并补充：

- 统一错误对象转换
- 请求超时
- 轮询辅助函数

#### B. 页面状态逻辑转为 composable

尤其适合抽离：

- 当前任务轮询
- 步骤编辑状态
- 起始步骤与依赖输入映射

这样能把“页面怎么渲染”和“任务状态怎么流转”分开。

#### C. 降低内联样式占比

`PipelineView.vue` 中存在大量内联 `style`。这不影响功能，但会让：

- 样式难复用
- 视觉调整时搜索成本高
- 结构和样式耦合过深

建议迁移到具名 class，并在组件内保留少量确有必要的动态样式。

### 3.5 测试与重构护栏

在做结构整理前，建议先补以下“最小保护测试”：

- `TaskManager.start_task / run_step / cancel_task / load_from_disk`
- `record.py` 的 `_build_cli_args()`
- `demo.py` 对 `duration=0` 和 `stop_condition` 的约束
- `PipelineView` 的跳步创建、轮询停止、步骤编辑

建议原则：

- 先补契约测试，再做文件拆分
- 先锁住序列化格式，再抽离存储模块
- 先锁住 CLI 参数协议，再抽离浏览器录制准备逻辑

## 4. 分阶段执行建议

### 第一阶段：低风险整理

- 统一注释风格和模块头部说明
- 合并重复的配置读取逻辑
- 提取常量、类型别名、序列化辅助函数
- 为大文件增加清晰的区域分段注释
- 补充架构型文档

这一阶段几乎不改调用关系，最适合先做。

### 第二阶段：文件级拆分

- 拆 `TaskManager`
- 拆 `demo.py`
- 拆 `PipelineView.vue`
- 提取前端 API 请求层

这一阶段仍可做到“行为不变”，但必须在已有测试保护下进行。

### 第三阶段：约束统一化

- 建立统一工作流定义源
- 建立统一录制配置定义源
- 建立统一错误结构与日志字段

这一阶段仍以工程整理为主，但会开始改善模块间协作体验。

## 5. 建议优先级

### P0: 立即可做，收益高、风险低

- 为 `TaskManager`、`demo.py`、`screencast.py`、`PipelineView.vue` 增加结构性注释
- 抽取重复常量和配置读取
- 为流程与录制链路补架构文档
- 为重构前的关键路径补最小测试

### P1: 下一轮维护时做

- 按职责拆 `TaskManager`
- 抽离 WebGal 注入与游戏配置逻辑
- 拆分前端页面与 composable
- 收敛 API 请求层

### P2: 中期演进

- 统一工作流定义与前后端步骤元数据
- 统一录制配置默认值与传输模型
- 建立更明确的错误码、日志字段、序列化协议

## 6. 一个务实的落地顺序

建议按这个顺序推进，能最大限度降低“整理代码时顺手改坏功能”的风险：

1. 先补测试，锁住任务流、录制 CLI 协议、前端关键交互。
2. 再补文档和注释，让重构目标先被说清楚。
3. 然后做内部提取，先提函数、常量、类型，不急着拆 API。
4. 最后再做文件拆分和前后端定义统一。

## 7. 总结

这个项目的基础结构并不混乱，真正的问题不是“需要推倒重来”，而是几个核心文件已经承担了过多上下文，继续在原位叠加功能会越来越难维护。

因此最值得做的不是大改业务逻辑，而是：

- 先把隐式规则写清楚
- 先把大文件拆出明确边界
- 先给重构补测试护栏
- 再逐步统一前后端和录制链路中的重复定义

这样可以在不改变程序功能的前提下，显著降低后续开发、排障和协作成本。
