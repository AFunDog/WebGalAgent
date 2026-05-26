"""WebGal 游戏素材扫描 API 路由。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from webgal_agent.tools._paths import resolve_asset_dir, resolve_asset_dirs, resolve_game_dir

router = APIRouter(prefix="/api/assets", tags=["assets"])

ASSET_CATEGORIES = ("animation", "background", "bgm", "figure")

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
    directory: str = Field(description="该类别实际扫描的目录路径")
    count: int
    files: list[AssetEntry]


class AssetsScanResponse(BaseModel):
    """全部素材类别的扫描结果。"""

    game_dir: str
    asset_dirs: dict[str, str]
    categories: list[AssetCategoryResponse]
    total_files: int


def _resolve_category_dir(category: str) -> Path | None:
    asset_dir = resolve_asset_dir(category)
    return asset_dir if asset_dir is not None else None


def _scan_directory(directory: Path | None, extensions: set[str]) -> list[AssetEntry]:
    """递归扫描目录，收集匹配指定扩展名的文件。"""
    entries: list[AssetEntry] = []
    if directory is None or not directory.exists():
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
    asset_dirs = resolve_asset_dirs()
    if not asset_dirs:
        raise HTTPException(
            status_code=404,
            detail="No asset directories configured",
        )

    categories: list[AssetCategoryResponse] = []
    total = 0

    for cat_name in ASSET_CATEGORIES:
        cat_path = _resolve_category_dir(cat_name)
        extensions = ASSET_EXTENSIONS.get(cat_name, set())
        files = _scan_directory(cat_path, extensions)
        total += len(files)
        categories.append(
            AssetCategoryResponse(
                category=cat_name,
                directory=str(cat_path) if cat_path is not None else "",
                count=len(files),
                files=files,
            )
        )

    return AssetsScanResponse(
        game_dir=str(resolve_game_dir() or ""),
        asset_dirs={name: str(path) for name, path in asset_dirs.items()},
        categories=categories,
        total_files=total,
    )


@router.get("/scan/{category}", response_model=AssetCategoryResponse)
async def scan_asset_category(category: str) -> AssetCategoryResponse:
    """扫描指定的素材类别。"""
    if category not in ASSET_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown category '{category}'. Valid: {list(ASSET_CATEGORIES)}",
        )

    cat_path = _resolve_category_dir(category)
    if cat_path is None or not cat_path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"Asset directory not found for category '{category}': "
                f"{str(cat_path) if cat_path is not None else '(not configured)'}"
            ),
        )

    extensions = ASSET_EXTENSIONS.get(category, set())
    files = _scan_directory(cat_path, extensions)

    return AssetCategoryResponse(
        category=category,
        directory=str(cat_path),
        count=len(files),
        files=files,
    )
