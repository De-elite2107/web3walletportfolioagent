"""Model-tier resolution, backed by models.yaml + the MODEL_TIER env var.

Lets you switch which model the AI gateway calls (draft / production /
premium) without touching code - just change MODEL_TIER in .env.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml

from app.config import settings

REPO_ROOT = Path(__file__).resolve().parents[2]
MODELS_CONFIG_PATH = Path(__file__).resolve().parents[1] / "models.yaml"


@dataclass(frozen=True)
class ModelTier:
    name: str
    model: str
    description: str


def _load_config() -> dict:
    with open(MODELS_CONFIG_PATH) as f:
        return yaml.safe_load(f)


_config = _load_config()
_tiers: dict[str, ModelTier] = {
    name: ModelTier(name=name, model=spec["model"], description=spec.get("description", "").strip())
    for name, spec in _config["tiers"].items()
}
_default_tier_name = _config.get("default_tier", "draft")


def get_tier(tier_name: str | None = None) -> ModelTier:
    """Resolve a tier name to its ModelTier config.

    Falls back to models.yaml's default_tier, then hardcoded "draft", if
    tier_name is not given. Raises ValueError for an unknown tier name -
    better to fail loudly than silently fall back to a different tier and
    surprise someone on spend.
    """
    name = tier_name or _default_tier_name
    try:
        return _tiers[name]
    except KeyError:
        known = ", ".join(sorted(_tiers))
        raise ValueError(f"Unknown model tier {name!r} - expected one of: {known}") from None


def current_tier() -> ModelTier:
    """The tier selected by MODEL_TIER in .env (default: draft)."""
    return get_tier(settings.model_tier)
