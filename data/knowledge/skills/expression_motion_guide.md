---
category: skill
tags: [kind:reference-expression-guide, audience:script-converter]
title: 角色动作与表情一览表
---

# 角色动作与表情一览表

> 使用 `read_model` 工具读取角色 model.json 可获取该角色实际可用的动作和表情列表。
> 需要角色专属的动作表情语义时，优先调用 `search_expression_motion` 按需检索 `expression_motion.json`，不要依赖把整份角色动作文档预先塞进上下文。
> 角色专属的动作表情对照、特色表情和演出建议仍保存在各角色目录下的 `expression_motion.md`，供人工维护和离线查阅：
>
> - `data/knowledge/characters/anon/expression_motion.md`
> - `data/knowledge/characters/soyo/expression_motion.md`
> - `data/knowledge/characters/rana/expression_motion.md`
> - `data/knowledge/characters/taki/expression_motion.md`
> - `data/knowledge/characters/tomori/expression_motion.md`
>
> 本文档保留“如何选择和使用动作表情”的通用规则。

## 情绪 → 推荐选择速查

| 对话情绪 | 推荐 expression | 推荐 motion |
|----------|----------------|-------------|
| 中性日常 | `default` | `idle01` / `nf01` |
| 友好交流 | `smile01` | `nf01` ~ `nf03` |
| 开心愉快 | `smile02` ~ `smile03` | `smile02` ~ `smile03` |
| 被逗笑/大笑 | `smile04` | `smile04` |
| 轻微不满 | `angry01` | `nf01` |
| 生气反驳 | `angry02` ~ `angry03` | `angry02` ~ `angry03` |
| 激烈争吵 | `angry04` | `angry04` |
| 失落沮丧 | `sad01` | `sad01` |
| 悲伤难过 | `sad02` ~ `sad03` | `sad02` ~ `sad03` |
| 崩溃哭泣 | `cry01` ~ `cry02` | `cry01` ~ `cry02` |
| 意外吃惊 | `surprised01` ~ `surprised02` | `surprised01` ~ `surprised02` |
| 认真谈话 | `serious01` | `serious01` / `nf03` |
| 强硬警告 | `serious02` | `serious02` |
| 害羞脸红 | `shame01` ~ `shame02` | `shame01` ~ `shame02` |
| 思索考虑 | `thinking01` ~ `thinking02` | `thinking01` ~ `thinking02` |
| 困惑不解 | `thinking03` | `thinking03` |
| 被感动 | `kandou01` ~ `kandou02` | `kandou01` ~ `kandou02` |
| 耍帅装酷 | `kime01` | `kime01` |
| 坚定决心 | `kime02` | `kime02` |
| 使眼色/俏皮 | `wink01` | `wink01` |
| 道别 | `smile01` / `default` | `bye01` |

## 使用守则

1. **先查询后使用**：通过 `read_model` 确认角色实际支持的 expression/motion 名称后再写入脚本。注意各角色可用列表不同（例如 `wink01` 仅爱音和素世有，`sing01`/`sing02` 仅灯有）
2. **按情绪变化切换**：优先在情绪、态度、关系变化时切换 expression 或 motion，而不是机械地每句都切
3. **频率只作兜底**：如果一段对话较长且情绪基本不变，可隔 1~2 句做一次轻微变化，避免立绘完全僵住
4. **角色特征优先**：同样是“微笑”或“生气”，不同角色应优先使用最符合其性格气质的专属表情，具体参考角色文档中的“演出使用建议”
5. **加 `-next`**：`changeFigure` 末尾加 `-next`，让切换不阻塞后续对话
6. **情绪递进**：同一情绪持续多句时，可从低强度编号逐步递进到高强度编号
7. **区分 expression 和 motion**：expression 更偏面部表情，motion 更偏身体动作和演出状态；脚本中它们用在不同位置，注意查阅语法文档
8. **角色独有表情慎用**：如灯的 `sing01`/`sing02` 仅适合演唱或情绪宣言场景，其他角色的特色表情也应结合人物性格使用
9. **跨角色复用以模型为准**：角色实际可用的动作和表情取决于其 `model.json` 文件中的列表，而非角色身份。始终以 `read_model` 工具读取到的列表为准
