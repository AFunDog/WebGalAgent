---
category: skill
tags: [kind:reference-webgal-syntax, topic:webgal, audience:script-converter]
title: WebGal脚本语法参考
---

# WebGal脚本语法参考

## 基本结构

- 脚本文件为 `.txt` 格式，放在 `game/scene/` 目录下
- 程序启动时从 `start.txt` 开始运行，请勿重命名或删除
- 每条语句以**英文分号** `;` 结尾
- 英文分号后的内容视为注释：`角色:对话; 这是注释`
- 单独一行写 `;` 后的内容也视为注释

## 素材目录约定

素材文件存放在游戏根目录下的对应子目录中，引用时使用**相对于该子目录**的路径（即路径中不包含子目录名本身）：

| 素材类型 | 目录 | 引用示例 |
|----------|------|----------|
| 背景图片 | `background/` | `changeBg:场景/背景.jpg;` |
| 人物立绘 | `figure/` | `changeFigure:角色/model.json -id=角色id;` |
| 背景音乐 | `bgm/` | `bgm:音乐/曲名.mp3;` |
| 动画文件 | `animation/` | `setAnimation:动画名 -target=作用目标;` |
| 语音 | `vocal/` | `角色:对话 -语音.ogg;` |
| 视频 | `video/` | `playVideo:OP.mp4;` |
| 纹理 | `tex/` | 特效中使用 |

**重要**：系统会自动扫描可用素材并在生成脚本时提供素材清单，请严格按照清单中的路径引用素材，不要编造不存在的素材路径。

## 通用参数

| 参数 | 作用 | 示例 |
|------|------|------|
| `-next` | 执行完本条后立刻跳到下一条 | `changeBg:bg.jpg -next;` |
| `-notend` | 本句对话未结束，后面还会连接演出或对话 | `角色:说话 -notend;` |
| `-concat` | 本句连接在上一句对话之后 | `继续说话 -concat;` |
| `-when=(条件)` | 条件为真时才执行本条语句 | `changeScene:2.txt -when=a>1;` |
| `-duration=毫秒` | 设置动画/变换持续时间 | `setTransform:... -duration=1000 -target=x;` |

`-next` 常用于需要在同一时间内执行多步操作的场景。

`-notend` 和 `-concat` 配合使用可在对话进行中插入演出效果（如切换表情、立绘等）。

## 对话指令

### 角色对话

```
角色名:对话内容;
```

示例：
```
长崎素世:小爱音醒了……早餐还没做好，先去洗漱换衣服吧;
千早爱音:好！;
```

### 连续对话

同一角色连续说话时，可省略角色名：
```
千早爱音:第一句;
; 角色名仍然是"千早爱音"
第二句;
```

### 旁白/叙述

冒号前留空（不能省略冒号）：
```
:清晨的阳光悄然洒进房间，透过半开的窗帘，在木质地板上投下斑驳的光影;
```

### 黑屏独白（intro）

用 `|` 分隔换行：
```
intro:回忆不需要适合的剧本，|反正一说出口，|都成了戏言。;
```

加 `-hold` 在独白结束后保持界面：
```
intro:回忆不需要适合的剧本，|反正一说出口，|都成了戏言。 -hold;
```

### 对话中换行

使用 `|` 在对话文本中换行：
```
长崎素世:你要是能帮我做饭做家务的话，我还会犹豫一下|你在的这几天我都要做两人份的早餐和晚餐;
```

### 语音播放

在对话后加 `-语音文件名`（文件放在 `vocal/` 目录）：
```
比企谷八幡:刚到而已 -V3.ogg;
```

可加 `-volume=0~100` 调整音量。

### 对话中插入演出

```
千早爱音:说话内容 -notend;
changeFigure:x.png -next;
继续说话 -concat;
```

### 字体大小

```
:文本内容 -fontSize=small;   ; 小字，文本框显示3行
:文本内容 -fontSize=medium;  ; 中字，文本框显示2行
:文本内容 -fontSize=large;   ; 大字，文本框显示2行
```


### 文本拓展语法

为文本添加样式，`style` 控制颜色，`style-alltext` 控制字体大小/斜体等：
```
[文本](style-alltext=font-style:italic\;font-size:120%\; style=color:gold\;)
```

注意：文本拓展语法中的 `;` 需转义为 `\;`。

## 背景切换

背景图片放在 `background/` 目录：
```
changeBg:背景图.jpg;
changeBg:none;  ; 关闭背景
```

### 带效果切换

```
changeBg:bg.jpg -next -transform={"bloom":0.1,"bloomBlur":16,"bloomThreshold":0.8};
```

`-transform` 支持的常用属性：
- `bloom`/`bloomBlur`/`bloomThreshold` — 泛光效果
- `brightness` — 亮度（0~2，默认1）
- `colorRed`/`colorGreen`/`colorBlue` — 颜色分量（0~255）
- `saturation` — 饱和度

## 立绘控制

立绘图片放在 `figure/` 目录。

### 基本用法

```
changeFigure:立绘.png;              ; 中间立绘
changeFigure:立绘.png -left;        ; 左侧立绘
changeFigure:立绘.png -right;       ; 右侧立绘
changeFigure:none;                   ; 关闭中间立绘
changeFigure:none -left;            ; 关闭左侧立绘
changeFigure:none -right;           ; 关闭右侧立绘
```

三个位置的立绘相互独立，需分别清除。

### 带ID的自由立绘

支持超过3个立绘，可精确控制：
```
changeFigure:立绘.png -left -id=角色id;
changeFigure:none -id=角色id;  ; 通过id关闭
```

### Live2D模型

Live2D模型使用 `model.json`，可指定动作和表情：
```
changeFigure:anon/model.json -id=anon -motion=anon/smile01 -expression=anon/default;
```

> **技巧**：切换立绘的动作（`-motion`）和表情（`-expression`）通常在对话之前执行，在 `changeFigure` 指令末尾添加 `-next` 参数可以让动作/表情切换与后续对话同时进行，不被切换动画阻塞：
> ```
> changeFigure:anon/model.json -id=anon -motion=anon/angry01 -expression=anon/angry01 -next;
> 千早爱音:你在说什么！;
> ```
>
> **最佳实践**：在角色对话前使用 `changeFigure` 将表情和动作切换为**匹配该句情绪**的状态，做到"一句一表情"。切换间隔建议每 1~2 句一次，持续对话时从低情绪强度递进到高强度（如 `smile01` → `smile02` → `smile03`）。

### 设置立绘时的效果

```
changeFigure:stand.png -id=anon -transform={"position":{"x":-500}} -duration=2000 -ease=easeIn;
```

`-transform` 支持的属性：
- `position` — 位置偏移 `{"x":0,"y":0}`
- `scale` — 缩放 `{"x":1,"y":1}`
- `alpha` — 透明度（0~1）
- `rotation` — 旋转角度（弧度）
- `brightness`/`contrast`/`saturation`/`gamma` — 亮度/对比度/饱和度/伽马
- `blur` — 高斯模糊半径
- `bloom`/`bloomBlur`/`bloomThreshold` — 泛光
- `bevel`/`bevelThickness`/`bevelSoftness` — 斜角效果

### 对已有立绘设置变换

```
setTransform:{"position":{"x":100}} -target=角色id -duration=1000;
```

`-target` 可选值：`fig-left`、`fig-center`、`fig-right`、`bg-main`、`stage-main`、或自定义 `id`。

`-continue=true` 可在已有动画基础上叠加变换：
```
setTransform:{"position":{"x":-200}} -continue=true -duration=666 -target=anon;
```

### 聚焦

```
changeFigure:立绘.png -id=anon -focus={"x":-0.3};
setTransform:{"focus":{"x":0}} -target=anon;
```

### 层级

```
changeFigure:立绘.png -id=anon -zIndex=1;  ; 提高层级
```

### 小头像

```
miniAvatar:头像.png;  ; 显示
miniAvatar:none;       ; 关闭
```

## 音乐与音效

### BGM

BGM文件放在 `bgm/` 目录：
```
bgm:音乐.mp3;
bgm:音乐.mp3 -volume=30;      ; 设置音量(0~100)
bgm:音乐.mp3 -enter=3000;     ; 淡入(毫秒)
bgm:none -enter=3000;         ; 淡出
```

### 效果音

效果音文件放在 `vocal/` 目录：
```
playEffect:音效.mp3;
playEffect:音效.mp3 -volume=30;
playEffect:音效.mp3 -id=loop1;   ; 带id自动循环
playEffect:none -id=loop1;        ; 停止循环
```

## 转场效果

覆盖默认的渐变进出场效果：
```
setTransition: -target=fig-center -enter=enter-from-bottom -exit=exit;
```

注意：必须在立绘/背景设置后、连续执行时设置。

## 动画效果

> **推荐**：优先使用 `setTempAnimation`，它更灵活且无需依赖外部动画文件。

### 临时动画 setTempAnimation（推荐）

直接在代码中定义多段动画，无需额外文件。格式为 JSON 数组，每段动画是一个对象：

```
setTempAnimation:[段1, 段2, ...] -target=作用目标;
```

每段支持的属性：`brightness`、`contrast`、`saturation`、`scale{"x","y"}`、`position{"x","y"}`、`alpha`、`rotation`、`blur` 等，均需带 `duration`（毫秒）和可选的 `ease`。

示例 — 闪光弹效果：
```
setTempAnimation:[{"duration":0},{"brightness":2,"contrast":0,"duration":200,"ease":"circIn"},{"brightness":1,"contrast":1,"duration":200},{"brightness":2,"contrast":0,"duration":200,"ease":"circIn"},{"brightness":1,"contrast":1,"duration":2500}] -target=aaa;
```

参数：
- `-target`：作用目标（`fig-left`、`fig-center`、`fig-right`、`bg-main`、或自定义 `id`）
- `-writeDefault`：将动画写入默认值，后续不带 `-keep` 时会回到此状态
- `-keep`：动画完成后保持最终状态，不自动还原。跨对话持续生效，直到该目标执行新的不带 `-keep` 的 `setTempAnimation`

### 预制动画 setAnimation

读取 `animation/` 目录下的预制动画文件：

```
setAnimation:动画名 -target=作用目标 -next;
```

| 动画效果 | 动画名 | 持续时间 |
|----------|--------|----------|
| 渐入 | `enter` | 300ms |
| 渐出 | `exit` | 300ms |
| 左右摇晃 | `shake` | 1000ms |
| 从下方进入 | `enter-from-bottom` | 500ms |
| 从左侧进入 | `enter-from-left` | 500ms |
| 从右侧进入 | `enter-from-right` | 500ms |
| 前后移动 | `move-front-and-back` | 1000ms |

`-target` 可选值：`fig-left`、`fig-center`、`fig-right`、`bg-main`、或自定义 `id`。

## 特效

### 初始化与使用

```
pixiInit;                    ; 初始化（也用于清除所有特效）
pixiPerform:rain;            ; 下雨
pixiPerform:snow;            ; 下雪
pixiPerform:heavySnow;       ; 大雪
pixiPerform:cherryBlossoms;  ; 樱花
```

特效可叠加，用 `pixiInit` 清除全部。

## 场景与分支

### 场景跳转

跳转到新场景，不再返回：
```
changeScene:Chapter-2.txt;
```

### 场景调用

调用另一场景，执行完后返回：
```
callScene:Chapter-2.txt;
```

**注意**：跳转/调用后舞台不会清除，BGM、立绘、背景等会被继承。


## 视频播放

视频文件放在 `video/` 目录：
```
playVideo:OP.mp4;
playVideo:OP.mp4 -skipOff;  ; 禁止跳过
```

## 其他指令

### 等待

```
wait:1333;  ; 等待1333毫秒
```

### 关闭/显示文本框

```
setTextbox:hide;  ; 关闭文本框
setTextbox:on;    ; 重新显示（除hide外的任意值）
```
