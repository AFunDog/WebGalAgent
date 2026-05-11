"""API route: provider configuration."""

from __future__ import annotations

from fastapi import APIRouter

from webgal_agent.config.provider_manager import ProviderConfig, PROVIDER_PRESETS

router = APIRouter(prefix="/api/providers", tags=["providers"])


def _get_pm():
    """Lazily get the provider manager to avoid circular imports."""
    from webgal_agent.api.app import get_provider_manager
    return get_provider_manager()


@router.get("")
async def list_providers() -> dict[str, object]:
    """List all agent provider configurations."""
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
    """List available provider presets."""
    return PROVIDER_PRESETS


@router.get("/{agent_name}")
async def get_provider(agent_name: str) -> dict[str, object]:
    """Get provider config for a specific agent."""
    pm = _get_pm()
    cfg = pm.get(agent_name)
    return cfg.model_dump()


@router.put("/{agent_name}")
async def update_provider(agent_name: str, config: ProviderConfig) -> dict[str, object]:
    """Update provider config for a specific agent."""
    pm = _get_pm()
    pm.set(agent_name, config)
    return {"ok": True, "agent": agent_name}


@router.put("")
async def update_defaults(config: ProviderConfig) -> dict[str, object]:
    """Update default provider config (applied to agents without overrides)."""
    pm = _get_pm()
    pm.set_defaults(config)
    return {"ok": True}
