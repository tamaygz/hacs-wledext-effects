"""Effect module initialization and discovery."""
from __future__ import annotations

import importlib
import logging
import pkgutil
from pathlib import Path
from typing import TYPE_CHECKING

from .base import EffectProtocol, WLEDEffectBase
from .registry import EFFECT_REGISTRY, register_effect

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "EffectProtocol",
    "WLEDEffectBase",
    "EFFECT_REGISTRY",
    "register_effect",
    "discover_effects",
]


def discover_effects() -> None:
    """Discover and import all effect modules.
    
    This function scans the effects directory for Python modules
    and imports them, which triggers the @register_effect decorators
    to register the effects with the global registry.
    """
    _LOGGER.info("Discovering effects...")

    effects_dir = Path(__file__).parent
    package_name = __package__

    # Find all Python modules in the effects directory
    for _, module_name, is_pkg in pkgutil.iter_modules([str(effects_dir)]):
        # Skip special modules
        if module_name in ("__init__", "base", "registry"):
            continue

        # Skip packages (subdirectories)
        if is_pkg:
            continue

        try:
            full_module_name = f"{package_name}.{module_name}"
            _LOGGER.debug("Importing effect module: %s", full_module_name)
            importlib.import_module(full_module_name)

        except Exception as err:
            _LOGGER.error(
                "Failed to import effect module %s: %s",
                module_name,
                err,
                exc_info=True,
            )

    discovered_effects = EFFECT_REGISTRY.list_effects()
    _LOGGER.info(
        "Effect discovery complete. Found %d effects: %s",
        len(discovered_effects),
        ", ".join(discovered_effects),
    )


# Auto-discover effects on module import
discover_effects()
