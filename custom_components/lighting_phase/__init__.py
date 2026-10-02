"""The Lighting Phase integration."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, PHASES
from .coordinator import LightingPhaseCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "select", "number", "binary_sensor"]

SERVICE_SET_PHASE = "set_phase"
ATTR_DEVICE_ID = "device_id"
ATTR_PHASE = "phase"
SERVICE_SET_PHASE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_PHASE): vol.In(PHASES),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Lighting Phase from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = LightingPhaseCoordinator(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await coordinator.async_setup()

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    async def _handle_set_phase(call: ServiceCall) -> None:
        """Emergency manual override - force one zone's phase to a specific value."""
        device_id = call.data[ATTR_DEVICE_ID]
        phase = call.data[ATTR_PHASE]

        device_reg = dr.async_get(hass)
        device = device_reg.async_get(device_id)
        if device is None:
            raise HomeAssistantError(f"Unknown device_id: {device_id}")

        target_entry_id = next(
            (eid for eid in device.config_entries if eid in hass.data[DOMAIN]), None
        )
        if target_entry_id is None:
            raise HomeAssistantError(f"Device {device_id} is not a Lighting Phase zone")

        coordinator: LightingPhaseCoordinator = hass.data[DOMAIN][target_entry_id]
        if coordinator.phase_entity is not None:
            await coordinator.phase_entity.async_set_phase(phase, manual=True)

    if not hass.services.has_service(DOMAIN, SERVICE_SET_PHASE):
        hass.services.async_register(
            DOMAIN, SERVICE_SET_PHASE, _handle_set_phase, schema=SERVICE_SET_PHASE_SCHEMA
        )

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: LightingPhaseCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator.async_unload()
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_SET_PHASE)
    return unload_ok
