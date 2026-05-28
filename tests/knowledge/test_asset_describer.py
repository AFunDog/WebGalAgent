from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from webgal_agent.knowledge.asset_describer import (
    AssetDescription,
    CharacterAsset,
    _load_character_aliases,
    discover_character_assets,
    generate_character_asset_json,
)


def _make_temp_dir() -> Path:
    path = Path("data/temp") / f"pytest_asset_describer_{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_load_character_aliases_merges_custom_values() -> None:
    temp_dir = _make_temp_dir()
    alias_path = temp_dir / "aliases.json"
    alias_path.write_text(
        json.dumps({"anon": "测试爱音", "new": "新角色"}, ensure_ascii=False),
        encoding="utf-8",
    )

    try:
        aliases = _load_character_aliases(alias_path)

        assert aliases["anon"] == "测试爱音"
        assert aliases["new"] == "新角色"
        assert aliases["soyo"] == "长崎素世"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_discover_character_assets_parses_prefixed_names() -> None:
    temp_dir = _make_temp_dir()
    asset_dir = temp_dir / "anon"
    nested_dir = asset_dir / "alt"
    nested_dir.mkdir(parents=True)
    (asset_dir / "anon__smile01.png").write_bytes(b"png")
    (nested_dir / "idle02.webm").write_bytes(b"webm")
    (asset_dir / "mana__angry01.png").write_bytes(b"png")
    (asset_dir / "notes.txt").write_text("skip", encoding="utf-8")

    try:
        assets = discover_character_assets(temp_dir, {"anon": "千早爱音"})

        assert sorted(asset.state_name for asset in assets) == ["idle02", "smile01"]
        assert sorted(asset.media_type for asset in assets) == ["image", "video"]
        assert all(asset.display_name == "千早爱音" for asset in assets)
        assert {asset.relative_path for asset in assets} == {"alt/idle02.webm", "anon__smile01.png"}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


class _FakeDescriber:
    async def describe(self, asset: CharacterAsset) -> AssetDescription:
        return AssetDescription(
            summary=f"{asset.state_name} 的概述",
            emotion="平静",
            pose="站姿",
            cues=[asset.media_type, asset.state_name],
            usage="用于脚本转换",
            confidence="high",
            note="",
        )


async def test_generate_character_asset_json_writes_grouped_json() -> None:
    temp_dir = _make_temp_dir()
    output_root = temp_dir / "out"
    source_file = temp_dir / "anon" / "anon__smile01.png"
    source_file.parent.mkdir(parents=True)
    source_file.write_bytes(b"png")
    assets = [
        CharacterAsset(
            character_id="anon",
            display_name="千早爱音",
            asset_name="anon__smile01",
            state_name="smile01",
            source_path=source_file,
            relative_path="anon__smile01.png",
            media_type="image",
        )
    ]

    try:
        written = await generate_character_asset_json(
            assets=assets,
            describer=_FakeDescriber(),
            output_root=output_root,
        )

        assert written == [output_root / "千早爱音" / "expression_motion.json"]
        payload = json.loads(written[0].read_text(encoding="utf-8"))
        assert payload["character_id"] == "anon"
        assert payload["display_name"] == "千早爱音"
        assert payload["asset_count"] == 1
        assert payload["assets"][0]["state_name"] == "smile01"
        assert payload["assets"][0]["description"]["summary"] == "smile01 的概述"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
