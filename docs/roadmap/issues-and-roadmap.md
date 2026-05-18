# WebGalAgent 问题与路线图

最后更新: 2026-05-17

本文档聚焦当前真实代码状态，不保留已经明显过时的实现描述。

## 当前高优先级问题

### 1. LLM 超时仍然硬编码

- 位置: `src/webgal_agent/core/agent.py`
- 现状: 客户端 timeout 仍是固定值，不能按模型或智能体细调
- 影响: `script_converter` 等重型步骤容易超时
- 建议: 将 timeout 提升到 provider/agent 级配置

### 2. LLM 调用缺少统一重试

- 位置: `src/webgal_agent/core/agent.py`
- 现状: 网络波动、限流、认证异常缺少系统化重试
- 影响: 长任务脆弱
- 建议: 指数退避 + 可配置最大重试次数

### 3. API 层缺少统一异常处理

- 位置: `src/webgal_agent/api/app.py`
- 现状: 路由异常较多依赖默认 500
- 影响: 前端错误体验差，调试信息不统一
- 建议: 增加全局 exception handler，返回结构化错误

### 4. 浏览器录制仍依赖页面内部脆弱符号

- 位置: `src/webgal_agent/browser/demo.py`
- 现状: WebGal 录制通过注入 `gCe` / `wU` / `_r` / `Vh` / `L` 等页面构建产物符号
- 影响: 前端资源构建变动后很容易失效
- 建议: 把注入点和失败诊断做得更明确，必要时增加版本兼容层

### 5. WebGal 配置注入链路缺少更强校验

- 位置: `src/webgal_agent/browser/demo.py`
- 现状: 已确认 `saveConfig()` 会触发异步 IndexedDB 写入，短延迟可避免冲突；但配置是否真正影响运行态仍依赖具体页面行为
- 影响: 日志显示“已更新”不一定等于“游戏行为已生效”
- 建议:
  - 保留数据库回读验证
  - 必要时增加运行态配置回读
  - 明确 `MyGO` key 是否需要配置化

## 当前中优先级问题

### 6. 前端 API 请求缺少显式超时与错误分类

- 位置: `src/frontend/src/api/index.ts`
- 影响: 长时间挂起时体验差

### 7. TaskManager 仍有一些职责过重问题

- 位置: `src/webgal_agent/api/task_manager.py`
- 现状: 配置加载、知识筛选、步骤执行、状态维护耦合较深
- 影响: 后续重构和测试成本高

### 8. 知识上下文构建仍有冗余

- 位置: `src/webgal_agent/api/task_manager.py`
- 现状: 存在为多个智能体构建上下文但只消费部分结果的空间
- 影响: 不必要的 token 和 CPU 消耗

### 9. 测试覆盖不足

- 位置: `tests/`
- 现状: 核心浏览器录制链路、TaskManager、复杂路由覆盖不够
- 影响: 重构风险高

### 10. 文档长期容易与实现漂移

- 位置: `README.md`, `src/webgal_agent/browser/README.md`, `AGENTS.md`
- 现状: 本次审查前已经出现“文档描述旧录制架构，但代码已切到新实现”的问题
- 建议: 每次修改录制链路或 CLI 参数时同步更新文档

## 已确认并记录的录制结论

### WebGal 配置注入

- IndexedDB 数据库名是 `localforage`
- 当前配置记录按 key `MyGO` 访问
- `window.saveConfig()` 虽然看起来是同步调用，但会触发异步数据库写入
- 若在其后立刻访问同一 store，可能产生写冲突
- 当前经验规则: `saveConfig()` 后先留一个短延迟，再执行自定义写入

### 当前录制架构

- 使用 `Page.startScreencast`
- 原始帧写入临时目录
- 录制结束后用 FFmpeg 离线编码
- 音频通过 WebAudio hook + PCM/WAV 合流
- API 使用子进程跑 `browser/demo.py`

## 已完成事项

### 2026-05 浏览器录制相关

- 切换到 `ScreencastRecorder`
- API 录制使用子进程隔离
- Windows 入口点 event loop policy 已归位
- 录制配置与 Web UI 基本打通
- 文档已更新为“写磁盘后离线编码”的真实架构
- 已确认 `saveConfig()` 与 IndexedDB 冲突的根因

### 2026-05 工程协作相关

- 增加 `AGENTS.md`
- 明确默认 Python 解释器为 `.venv\Scripts\python.exe`
- 补充 browser 子系统的当前行为说明

## 近期建议

1. 给浏览器录制链路补最小可回归验证。
2. 把 `MyGO` 这类页面特定 key 变成配置项，而不是写死在脚本里。
3. 给 `record` CLI 增加更明确的诊断输出开关，便于排查页面注入失败点。
4. 将 LLM timeout / retry 配置化。
5. 为 API 统一错误返回结构。

## 中长期方向

### 工程稳定性

- 配置系统统一化
- 更高测试覆盖率
- 更明确的错误分类和可观测性

### 产品能力

- 更灵活的工作流模式
- 实时任务推送而非轮询
- 更强的素材与场景管理
- 更完善的录制预设与调试工具
