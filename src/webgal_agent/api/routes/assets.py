"""WebGal 游戏素材扫描 API 路由。"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/assets", tags=["assets"])

# 待扫描的子目录（相对于 game_dir）
ASSET_SUBDIRS = {
    "animation": "animation",
    "background": "background",
    "bgm": "bgm",
    "figure": "figure",
}

# 各素材类型包含的文件扩展名
ASSET_EXTENSIONS: dict[str, set[str]] = {
    "animation": {".json"},
    "background": {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"},
    "bgm": {".mp3", ".wav", ".ogg", ".m4a", ".flac"},
    "figure": {".png", ".json", ".webp"},
}


class AssetEntry(BaseModel):
    """单个素材文件条目。"""

    path: str = Field(description="相对于素材子目录根的路径")
    name: str = Field(description="包含扩展名的文件名")


class AssetCategoryResponse(BaseModel):
    """按类别分组的素材响应。"""

    category: str
    directory: str = Field(description="game_dir 下的子目录名")
    count: int
    files: list[AssetEntry]


class AssetsScanResponse(BaseModel):
    """全部素材类别的扫描结果。"""

    game_dir: str
    categories: list[AssetCategoryResponse]
    total_files: int


def _resolve_game_dir() -> Path:
    """从配置或环境变量解析游戏目录路径。"""
    game_dir = os.getenv("WEBGAL_GAME_DIR")
    if game_dir:
        return Path(game_dir)

    # 尝试从 configs/default.yaml 加载
    import yaml

    config_path = Path("configs/default.yaml")
    if config_path.exists():
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if data and isinstance(data, dict):
            assets_cfg = data.get("assets", {})
            dir_str = assets_cfg.get("game_dir", "")
            if dir_str:
                return Path(dir_str)

    return Path()


def _scan_directory(directory: Path, extensions: set[str]) -> list[AssetEntry]:
    """递归扫描目录，收集匹配指定扩展名的文件。"""
    entries: list[AssetEntry] = []
    if not directory.exists():
        return entries

    for file_path in sorted(directory.rglob("*")):
        if file_path.is_file() and file_path.suffix.lower() in extensions:
            rel_path = file_path.relative_to(directory).as_posix()
            entries.append(AssetEntry(path=rel_path, name=file_path.name))

    return entries


@router.get("/scan", response_model=AssetsScanResponse)
async def scan_assets() -> AssetsScanResponse:
    """扫描配置的游戏目录中的全部可用素材。

    按类别（animation、background、bgm、figure）分组返回文件列表。
    """
    game_dir = _resolve_game_dir()
    if not game_dir or not game_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Game directory not found: {game_dir or '(not configured)'}",
        )

    categories: list[AssetCategoryResponse] = []
    total = 0

    for cat_name, subdir in ASSET_SUBDIRS.items():
        cat_path = game_dir / subdir
        extensions = ASSET_EXTENSIONS.get(cat_name, set())
        files = _scan_directory(cat_path, extensions)
        total += len(files)
        categories.append(
            AssetCategoryResponse(
                category=cat_name,
                directory=subdir,
                count=len(files),
                files=files,
            )
        )

    return AssetsScanResponse(
        game_dir=str(game_dir),
        categories=categories,
        total_files=total,
    )


@router.get("/scan/{category}", response_model=AssetCategoryResponse)
async def scan_asset_category(category: str) -> AssetCategoryResponse:
    """扫描指定的素材类别。"""
    if category not in ASSET_SUBDIRS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown category '{category}'. Valid: {list(ASSET_SUBDIRS.keys())}",
        )

    game_dir = _resolve_game_dir()
    if not game_dir or not game_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Game directory not found: {game_dir or '(not configured)'}",
        )

    subdir = ASSET_SUBDIRS[category]
    cat_path = game_dir / subdir
    extensions = ASSET_EXTENSIONS.get(category, set())
    files = _scan_directory(cat_path, extensions)

    return AssetCategoryResponse(
        category=category,
        directory=subdir,
        count=len(files),
        files=files,
    )


def build_assets_context(game_dir: Path | None = None) -> str:
    """构建可用素材的文本摘要，用于注入智能体上下文。

    由 TaskManager 调用，将素材信息追加到 script_converter 的知识库上下文中。
    """
    if game_dir is None:
        game_dir = _resolve_game_dir()
    if not game_dir or not game_dir.exists():
        return ""

    parts: list[str] = ["# 可用素材清单\n"]
    parts.append(f"素材根目录: {game_dir}\n")

    for cat_name, subdir in ASSET_SUBDIRS.items():
        cat_path = game_dir / subdir
        extensions = ASSET_EXTENSIONS.get(cat_name, set())
        files = _scan_directory(cat_path, extensions)

        if not files:
            continue

        # 按子目录分组以提高可读性
        parts.append(f"\n## {cat_name} ({subdir}/)\n")
        parts.append(f"共 {len(files)} 个文件\n")

        # 按父目录归组文件
        dir_groups: dict[str, list[str]] = {}
        for f in files:
            parent = str(Path(f.path).parent)
            if parent == ".":
                parent = "(根目录)"
            dir_groups.setdefault(parent, []).append(f.name)

        for dir_name, file_names in sorted(dir_groups.items()):
            parts.append(f"\n### {dir_name}/\n")
            for name in file_names:
                # 对于立绘条目，显示相对于 figure/ 的路径
                f_entry = next(f for f in files if f.name == name)
                parts.append(f"- {f_entry.path}")

    return "\n".join(parts)
