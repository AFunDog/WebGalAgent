"""动作表情知识检索工具：仅检索 expression_motion.json。"""

from __future__ import annotations

import json
import math
import os
import pathlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from openai import AsyncOpenAI

from webgal_agent.config.prompt_config import extract_system_prompts, load_prompt_config
from webgal_agent.tools.base import Tool, ToolResult
from webgal_agent.utils.logging import get_logger

if TYPE_CHECKING:
    from webgal_agent.config.provider_manager import ProviderConfig

DEFAULT_KNOWLEDGE_DIR = pathlib.Path("data/knowledge")
DEFAULT_PROVIDER_SLOT = "expression_motion_retriever"
DEFAULT_PROMPTS_PATH = Path("src/configs/prompts.yaml")
DEFAULT_RETRIEVER_PROMPT = (
    "你是一个动作表情检索重排器。"
    "你只能从给定候选中挑选最符合场景语义的 action，不能编造新 action。"
    "请输出 JSON 数组，每个元素包含 action、score、reason。"
    "score 使用 0 到 1 的数字，reason 用一句简短中文说明。"
)
logger = get_logger("webgal_agent.search_expression_motion")


@dataclass(slots=True)
class ExpressionMotionEntry:
    action: str
    description: str


class LLMRerankError(RuntimeError):
    """重排模型返回不可用结果时，携带原始输出便于排查。"""

    def __init__(self, message: str, raw_output: str = "") -> None:
        super().__init__(message)
        self.raw_output = raw_output


def _resolve_knowledge_dir() -> pathlib.Path:
    knowledge_dir = os.getenv("WEBGAL_KNOWLEDGE_DIR", str(DEFAULT_KNOWLEDGE_DIR)).strip()
    return pathlib.Path(knowledge_dir)


def load_expression_motion_retriever_prompt(
    prompts_path: str | Path = DEFAULT_PROMPTS_PATH,
) -> str:
    prompt_config = load_prompt_config(prompts_path)
    prompts = extract_system_prompts(prompt_config)
    prompt = prompts.get(DEFAULT_PROVIDER_SLOT, "").strip()
    return prompt or DEFAULT_RETRIEVER_PROMPT


def _load_expression_motion_entries(
    character_id: str,
) -> tuple[list[ExpressionMotionEntry], str | None]:
    knowledge_root = _resolve_knowledge_dir() / "characters"
    if not knowledge_root.exists():
        return [], None

    best_entries: list[ExpressionMotionEntry] = []
    best_source: str | None = None
    best_score = 0

    for path in sorted(knowledge_root.rglob("expression_motion.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        if not isinstance(data, list):
            continue

        entries: list[ExpressionMotionEntry] = []
        score = 0
        for item in data:
            if not isinstance(item, dict):
                continue
            action = item.get("action")
            description = item.get("description")
            if not isinstance(action, str) or not isinstance(description, str):
                continue
            if action.startswith(f"{character_id}/"):
                entries.append(ExpressionMotionEntry(action=action, description=description))
                score += 1

        if score > best_score and entries:
            best_score = score
            best_entries = entries
            best_source = path.relative_to(knowledge_root.parent).as_posix()

    return best_entries, best_source


def _normalize_text(text: str) -> list[str]:
    lowered = text.lower()
    parts = re.split(r"[^0-9a-zA-Z\u4e00-\u9fff]+", lowered)
    return [part for part in parts if part]


def _heuristic_score(query_text: str, action: str, description: str) -> float:
    query_tokens = _normalize_text(query_text)
    if not query_tokens:
        return 0.0

    haystack = f"{action} {description}"
    haystack_tokens = set(_normalize_text(haystack))
    overlap = sum(1 for token in query_tokens if token in haystack_tokens)

    action_name = action.split("/", 1)[-1]
    prefix_bonus_map = {
        "angry": ["生气", "愤怒", "不满", "怒"],
        "cry": ["哭", "悲伤", "难过", "委屈", "失落"],
        "sad": ["伤心", "悲伤", "低落", "失落"],
        "smile": ["笑", "开心", "轻松", "温柔"],
        "thinking": ["思考", "犹豫", "沉思", "纠结"],
        "serious": ["严肃", "认真", "冷静"],
        "surprised": ["惊讶", "吃惊", "震惊"],
        "shame": ["害羞", "羞涩", "尴尬"],
        "wink": ["眨眼", "俏皮"],
    }
    semantic_bonus = 0.0
    for prefix, keywords in prefix_bonus_map.items():
        if action_name.startswith(prefix) and any(keyword in query_text for keyword in keywords):
            semantic_bonus += 1.5

    density = overlap / math.sqrt(max(len(haystack_tokens), 1))
    return overlap + density + semantic_bonus


def _strip_markdown_fence(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fenced:
        return fenced.group(1)
    return text.strip()


def _extract_json_array(text: str) -> list[dict[str, object]] | None:
    stripped = _strip_markdown_fence(text)
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, list):
        return parsed

    start = stripped.find("[")
    while start != -1:
        depth = 0
        in_string = False
        escape = False
        for idx in range(start, len(stripped)):
            ch = stripped[idx]
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    candidate = stripped[start : idx + 1]
                    try:
                        parsed = json.loads(candidate)
                    except json.JSONDecodeError:
                        break
                    if isinstance(parsed, list):
                        return parsed
                    break
        start = stripped.find("[", start + 1)
    return None


class SearchExpressionMotionTool(Tool):
    """从 expression_motion.json 检索最相关的动作和表情候选。"""

    def __init__(
        self,
        provider_config: ProviderConfig | None = None,
        prompts_path: str | Path = DEFAULT_PROMPTS_PATH,
    ) -> None:
        self._provider_config = provider_config
        self._system_prompt = load_expression_motion_retriever_prompt(prompts_path)

    @property
    def name(self) -> str:
        return "search_expression_motion"

    @property
    def description(self) -> str:
        return (
            "仅从角色的 expression_motion.json 检索最符合当前场景描述的动作/表情候选。"
            "适合在 read_model 拿到合法动作列表后，按语义进一步缩小候选范围。"
        )

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "type": "object",
            "properties": {
                "character_id": {
                    "type": "string",
                    "description": "角色ID，例如 anon、soyo、taki。",
                },
                "query_text": {
                    "type": "string",
                    "description": "当前场景中与该角色相关的描写、对白或情绪描述。",
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回候选数量，默认 3，建议 1~5。",
                    "minimum": 1,
                    "maximum": 10,
                },
                "allowed_actions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "可选。只在这些 action 中检索，"
                        "例如 read_model 返回的 motions/expressions。"
                    ),
                },
            },
            "required": ["character_id", "query_text"],
        }

    async def execute(self, **kwargs: object) -> ToolResult:
        character_id = str(kwargs.get("character_id", "")).strip()
        query_text = str(kwargs.get("query_text", "")).strip()
        top_k = int(kwargs.get("top_k", 3) or 3)
        allowed_actions_raw = kwargs.get("allowed_actions", [])

        if not character_id:
            return ToolResult(success=False, error="缺少 'character_id' 参数")
        if not query_text:
            return ToolResult(success=False, error="缺少 'query_text' 参数")

        entries, source = _load_expression_motion_entries(character_id)
        if not entries:
            return ToolResult(
                success=False,
                error=f"未找到角色 {character_id} 的 expression_motion.json 数据",
            )

        allowed_actions = {
            action for action in allowed_actions_raw
            if isinstance(action, str) and action.startswith(f"{character_id}/")
        }
        if allowed_actions:
            entries = [entry for entry in entries if entry.action in allowed_actions]

        if not entries:
            return ToolResult(success=False, error="过滤后没有可检索的动作候选")

        top_k = max(1, min(top_k, 10, len(entries)))
        ranked = sorted(
            (
                {
                    "action": entry.action,
                    "description": entry.description,
                    "score": _heuristic_score(query_text, entry.action, entry.description),
                }
                for entry in entries
            ),
            key=lambda item: item["score"],
            reverse=True,
        )
        shortlist = ranked

        if self._provider_config is not None:
            try:
                llm_candidates = await self._rerank_with_llm(
                    character_id=character_id,
                    query_text=query_text,
                    source=source,
                    shortlist=shortlist,
                    top_k=top_k,
                )
                payload = {"candidates": llm_candidates}
                return ToolResult(success=True, output=json.dumps(payload, ensure_ascii=False))
            except Exception as exc:
                raw_output = exc.raw_output if isinstance(exc, LLMRerankError) else ""
                logger.warning(
                    "本地模型重排失败，回退到启发式检索: %s raw_output=%s",
                    exc,
                    raw_output[:500] if raw_output else "<empty>",
                )
                payload = {
                    "candidates": [
                        {
                            "action": item["action"],
                            "description": item["description"],
                            "score": round(float(item["score"]), 4),
                            "reason": "基于场景文本与动作描述的启发式匹配。",
                        }
                        for item in shortlist[:top_k]
                    ],
                }
                return ToolResult(success=True, output=json.dumps(payload, ensure_ascii=False))

        payload = {
            "candidates": [
                {
                    "action": item["action"],
                    "description": item["description"],
                    "score": round(float(item["score"]), 4),
                    "reason": "基于场景文本与动作描述的启发式匹配。",
                }
                for item in shortlist[:top_k]
            ],
        }
        return ToolResult(success=True, output=json.dumps(payload, ensure_ascii=False))

    async def _rerank_with_llm(
        self,
        *,
        character_id: str,
        query_text: str,
        source: str | None,
        shortlist: list[dict[str, object]],
        top_k: int,
    ) -> list[dict[str, object]]:
        assert self._provider_config is not None
        base_url = self._provider_config.base_url
        if base_url.endswith("/chat/completions"):
            base_url = base_url[: -len("/chat/completions")]
        client = AsyncOpenAI(
            api_key=self._provider_config.api_key or "sk-placeholder",
            base_url=base_url,
            timeout=180.0,
        )

        candidate_lines = [
            {
                "action": str(item["action"]),
                "description": str(item["description"]),
                "heuristic_score": round(float(item["score"]), 4),
            }
            for item in shortlist
        ]
        user_prompt = json.dumps(
            {
                "character_id": character_id,
                "source": source,
                "query_text": query_text,
                "top_k": top_k,
                "candidates": candidate_lines,
                "output_rules": {
                    "must_choose_from_candidates_only": True,
                    "allow_empty_array": True,
                    "max_items": top_k,
                    "return_json_only": True,
                },
            },
            ensure_ascii=False,
        )

        extra_kwargs: dict[str, Any] = {}
        if self._provider_config.reasoning_effort:
            extra_kwargs["reasoning_effort"] = self._provider_config.reasoning_effort
        if self._provider_config.extra_body:
            extra_kwargs["extra_body"] = self._provider_config.extra_body

        response = await client.chat.completions.create(
            model=self._provider_config.model,
            messages=[
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=min(self._provider_config.temperature, 0.3),
            max_tokens=min(self._provider_config.max_tokens, 1200),
            **extra_kwargs,
        )
        content = response.choices[0].message.content or "[]"
        parsed = _extract_json_array(content)
        if parsed is None:
            raise LLMRerankError("重排模型未返回合法 JSON", raw_output=content)

        shortlist_by_action = {str(item["action"]): item for item in shortlist}
        candidates: list[dict[str, object]] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            action = item.get("action")
            if not isinstance(action, str) or action not in shortlist_by_action:
                continue
            reason = item.get("reason", "")
            score = item.get("score", 0)
            original = shortlist_by_action[action]
            try:
                numeric_score = round(float(score), 4)
            except (TypeError, ValueError):
                numeric_score = round(float(original["score"]), 4)
            candidates.append(
                {
                    "action": action,
                    "description": str(original["description"]),
                    "score": numeric_score,
                    "reason": str(reason).strip() or "本地模型认为该动作与场景语义更贴近。",
                }
            )
            if len(candidates) >= top_k:
                break

        return candidates
