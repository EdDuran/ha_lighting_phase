"""Number platform for Lighting Phase - all user-adjustable thresholds."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    ALL_NUMBER_KEYS,
    DOMAIN,
    ELEV_NUMBER_KEYS,
    LUX_NUMBER_KEYS,
    NUMBER_DEFAULTS,
    NUMBER_ELEV_TOLERANCE,
    NUMBER_LABELS,
    NUMBER_STORM_LUX_PERCENT,
)
from .coordinator import LightingPhaseCoordinator


def _bounds_for(key: str) -> tuple[float, float, float, str | None]:
    """Return (min, max, step, unit) for a given threshold key."""
    if key in LUX_NUMBER_KEYS:
        return 0, 1000, 1, "lx"
    if key in ELEV_NUMBER_KEYS:
        return -10, 10, 0.1, "°"
    if key == NUMBER_ELEV_TOLERANCE:
        return 0, 30, 0.5, "°"
    if key == NUMBER_STORM_LUX_PERCENT:
        return 0, 100, 1, "%"
    return 0, 1000, 1, None


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: LightingPhaseCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [LightingPhaseNumber(coordinator, entry, key) for key in ALL_NUMBER_KEYS]
    async_add_entities(entities)


class LightingPhaseNumber(RestoreEntity, NumberEntity):
    """A single threshold. Seeded from the config flow, then fully
    user-adjustable in the UI from then on (value persists via RestoreEntity,
    independent of the config entry)."""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: LightingPhaseCoordinator, entry: ConfigEntry, key: str) -> None:
        self._coordinator = coordinator
        self._entry = entry
        self._key = key
        min_v, max_v, step, unit = _bounds_for(key)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = NUMBER_LABELS.get(key, key)
        self._attr_native_min_value = min_v
        self._attr_native_max_value = max_v
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_native_value = entry.data.get(key, NUMBER_DEFAULTS.get(key, 0))
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name=entry.title
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._attr_native_value = float(last_state.state)
            except ValueError:
                pass
        self._coordinator.register_number(self._key, self)

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()
