# 任务流水线说明

最后更新: 2026-05-18

本文档描述当前任务流水线的真实结构，以及拆分后的代码位置。

## 流水线步骤

当前固定为三步：

1. `outline_writer`
2. `script_writer`
3. `script_converter`

共享定义位置：

- `src/webgal_agent/api/workflow_definition.py`
- `src/frontend/src/constants/pipeline.ts`

## 当前代码分层

任务编排相关逻辑已从原始大文件中拆分为：

- `src/webgal_agent/api/task_manager.py`
  对外编排入口，协调任务启动、单步执行、取消、状态查询
- `src/webgal_agent/api/task_state.py`
  `TaskInfo`、标题提取、工作流响应类型
- `src/webgal_agent/api/task_storage.py`
  任务落盘与恢复
- `src/webgal_agent/api/task_context.py`
  知识上下文与步骤输入构建
- `src/webgal_agent/api/task_agents.py`
  agent 构建与 agent 信息序列化

## 单步执行流程

1. `TaskManager.run_step()` 校验任务状态并创建后台协程。
2. `_run_step_background()` 根据当前步骤名构建 agent。
3. 从知识库生成当前步骤需要的知识上下文。
4. 把用户输入、前序步骤输出、知识条目拼接成单步输入文本。
5. 调用 `agent.handle()` 执行一步。
6. 写回 `TaskInfo` 的消息、步骤输出、token 统计。
7. 调用 `task_storage.save_task_to_disk()` 写入磁盘快照。

## 持久化格式

当前任务目录结构：

```text
data/tasks/<task_id>/
├── process.json
├── result.txt
├── step_1_outline_writer.txt
├── step_2_script_writer.txt
└── ...
```

说明：

- `process.json` 保存完整任务状态与消息过程
- `result.txt` 保存最后一步文本输出摘要
- `step_*.txt` 保存各步骤独立输出，便于人工检查和编辑
