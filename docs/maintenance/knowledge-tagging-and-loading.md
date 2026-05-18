# 知识库标签与加载约定

最后更新: 2026-05-18

本文档说明 WebGalAgent 当前如何从 `data/knowledge/` 读取知识、如何根据 `prompts.yaml` 将知识分发给不同智能体，以及角色知识当前推荐的两层拆分方式。

## 目标

这份约定主要解决两个问题：

1. 避免前序智能体拿到过细的后期演出知识。
2. 避免知识文件拆分后，后续维护者不清楚应该给哪个文件打什么标签。

## 当前加载链路

### 1. 磁盘文件 -> KnowledgeEntry

应用启动时会初始化 `FileKnowledgeStore`，入口在：

- `src/webgal_agent/api/app.py`

实际加载逻辑在：

- `src/webgal_agent/knowledge/store.py`

行为规则如下：

- 递归扫描 `data/knowledge/**/*.md`
- 每个 `.md` 文件都会被加载为一条独立 `KnowledgeEntry`
- frontmatter 中的 `category`、`tags`、`title` 会被解析
- Markdown 正文作为 `body`
- 相对路径作为 `source`

注意：

- 目录本身不会成为知识条目
- 同一角色目录下的多个文件会被视为多条独立知识，而不是自动合并

### 2. prompts.yaml -> 知识筛选条件

`TaskManager` 初始化时会读取：

- `src/configs/prompts.yaml`

通过：

- `src/webgal_agent/config/prompt_config.py`

提取每个智能体的：

- `categories`
- `tags`

这些配置决定每个智能体会看到哪些知识条目。

### 3. 筛选 -> 拼接为知识上下文

知识上下文构建逻辑在：

- `src/webgal_agent/api/task_context.py`

当前筛选规则是：

- 先按 `category` 查询
- 再按 `tags` 查询
- 最后合并去重

这是**并集**逻辑，不是交集逻辑。

换句话说：

- 只要命中指定 `category`
- 或命中指定 `tags`

就会进入该智能体的知识上下文。

## 当前角色知识的两层拆分

角色知识目前推荐拆成两层：

### 第一层：角色信息

文件名：

- `profile.md`

建议承载内容：

- 基本信息
- 性格
- 背景
- 外貌
- 喜好
- 人际关系
- 写作提示

用途：

- 供 `outline_writer`
- 供 `script_writer`

这层的重点是：

- 帮助前序智能体理解人物设定
- 帮助剧本生成保持角色行为与关系一致

### 第二层：角色立绘表情动作

文件名：

- `expression_motion.md`

建议承载内容：

- expression 列表
- motion 列表
- 立绘演出建议
- 表情切换节奏建议

用途：

- 供 `script_converter`

这层的重点是：

- 指导脚本转换阶段选择立绘动作和表情
- 支持更稳定的 WebGal 演出生成

## 当前推荐标签

### profile.md

推荐 frontmatter：

```yaml
category: character
tags: [character-profile]
```

说明：

- `category: character` 表示角色知识
- `character-profile` 用来标记“可供前序写作智能体消费的角色信息”

### expression_motion.md

推荐 frontmatter：

```yaml
category: character
tags: [character-expression, compact]
```

说明：

- `character-expression` 表示这是立绘表情动作知识
- `compact` 表示内容适合直接进入 `script_converter` 的紧凑型参考上下文

## 当前 prompts.yaml 的知识取用策略

当前配置如下：

### outline_writer

- `categories: [setting]`
- `tags: [character-profile]`

这意味着它会读取：

- 所有 `setting` 类知识
- 所有带 `character-profile` 标签的角色信息文件

它不会因为角色目录存在就自动拿到 `expression_motion.md`。

### script_writer

- `categories: [setting]`
- `tags: [character-profile]`

含义与 `outline_writer` 相同。

这一步的目标是：

- 让剧本编写看到角色设定与关系
- 但不要提前接触表情动作层知识

### script_converter

- `categories: [setting]`
- `tags: [compact, character-expression]`

这意味着它会读取：

- 所有 `setting` 类知识
- 所有带 `compact` 标签的紧凑参考
- 所有带 `character-expression` 标签的角色立绘动作知识

这一步的目标是：

- 保留 WebGal 语法和动画配方
- 额外补充角色立绘表情动作信息

## 维护规则

### 1. 不要把角色演出知识写回 profile.md

如果某条内容主要服务于：

- 表情切换
- motion 选择
- 立绘演出节奏
- 镜头或立绘强弱控制

它就应该进入 `expression_motion.md`，而不是 `profile.md`。

### 2. 不要把剧情设定型信息写进 expression_motion.md

如果某条内容主要服务于：

- 性格理解
- 人际关系
- 角色背景
- 对话风格

它就应该进入 `profile.md`。

### 3. 谨慎使用 `compact`

当前筛选逻辑是并集，因此 `compact` 的影响很大。

如果某个文件被打上 `compact`：

- `script_converter` 很可能会直接看到它

因此：

- `profile.md` 默认不要打 `compact`
- 只有明确想喂给 `script_converter` 的知识才打 `compact`

### 4. 新增角色时优先补齐两层文件

新增角色时，推荐最少创建：

- `data/knowledge/characters/<角色名>/profile.md`
- `data/knowledge/characters/<角色名>/expression_motion.md`

即使资料不完整，也先建立骨架，后续再补充。

## 推荐目录结构

```text
data/knowledge/characters/
  千早爱音/
    profile.md
    expression_motion.md
  长崎素世/
    profile.md
    expression_motion.md
  要乐奈/
    profile.md
    expression_motion.md
```

## 结论

当前知识库的核心原则不是“按目录读取”，而是：

- 每个 Markdown 文件是独立知识条目
- 标签和类别决定它最终被谁看到

角色知识当前推荐长期保持两层：

- `profile.md` 负责人物信息
- `expression_motion.md` 负责立绘表情动作信息

如果后续继续细分知识，也应优先围绕“哪类智能体需要这份知识”来拆，而不是只按文件大小或人工阅读习惯拆。
