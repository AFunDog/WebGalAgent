---
category: reference
tags: [compact]
title: 角色动作与表情一览表
---

# 角色动作与表情一览表

> 使用 `read_model` 工具读取角色 model.json 可获取该角色实际可用的动作和表情列表。以下为通用名称与其含义的对照，便于根据对话情绪选择合适的参数。

## 通用动作与表情名称

格式为 `<角色名>/<名称>`，如 `anon/smile01`、`soyo/angry01`。

### 表情类（expression）

| 名称 | 情绪/含义 | 适用场景 |
|------|-----------|----------|
| `default` | 默认表情 | 初次出场、普通状态 |
| `smile01` | 微笑（轻） | 日常对话、友善回应 |
| `smile02` | 微笑（中） | 愉快交谈 |
| `smile03` | 微笑（强） | 开心的消息、幸福感 |
| `smile04` | 大笑 | 非常开心、被逗乐 |
| `angry01` | 不悦（轻） | 轻微不快、嘟囔 |
| `angry02` | 生气（中） | 被惹恼、反驳 |
| `angry03` | 愤怒（强） | 激烈争吵、大声抗议 |
| `angry04` | 暴怒 | 情绪爆发、吼叫 |
| `sad01` | 失落（轻） | 有点沮丧、心情低落 |
| `sad02` | 难过（中） | 悲伤、被伤害 |
| `sad03` | 悲伤（强） | 深受打击 |
| `sad04` | 悲痛 | 撕心裂肺 |
| `cry01` | 哭泣（轻） | 流泪、哽咽 |
| `cry02` | 哭泣（重） | 痛哭、泣不成声 |
| `surprised01` | 惊讶（轻） | 意外、愣住 |
| `surprised02` | 惊讶（重） | 震惊、目瞪口呆 |
| `serious01` | 严肃（轻） | 认真说话、谈正事 |
| `serious02` | 严肃（重） | 强硬表态、警告 |
| `shame01` | 害羞（轻） | 不好意思、脸红 |
| `shame02` | 害羞（重） | 极度羞耻、无地自容 |
| `thinking01` | 思考（轻） | 稍加思索 |
| `thinking02` | 思考（中） | 认真考虑 |
| `thinking03` | 思考（重） | 苦苦思索、困惑 |
| `kandou01` | 感动（轻） | 被触动 |
| `kandou02` | 感动（重） | 深受感动、眼角湿润 |
| `wink01` | 眨眼 | 俏皮、使眼色 |

### 动作类（motion）

| 名称 | 动作/含义 | 适用场景 |
|------|-----------|----------|
| `idle01` | 待机/默认 | 站立等待、普通姿态 |
| `nf01` ~ `nf05` | 日常动作 1~5 | 普通对话中的自然动作 |
| `nnf03` ~ `nnf05` | 稍变日常 3~5 | 略有变化的日常动作 |
| `nf_left01` | 看向左侧 | 望向左边的事物或人 |
| `nf_right01` | 看向右侧 | 望向右边的事物或人 |
| `kime01` | 帅气姿势 | 角色耍帅、摆酷 |
| `kime02` | 决心姿势 | 坚定表态、下决心 |
| `bye01` | 挥手告别 | 道别、"再见" |

> **注意**：`smile`、`angry`、`sad`、`serious`、`surprised`、`shame`、`thinking`、`kandou` 等名称既是 expression 也是 motion。编号越大情绪强度越高。

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

1. **先查询后使用**：通过 `read_model` 确认角色实际支持的 expression/motion 名称后再写入脚本
2. **频繁切换**：每 1~2 句对话切换一次 expression 或 motion，让立绘生动
3. **加 `-next`**：`changeFigure` 末尾加 `-next`，让切换不阻塞后续对话
4. **情绪递进**：同一情绪持续多句时，可从低编号递进到高编号（如 smile01 → smile02 → smile03）
