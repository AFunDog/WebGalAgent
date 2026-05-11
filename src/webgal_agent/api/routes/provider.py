"""API 路由：供应商配置。"""

from __future__ import annotations

from fastapi import APIRouter

from webgal_agent.config.provider_manager import ProviderConfig, PROVIDER_PRESETS

router = APIRouter(prefix="/api/providers", tags=["providers"])


def _get_pm():
    """延迟获取供应商管理器，避免循环导入。"""
    from webgal_agent.api.app import get_provider_manager
    return get_provider_manager()


@router.get("")
async def list_providers() -> dict[str, object]:
    """列出所有智能体供应商配置。"""
    pm = _get_pm()
    result = {}
    for name, cfg in pm.list_all().items():
        result[name] = cfg.model_dump()
    return {
        "defaults": pm.get_defaults().model_dump(),
        "agents": result,
    }


@router.get("/presets")
async def list_presets() -> dict[str, dict[str, str]]:
    """列出可用的供应商预设。"""
    return PROVIDER_PRESETS


@router.get("/{agent_name}")
async def get_provider(agent_name: str) -> dict[str, object]:
    """获取指定智能体的供应商配置。"""
    pm = _get_pm()
    cfg = pm.get(agent_name)
    return cfg.model_dump()


@router.put("/{agent_name}")
async def update_provider(agent_name: str, config: ProviderConfig) -> dict[str, object]:
    """更新指定智能体的供应商配置。"""
    pm = _get_pm()
    pm.set(agent_name, config)
    return {"ok": True, "agent": agent_name}


@router.put("")
async def update_defaults(config: ProviderConfig) -> dict[str, object]:
    """更新默认供应商配置（应用于未覆盖的智能体）。"""
    pm = _get_pm()
    pm.set_defaults(config)
    return {"ok": True}
