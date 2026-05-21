# WebGalAgent 问题与路线图

最后更新: 2026-05-21

本文档只记录当前待解决问题和建议方向，不再重复 README 与 browser README 已稳定的实现说明。

## 高优先级问题

### 1. LLM 超时仍然缺少细粒度配置

- 位置：`src/webgal_agent/core/agent.py`
- 现状：超时控制仍偏硬编码，难以按 provider 或 agent 细调
- 影响：`script_converter` 这类重步骤更容易因模型响应波动失败
- 建议：把 timeout 下沉到 provider/agent 配置层

### 2. LLM 调用缺少统一重试策略

- 位置：`src/webgal_agent/core/agent.py`
- 现状：网络抖动、限流、短时上游异常没有统一退避策略
- 影响：长链路任务稳定性不足
- 建议：实现可配置的指数退避与最大重试次数

### 3. API 层缺少统一异常返回

- 位置：`src/webgal_agent/api/app.py`
- 现状：很多错误仍直接落到默认 500
- 影响：前端错误体验和调试一致性都较弱
- 建议：增加全局异常处理与统一错误结构

### 4. WebGal 页面注入仍依赖脆弱页面符号

- 位置：`src/webgal_agent/browser/webgal_session.py` 及相关注入逻辑
- 现状：部分录制准备仍建立在页面构建产物符号之上
- 影响：WebGal 页面构建或变量名变化时容易失效
- 建议：补强失败诊断，必要时抽象兼容层

### 5. 配置注入的运行态校验仍不足

- 位置：`src/webgal_agent/browser/demo_session.py`
- 现状：数据库写回可验证，但“页面运行态已生效”仍依赖页面行为
- 影响：日志成功不一定等于录制行为已经按预期改变
- 建议：保留回读验证，并补充必要的运行态确认

## 中优先级问题

### 6. TaskManager 仍然偏重

- 位置：`src/webgal_agent/api/task_manager.py`
- 现状：虽然已拆出若干辅助模块，但总入口仍聚合较多职责
- 影响：继续扩展任务流程时可维护性压力较大

### 7. 知识上下文构建还有裁剪空间

- 位置：`src/webgal_agent/api/task_context.py`
- 现状：上下文构建仍可能为部分步骤准备了冗余内容
- 影响：额外 token 消耗与不必要的字符串拼接

### 8. 浏览器录制的回归验证仍偏弱

- 位置：`tests/browser/`, `tests/api/test_record_route_unit.py`
- 现状：单元测试已有，但真实录制链路仍缺少更强的可回归验证
- 影响：录制相关重构风险较高

### 9. 文档仍需持续防漂移

- 位置：`README.md`, `src/webgal_agent/browser/README.md`, `docs/README.md`, `AGENTS.md`
- 现状：本轮已做精简重组，但后续若改 CLI、录制默认值或页面入口，仍需同步更新
- 建议：每次改入口、默认值、路由或录制协议时，同步检查这四份文档

## 近期建议

1. 给录制链路补一个最小的端到端回归样例。
2. 把 timeout / retry 配置化，减少长任务脆弱性。
3. 给录制配置注入补更明确的运行态校验点。
4. 为 API 增加统一异常处理。
5. 继续收窄 `TaskManager` 的聚合职责。
