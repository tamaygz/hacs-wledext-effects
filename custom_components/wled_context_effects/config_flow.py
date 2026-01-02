"""Config flow for WLED Effects integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.wled import DOMAIN as WLED_DOMAIN
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .const import (
    CONF_AUTO_DETECT,
    CONF_AUTO_START,
    CONF_BRIGHTNESS,
    CONF_EFFECT_CONFIG,
    CONF_EFFECT_NAME,
    CONF_EFFECT_TYPE,
    CONF_ENABLED,
    CONF_SEGMENT_ID,
    CONF_START_LED,
    CONF_STOP_LED,
    CONF_WLED_DEVICE_ID,
    CONF_WLED_HOST,
    DEFAULT_AUTO_START,
    DEFAULT_BRIGHTNESS,
    DEFAULT_ENABLED,
    DEFAULT_SEGMENT_ID,
    DOMAIN,
)
from .effects import EFFECT_REGISTRY
from .errors import EffectNotFoundError
from .wled_manager import WLEDConnectionManager

_LOGGER = logging.getLogger(__name__)


class WLEDEffectsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WLED Effects."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._wled_device_id: str | None = None
        self._wled_host: str | None = None
        self._effect_type: str | None = None
        self._effect_config: dict[str, Any] = {}
        self._reauth_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - select WLED device."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check if manual host was provided
            if user_input.get(CONF_WLED_HOST):
                self._wled_host = user_input[CONF_WLED_HOST].strip()
                
                # Validate host format
                if not self._wled_host:
                    errors[CONF_WLED_HOST] = "invalid_host"
                else:
                    # Test connection
                    connection_manager = WLEDConnectionManager(self.hass)
                    try:
                        if not await connection_manager.test_connection(self._wled_host):
                            errors[CONF_WLED_HOST] = "cannot_connect"
                        else:
                            return await self.async_step_effect_type()
                    except Exception as err:
                        _LOGGER.exception("Error testing connection to %s", self._wled_host)
                        errors[CONF_WLED_HOST] = "cannot_connect"
            
            # Or use selected device
            elif user_input.get(CONF_WLED_DEVICE_ID):
                self._wled_device_id = user_input[CONF_WLED_DEVICE_ID]
                
                # Get host from WLED config entries
                wled_entries = self.hass.config_entries.async_entries(WLED_DOMAIN)
                device_registry = dr.async_get(self.hass)
                
                for entry in wled_entries:
                    # Check if this entry's device matches our selected device
                    device = device_registry.async_get_device(
                        identifiers={(WLED_DOMAIN, entry.unique_id)}
                    )
                    if device and device.id == self._wled_device_id:
                        self._wled_host = entry.data.get("host")
                        break
                
                if not self._wled_host:
                    _LOGGER.error(
                        "Could not find host for device %s. Available WLED entries: %s",
                        self._wled_device_id,
                        [e.entry_id for e in wled_entries],
                    )
                    errors[CONF_WLED_DEVICE_ID] = "device_not_found"
                else:
                    return await self.async_step_effect_type()
            else:
                errors["base"] = "no_device_selected"

        # Get available WLED devices
        wled_devices = await self._async_get_wled_devices()
        
        if not wled_devices and not errors:
            # No WLED devices found, force manual entry
            data_schema = vol.Schema({
                vol.Required(CONF_WLED_HOST): str,
            })
        else:
            data_schema = vol.Schema({
                vol.Optional(CONF_WLED_DEVICE_ID): vol.In(wled_devices),
                vol.Optional(CONF_WLED_HOST): str,
            })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_effect_type(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle effect type selection step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._effect_type = user_input[CONF_EFFECT_TYPE]
            
            # Validate effect type exists
            try:
                EFFECT_REGISTRY.get_effect_class(self._effect_type)
                return await self.async_step_configure()
            except EffectNotFoundError:
                errors["base"] = "unknown"

        # Get available effects
        effects = EFFECT_REGISTRY.list_effects()
        effect_options = {effect: effect for effect in effects}

        return self.async_show_form(
            step_id="effect_type",
            data_schema=vol.Schema({
                vol.Required(CONF_EFFECT_TYPE): vol.In(effect_options),
            }),
            errors=errors,
            description_placeholders={"effect_count": str(len(effects))},
        )

    async def async_step_configure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle effect configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Extract common fields
            effect_name = user_input[CONF_EFFECT_NAME].strip()
            segment_id = user_input[CONF_SEGMENT_ID]
            brightness = user_input[CONF_BRIGHTNESS]
            auto_start = user_input.get(CONF_AUTO_START, DEFAULT_AUTO_START)
            auto_detect = user_input.get(CONF_AUTO_DETECT, True)

            # Validate effect name
            if not effect_name:
                errors[CONF_EFFECT_NAME] = "empty_name"

            # Handle LED range
            if auto_detect:
                start_led = None
                stop_led = None
            else:
                start_led = user_input.get(CONF_START_LED)
                stop_led = user_input.get(CONF_STOP_LED)
                
                if start_led is not None and stop_led is not None:
                    if start_led > stop_led:
                        errors[CONF_START_LED] = "invalid_led_range"
                    elif start_led < 0:
                        errors[CONF_START_LED] = "negative_value"
                    elif stop_led < 0:
                        errors[CONF_STOP_LED] = "negative_value"

            if not errors:
                # Get effect-specific config
                effect_class = EFFECT_REGISTRY.get_effect_class(self._effect_type)
                effect_schema = effect_class.config_schema()
                
                # Extract effect-specific fields
                effect_config = {}
                common_fields = {
                    CONF_EFFECT_NAME, CONF_SEGMENT_ID, CONF_BRIGHTNESS,
                    CONF_START_LED, CONF_STOP_LED, CONF_AUTO_START,
                    CONF_AUTO_DETECT, CONF_ENABLED
                }
                for key, value_schema in effect_schema.get("properties", {}).items():
                    if key in user_input and key not in common_fields:
                        effect_config[key] = user_input[key]

                # Set unique ID based on device+segment to prevent duplicates
                unique_id = f"{self._wled_host}_{segment_id}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                # Create config entry
                data = {
                    CONF_WLED_HOST: self._wled_host,
                    CONF_EFFECT_TYPE: self._effect_type,
                }
                
                if self._wled_device_id:
                    data[CONF_WLED_DEVICE_ID] = self._wled_device_id

                options = {
                    CONF_EFFECT_NAME: effect_name,
                    CONF_SEGMENT_ID: segment_id,
                    CONF_BRIGHTNESS: brightness,
                    CONF_AUTO_START: auto_start,
                    CONF_ENABLED: DEFAULT_ENABLED,
                    CONF_EFFECT_CONFIG: effect_config,
                }
                
                if start_led is not None:
                    options[CONF_START_LED] = start_led
                if stop_led is not None:
                    options[CONF_STOP_LED] = stop_led

                return self.async_create_entry(
                    title=effect_name,
                    data=data,
                    options=options,
                )

        # Build schema dynamically based on effect type
        schema_dict = {
            vol.Required(CONF_EFFECT_NAME, default=f"{self._effect_type} Effect"): str,
            vol.Required(CONF_SEGMENT_ID, default=DEFAULT_SEGMENT_ID): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=31)
            ),
            vol.Required(CONF_BRIGHTNESS, default=DEFAULT_BRIGHTNESS): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=255)
            ),
            vol.Optional(CONF_AUTO_START, default=DEFAULT_AUTO_START): bool,
            vol.Optional(CONF_AUTO_DETECT, default=True): bool,
        }

        # Add LED range fields if auto-detect is not selected
        # (In actual form, these would be conditionally shown)
        schema_dict.update({
            vol.Optional(CONF_START_LED): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=1000)
            ),
            vol.Optional(CONF_STOP_LED): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=1000)
            ),
        })

        # Add effect-specific fields
        try:
            effect_class = EFFECT_REGISTRY.get_effect_class(self._effect_type)
            effect_schema = effect_class.config_schema()
            
            for key, value_schema in effect_schema.get("properties", {}).items():
                # Skip common fields already added
                if key in (CONF_EFFECT_NAME, CONF_SEGMENT_ID, CONF_BRIGHTNESS,
                          CONF_START_LED, CONF_STOP_LED):
                    continue
                
                # Add effect-specific field
                field_type = value_schema.get("type", "string")
                default = value_schema.get("default")
                
                if field_type == "integer":
                    minimum = value_schema.get("minimum", 0)
                    maximum = value_schema.get("maximum", 100)
                    schema_dict[vol.Optional(key, default=default)] = vol.All(
                        vol.Coerce(int), vol.Range(min=minimum, max=maximum)
                    )
                elif field_type == "number":
                    minimum = value_schema.get("minimum", 0.0)
                    maximum = value_schema.get("maximum", 100.0)
                    schema_dict[vol.Optional(key, default=default)] = vol.All(
                        vol.Coerce(float), vol.Range(min=minimum, max=maximum)
                    )
                elif field_type == "boolean":
                    schema_dict[vol.Optional(key, default=default or False)] = bool
                else:
                    schema_dict[vol.Optional(key, default=default or "")] = str
        
        except Exception as err:
            _LOGGER.error("Error building config schema: %s", err)

        return self.async_show_form(
            step_id="configure",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={"effect_type": self._effect_type},
        )

    async def _async_get_wled_devices(self) -> dict[str, str]:
        """Get available WLED devices.

        Returns:
            Dict mapping device IDs to device names
        """
        devices = {}
        device_registry = dr.async_get(self.hass)
        
        # Get all WLED config entries
        wled_entries = self.hass.config_entries.async_entries(WLED_DOMAIN)
        
        for entry in wled_entries:
            # Find device for this entry
            device = device_registry.async_get_device(
                identifiers={(WLED_DOMAIN, entry.unique_id)}
            )
            if device:
                devices[device.id] = f"{device.name or entry.title}"
        
        return devices

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration of the integration."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if entry is None:
            return self.async_abort(reason="reconfigure_failed")

        errors: dict[str, str] = {}

        if user_input is not None:
            # Check if manual host was provided
            if user_input.get(CONF_WLED_HOST):
                new_host = user_input[CONF_WLED_HOST].strip()
                
                # Validate host format
                if not new_host:
                    errors[CONF_WLED_HOST] = "invalid_host"
                else:
                    # Test connection
                    connection_manager = WLEDConnectionManager(self.hass)
                    try:
                        if not await connection_manager.test_connection(new_host):
                            errors[CONF_WLED_HOST] = "cannot_connect"
                        else:
                            # Update the config entry
                            return self.async_update_reload_and_abort(
                                entry,
                                data={**entry.data, CONF_WLED_HOST: new_host},
                                reason="reconfigure_successful",
                            )
                    except Exception as err:
                        _LOGGER.exception("Error testing connection during reconfigure")
                        errors[CONF_WLED_HOST] = "cannot_connect"
            else:
                errors["base"] = "no_device_selected"

        # Show form with current host
        current_host = entry.data.get(CONF_WLED_HOST, "")
        data_schema = vol.Schema({
            vol.Required(CONF_WLED_HOST, default=current_host): str,
        })

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={"current_host": current_host},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> WLEDEffectsOptionsFlow:
        """Get the options flow for this handler."""
        return WLEDEffectsOptionsFlow(config_entry)


class WLEDEffectsOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for WLED Effects."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate effect name
            effect_name = user_input.get(CONF_EFFECT_NAME, "").strip()
            if not effect_name:
                errors[CONF_EFFECT_NAME] = "empty_name"

            # Validate LED range if provided
            start_led = user_input.get(CONF_START_LED)
            stop_led = user_input.get(CONF_STOP_LED)
            
            if start_led is not None and stop_led is not None:
                if start_led > stop_led:
                    errors[CONF_START_LED] = "invalid_led_range"
                elif start_led < 0:
                    errors[CONF_START_LED] = "negative_value"
                elif stop_led < 0:
                    errors[CONF_STOP_LED] = "negative_value"
            
            if not errors:
                # Extract effect-specific config separately
                effect_type = self._config_entry.data.get(CONF_EFFECT_TYPE, "")
                effect_config = {}
                common_fields = {
                    CONF_EFFECT_NAME, CONF_SEGMENT_ID, CONF_BRIGHTNESS,
                    CONF_START_LED, CONF_STOP_LED, CONF_AUTO_START, CONF_ENABLED
                }
                
                try:
                    effect_class = EFFECT_REGISTRY.get_effect_class(effect_type)
                    effect_schema = effect_class.config_schema()
                    
                    for key, value_schema in effect_schema.get("properties", {}).items():
                        if key in user_input and key not in common_fields:
                            effect_config[key] = user_input[key]
                except Exception as err:
                    _LOGGER.error("Error extracting effect config: %s", err)

                # Build options dict with effect config nested
                options_data = {
                    CONF_EFFECT_NAME: effect_name,
                    CONF_SEGMENT_ID: user_input[CONF_SEGMENT_ID],
                    CONF_BRIGHTNESS: user_input[CONF_BRIGHTNESS],
                    CONF_AUTO_START: user_input.get(CONF_AUTO_START, DEFAULT_AUTO_START),
                    CONF_ENABLED: user_input.get(CONF_ENABLED, DEFAULT_ENABLED),
                    CONF_EFFECT_CONFIG: effect_config,
                }
                
                if start_led is not None:
                    options_data[CONF_START_LED] = start_led
                if stop_led is not None:
                    options_data[CONF_STOP_LED] = stop_led

                return self.async_create_entry(title="", data=options_data)

        # Get current options
        options = self._config_entry.options
        effect_type = self._config_entry.data.get(CONF_EFFECT_TYPE, "")

        # Build schema with current values
        schema_dict = {
            vol.Required(
                CONF_EFFECT_NAME,
                default=options.get(CONF_EFFECT_NAME, ""),
            ): str,
            vol.Required(
                CONF_SEGMENT_ID,
                default=options.get(CONF_SEGMENT_ID, DEFAULT_SEGMENT_ID),
            ): vol.All(vol.Coerce(int), vol.Range(min=0, max=31)),
            vol.Required(
                CONF_BRIGHTNESS,
                default=options.get(CONF_BRIGHTNESS, DEFAULT_BRIGHTNESS),
            ): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
            vol.Optional(
                CONF_START_LED,
                default=options.get(CONF_START_LED),
            ): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=0, max=1000))),
            vol.Optional(
                CONF_STOP_LED,
                default=options.get(CONF_STOP_LED),
            ): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=0, max=1000))),
            vol.Optional(
                CONF_AUTO_START,
                default=options.get(CONF_AUTO_START, DEFAULT_AUTO_START),
            ): bool,
            vol.Optional(
                CONF_ENABLED,
                default=options.get(CONF_ENABLED, DEFAULT_ENABLED),
            ): bool,
        }

        # Add effect-specific fields
        try:
            effect_class = EFFECT_REGISTRY.get_effect_class(effect_type)
            effect_schema = effect_class.config_schema()
            effect_config = options.get(CONF_EFFECT_CONFIG, {})
            
            for key, value_schema in effect_schema.get("properties", {}).items():
                # Skip common fields
                if key in (CONF_EFFECT_NAME, CONF_SEGMENT_ID, CONF_BRIGHTNESS,
                          CONF_START_LED, CONF_STOP_LED):
                    continue
                
                current_value = effect_config.get(key, value_schema.get("default"))
                field_type = value_schema.get("type", "string")
                
                if field_type == "integer":
                    minimum = value_schema.get("minimum", 0)
                    maximum = value_schema.get("maximum", 100)
                    schema_dict[vol.Optional(key, default=current_value)] = vol.All(
                        vol.Coerce(int), vol.Range(min=minimum, max=maximum)
                    )
                elif field_type == "number":
                    minimum = value_schema.get("minimum", 0.0)
                    maximum = value_schema.get("maximum", 100.0)
                    schema_dict[vol.Optional(key, default=current_value)] = vol.All(
                        vol.Coerce(float), vol.Range(min=minimum, max=maximum)
                    )
                elif field_type == "boolean":
                    schema_dict[vol.Optional(key, default=current_value or False)] = bool
                else:
                    schema_dict[vol.Optional(key, default=current_value or "")] = str
        
        except Exception as err:
            _LOGGER.error("Error building options schema: %s", err)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )
