"""基于多模态模型的角色动作素材描述器。"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import mimetypes
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from openai import AsyncOpenAI

from webgal_agent.config.prompt_config import extract_system_prompts, load_prompt_config
from webgal_agent.config.provider_manager import ProviderConfig, ProviderConfigManager

DEFAULT_PROVIDER_SLOT = "asset_describer"
DEFAULT_ASSET_ROOT = Path("data/figure_assets")
DEFAULT_OUTPUT_ROOT = Path("data/knowledge/characters")
DEFAULT_PROMPTS_PATH = Path("src/configs/prompts.yaml")
SUPPORTED_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")
SUPPORTED_VIDEO_SUFFIXES = (".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v")
DEFAULT_CHARACTER_ALIASES: dict[str, str] = {
    "anon": "千早爱音",
    "soyo": "长崎素世",
    "taki": "椎名立希",
    "tomori": "高松灯",
    "rana": "要乐奈",
}
DEFAULT_ASSET_DESCRIBER_PROMPT = (
    "你在为视觉小说脚本转换流程标注角色动作素材。"
    "只描述素材里能稳定观察到的表情、视线、姿态、动作趋势和整体气质。"
    "不要编造剧情，不要复述文件名。"
)


@dataclass(slots=True)
class CharacterAsset:
    character_id: str
    display_name: str
    asset_name: str
    state_name: str
    source_path: Path
    relative_path: str
    media_type: str


@dataclass(slots=True)
class AssetDescription:
    text: str


class AssetDescriber(Protocol):
    async def describe(self, asset: CharacterAsset) -> AssetDescription:
        """为单个素材生成结构化描述。"""


def _strip_markdown_fence(text: str) -> str:
    fenced = re.search(r"```(?:text|markdown)?\s*(.*?)\s*```", text, re.DOTALL)
    if fenced:
        return fenced.group(1)
    return text.strip()


def _guess_mime_type(path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(path.name)
    return mime_type or "application/octet-stream"


def _to_data_url(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{_guess_mime_type(path)};base64,{encoded}"


def _to_dashscope_file_uri(path: Path) -> str:
    resolved = path.resolve()
    if os.name == "nt":
        return f"file://{resolved.as_posix()}"
    return resolved.as_uri()


def _load_character_aliases(alias_path: Path | None) -> dict[str, str]:
    aliases = dict(DEFAULT_CHARACTER_ALIASES)
    if alias_path is None or not alias_path.exists():
        return aliases

    if alias_path.suffix.lower() == ".json":
        data = json.loads(alias_path.read_text(encoding="utf-8"))
    else:
        import yaml

        data = yaml.safe_load(alias_path.read_text(encoding="utf-8"))

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(key, str) and isinstance(value, str):
                aliases[key] = value
    return aliases


def load_asset_describer_prompt(prompts_path: str | Path = DEFAULT_PROMPTS_PATH) -> str:
    prompt_config = load_prompt_config(prompts_path)
    prompts = extract_system_prompts(prompt_config)
    prompt = prompts.get("asset_describer", "").strip()
    return prompt or DEFAULT_ASSET_DESCRIBER_PROMPT


def _is_supported_media(path: Path) -> bool:
    suffix = path.suffix.lower()
    return suffix in SUPPORTED_IMAGE_SUFFIXES or suffix in SUPPORTED_VIDEO_SUFFIXES


def _detect_media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in SUPPORTED_IMAGE_SUFFIXES:
        return "image"
    if suffix in SUPPORTED_VIDEO_SUFFIXES:
        return "video"
    return "file"


def _extract_state_name(asset_path: Path, character_id: str) -> str | None:
    stem = asset_path.stem
    if "__" not in stem:
        return stem or None

    prefix, state_name = stem.split("__", 1)
    if prefix and prefix != character_id:
        return None
    return state_name or None


def discover_character_assets(
    asset_root: Path,
    alias_map: dict[str, str],
    character_filter: set[str] | None = None,
) -> list[CharacterAsset]:
    assets: list[CharacterAsset] = []
    if not asset_root.exists():
        return assets

    for character_dir in sorted(asset_root.iterdir()):
        if not character_dir.is_dir() or character_dir.name.startswith("."):
            continue

        character_id = character_dir.name
        if character_filter and character_id not in character_filter:
            continue

        display_name = alias_map.get(character_id, character_id)
        for asset_path in sorted(path for path in character_dir.rglob("*") if path.is_file()):
            if not _is_supported_media(asset_path):
                continue
            relative_parts = asset_path.relative_to(character_dir).parts[:-1]
            if any(part.startswith(".") for part in relative_parts):
                continue

            state_name = _extract_state_name(asset_path, character_id)
            if state_name is None:
                continue

            assets.append(
                CharacterAsset(
                    character_id=character_id,
                    display_name=display_name,
                    asset_name=asset_path.stem,
                    state_name=state_name,
                    source_path=asset_path,
                    relative_path=asset_path.relative_to(character_dir).as_posix(),
                    media_type=_detect_media_type(asset_path),
                )
            )
    return assets


class OpenAIMultimodalAssetDescriber:
    """调用 OpenAI 兼容多模态模型描述动作素材。"""

    def __init__(self, provider_config: ProviderConfig, system_prompt: str) -> None:
        base_url = provider_config.base_url
        if base_url.endswith("/chat/completions"):
            base_url = base_url[: -len("/chat/completions")]
        self._config = provider_config
        self._system_prompt = system_prompt.strip() or DEFAULT_ASSET_DESCRIBER_PROMPT
        self._client = AsyncOpenAI(
            api_key=provider_config.api_key or "sk-placeholder",
            base_url=base_url,
            timeout=180.0,
        )

    async def describe(self, asset: CharacterAsset) -> AssetDescription:
        content: list[dict[str, Any]] = [
            {
                "type": "input_text",
                "text": (
                    f"{self._system_prompt} "
                    f"角色ID={asset.character_id}，状态名={asset.state_name}，"
                    f"素材类型={asset.media_type}，相对路径={asset.relative_path}。"
                ),
            }
        ]

        if asset.media_type == "image":
            content.append(
                {
                    "type": "input_image",
                    "image_url": _to_data_url(asset.source_path),
                    "detail": "high",
                }
            )
        else:
            content.append(
                {
                    "type": "input_file",
                    "filename": asset.source_path.name,
                    "file_data": _to_data_url(asset.source_path),
                    "detail": "high",
                }
            )

        extra_kwargs: dict[str, Any] = {}
        if self._config.reasoning_effort:
            extra_kwargs["reasoning"] = {"effort": self._config.reasoning_effort}
        if self._config.extra_body:
            extra_kwargs["extra_body"] = self._config.extra_body

        response = await self._client.responses.create(
            model=self._config.model,
            input=[{"role": "user", "content": content}],
            temperature=min(self._config.temperature, 0.3),
            max_output_tokens=min(self._config.max_tokens, 1200),
            text={"verbosity": "low"},
            **extra_kwargs,
        )
        return AssetDescription(text=_strip_markdown_fence(response.output_text))


class DashScopeMultimodalAssetDescriber:
    """调用 DashScope 原生多模态 SDK 描述动作素材。"""

    def __init__(self, provider_config: ProviderConfig, system_prompt: str) -> None:
        self._config = provider_config
        self._system_prompt = system_prompt.strip() or DEFAULT_ASSET_DESCRIBER_PROMPT

    async def describe(self, asset: CharacterAsset) -> AssetDescription:
        return await asyncio.to_thread(self._describe_sync, asset)

    def _describe_sync(self, asset: CharacterAsset) -> AssetDescription:
        try:
            import dashscope
            from dashscope import MultiModalConversation
        except ImportError as exc:
            raise RuntimeError(
                "DashScope provider 需要安装 `dashscope` 包。"
            ) from exc

        if self._config.base_url:
            dashscope.base_http_api_url = self._config.base_url

        media_payload: dict[str, Any]
        if asset.media_type == "video":
            media_payload = {
                "video": _to_dashscope_file_uri(asset.source_path),
                "fps": self._config.extra_body.get("fps", 2) if self._config.extra_body else 2,
            }
        else:
            media_payload = {"image": _to_dashscope_file_uri(asset.source_path)}

        prompt = (
            f"{self._system_prompt} "
            f"角色ID={asset.character_id}，状态名={asset.state_name}，"
            f"素材类型={asset.media_type}，相对路径={asset.relative_path}。"
            " 请直接输出一段中文描述文本，不要输出 JSON、标题、列表或额外解释。"
        )

        response = MultiModalConversation.call(
            api_key=self._config.api_key or os.getenv("DASHSCOPE_API_KEY"),
            model=self._config.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        media_payload,
                        {"text": prompt},
                    ],
                }
            ],
        )

        try:
            raw_text = response.output.choices[0].message.content[0]["text"]
        except (AttributeError, IndexError, KeyError, TypeError) as exc:
            raise RuntimeError(f"无法解析 DashScope 响应: {response}") from exc

        return AssetDescription(text=_strip_markdown_fence(raw_text))


def build_asset_describer(provider_config: ProviderConfig, system_prompt: str) -> AssetDescriber:
    provider_name = provider_config.provider.lower().strip()
    if provider_name == "dashscope":
        return DashScopeMultimodalAssetDescriber(provider_config, system_prompt)
    return OpenAIMultimodalAssetDescriber(provider_config, system_prompt)


def _build_output_payload(
    character_assets: list[CharacterAsset],
    descriptions: dict[str, AssetDescription],
) -> list[dict[str, Any]]:
    return [
        {
            "action": f"{asset.character_id}/{asset.state_name}",
            "description": descriptions[asset.relative_path].text,
        }
        for asset in character_assets
    ]


async def generate_character_asset_json(
    assets: list[CharacterAsset],
    describer: AssetDescriber,
    output_root: Path,
    dry_run: bool = False,
) -> list[Path]:
    grouped: dict[str, list[CharacterAsset]] = defaultdict(list)
    for asset in assets:
        grouped[asset.display_name].append(asset)

    written_paths: list[Path] = []
    for display_name, character_assets in grouped.items():
        descriptions: dict[str, AssetDescription] = {}
        for asset in character_assets:
            descriptions[asset.relative_path] = await describer.describe(asset)

        payload = _build_output_payload(character_assets, descriptions)
        output_path = output_root / display_name / "expression_motion.json"
        if not dry_run:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        written_paths.append(output_path)
    return written_paths


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="为角色动作素材生成多模态 JSON 描述文件")
    parser.add_argument(
        "--asset-root",
        default=str(DEFAULT_ASSET_ROOT),
        help="角色素材根目录，默认 data/figure_assets",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="输出目录根路径，默认 data/knowledge/characters",
    )
    parser.add_argument(
        "--providers-path",
        default=os.getenv("WEBGAL_PROVIDERS_PATH", "src/configs/providers.yaml"),
        help="providers.yaml 路径",
    )
    parser.add_argument(
        "--prompts-path",
        default=os.getenv("WEBGAL_PROMPTS_PATH", str(DEFAULT_PROMPTS_PATH)),
        help="prompts.yaml 路径",
    )
    parser.add_argument(
        "--provider-slot",
        default=DEFAULT_PROVIDER_SLOT,
        help="provider 槽位名，默认 asset_describer",
    )
    parser.add_argument(
        "--alias-map",
        default="",
        help="角色ID到展示名/知识库目录名的映射文件（json/yaml）",
    )
    parser.add_argument(
        "--character-id",
        action="append",
        default=[],
        help="只处理指定角色ID，可重复传入",
    )
    parser.add_argument("--dry-run", action="store_true", help="只演算不写文件")
    return parser


async def _async_main(args: argparse.Namespace) -> int:
    alias_path = Path(args.alias_map) if args.alias_map else None
    alias_map = _load_character_aliases(alias_path)
    provider_manager = ProviderConfigManager(args.providers_path)
    provider_config = provider_manager.get(args.provider_slot)
    system_prompt = load_asset_describer_prompt(args.prompts_path)

    assets = discover_character_assets(
        asset_root=Path(args.asset_root),
        alias_map=alias_map,
        character_filter=set(args.character_id) if args.character_id else None,
    )
    if not assets:
        print("未发现符合条件的动作素材")
        return 1

    describer = build_asset_describer(provider_config, system_prompt)
    written = await generate_character_asset_json(
        assets=assets,
        describer=describer,
        output_root=Path(args.output_root),
        dry_run=args.dry_run,
    )
    action = "将写入" if args.dry_run else "已写入"
    print(f"{action}以下描述文件：")
    for path in written:
        print(f"- {path}")
    return 0


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()
    return asyncio.run(_async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
