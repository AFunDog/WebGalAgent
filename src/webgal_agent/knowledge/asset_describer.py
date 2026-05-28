"""基于多模态模型的角色动作素材描述器。"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import mimetypes
import os
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from webgal_agent.config.provider_manager import ProviderConfig, ProviderConfigManager

DEFAULT_PROVIDER_SLOT = "asset_describer"
DEFAULT_ASSET_ROOT = Path("data/figure_assets")
DEFAULT_OUTPUT_ROOT = Path("data/knowledge/characters")
SUPPORTED_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")
SUPPORTED_VIDEO_SUFFIXES = (".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v")
DEFAULT_CHARACTER_ALIASES: dict[str, str] = {
    "anon": "千早爱音",
    "soyo": "长崎素世",
    "taki": "椎名立希",
    "tomori": "高松灯",
    "rana": "要乐奈",
}


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
    summary: str
    emotion: str
    pose: str
    cues: list[str]
    usage: str
    confidence: str
    note: str = ""


class AssetDescriptionPayload(BaseModel):
    summary: str = Field(description="一句简洁中文概述，不重复状态名")
    emotion: str = Field(description="从素材中能观察出的情绪")
    pose: str = Field(description="姿态、朝向或动作主体")
    cues: list[str] = Field(description="可稳定观察到的关键线索")
    usage: str = Field(description="适合用于什么脚本演出场景")
    confidence: str = Field(description="high、medium、low 或 unsupported_video")
    note: str = Field(default="", description="补充限制、遮挡或视频兼容情况")


class AssetDescriber(Protocol):
    async def describe(self, asset: CharacterAsset) -> AssetDescription:
        """为单个素材生成结构化描述。"""


def _schema_for_payload() -> dict[str, Any]:
    schema = AssetDescriptionPayload.model_json_schema()
    schema["additionalProperties"] = False
    return schema


def _guess_mime_type(path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(path.name)
    return mime_type or "application/octet-stream"


def _to_data_url(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{_guess_mime_type(path)};base64,{encoded}"


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

    def __init__(self, provider_config: ProviderConfig) -> None:
        base_url = provider_config.base_url
        if base_url.endswith("/chat/completions"):
            base_url = base_url[: -len("/chat/completions")]
        self._config = provider_config
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
                    "你在为视觉小说脚本转换流程标注角色动作素材。"
                    "只描述素材里能稳定观察到的表情、视线、姿态、动作趋势和整体气质。"
                    "不要编造剧情，不要复述文件名。"
                    f" 角色ID={asset.character_id}，状态名={asset.state_name}，"
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
            text={
                "format": {
                    "type": "json_schema",
                    "name": "character_asset_description",
                    "schema": _schema_for_payload(),
                    "strict": True,
                },
                "verbosity": "low",
            },
            **extra_kwargs,
        )
        payload = AssetDescriptionPayload.model_validate_json(response.output_text)
        return AssetDescription(**payload.model_dump())


def _build_output_payload(
    display_name: str,
    character_assets: list[CharacterAsset],
    descriptions: dict[str, AssetDescription],
) -> dict[str, Any]:
    return {
        "character_id": character_assets[0].character_id,
        "display_name": display_name,
        "generated_at": datetime.now(UTC).isoformat(),
        "asset_count": len(character_assets),
        "assets": [
            {
                "asset_name": asset.asset_name,
                "state_name": asset.state_name,
                "media_type": asset.media_type,
                "relative_path": asset.relative_path,
                "source_path": asset.source_path.as_posix(),
                "description": asdict(descriptions[asset.relative_path]),
            }
            for asset in character_assets
        ],
    }


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

        payload = _build_output_payload(display_name, character_assets, descriptions)
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

    assets = discover_character_assets(
        asset_root=Path(args.asset_root),
        alias_map=alias_map,
        character_filter=set(args.character_id) if args.character_id else None,
    )
    if not assets:
        print("未发现符合条件的动作素材")
        return 1

    describer = OpenAIMultimodalAssetDescriber(provider_config)
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
