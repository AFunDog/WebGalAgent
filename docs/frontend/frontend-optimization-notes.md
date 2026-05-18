# WebGalAgent 前端页面优化建议

最后更新: 2026-05-18

本文档聚焦当前前端页面层面的优化点，目标是提升可维护性、交互一致性、响应式表现和后续扩展效率。以下建议均以“不改变核心功能”为前提。

## 已完成进展

截至 2026-05-18，已完成以下前端整理：

- `api/index.ts` 已拆为分模块 API 文件
- 新增 `constants/pipeline.ts`
- 新增 `utils/taskDisplay.ts`
- 新增 `composables/useTaskPolling.ts`
- `PipelineView.vue` 与 `TasksView.vue` 已改为消费共享轮询与共享展示逻辑

因此本文档中的以下项已从“建议”进入“已部分完成”：

- API 模块拆分
- 流水线定义收敛
- 轮询逻辑抽离

## 1. 当前主要问题

### 1.1 页面组件承担了过多状态逻辑

当前几个主要页面都同时承担了：

- 页面展示
- API 调用
- 轮询控制
- 错误处理
- 局部编辑状态
- 状态映射与格式化

典型文件：

- `src/frontend/src/views/PipelineView.vue`
- `src/frontend/src/views/TasksView.vue`
- `src/frontend/src/views/RecordView.vue`

这会导致：

- 页面越来越长，阅读成本高
- 相似逻辑在多个页面重复实现
- 一处改动后，其他页面容易忘记同步

### 1.2 流水线定义在前端重复维护

当前 `PipelineView.vue` 和 `TasksView.vue` 都定义了自己的 `pipelineSteps`。

风险：

- 步骤名、标签、依赖关系可能与后端漂移
- 后续如果调整工作流顺序，需要多处同步修改

### 1.3 API 层过于集中

`src/frontend/src/api/index.ts` 当前是单文件汇总：

- 知识库
- 任务
- 提供商
- 场景链接
- 录制

短期可用，但继续增长后会带来：

- 文件过长
- 接口分组不清晰
- 错误处理和超时逻辑难统一抽象

### 1.4 轮询实现分散且风格不一致

当前存在多套轮询逻辑：

- `PipelineView.vue`: 当前任务轮询
- `TasksView.vue`: 多任务轮询
- `RecordView.vue`: while-loop 轮询录制状态

风险：

- 生命周期清理不一致
- 重复轮询或并发竞争
- 难以统一超时、重试、错误行为

### 1.5 错误反馈方式较原始

当前不少页面仍然直接使用：

- `alert()`
- `console.error()`

这会导致：

- 打断用户操作
- 错误展示不统一
- 无法形成可复用的提示机制

### 1.6 内联样式偏多

多个页面中存在大量 `style=""`：

- `PipelineView.vue`
- `TasksView.vue`
- `RecordView.vue`
- `App.vue`

问题：

- 样式复用差
- 页面结构与视觉耦合
- 后续改响应式和主题时搜索成本高

### 1.7 响应式适配不足

全局样式目前偏桌面优先：

- 侧栏固定宽度
- 多列表单固定横排
- token 统计卡片固定 4 列

在窄屏或较小窗口下，体验会明显下降。

### 1.8 页面状态和接口字段有轻微漂移风险

例如 `RecordView.vue` 中保留了一些前端状态字段，但并非都与当前后端请求模型严格一致。

风险：

- 用户看到的配置项不一定真正生效
- 页面状态复杂度高于真实 API 能力

### 1.9 公共映射和格式化逻辑未收敛

当前多处存在相似逻辑：

- `formatTokenCount`
- 状态文案映射
- agent 标签映射
- 步骤标签映射

问题：

- 重复
- 难统一修改
- 容易产生细小不一致

## 2. 优先级建议

### P0：优先处理

- 把轮询逻辑抽成 composable
- 收敛 `pipelineSteps` 和步骤标签映射
- 拆分 `api/index.ts`
- 替换 `alert()` 为统一错误提示机制

### P1：下一轮处理

- 清理页面内联样式
- 提取公共格式化函数与标签映射
- 增加更清晰的加载态、空态、失败态
- 统一 `RecordView` 的表单约束逻辑

### P2：中期优化

- 增加响应式布局
- 提升页面视觉层级
- 建立更严格的前端状态类型
- 减少前端本地重复定义，更多依赖后端元数据

## 3. 具体优化方向

### 3.1 状态逻辑拆分

建议新增：

- `src/frontend/src/composables/useTaskPolling.ts`
- `src/frontend/src/composables/usePipelineTask.ts`
- `src/frontend/src/composables/useRecordSession.ts`

目标：

- 页面只负责展示和事件绑定
- 轮询、状态流转、接口协调从页面中抽离

### 3.2 API 模块拆分

建议拆成：

- `api/request.ts`
- `api/tasks.ts`
- `api/knowledge.ts`
- `api/providers.ts`
- `api/record.ts`
- `api/sceneLink.ts`

收益：

- 接口边界清晰
- 更容易统一超时和错误处理
- 更适合后续为不同模块补测试

### 3.3 收敛工作流定义

建议前端新增统一常量模块，例如：

- `src/frontend/src/constants/pipeline.ts`

统一维护：

- 步骤顺序
- 标签
- 前序依赖

更理想的长期方向：

- 前端直接消费后端返回的工作流元数据，而不是本地维护副本

### 3.4 统一错误提示

建议引入轻量全局提示机制，例如：

- 页面顶部错误条
- toast 提示
- 统一错误展示组件

替代：

- `alert()`
- 分散的 `console.error()` + 静默失败

### 3.5 样式层整理

建议：

- 把页面中的 `style=""` 改成 class
- 抽公共布局 class
- 把重复的按钮区、状态区、结果区样式抽成可复用模式

适合优先清理的页面：

- `PipelineView.vue`
- `TasksView.vue`
- `RecordView.vue`

### 3.6 录制页交互约束增强

`RecordView.vue` 建议补充前端校验：

- `duration = 0` 时必须要求填写 `stop_condition`
- `format = png` 时弱化或禁用 `quality`
- 录制进行中锁定配置表单
- 明确提示某些字段是否真的被后端消费

### 3.7 响应式支持

建议至少补一组中等宽度断点，例如：

- `max-width: 900px`

优先处理：

- 顶层布局
- 表单双列改单列
- token 卡片布局
- 侧栏收缩或改顶部导航

### 3.8 提取公共工具函数

建议新增：

- `src/frontend/src/utils/format.ts`
- `src/frontend/src/constants/labels.ts`

统一放置：

- token 格式化
- 状态文案
- agent 文案
- 通用展示标签

## 4. 推荐执行顺序

建议按以下顺序推进：

1. 抽轮询 composable
2. 收敛 `pipelineSteps`
3. 拆 API 层
4. 统一错误提示
5. 清理内联样式
6. 补响应式布局

这个顺序的优点是：

- 先解决结构问题
- 再解决重复问题
- 最后再做视觉和适配层优化

## 5. 总结

当前前端并不是功能不可用，而是已经出现了明显的“页面组件承担太多职责”的迹象。

最值得优先处理的不是换视觉，而是：

- 抽状态逻辑
- 统一轮询
- 收敛重复定义
- 清理 API 和错误处理边界

这样后面无论是继续加功能，还是做响应式和样式升级，成本都会明显下降。
