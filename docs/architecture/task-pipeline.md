# 任务流水线细节

最后更新: 2026-05-21

## 当前步骤定义

共享定义位于：

- `src/webgal_agent/api/workflow_definition.py`
- `src/frontend/src/constants/pipeline.ts`

固定顺序：

1. `outline_writer`
2. `script_writer`
3. `script_converter`

当前依赖关系：

- `outline_writer`: 无前序结果依赖
- `script_writer`: 默认读取前序结果
- `script_converter`: 当前只显式依赖 `script_writer` 输出

## 后端分层

- `task_manager.py`: 对外编排入口
- `task_context.py`: 知识上下文与单步输入构建
- `task_agents.py`: agent 构建与元数据输出
- `task_state.py`: 任务状态模型
- `task_storage.py`: 磁盘持久化与恢复

## 单步执行流程

1. 前端创建任务或读取已有任务。
2. `/api/tasks/{id}/run-step` 触发下一步执行。
3. `TaskManager` 按当前步骤构建 agent。
4. 根据 `prompts.yaml` 的知识需求装配知识上下文。
5. 拼接用户输入、前序输出、知识上下文，形成当前步骤输入。
6. 调用 `agent.handle()`。
7. 把结果写回内存状态与 `data/tasks/<task_id>/`。

## 持久化结果

```text
data/tasks/<task_id>/
├── process.json
├── result.txt
├── step_1_outline_writer.txt
├── step_2_script_writer.txt
└── step_3_script_converter.txt
```

这些文件的定位：

- `process.json`: 完整任务状态与消息过程
- `result.txt`: 最终结果摘要
- `step_*.txt`: 各步骤独立输出，便于人工修改与复用
