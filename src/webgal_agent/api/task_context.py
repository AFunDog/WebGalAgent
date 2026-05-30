"""任务上下文构建辅助。"""

from __future__ import annotations

from webgal_agent.api.workflow_definition import AGENT_PREV_DEPS, PIPELINE_ORDER
from webgal_agent.api.task_state import TaskInfo
from webgal_agent.knowledge import KnowledgeStore
from webgal_agent.knowledge.models import KnowledgeEntry


def build_knowledge_context(
    knowledge_store: KnowledgeStore | None,
    knowledge_requirements: dict[str, dict[str, list[str]]],
    agent_name: str = "",
) -> str:
    """将知识库条目格式化为指定智能体的上下文文本。"""
    if knowledge_store is None:
        return ""

    requirements = knowledge_requirements.get(agent_name, {}) if agent_name else {}
    categories = requirements.get("categories", [])
    tags = requirements.get("tags", [])

    if categories or tags:
        entries_by_category: list[KnowledgeEntry] = []
        entries_by_tags: list[KnowledgeEntry] = []
        if categories:
            for cat in categories:
                entries_by_category.extend(knowledge_store.query(category=cat))
        if tags:
            entries_by_tags = knowledge_store.query(tags=tags)

        seen_ids: set[str] = set()
        entries: list[KnowledgeEntry] = []
        for entry in entries_by_category + entries_by_tags:
            if entry.id not in seen_ids:
                seen_ids.add(entry.id)
                entries.append(entry)
    else:
        entries = knowledge_store.list_all()

    if not entries:
        return ""

    parts: list[str] = []
    for entry in entries:
        header = f"### {entry.title}"
        if entry.category:
            header += f" [{entry.category}]"
        parts.append(f"{header}\n{entry.body}")

    return "\n\n".join(parts)


def build_all_knowledge_contexts(
    knowledge_store: KnowledgeStore | None,
    knowledge_requirements: dict[str, dict[str, list[str]]],
) -> dict[str, str]:
    """为流水线中的每个智能体构建知识库上下文。"""
    return {
        name: build_knowledge_context(knowledge_store, knowledge_requirements, name)
        for name in PIPELINE_ORDER
    }


def build_step_input(
    task: TaskInfo,
    agent_name: str,
    step_index: int,
    knowledge_contexts: dict[str, str],
    revision_source_output: str | None = None,
    revision_instruction: str | None = None,
) -> str:
    """构建当前步骤给 agent 的输入文本。"""
    context_parts: list[str] = []

    if task.content:
        context_parts.append(f"【用户输入】\n{task.content}")

    agent_knowledge = knowledge_contexts.get(agent_name, "")
    if agent_knowledge:
        context_parts.append(f"【知识库】\n{agent_knowledge}")

    prev_deps = AGENT_PREV_DEPS.get(agent_name)
    for idx in range(step_index):
        prev_name = PIPELINE_ORDER[idx]
        if prev_deps is not None and prev_name not in prev_deps:
            continue
        prev_output = task.step_results.get(idx, "")
        if prev_output:
            context_parts.append(f"【{prev_name} 的输出】\n{prev_output}")

    if revision_source_output:
        context_parts.append(f"【上一次输出】\n{revision_source_output}")

    if revision_instruction:
        context_parts.append(
            "【本轮修订要求】\n"
            "请基于上一次输出和已有上下文重新生成当前步骤结果，并严格响应下面的额外要求。\n"
            f"{revision_instruction}"
        )

    return "\n\n".join(context_parts) if context_parts else task.content
