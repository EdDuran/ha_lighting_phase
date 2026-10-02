"""Binary sensor platform for Lighting Phase - storm / transient darkness overlay."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .coordinator import LightingPhaseCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: LightingPhaseCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LightingPhaseStormBinarySensor(coordinator, entry)])


class LightingPhaseStormBinarySensor(RestoreEntity, BinarySensorEntity):
    """Computed, read-only. Interior lights/automations react to this."""

    _attr_has_entity_name = True
    _attr_name = "Storm Dark Mode"
    _attr_icon = "mdi:weather-lightning"

    def __init__(self, coordinator: LightingPhaseCoordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_storm_mode"
        self._attr_is_on = False
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name=entry.title
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._attr_is_on = last_state.state == "on"
        self._coordinator.register_storm_entity(self)

    async def async_set_is_on(self, is_on: bool) -> None:
        self._attr_is_on = is_on
        self.async_write_ha_state()
