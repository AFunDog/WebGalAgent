---
category: reference
tags: [webgal, compact]
title: 动画演出效果配方
---

# 动画演出效果配方

> 本文档提供按情绪/场景分类的 `setTempAnimation` 和 `setTransform` 预制效果模板。
> 转换脚本时，根据剧本描写中的情绪和场景选用或组合这些效果，为脚本增添生动的演出。

## 通用规则

1. **滤镜参数必须用数字**：`-transform={}`、`setTempAnimation`、`setTransform` 的 JSON 中，所有滤镜参数值必须是 `0`~`1` 的数字，**严禁使用布尔值 `true`/`false`**。
   - 正确：`"vignetting":1`、`"oldFilm":0.5`、`"glitchFilm":0`
   - 错误：`"vignetting":true`、`"oldFilm":false`
   - 不需要的滤镜直接不写，不要写成 `false` 或 `0`
2. **优先内联 transform**：需要为背景或立绘添加滤镜时，优先在 `changeBg`/`changeFigure` 中用 `-transform={}` 内联添加，而非单独使用 `setTransform`。若首次出现的立绘/背景未添加滤镜，后续需先关闭再重建（带新滤镜）
3. **-target 可选值**：`fig-left`、`fig-center`、`fig-right`、`bg-main`、`stage-main`、或自定义立绘 `id`

---

## 一、氛围/环境类

### 1.1 柔光暖色（温馨日常）

适用：温暖的家庭场景、朋友聚会、日常闲聊

```
changeBg:背景.jpg -next -transform={"brightness":0.85,"contrast":0.9,"saturation":0.85,"colorRed":255,"colorGreen":235,"colorBlue":210,"bloom":0.6,"bloomBrightness":0.8,"bloomBlur":12};
```

立绘同理：
```
changeFigure:角色/model.json -id=角色id -transform={"brightness":0.7,"contrast":1.1,"saturation":0.9,"colorRed":255,"colorGreen":234,"colorBlue":217,"bloom":0.4,"bloomBrightness":0.9,"bloomBlur":10} -motion=角色/表情 -expression=角色/表情 -next;
```

### 1.2 冷色调（忧郁/孤独）

适用：独处、雨天、内心独白、冷清场景

```
changeBg:背景.jpg -next -transform={"brightness":0.7,"contrast":1.1,"saturation":0.6,"colorRed":180,"colorGreen":200,"colorBlue":230};
```

### 1.3 黄昏暖阳

适用：夕阳、放学、回忆

```
changeBg:背景.jpg -next -transform={"brightness":0.8,"contrast":0.95,"saturation":0.9,"colorRed":255,"colorGreen":210,"colorBlue":160,"bloom":0.5,"bloomBrightness":0.8,"bloomBlur":15};
```

### 1.4 夜晚/月色

适用：深夜、月光、安静

```
changeBg:背景.jpg -next -transform={"brightness":0.5,"contrast":1.1,"saturation":0.5,"colorRed":160,"colorGreen":180,"colorBlue":220,"bloom":0.3,"bloomBrightness":0.6,"bloomBlur":10};
```

### 1.5 赛博朋克/电子故障

适用：受到干扰、电子画面、内心崩坏

```
setTransform:{"glitchFilm":1,"rgbFilm":1,"oldFilm":0.5,"colorRed":200,"colorGreen":255,"colorBlue":255,"brightness":1.2} -target=bg-main -duration=0;
```

### 1.6 复古黑白电视/监控画面

适用：查看监控、老电视、过去的时间线

```
setTransform:{"oldFilm":1,"vignetting":1,"vignettingAlpha":0.8,"saturation":0,"contrast":1.5} -target=bg-main -duration=0;
```

---

## 二、情绪/心理类（setTempAnimation）

### 2.1 闪光弹/记忆涌现

适用：回忆闪回、重要记忆浮现

```
setTempAnimation:[{"duration":0},{"brightness":2,"contrast":0,"duration":200,"ease":"circIn"},{"brightness":1,"contrast":1,"duration":200},{"brightness":2,"contrast":0,"duration":200,"ease":"circIn"},{"brightness":1,"contrast":1,"duration":2500}] -target=bg-main -next;
```

### 2.2 缓慢推近（Slow Zoom In）

适用：制造压迫感、聚焦关键信息、紧张

```
setTempAnimation:[{"duration":0,"scale":{"x":1,"y":1}},{"duration":3000,"scale":{"x":1.2,"y":1.2}}] -target=bg-main;
```

### 2.3 快速拉远（Quick Zoom Out）

适用：揭示全景、惊讶、视角突然放开

```
setTempAnimation:[{"duration":0,"scale":{"x":1.3,"y":1.3}},{"duration":400,"scale":{"x":1.0,"y":1.0}}] -target=bg-main -next;
```

### 2.4 荷兰式倾斜（Dutch Angle）

适用：不安、疯狂、失衡

```
setTempAnimation:[{"duration":0,"rotation":0,"scale":{"x":1.2,"y":1.2}},{"duration":2000,"rotation":0.1}] -target=bg-main;
```

### 2.5 急剧对焦（Re-Focus）

适用：从模糊到清晰、恍然大悟

```
setTempAnimation:[{"duration":0,"blur":30},{"duration":800,"blur":0}] -target=bg-main -next;
```

### 2.6 惊恐心跳（Heartbeat）

适用：恐惧、紧张、遇到危险、心动

```
setTempAnimation:[{"duration":0,"scale":{"x":1,"y":1},"colorGreen":255,"colorBlue":255},{"duration":100,"scale":{"x":1.05,"y":1.05},"colorGreen":200,"colorBlue":200},{"duration":300,"scale":{"x":1,"y":1},"colorGreen":255,"colorBlue":255}] -target=bg-main;
```

### 2.7 闪回白光（Bright Flashback）

适用：记忆涌现、强烈冲击

```
setTempAnimation:[{"duration":0,"brightness":1,"blur":0},{"duration":200,"brightness":5,"blur":10},{"duration":1500,"brightness":1,"blur":0}] -target=bg-main -next;
```

### 2.8 灰暗绝望（Despair/Grey）

适用：失去希望、悲伤、绝望

```
setTempAnimation:[{"duration":0,"saturation":1},{"duration":2000,"saturation":0,"brightness":0.8}] -target=bg-main;
```

### 2.9 愤怒爆发（Rage）

适用：愤怒、激烈争吵

```
setTempAnimation:[{"duration":0,"colorGreen":255,"colorBlue":255},{"duration":200,"colorGreen":100,"colorBlue":100,"position":{"x":10,"y":10}},{"duration":200,"position":{"x":-10,"y":-10}},{"duration":200,"position":{"x":0,"y":0}}] -target=bg-main;
```

### 2.10 中毒/眩晕（Poisoned）

适用：眩晕、中毒、意识模糊

```
setTempAnimation:[{"duration":0,"colorRed":255,"colorGreen":255,"colorBlue":255,"blur":0},{"duration":1000,"colorRed":200,"colorGreen":100,"colorBlue":255,"blur":5},{"duration":1000,"colorRed":255,"colorGreen":255,"colorBlue":255,"blur":0}] -target=bg-main;
```

### 2.11 冰冻/寒冷（Freezing）

适用：寒冷、恐惧中的僵硬

```
setTempAnimation:[{"duration":0,"colorRed":255,"colorGreen":255,"contrast":1},{"duration":1000,"colorRed":150,"colorGreen":200,"contrast":1.2}] -target=bg-main;
```

### 2.12 警报/红光闪烁（Alarm）

适用：紧急情况、危险警告

```
setTempAnimation:[{"duration":0,"colorGreen":255,"colorBlue":255},{"duration":500,"colorGreen":100,"colorBlue":100},{"duration":500,"colorGreen":255,"colorBlue":255}] -target=bg-main;
```

### 2.13 眨眼（Blinking）

适用：瞬间黑屏再恢复、转场

```
setTempAnimation:[{"duration":0,"brightness":1},{"duration":100,"brightness":0},{"duration":50,"brightness":0},{"duration":100,"brightness":1}] -target=bg-main -next;
```

### 2.14 昏昏欲睡（Drowsy）

适用：困倦、意识模糊后惊醒

```
setTempAnimation:[{"duration":0,"brightness":1,"blur":0},{"duration":3000,"brightness":0.5,"blur":10},{"duration":200,"brightness":1,"blur":0}] -target=bg-main -next;
```

### 2.15 灵感/发现（Idea）

适用：恍然大悟、灵光一闪

```
setTempAnimation:[{"duration":0,"brightness":1},{"duration":100,"brightness":1.5},{"duration":300,"brightness":1}] -target=bg-main;
```

### 2.16 打雷（Thunder）

适用：雷声、快速闪光

```
setTempAnimation:[{"duration":0,"brightness":1},{"duration":50,"brightness":3},{"duration":50,"brightness":1},{"duration":50,"brightness":1.5},{"duration":50,"brightness":1}] -target=bg-main;
```

### 2.17 呼吸缩放（Breathing Zoom）

适用：增加静态演出的动态感，长对话不显枯燥。5秒周期

```
setTempAnimation:[{"duration":0,"scale":{"x":1,"y":1}},{"duration":2500,"scale":{"x":1.05,"y":1.05}},{"duration":2500,"scale":{"x":1,"y":1}}] -target=bg-main;
```

### 2.18 紧张心跳暗角（Tense Vignetting）

适用：恐惧、紧张、心动时视线收窄

```
setTempAnimation:[{"duration":0,"vignetting":1,"vignettingAlpha":0,"colorRed":255,"colorGreen":255,"colorBlue":255},{"duration":200,"vignettingAlpha":0.6,"colorRed":255,"colorGreen":200,"colorBlue":200},{"duration":1000,"vignettingAlpha":0,"colorRed":255,"colorGreen":255,"colorBlue":255}] -target=bg-main -next;
```

---

## 三、冲击/特效类（setTransform）

### 3.1 受伤/濒死/强烈冲击

适用：受到攻击、地震、极度恐惧

```
setTransform:{"shakePower":20,"shakeSpeed":5,"colorRed":255,"colorGreen":150,"colorBlue":150,"vignetting":1,"vignettingAlpha":0.5} -target=bg-main -duration=300;
```

### 3.2 去饱和（回忆/梦境）

适用：回忆场景、梦境、失去活力的场景。结束时要恢复 `saturation:1`

```
setTransform:{"saturation":0,"brightness":0.85} -target=bg-main -duration=1000;
```

恢复：
```
setTransform:{"saturation":1,"brightness":1} -target=bg-main -duration=1000;
```

---

## 四、使用策略

### 4.1 情绪 → 效果速查

| 剧本情绪 | 推荐效果 | 作用目标 |
|----------|----------|----------|
| 温馨日常 | 柔光暖色滤镜 | bg-main（-transform 内联） |
| 孤独忧郁 | 冷色调滤镜 | bg-main（-transform 内联） |
| 夕阳回忆 | 黄昏暖阳滤镜 | bg-main（-transform 内联） |
| 深夜安静 | 夜晚月色滤镜 | bg-main（-transform 内联） |
| 记忆涌现 | 闪光弹 / 闪回白光 | bg-main |
| 紧张压迫 | 缓慢推近 / 呼吸缩放 | bg-main |
| 恐惧心跳 | 心跳 / 紧张暗角 | bg-main |
| 愤怒爆发 | 愤怒 Rage / 红光闪烁 | bg-main |
| 绝望悲伤 | 灰暗绝望 / 去饱和 | bg-main |
| 惊讶震惊 | 快速拉远 / 急剧对焦 | bg-main |
| 眩晕模糊 | 中毒眩晕 / 昏昏欲睡 | bg-main |
| 恍然大悟 | 灵感发现 / 急剧对焦 | bg-main |
| 不安失衡 | 荷兰式倾斜 | bg-main |
| 紧急危险 | 警报红光 / 打雷 | bg-main |
| 受伤冲击 | 冲击震动 | bg-main |
| 回忆/梦境 | 去饱和 / 复古黑白 | bg-main |

### 4.2 使用原则

1. **每个场景开头**：用 `-transform` 内联设置背景滤镜奠定氛围
2. **情绪转折处**：用 `setTempAnimation` 制造动态演出效果
3. **效果不要堆叠**：同一时刻只对一个目标使用一种动态动画效果
4. **适时恢复**：使用去饱和、倾斜等持续效果后，必须在场景结束或情绪转变时恢复（`saturation:1`、`rotation:0`、`brightness:1` 等）
5. **灵活组合**：以上模板是起点，应根据具体剧本文本调整参数（时长、强度、颜色等），不必拘泥于固定数值
