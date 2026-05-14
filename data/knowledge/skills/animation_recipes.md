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

> 以下配方均提供**背景**和**人物**两行 `setTransform`，需同时使用以保持画面一致。
> 人物的 `-target` 需根据实际立绘位置替换为 `fig-left`、`fig-center`、`fig-right` 或自定义 `-id`。
> `bevel`（边缘光/倒角滤镜）的 `bevelRotation` 需根据实际光源调整（约80为居中）。
> 优先用 `-transform={}` 内联在 `changeBg`/`changeFigure` 中，而非单独 `setTransform`。

### 1.1 白天室外晴天

适用：晴天户外、学校操场、街道

背景：
```
setTransform:{"brightness":0.8,"contrast":0.8,"saturation":0.7,"gamma":0.5,"colorRed":227,"colorGreen":227,"colorBlue":227,"bloom":0.7,"bloomBrightness":1,"bloomBlur":10} -target=bg-main -duration=0 -next;
```
人物：
```
setTransform:{"brightness":0.75,"contrast":1,"saturation":0.8,"gamma":0.7,"colorRed":255,"colorGreen":255,"colorBlue":255,"bloom":0.5,"bloomBrightness":0.85,"bloomBlur":4,"bevel":0.5,"bevelThickness":8,"bevelRotation":30,"bevelRed":196,"bevelGreen":185,"bevelBlue":185} -target=fig-center -duration=0;
```

### 1.2 白天（通用）

适用：室内白天、日常场景

背景：
```
setTransform:{"brightness":0.7,"contrast":1.1,"saturation":0.8,"gamma":0.5,"colorRed":255,"colorGreen":255,"colorBlue":255,"bloom":0.5,"bloomBrightness":0.8,"bloomBlur":10} -target=bg-main -duration=0 -next;
```
人物：
```
setTransform:{"brightness":0.6,"contrast":1.1,"saturation":0.8,"gamma":0.6,"colorRed":255,"colorGreen":255,"colorBlue":255,"bloom":0.7,"bloomBrightness":0.6,"bloomBlur":10,"bevel":1,"bevelThickness":18,"bevelRotation":30,"bevelRed":255,"bevelGreen":255,"bevelBlue":255} -target=fig-center -duration=0;
```

### 1.3 清爽版室内白天

适用：明亮的室内、教室、活动室

背景：
```
setTransform:{"brightness":0.7,"contrast":1.1,"saturation":0.8,"gamma":0.5,"colorRed":255,"colorGreen":255,"colorBlue":255,"bloom":0.5,"bloomBrightness":1,"bloomBlur":10} -target=bg-main -duration=0 -next;
```
人物：
```
setTransform:{"brightness":0.6,"contrast":1.1,"saturation":0.9,"gamma":0.9,"colorRed":255,"colorGreen":234,"colorBlue":217,"bloom":0.7,"bloomBrightness":1,"bloomBlur":2,"bevel":1,"bevelThickness":4,"bevelRotation":30,"bevelRed":255,"bevelGreen":238,"bevelBlue":224} -target=fig-center -duration=0;
```

### 1.4 清晨/黄昏（轻）

适用：清晨、傍晚的柔和光线、回忆

背景：
```
setTransform:{"brightness":0.7,"contrast":0.8,"saturation":0.7,"gamma":0.5,"colorRed":255,"colorGreen":234,"colorBlue":214,"bloom":1,"bloomBrightness":0.7,"bloomBlur":10} -target=bg-main -duration=0 -next;
```
人物：
```
setTransform:{"brightness":0.6,"contrast":1.1,"saturation":0.9,"gamma":0.9,"colorRed":255,"colorGreen":234,"colorBlue":217,"bloom":0.4,"bloomBrightness":0.9,"bloomBlur":10,"bevel":1,"bevelThickness":10,"bevelRotation":30,"bevelRed":255,"bevelGreen":238,"bevelBlue":224} -target=fig-center -duration=0;
```

### 1.5 黄昏(重)（室外）

适用：夕阳强烈的室外、天空被染橙

背景：
```
setTransform:{"brightness":0.9,"contrast":0.8,"saturation":0.7,"gamma":0.5,"colorRed":255,"colorGreen":205,"colorBlue":171,"bloom":0.7,"bloomBrightness":0.8,"bloomBlur":10} -target=bg-main -duration=0 -next;
```
人物：
```
setTransform:{"brightness":0.4,"contrast":1.2,"saturation":0.7,"gamma":0.8,"colorRed":255,"colorGreen":213,"colorBlue":176,"bloom":0.5,"bloomBlur":10,"bevel":1,"bevelThickness":18,"bevelRotation":30,"bevelRed":255,"bevelGreen":204,"bevelBlue":148} -target=fig-center -duration=0;
```

### 1.6 黄昏(重)（室内）

适用：夕阳透窗的室内、暖橙色氛围

背景：
```
setTransform:{"brightness":0.9,"contrast":0.8,"saturation":0.7,"gamma":0.5,"colorRed":255,"colorGreen":203,"colorBlue":171,"bloom":0.7,"bloomBrightness":0.9,"bloomBlur":10} -target=bg-main -duration=0 -next;
```
人物：
```
setTransform:{"brightness":0.5,"contrast":1.2,"saturation":0.7,"gamma":0.8,"colorRed":255,"colorGreen":208,"colorBlue":176,"bloom":0.5,"bloomBlur":10,"bevel":1,"bevelThickness":18,"bevelRotation":30,"bevelRed":255,"bevelGreen":184,"bevelBlue":148} -target=fig-center -duration=0;
```

### 1.7 淡色黄昏

适用：柔和黄昏、略带怀旧的温暖氛围

背景：特写用高斯模糊20，大场景用高斯模糊5（附加 `blur` 参数）
人物：
```
setTransform:{"brightness":1,"contrast":1,"saturation":1.5,"colorRed":255,"colorGreen":251,"colorBlue":217,"bloomThreshold":10,"bevel":1,"bevelThickness":15,"bevelSoftness":1,"bevelRed":253,"bevelGreen":255,"bevelBlue":181} -target=fig-center -duration=0;
```

### 1.8 室内有光暖色

适用：暖色灯光室内、温馨房间

人物：
```
setTransform:{"brightness":0.75,"contrast":1.1,"saturation":0.8,"gamma":1,"colorRed":255,"colorGreen":234,"colorBlue":217,"bloom":0.6,"bloomBrightness":0.7,"bloomBlur":1,"bevel":2,"bevelThickness":5,"bevelRotation":80,"bevelRed":255,"bevelGreen":201,"bevelBlue":125} -target=fig-center -duration=0;
```
背景：
```
setTransform:{"brightness":0.9,"contrast":0.8,"saturation":0.5,"gamma":0.6,"colorRed":255,"colorGreen":218,"colorBlue":184,"bloom":1,"bloomBrightness":0.8,"bloomBlur":2,"bevelRed":255,"bevelGreen":194,"bevelBlue":125} -target=bg-main -duration=0;
```

### 1.9 夜晚室内白光

适用：夜间开灯的室内、冷白灯光

人物：
```
setTransform:{"brightness":0.6,"contrast":1.1,"saturation":0.9,"gamma":0.9,"colorRed":255,"colorGreen":255,"colorBlue":255,"bloom":0.5,"bloomBrightness":1,"bloomBlur":2,"bevel":1,"bevelThickness":8,"bevelRotation":30,"bevelRed":204,"bevelGreen":204,"bevelBlue":204} -target=fig-center -duration=0;
```
背景：
```
setTransform:{"brightness":0.7,"contrast":0.8,"saturation":0.7,"gamma":0.5,"colorRed":255,"colorGreen":255,"colorBlue":255,"bloom":1,"bloomBrightness":1,"bloomBlur":2} -target=bg-main -duration=500;
```

### 1.10 黑暗（有灯光）

适用：夜间有光源的场景、路灯下、台灯旁

背景：
```
setTransform:{"brightness":0.7,"contrast":0.8,"saturation":0.7,"gamma":0.5,"colorRed":255,"colorGreen":255,"colorBlue":255,"bloom":1,"bloomBrightness":0.7,"bloomBlur":10} -target=bg-main -duration=0 -next;
```
人物：
```
setTransform:{"brightness":0.6,"contrast":1.1,"saturation":0.9,"gamma":0.9,"colorRed":255,"colorGreen":255,"colorBlue":255,"bloom":0.2,"bloomBrightness":0.9,"bloomBlur":10,"bevel":1,"bevelThickness":18,"bevelRotation":30,"bevelRed":204,"bevelGreen":204,"bevelBlue":204} -target=fig-center -duration=0;
```

### 1.11 黑暗（无灯光）

适用：完全黑暗或仅有极微弱光线

背景：
```
setTransform:{"brightness":0.7,"contrast":0.8,"saturation":0.7,"gamma":0.5,"colorRed":222,"colorGreen":222,"colorBlue":222,"bloom":1,"bloomBrightness":0.7,"bloomBlur":10} -target=bg-main -duration=0 -next;
```
人物：
```
setTransform:{"brightness":0.4,"contrast":1.1,"saturation":0.9,"gamma":0.7,"colorRed":255,"colorGreen":255,"colorBlue":255,"bloom":0.2,"bloomBrightness":0.9,"bloomBlur":10,"bevel":0.2,"bevelThickness":18,"bevelRotation":130,"bevelRed":161,"bevelGreen":161,"bevelBlue":161} -target=fig-center -duration=0;
```

### 1.12 黑夜微光

适用：深夜仅有月光或远处微光

人物：
```
setTransform:{"colorRed":209,"colorGreen":224,"colorBlue":255,"bevel":1,"bevelThickness":10,"bevelRotation":30,"bevelSoftness":0,"bevelRed":119,"bevelGreen":168,"bevelBlue":252} -target=fig-center -duration=0;
```

### 1.13 火光/爆炸

适用：火灾、爆炸、篝火旁、强烈暖光源

背景：
```
setTransform:{"brightness":0.9,"contrast":0.8,"saturation":0.5,"gamma":0.6,"colorRed":255,"colorGreen":218,"colorBlue":184,"bloom":1,"bloomBrightness":0.8,"bloomBlur":8,"bevelRed":255,"bevelGreen":194,"bevelBlue":125} -target=bg-main -duration=0 -next;
```
人物：
```
setTransform:{"brightness":0.75,"contrast":1.1,"saturation":0.8,"gamma":1,"colorRed":255,"colorGreen":234,"colorBlue":217,"bloom":0.6,"bloomBrightness":0.7,"bloomBlur":4,"bevel":2,"bevelThickness":20,"bevelRotation":80,"bevelRed":255,"bevelGreen":201,"bevelBlue":125} -target=fig-center -duration=0;
```

### 1.14 面光（白天）

适用：白天正面对光、角色面向光源

背景：
```
setTransform:{"brightness":0.8,"contrast":0.8,"saturation":0.7,"gamma":0.5,"colorRed":227,"colorGreen":227,"colorBlue":227,"bloom":0.7,"bloomBrightness":0.8,"bloomBlur":10} -target=bg-main -duration=0 -next;
```
人物：
```
setTransform:{"brightness":0.75,"contrast":1,"saturation":0.8,"gamma":0.7,"colorRed":255,"colorGreen":255,"colorBlue":255,"bloom":0.5,"bloomBrightness":1,"bloomBlur":10,"bevel":0.5,"bevelThickness":18,"bevelRotation":30,"bevelRed":196,"bevelGreen":185,"bevelBlue":185} -target=fig-center -duration=0;
```

### 1.15 面光（黄昏）

适用：黄昏正面对光、逆光夕阳

背景：
```
setTransform:{"brightness":0.7,"contrast":0.8,"saturation":0.7,"gamma":0.5,"colorRed":255,"colorGreen":203,"colorBlue":171,"bloom":0.6,"bloomBrightness":0.8,"bloomBlur":10} -target=bg-main -duration=0 -next;
```
人物：
```
setTransform:{"brightness":0.5,"contrast":1,"saturation":0.7,"gamma":1,"colorRed":255,"colorGreen":208,"colorBlue":176,"bloom":0.4,"bloomBrightness":1.8,"bloomBlur":10,"bevel":0.3,"bevelThickness":18,"bevelRotation":30,"bevelRed":255,"bevelGreen":184,"bevelBlue":148} -target=fig-center -duration=0;
```

### 1.16 面光[清晨/黄昏（轻）]

适用：清晨或轻黄昏的柔光面光

背景：
```
setTransform:{"brightness":0.7,"contrast":0.8,"saturation":0.7,"gamma":0.5,"colorRed":255,"colorGreen":234,"colorBlue":214,"bloom":1,"bloomBrightness":0.7,"bloomBlur":10} -target=bg-main -duration=0 -next;
```
人物：
```
setTransform:{"brightness":0.8,"contrast":1.1,"saturation":0.9,"gamma":0.8,"colorRed":242,"colorGreen":216,"colorBlue":194,"bloom":0.5,"bloomBrightness":0.8,"bloomBlur":10,"bevel":1,"bevelThickness":15,"bevelRotation":30,"bevelRed":255,"bevelGreen":212,"bevelBlue":176} -target=fig-center -duration=0;
```

### 1.17 赛博朋克/电子故障

适用：受到干扰、电子画面、内心崩坏

```
setTransform:{"glitchFilm":1,"rgbFilm":1,"oldFilm":0.5,"colorRed":200,"colorGreen":255,"colorBlue":255,"brightness":1.2} -target=bg-main -duration=0;
```

### 1.18 复古黑白电视/监控画面

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
| 温馨日常 | 室内有光暖色 / 清爽版室内白天 | bg-main + fig |
| 晴天户外 | 白天室外晴天 | bg-main + fig |
| 室内白天 | 白天（通用）/ 清爽版室内白天 | bg-main + fig |
| 柔和晨暮 | 清晨/黄昏（轻） | bg-main + fig |
| 夕阳强烈 | 黄昏(重)（室外） | bg-main + fig |
| 室内夕阳 | 黄昏(重)（室内） | bg-main + fig |
| 柔和黄昏 | 淡色黄昏 | fig（背景加模糊） |
| 暖色灯光 | 室内有光暖色 | bg-main + fig |
| 夜间开灯 | 夜晚室内白光 | bg-main + fig |
| 夜间有灯 | 黑暗（有灯光） | bg-main + fig |
| 完全黑暗 | 黑暗（无灯光） | bg-main + fig |
| 深夜微光 | 黑夜微光 | fig |
| 火光爆炸 | 火光/爆炸 | bg-main + fig |
| 白天面光 | 面光（白天） | bg-main + fig |
| 黄昏面光 | 面光（黄昏） | bg-main + fig |
| 轻柔面光 | 面光[清晨/黄昏（轻）] | bg-main + fig |
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
