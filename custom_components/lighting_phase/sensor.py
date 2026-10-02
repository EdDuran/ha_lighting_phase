"""Sensor platform for Lighting Phase - the computed phase itself."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, PHASE_DAY, PHASES
from .coordinator import LightingPhaseCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: LightingPhaseCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LightingPhaseSensor(coordinator, entry)])


class LightingPhaseSensor(RestoreEntity, SensorEntity):
    """The computed lighting phase.

    Normally only ever written by the coordinator. The lighting_phase.set_phase
    service can force it directly as an emergency manual override - the
    coordinator simply resumes computing from wherever it's been set.
    """

    _attr_has_entity_name = True
    _attr_name = "Lighting Phase"
    _attr_icon = "mdi:theme-light-dark"
    _attr_device_class = "enum"
    _attr_options = PHASES

    def __init__(self, coordinator: LightingPhaseCoordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_phase"
        self._attr_native_value = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Custom",
            model="Lighting Phase Controller",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in PHASES:
            self._attr_native_value = last_state.state
        else:
            self._attr_native_value = PHASE_DAY
        self._coordinator.register_phase_entity(self)

    async def async_set_phase(self, phase: str, manual: bool = False) -> None:
        """Set the phase. Used by the coordinator, and by the manual override service."""
        if phase not in PHASES:
            _LOGGER.error("Invalid phase '%s' ignored", phase)
            return
        self._attr_native_value = phase
        self.async_write_ha_state()
        if manual:
            _LOGGER.warning("Lighting phase manually overridden to '%s'", phase)
