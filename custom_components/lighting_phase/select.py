"""Select platform for Lighting Phase - sensor vs elevation operating mode."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, MODE_ELEVATION, MODE_SENSOR, MODES
from .coordinator import LightingPhaseCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: LightingPhaseCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LightingPhaseModeSelect(coordinator, entry)])


class LightingPhaseModeSelect(RestoreEntity, SelectEntity):
    """Which table drives the state machine: the lux sensor or sun elevation.

    User-settable, and also set automatically by the coordinator if the
    lux sensor goes unavailable (failover to elevation).
    """

    _attr_has_entity_name = True
    _attr_name = "Lighting Mode"
    _attr_icon = "mdi:swap-horizontal"
    _attr_options = MODES

    def __init__(self, coordinator: LightingPhaseCoordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_mode"
        self._attr_current_option = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name=entry.title
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in MODES:
            self._attr_current_option = last_state.state
        else:
            self._attr_current_option = (
                MODE_SENSOR if self._coordinator.lux_sensor_entity_id else MODE_ELEVATION
            )
        self._coordinator.register_mode_entity(self)

    async def async_select_option(self, option: str) -> None:
        if option not in MODES:
            return
        self._attr_current_option = option
        self.async_write_ha_state()
