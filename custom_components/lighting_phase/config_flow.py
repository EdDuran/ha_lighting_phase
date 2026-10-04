"""Config flow for Lighting Phase."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_DELAY_BRIGHTENING_MIN,
    CONF_DELAY_DARKENING_MIN,
    CONF_LUX_SENSOR,
    CONF_NAME,
    CONF_NOTIFY_TARGET,
    CONF_PHASE_SOUND,
    CONF_STORM_ENTER_DELAY_SEC,
    CONF_STORM_EXIT_DELAY_SEC,
    CONF_STORM_WINDOW_MIN,
    DEFAULT_DELAY_BRIGHTENING_MIN,
    DEFAULT_DELAY_DARKENING_MIN,
    DEFAULT_NAME,
    DEFAULT_STORM_ENTER_DELAY_SEC,
    DEFAULT_STORM_EXIT_DELAY_SEC,
    DEFAULT_STORM_WINDOW_MIN,
    DOMAIN,
    ELEV_NUMBER_KEYS,
    LUX_NUMBER_KEYS,
    NUMBER_DEFAULTS,
    NUMBER_ELEV_TOLERANCE,
    NUMBER_STORM_LUX_PERCENT,
)


def _numbers_schema(keys: list[str], min_v: float, max_v: float, step: float) -> dict:
    schema: dict = {}
    for key in keys:
        schema[vol.Required(key, default=NUMBER_DEFAULTS[key])] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=min_v, max=max_v, step=step, mode=selector.NumberSelectorMode.BOX
            )
        )
    return schema


class LightingPhaseConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle setup. Multiple instances are supported - one per zone,
    each with its own lux sensor (or elevation-only), thresholds, and
    device/entities."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_lux_thresholds()

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Optional(CONF_LUX_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_NOTIFY_TARGET, default=""): str,
                vol.Optional(CONF_PHASE_SOUND, default=""): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_lux_thresholds(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_elevation_thresholds()

        schema = vol.Schema(_numbers_schema(LUX_NUMBER_KEYS, 0, 1000, 1))
        return self.async_show_form(step_id="lux_thresholds", data_schema=schema)

    async def async_step_elevation_thresholds(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_storm()

        schema = vol.Schema(
            {
                **_numbers_schema(ELEV_NUMBER_KEYS, -10, 10, 0.1),
                vol.Required(
                    NUMBER_ELEV_TOLERANCE, default=NUMBER_DEFAULTS[NUMBER_ELEV_TOLERANCE]
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=30, step=0.5, mode=selector.NumberSelectorMode.BOX
                    )
                ),
            }
        )
        return self.async_show_form(step_id="elevation_thresholds", data_schema=schema)

    async def async_step_storm(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            self._data.update(user_input)
            title = self._data.get(CONF_NAME) or DEFAULT_NAME
            return self.async_create_entry(title=title, data=self._data)

        schema = vol.Schema(
            {
                vol.Required(
                    NUMBER_STORM_LUX_PERCENT, default=NUMBER_DEFAULTS[NUMBER_STORM_LUX_PERCENT]
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=100, step=1, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Required(
                    CONF_DELAY_DARKENING_MIN, default=DEFAULT_DELAY_DARKENING_MIN
                ): vol.Coerce(float),
                vol.Required(
                    CONF_DELAY_BRIGHTENING_MIN, default=DEFAULT_DELAY_BRIGHTENING_MIN
                ): vol.Coerce(float),
                vol.Required(
                    CONF_STORM_WINDOW_MIN, default=DEFAULT_STORM_WINDOW_MIN
                ): vol.Coerce(float),
                vol.Required(
                    CONF_STORM_ENTER_DELAY_SEC, default=DEFAULT_STORM_ENTER_DELAY_SEC
                ): vol.Coerce(float),
                vol.Required(
                    CONF_STORM_EXIT_DELAY_SEC, default=DEFAULT_STORM_EXIT_DELAY_SEC
                ): vol.Coerce(float),
            }
        )
        return self.async_show_form(step_id="storm", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "LightingPhaseOptionsFlow":
        return LightingPhaseOptionsFlow()


class LightingPhaseOptionsFlow(config_entries.OptionsFlow):
    """Change the sensor / notify / timing settings after setup.

    Threshold values themselves live on number entities (adjustable
    directly in the UI / Lovelace) once the integration is running, so
    they are intentionally not repeated here.
    """

    # No __init__ override: current HA core exposes `self.config_entry` as
    # a read-only property on OptionsFlow, resolved automatically from the
    # flow's own entry id. Assigning to it (the old pre-2024.12 pattern)
    # now raises AttributeError, so it's intentionally left alone here.

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options}
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_LUX_SENSOR, default=current.get(CONF_LUX_SENSOR)
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
                vol.Optional(
                    CONF_NOTIFY_TARGET, default=current.get(CONF_NOTIFY_TARGET, "")
                ): str,
                vol.Optional(
                    CONF_PHASE_SOUND, default=current.get(CONF_PHASE_SOUND, "")
                ): str,
                vol.Required(
                    CONF_DELAY_DARKENING_MIN,
                    default=current.get(CONF_DELAY_DARKENING_MIN, DEFAULT_DELAY_DARKENING_MIN),
                ): vol.Coerce(float),
                vol.Required(
                    CONF_DELAY_BRIGHTENING_MIN,
                    default=current.get(
                        CONF_DELAY_BRIGHTENING_MIN, DEFAULT_DELAY_BRIGHTENING_MIN
                    ),
                ): vol.Coerce(float),
                vol.Required(
                    CONF_STORM_WINDOW_MIN,
                    default=current.get(CONF_STORM_WINDOW_MIN, DEFAULT_STORM_WINDOW_MIN),
                ): vol.Coerce(float),
                vol.Required(
                    CONF_STORM_ENTER_DELAY_SEC,
                    default=current.get(
                        CONF_STORM_ENTER_DELAY_SEC, DEFAULT_STORM_ENTER_DELAY_SEC
                    ),
                ): vol.Coerce(float),
                vol.Required(
                    CONF_STORM_EXIT_DELAY_SEC,
                    default=current.get(
                        CONF_STORM_EXIT_DELAY_SEC, DEFAULT_STORM_EXIT_DELAY_SEC
                    ),
                ): vol.Coerce(float),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
