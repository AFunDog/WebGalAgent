"""智能体基类与状态定义。"""

from __future__ import annotations

import abc
import asyncio
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, cast

from openai import AsyncOpenAI
from pydantic import BaseModel

from webgal_agent.core.memory import Memory, InMemoryMemory
from webgal_agent.core.message import Message
from webgal_agent.tools.base import Tool

logger = logging.getLogger("webgal_agent.agent")


class AgentState(str, Enum):
    """智能体可能的状态。"""

    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    ERROR = "error"
    DONE = "done"


class AgentConfig(BaseModel):
    """智能体实例的配置。"""

    name: str
    description: str = ""
    provider: str = "openai"
    model: str = "gpt-4o"
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    reasoning_effort: str | None = None
    extra_body: dict | None = None


@dataclass
class ToolCallRecord:
    """单次工具调用的记录。"""

    tool_name: str
    arguments: dict[str, Any]
    result: str
    success: bool
    round_idx: int


@dataclass
class LLMResponse:
    """LLM 响应结果（含工具调用记录和 Token 用量）。"""

    content: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class Agent(abc.ABC):
    """所有智能体的抽象基类。

    智能体是可接收消息、通过 LLM 处理并产生响应的自主单元。
    每个智能体拥有独立的记忆和可选的工具。

    工具调用流程（ReAct 循环）::

        1. LLM 收到 system_prompt + user_content + tools 定义
        2. LLM 返回文本回复 或 tool_call 请求
        3. 如果是 tool_call → 执行本地工具 → 将结果喂回 LLM → 回到步骤 2
        4. 如果是文本回复 → 返回给调用者
    """

    def __init__(
        self,
        config: AgentConfig,
        memory: Memory | None = None,
        tools: list[Tool] | None = None,
        system_prompt: str = "",
    ) -> None:
        self._config = config
        self._state = AgentState.IDLE
        self._memory = memory or InMemoryMemory()
        self._tools: dict[str, Tool] = {}
        self._cancel_event = asyncio.Event()
        self._custom_prompt = system_prompt
        if tools:
            for tool in tools:
                self._tools[tool.name] = tool

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def description(self) -> str:
        return self._config.description

    @property
    def state(self) -> AgentState:
        return self._state

    @property
    def memory(self) -> Memory:
        return self._memory

    @property
    def tools(self) -> dict[str, Tool]:
        """智能体当前可用的工具映射。"""
        return self._tools

    def add_tool(self, tool: Tool) -> None:
        """为智能体添加一个工具。"""
        self._tools[tool.name] = tool

    def cancel(self) -> None:
        """请求终止当前正在运行的智能体。"""
        self._cancel_event.set()
        logger.info("[%s] 收到终止请求", self._config.name)

    @property
    def is_cancelled(self) -> bool:
        """是否已被请求终止。"""
        return self._cancel_event.is_set()

    def _get_client(self) -> AsyncOpenAI:
        """创建基于当前配置的 AsyncOpenAI 客户端。"""
        base_url = self._config.base_url
        # 兼容用户在 base_url 中误带 /chat/completions 的情况
        if base_url.endswith("/chat/completions"):
            base_url = base_url[: -len("/chat/completions")]
        return AsyncOpenAI(
            api_key=self._config.api_key or "sk-placeholder",
            base_url=base_url,
            timeout=180.0,
        )

    async def _call_llm(self, system_prompt: str, user_content: str) -> LLMResponse:
        """调用 LLM 并返回生成文本（不含工具调用）。"""
        if self._cancel_event.is_set():
            raise asyncio.CancelledError("智能体已被终止")

        client = self._get_client()
        logger.info(
            "[%s] LLM 请求 ▶ model=%s",
            self._config.name, self._config.model,
        )
        logger.debug("[%s] system_prompt:\n%s", self._config.name, system_prompt[:500])
        logger.debug("[%s] user_content:\n%s", self._config.name, user_content[:500])
        extra_kwargs: dict[str, Any] = {}
        if self._config.reasoning_effort:
            extra_kwargs["reasoning_effort"] = self._config.reasoning_effort
        if self._config.extra_body:
            extra_kwargs["extra_body"] = self._config.extra_body
        response = await client.chat.completions.create(
            model=self._config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
            **extra_kwargs,
        )
        content = response.choices[0].message.content or ""
        prompt_tokens = response.usage.prompt_tokens if response.usage else 0
        completion_tokens = response.usage.completion_tokens if response.usage else 0
        total_tokens = response.usage.total_tokens if response.usage else 0
        logger.info(
            "[%s] LLM 响应 ◀ 长度=%d, tokens=%d(p=%d+c=%d)",
            self._config.name, len(content), total_tokens, prompt_tokens, completion_tokens,
        )
        preview = content[:300] + "…" if len(content) > 300 else content
        logger.info("[%s] 响应内容: %s", self._config.name, preview.replace("\n", " "))
        logger.debug("[%s] response:\n%s", self._config.name, content[:500])
        return LLMResponse(
            content=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

    async def _call_llm_with_tools(
        self,
        system_prompt: str,
        user_content: str,
        max_tool_rounds: int = 10,
    ) -> LLMResponse:
        """调用 LLM 并支持工具调用循环（ReAct 模式）。

        流程：
        1. 将 system_prompt、user_content 和工具定义发给 LLM
        2. 若 LLM 返回 tool_calls → 逐个执行 → 将结果追加到消息 → 再次调用 LLM
        3. 重复直到 LLM 返回纯文本（无 tool_calls）或达到最大轮数

        参数：
            system_prompt: 系统提示词
            user_content: 用户消息内容
            max_tool_rounds: 工具调用最大轮数（防止死循环）

        返回：
            LLMResponse，包含最终文本回复和工具调用记录
        """
        if not self._tools:
            # 没有工具则走简单路径
            return await self._call_llm(system_prompt, user_content)

        client = self._get_client()
        tool_schemas = [tool.schema() for tool in self._tools.values()]

        # 使用 Any 类型以兼容 OpenAI SDK 的严格消息类型
        messages: list[Any] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        tool_call_records: list[ToolCallRecord] = []
        accumulated_prompt_tokens = 0
        accumulated_completion_tokens = 0
        accumulated_total_tokens = 0

        logger.info(
            "[%s] LLM 请求 ▶ model=%s, tools=%s",
            self._config.name,
            self._config.model,
            [t.name for t in self._tools.values()],
        )
        logger.debug("[%s] system_prompt:\n%s", self._config.name, system_prompt[:500])
        logger.debug("[%s] user_content:\n%s", self._config.name, user_content[:500])

        for round_idx in range(max_tool_rounds):
            if self._cancel_event.is_set():
                logger.info("[%s] 在 round=%d 检测到终止信号", self._config.name, round_idx + 1)
                raise asyncio.CancelledError("智能体已被终止")

            extra_kwargs: dict[str, Any] = {}
            if self._config.reasoning_effort:
                extra_kwargs["reasoning_effort"] = self._config.reasoning_effort
            if self._config.extra_body:
                extra_kwargs["extra_body"] = self._config.extra_body
            response = await client.chat.completions.create(
                model=self._config.model,
                messages=messages,
                tools=cast(Any, tool_schemas),
                temperature=self._config.temperature,
                max_tokens=self._config.max_tokens,
                **extra_kwargs,
            )

            choice = response.choices[0]
            assistant_msg = choice.message

            # 累加 Token 用量
            if response.usage:
                accumulated_prompt_tokens += response.usage.prompt_tokens
                accumulated_completion_tokens += response.usage.completion_tokens
                accumulated_total_tokens += response.usage.total_tokens

            # 没有 tool_calls → LLM 给出了最终文本回复
            if not assistant_msg.tool_calls:
                content = assistant_msg.content or ""
                logger.info(
                    "[%s] LLM 响应 ◀ 长度=%d, 工具调用=%d次, tokens=%d",
                    self._config.name, len(content), len(tool_call_records), accumulated_total_tokens,
                )
                preview = content[:300] + "…" if len(content) > 300 else content
                logger.info("[%s] 响应内容: %s", self._config.name, preview.replace("\n", " "))
                logger.debug("[%s] response:\n%s", self._config.name, content[:500])
                return LLMResponse(
                    content=content,
                    tool_calls=tool_call_records,
                    prompt_tokens=accumulated_prompt_tokens,
                    completion_tokens=accumulated_completion_tokens,
                    total_tokens=accumulated_total_tokens,
                )

            # 有 tool_calls 时，也记录中间文本（如果有的话）
            if assistant_msg.content:
                preview = (assistant_msg.content[:300] + "…" 
                           if len(assistant_msg.content) > 300 else assistant_msg.content)
                logger.info(
                    "[%s] 中间文本: %s [round=%d]",
                    self._config.name, preview.replace("\n", " "), round_idx + 1,
                )

            # 将 assistant 消息（含 tool_calls）加入历史
            messages.append(assistant_msg)

            # 逐个执行工具调用
            for tc in assistant_msg.tool_calls:
                # OpenAI SDK: tc.function.name / tc.function.arguments
                func = tc.function  # type: ignore[union-attr]
                tool_name = func.name  # type: ignore[union-attr]
                tool = self._tools.get(tool_name)

                if tool is None:
                    logger.warning("LLM 请求了不存在的工具: %s", tool_name)
                    error_msg = json.dumps(
                        {"error": f"工具 '{tool_name}' 不存在"}, ensure_ascii=False
                    )
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": error_msg,
                    })
                    tool_call_records.append(ToolCallRecord(
                        tool_name=tool_name,
                        arguments={},
                        result=error_msg,
                        success=False,
                        round_idx=round_idx + 1,
                    ))
                    continue

                try:
                    args = json.loads(func.arguments)  # type: ignore[union-attr]
                    logger.info(
                        "工具调用: %s(%s) [round=%d]",
                        tool_name,
                        ", ".join(f"{k}={v!r}" for k, v in args.items()),
                        round_idx + 1,
                    )
                    result = await tool.execute(**args)
                    content = result.output if result.success else f"错误: {result.error}"
                    # 输出工具结果摘要（截断过长内容）
                    result_preview = content[:300] + "…" if len(content) > 300 else content
                    logger.info(
                        "工具结果: %s → %s [round=%d]",
                        tool_name,
                        result_preview.replace("\n", " "),
                        round_idx + 1,
                    )
                    tool_call_records.append(ToolCallRecord(
                        tool_name=tool_name,
                        arguments=args,
                        result=content,
                        success=result.success,
                        round_idx=round_idx + 1,
                    ))
                except json.JSONDecodeError:
                    content = json.dumps(
                        {"error": f"参数 JSON 解析失败: {func.arguments}"},  # type: ignore[union-attr]
                        ensure_ascii=False,
                    )
                    tool_call_records.append(ToolCallRecord(
                        tool_name=tool_name,
                        arguments={},
                        result=content,
                        success=False,
                        round_idx=round_idx + 1,
                    ))
                except Exception as exc:
                    logger.exception("工具 %s 执行异常", tool_name)
                    content = json.dumps(
                        {"error": str(exc)}, ensure_ascii=False
                    )
                    tool_call_records.append(ToolCallRecord(
                        tool_name=tool_name,
                        arguments={},
                        result=content,
                        success=False,
                        round_idx=round_idx + 1,
                    ))

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": content,
                })

        # 达到最大轮数
        logger.warning("工具调用达到最大轮数 %d，强制终止", max_tool_rounds)
        return LLMResponse(
            content=assistant_msg.content or "",
            tool_calls=tool_call_records,
            prompt_tokens=accumulated_prompt_tokens,
            completion_tokens=accumulated_completion_tokens,
            total_tokens=accumulated_total_tokens,
        )

    async def run(self, message: Message) -> Message:
        """处理传入消息并返回响应。

        默认实现：调用 LLM（含工具循环），将结果包装为 RESULT 消息返回。
        子类可覆盖此方法以实现自定义行为。
        """
        from webgal_agent.core.message import MessageType

        response = await self._call_llm_with_tools(
            system_prompt=self.system_prompt(),
            user_content=message.content,
        )
        metadata = dict(message.metadata)
        if response.tool_calls:
            metadata["tool_calls"] = [
                {"tool": tc.tool_name, "args": tc.arguments, "result": tc.result, "success": tc.success}
                for tc in response.tool_calls
            ]
        metadata["token_usage"] = {
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "total_tokens": response.total_tokens,
        }
        return message.reply(content=response.content, msg_type=MessageType.RESULT).model_copy(
            update={"metadata": metadata}
        )

    def system_prompt(self) -> str:
        """返回该智能体的系统提示词。

        如果构造时传入了 system_prompt 则使用它，否则返回空字符串。
        子类可覆盖此方法以提供动态提示词。
        """
        if self._custom_prompt:
            return self._custom_prompt
        return ""

    async def handle(self, message: Message) -> Message:
        """带状态管理的消息处理。

        在 ``run`` 方法外包装状态转换和错误处理。
        """
        self._state = AgentState.RUNNING
        self._cancel_event.clear()
        try:
            self._memory.add(message)
            result = await self.run(message)
            self._memory.add(result)
            self._state = AgentState.DONE
            return result
        except asyncio.CancelledError:
            self._state = AgentState.IDLE
            logger.info("[%s] 执行已被终止", self._config.name)
            raise
        except Exception:
            self._state = AgentState.ERROR
            raise

    def reset(self) -> None:
        """重置智能体到空闲状态并清空记忆。"""
        self._state = AgentState.IDLE
        self._memory.clear()
        self._cancel_event.clear()
