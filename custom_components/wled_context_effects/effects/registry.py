"""Effect registry for dynamic effect discovery and registration."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Type

from ..errors import EffectNotFoundError

if TYPE_CHECKING:
    from .base import WLEDEffectBase

_LOGGER = logging.getLogger(__name__)


class EffectRegistry:
    """Registry for available effects.
    
    This registry maintains a mapping of effect names to effect classes,
    enabling dynamic effect discovery, listing, and instantiation.
    """

    def __init__(self) -> None:
        """Initialize the effect registry."""
        self._effects: dict[str, Type[WLEDEffectBase]] = {}
        _LOGGER.debug("Effect registry initialized")

    def register(self, effect_class: Type[WLEDEffectBase]) -> None:
        """Register an effect class.

        Args:
            effect_class: Effect class to register
        """
        name = effect_class.__name__
        if name in self._effects:
            _LOGGER.warning(
                "Effect %s is already registered, overwriting",
                name,
            )
        self._effects[name] = effect_class
        _LOGGER.info("Registered effect: %s", name)

    def unregister(self, name: str) -> None:
        """Unregister an effect by name.

        Args:
            name: Name of effect to unregister
        """
        if name in self._effects:
            del self._effects[name]
            _LOGGER.info("Unregistered effect: %s", name)
        else:
            _LOGGER.warning("Attempted to unregister unknown effect: %s", name)

    def get_effect_class(self, name: str) -> Type[WLEDEffectBase]:
        """Get effect class by name.

        Args:
            name: Name of effect class

        Returns:
            Effect class

        Raises:
            EffectNotFoundError: If effect not found
        """
        if name not in self._effects:
            _LOGGER.error("Effect %s not found in registry", name)
            raise EffectNotFoundError(f"Effect '{name}' is not registered")

        return self._effects[name]

    def list_effects(self) -> list[str]:
        """List all registered effect names.

        Returns:
            List of effect names
        """
        return list(self._effects.keys())

    def get_effect_info(self, name: str) -> dict[str, Any]:
        """Get information about an effect.

        Args:
            name: Name of effect

        Returns:
            Dict with effect information

        Raises:
            EffectNotFoundError: If effect not found
        """
        effect_class = self.get_effect_class(name)

        return {
            "name": name,
            "description": effect_class.__doc__ or "No description available",
            "config_schema": effect_class.config_schema(),
        }

    def get_all_effects_info(self) -> dict[str, dict[str, Any]]:
        """Get information about all registered effects.

        Returns:
            Dict mapping effect names to their information
        """
        return {
            name: self.get_effect_info(name)
            for name in self.list_effects()
        }

    def clear(self) -> None:
        """Clear all registered effects."""
        _LOGGER.info("Clearing effect registry")
        self._effects.clear()


# Global registry instance
EFFECT_REGISTRY = EffectRegistry()


def register_effect(cls: Type[WLEDEffectBase]) -> Type[WLEDEffectBase]:
    """Decorator to register an effect class.

    Example:
        @register_effect
        class MyEffect(WLEDEffectBase):
            ...

    Args:
        cls: Effect class to register

    Returns:
        The same class (for decorator chaining)
    """
    EFFECT_REGISTRY.register(cls)
    return cls
