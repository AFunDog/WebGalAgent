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

## 当前推荐标签体系

当前建议把标签分成两种前缀：

- `kind:*`
  说明“这份知识是什么类型”
- `audience:*`
  说明“这份知识应该主要给谁看”

可选再补：

- `topic:*`
  说明知识主题
- `franchise:*`
  说明作品或 IP 归属

这个命名方式的目标是：

- 看到标签名就能猜到用途
- 不再依赖 `compact` 这类语义过于隐含的旧名字

### profile.md

推荐 frontmatter：

```yaml
category: character
tags: [kind:character-profile, audience:story-writer]
```

说明：

- `category: character` 表示角色知识
- `kind:character-profile` 表示这是角色设定信息
- `audience:story-writer` 表示它主要服务于前序写作智能体

### expression_motion.md

推荐 frontmatter：

```yaml
category: character
tags: [kind:character-expression, audience:script-converter]
```

说明：

- `kind:character-expression` 表示这是立绘表情动作知识
- `audience:script-converter` 表示它主要服务于脚本转换智能体

### 其他常见知识文件

推荐示例：

```yaml
category: reference
tags: [kind:reference-webgal-syntax, topic:webgal, audience:script-converter]
```

```yaml
category: reference
tags: [kind:reference-animation-recipes, topic:webgal, topic:animation, audience:script-converter]
```

```yaml
category: setting
tags: [kind:setting-world, franchise:bang-dream, topic:music, audience:story-writer, audience:script-converter]
```

## 当前 prompts.yaml 的知识取用策略

当前配置如下：

### outline_writer

- `tags: [audience:story-writer]`

这意味着它会读取：

- 所有带 `audience:story-writer` 标签的知识文件

它不会因为角色目录存在就自动拿到 `expression_motion.md`。

### script_writer

- `tags: [audience:story-writer]`

含义与 `outline_writer` 相同。

这一步的目标是：

- 让剧本编写看到角色设定与关系
- 但不要提前接触表情动作层知识

### script_converter

- `tags: [audience:script-converter]`

这意味着它会读取：

- 所有带 `audience:script-converter` 标签的知识文件

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

### 3. audience 标签优先决定知识去向

当前筛选逻辑是并集，因此标签一旦命中，就会进入该智能体上下文。

因此建议把“给谁看”这件事显式写进标签：

- `audience:story-writer`
- `audience:script-converter`

不要再依赖模糊语义标签去间接表达知识去向。

经验规则：

- `profile.md` 默认只打 `audience:story-writer`
- `expression_motion.md` 默认只打 `audience:script-converter`
- 同时需要两边消费的知识，再同时打两个 `audience:*`

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
