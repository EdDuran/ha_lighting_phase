"""Core state-machine logic for the Lighting Phase integration.

This is a port of the original pyscript's update_lighting_phase() /
update_storm_overlay() functions. Instead of input_select / input_number
helpers, thresholds live on number entities and the phase/mode live on
sensor/select entities that register themselves with this coordinator
when added to hass.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)

from .const import (
    CONF_DELAY_BRIGHTENING_MIN,
    CONF_DELAY_DARKENING_MIN,
    CONF_LUX_SENSOR,
    CONF_NOTIFY_TARGET,
    CONF_PHASE_SOUND,
    CONF_STORM_ENTER_DELAY_SEC,
    CONF_STORM_EXIT_DELAY_SEC,
    CONF_STORM_WINDOW_MIN,
    DEFAULT_DELAY_BRIGHTENING_MIN,
    DEFAULT_DELAY_DARKENING_MIN,
    DEFAULT_STORM_ENTER_DELAY_SEC,
    DEFAULT_STORM_EXIT_DELAY_SEC,
    DEFAULT_STORM_WINDOW_MIN,
    MODE_ELEVATION,
    MODE_SENSOR,
    NUMBER_ELEV_AFTERNOON,
    NUMBER_ELEV_DAWN,
    NUMBER_ELEV_DAY,
    NUMBER_ELEV_DUSK,
    NUMBER_ELEV_MORNING,
    NUMBER_ELEV_NIGHT,
    NUMBER_ELEV_TOLERANCE,
    NUMBER_LUX_AFTERNOON,
    NUMBER_LUX_DAWN,
    NUMBER_LUX_DAY,
    NUMBER_LUX_DUSK,
    NUMBER_LUX_MORNING,
    NUMBER_LUX_NIGHT,
    NUMBER_STORM_LUX_PERCENT,
    PHASE_AFTERNOON,
    PHASE_DAWN,
    PHASE_DAY,
    PHASE_DUSK,
    PHASE_MORNING,
    PHASE_NIGHT,
    STORM_ELIGIBLE_PHASES,
    SUN_ENTITY_ID,
    TREND_RISING,
    TREND_SETTING,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Transition:
    trend: str
    next_phase: str
    threshold_key: Optional[str]  # key into coordinator.number_entities, or None = borrow from next row


SENSOR_STATES = {
    PHASE_DAWN: Transition(TREND_RISING, PHASE_MORNING, NUMBER_LUX_MORNING),
    PHASE_MORNING: Transition(TREND_RISING, PHASE_DAY, NUMBER_LUX_DAY),
    PHASE_DAY: Transition(TREND_SETTING, PHASE_AFTERNOON, NUMBER_LUX_AFTERNOON),
    PHASE_AFTERNOON: Transition(TREND_SETTING, PHASE_DUSK, NUMBER_LUX_DUSK),
    PHASE_DUSK: Transition(TREND_SETTING, PHASE_NIGHT, NUMBER_LUX_NIGHT),
    PHASE_NIGHT: Transition(TREND_RISING, PHASE_DAWN, NUMBER_LUX_DAWN),
}

ELEVATION_STATES = {
    PHASE_DAWN: Transition(TREND_RISING, PHASE_MORNING, NUMBER_ELEV_MORNING),
    PHASE_MORNING: Transition(TREND_RISING, PHASE_DAY, NUMBER_ELEV_DAY),
    PHASE_DAY: Transition(TREND_SETTING, PHASE_AFTERNOON, NUMBER_ELEV_AFTERNOON),
    PHASE_AFTERNOON: Transition(TREND_SETTING, PHASE_DUSK, NUMBER_ELEV_DUSK),
    PHASE_DUSK: Transition(TREND_SETTING, PHASE_NIGHT, NUMBER_ELEV_NIGHT),
    PHASE_NIGHT: Transition(TREND_RISING, PHASE_DAWN, NUMBER_ELEV_DAWN),
}


class LightingPhaseCoordinator:
    """Owns the state machine. Entities register themselves with it."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry

        self.phase_entity = None
        self.mode_entity = None
        self.storm_entity = None
        self.number_entities: dict[str, "object"] = {}

        self._pending_target: Optional[str] = None
        self._pending_since: Optional[float] = None

        self._pending_storm_target: Optional[bool] = None
        self._pending_storm_since: Optional[float] = None

        self._lux_samples: list[tuple[float, float]] = []

        self._unsub: list = []

    # ------------------------------------------------------------------
    # Config / options accessors
    # ------------------------------------------------------------------
    @property
    def lux_sensor_entity_id(self) -> Optional[str]:
        return self.entry.options.get(CONF_LUX_SENSOR, self.entry.data.get(CONF_LUX_SENSOR))

    @property
    def notify_target(self) -> Optional[str]:
        target = self.entry.options.get(CONF_NOTIFY_TARGET, self.entry.data.get(CONF_NOTIFY_TARGET))
        return target or None

    @property
    def phase_sound(self) -> Optional[str]:
        sound = self.entry.options.get(CONF_PHASE_SOUND, self.entry.data.get(CONF_PHASE_SOUND))
        return sound or None

    @property
    def delay_darkening_minutes(self) -> float:
        return self.entry.options.get(CONF_DELAY_DARKENING_MIN, DEFAULT_DELAY_DARKENING_MIN)

    @property
    def delay_brightening_minutes(self) -> float:
        return self.entry.options.get(CONF_DELAY_BRIGHTENING_MIN, DEFAULT_DELAY_BRIGHTENING_MIN)

    @property
    def storm_window_minutes(self) -> float:
        return self.entry.options.get(CONF_STORM_WINDOW_MIN, DEFAULT_STORM_WINDOW_MIN)

    @property
    def storm_enter_delay_seconds(self) -> float:
        return self.entry.options.get(CONF_STORM_ENTER_DELAY_SEC, DEFAULT_STORM_ENTER_DELAY_SEC)

    @property
    def storm_exit_delay_seconds(self) -> float:
        return self.entry.options.get(CONF_STORM_EXIT_DELAY_SEC, DEFAULT_STORM_EXIT_DELAY_SEC)

    # ------------------------------------------------------------------
    # Entity registration - called from each platform's async_added_to_hass
    # ------------------------------------------------------------------
    def register_number(self, key: str, entity) -> None:
        self.number_entities[key] = entity

    def register_phase_entity(self, entity) -> None:
        self.phase_entity = entity

    def register_mode_entity(self, entity) -> None:
        self.mode_entity = entity

    def register_storm_entity(self, entity) -> None:
        self.storm_entity = entity

    # ------------------------------------------------------------------
    # Setup / teardown
    # ------------------------------------------------------------------
    async def async_setup(self) -> None:
        if self.lux_sensor_entity_id:
            self._unsub.append(
                async_track_state_change_event(
                    self.hass, [self.lux_sensor_entity_id], self._handle_watched_state_change
                )
            )

        self._unsub.append(
            async_track_time_interval(self.hass, self._handle_timer, timedelta(minutes=1))
        )

    def async_unload(self) -> None:
        for unsub in self._unsub:
            unsub()
        self._unsub = []

    @callback
    def _handle_watched_state_change(self, event: Event) -> None:
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        if not old_state or not new_state or old_state.state == new_state.state:
            return
        self.hass.async_create_task(self.async_update())

    @callback
    def _handle_timer(self, now) -> None:
        self.hass.async_create_task(self.async_update())

    # ------------------------------------------------------------------
    # Low-level readers
    # ------------------------------------------------------------------
    def _get_threshold(self, key: Optional[str]) -> float:
        if key is None:
            return 0.0
        entity = self.number_entities.get(key)
        if entity is None or entity.native_value is None:
            _LOGGER.error("Number entity for '%s' is not available yet", key)
            return 0.0
        return float(entity.native_value)

    def _get_phase_threshold_key(self, table: dict, phase: str) -> Optional[str]:
        row = table.get(phase)
        if row is None:
            return None
        if row.threshold_key is not None:
            return row.threshold_key
        return self._get_phase_threshold_key(table, row.next_phase)

    def _get_phase_threshold(self, table: dict, phase: str) -> float:
        key = self._get_phase_threshold_key(table, phase)
        return self._get_threshold(key)

    def _get_lux(self) -> Optional[float]:
        if not self.lux_sensor_entity_id:
            return None
        state = self.hass.states.get(self.lux_sensor_entity_id)
        if state is None or state.state in (None, "unknown", "unavailable"):
            return None
        try:
            return float(state.state)
        except (TypeError, ValueError):
            return None

    def _sun_state(self):
        return self.hass.states.get(SUN_ENTITY_ID)

    def _sun_elevation(self) -> float:
        sun = self._sun_state()
        if sun is None:
            return 0.0
        try:
            return float(sun.attributes.get("elevation", 0.0))
        except (TypeError, ValueError):
            return 0.0

    def _is_sun_rising(self) -> bool:
        sun = self._sun_state()
        if sun is None:
            return True
        return bool(sun.attributes.get("rising", True))

    def _sun_trend(self) -> str:
        return TREND_RISING if self._is_sun_rising() else TREND_SETTING

    def _current_phase(self) -> str:
        if self.phase_entity is None or self.phase_entity.native_value is None:
            return PHASE_DAY
        return self.phase_entity.native_value

    def _current_mode(self) -> str:
        if self.mode_entity is None or self.mode_entity.current_option is None:
            return MODE_ELEVATION
        return self.mode_entity.current_option

    # ------------------------------------------------------------------
    # State machine (ported from pyscript)
    # ------------------------------------------------------------------
    def _elevation_permits_transition(self, current_phase: str):
        """
        Cross-check a sensor-driven transition candidate against sun
        elevation. Lux says "it's dark enough to move on" - elevation says
        whether that's plausible for this time of day.
        """
        elevation = self._sun_elevation()
        elev_key = self._get_phase_threshold_key(ELEVATION_STATES, current_phase)
        elev_threshold = self._get_threshold(elev_key)
        tolerance = self._get_threshold(NUMBER_ELEV_TOLERANCE)

        sensor_transition = SENSOR_STATES.get(current_phase)
        if sensor_transition.trend == TREND_RISING:
            permitted = elevation >= (elev_threshold - tolerance)
        else:
            permitted = elevation < (elev_threshold + tolerance)
        return permitted, elevation, tolerance, elev_threshold

    def _get_next_phase(self, transition: Transition, current_phase: str) -> str:
        if self._sun_trend() != transition.trend:
            return current_phase
        return transition.next_phase

    def _get_new_phase(self, table: dict, current_phase: str, current_value: float) -> str:
        transition = table.get(current_phase)
        if transition is None:
            _LOGGER.error("No transition defined for phase '%s'; holding", current_phase)
            return current_phase

        threshold_value = self._get_phase_threshold(table, current_phase)
        new_phase = current_phase

        if transition.trend == TREND_RISING and current_value >= threshold_value:
            new_phase = self._get_next_phase(transition, current_phase)
        elif transition.trend == TREND_SETTING and current_value <= threshold_value:
            new_phase = self._get_next_phase(transition, current_phase)

        return new_phase

    def _get_phase_delay_minutes(self, current_phase: str, table: dict) -> float:
        transition = table.get(current_phase)
        if transition and transition.trend == TREND_SETTING:
            return self.delay_darkening_minutes
        return self.delay_brightening_minutes

    async def _get_phase_from_sensor(self, current_phase: str) -> str:
        lux = self._get_lux()
        if lux is None:
            _LOGGER.warning("Light sensor unavailable, failing over to elevation mode")
            if self.mode_entity is not None:
                await self.mode_entity.async_select_option(MODE_ELEVATION)
            await self._notify(
                title="Light Sensor Malfunction",
                message="Failing over to calculated (elevation) mode",
            )
            return self._get_phase_from_elevation(current_phase)

        new_phase = self._get_new_phase(SENSOR_STATES, current_phase, lux)
        permitted, elevation, tolerance, elev_threshold = self._elevation_permits_transition(
            current_phase
        )
        if new_phase != current_phase and not permitted:
            _LOGGER.info(
                "Phase blocked: [%s -> %s]; elevation %.1f not within %s of %.1f",
                current_phase,
                new_phase,
                elevation,
                tolerance,
                elev_threshold,
            )
            new_phase = current_phase
        return new_phase

    def _get_phase_from_elevation(self, current_phase: str) -> str:
        elevation = self._sun_elevation()
        return self._get_new_phase(ELEVATION_STATES, current_phase, elevation)

    async def _notify(self, title: str, message: str, sound: bool = False) -> None:
        if not self.notify_target:
            return
        call_data = {"title": title, "message": message}
        if sound and self.phase_sound:
            call_data["data"] = {
                "push": {
                    "interruption-level": "time-sensitive",
                    "sound": {"name": self.phase_sound, "critical": 0, "volume": 1.0},
                }
            }
        try:
            await self.hass.services.async_call(
                "notify", self.notify_target, call_data, blocking=False
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Failed to send notification: %s", err)

    # ------------------------------------------------------------------
    # Main update
    # ------------------------------------------------------------------
    async def async_update(self) -> None:
        try:
            await self._async_update_phase()
            await self._async_update_storm()
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Failed to update lighting phase: %s", err)

    async def _async_update_phase(self) -> None:
        current_phase = self._current_phase()
        mode = self._current_mode()

        if mode == MODE_SENSOR:
            new_phase = await self._get_phase_from_sensor(current_phase)
            table = SENSOR_STATES
        else:
            new_phase = self._get_phase_from_elevation(current_phase)
            table = ELEVATION_STATES

        now = time.time()
        delay_minutes = self._get_phase_delay_minutes(current_phase, table)

        if self._pending_target is not None:
            if new_phase == current_phase:
                # Candidate reverted before the debounce completed
                self._reset_delay()
                return

            elapsed = now - self._pending_since
            if elapsed >= delay_minutes * 60:
                lux = self._get_lux()
                lux_str = f"{lux:.0f}" if lux is not None else "n/a"
                _LOGGER.info(
                    "Lighting phase change: [%s -> %s] lux=%s elevation=%.1f",
                    current_phase,
                    new_phase,
                    lux_str,
                    self._sun_elevation(),
                )
                if self.phase_entity is not None:
                    await self.phase_entity.async_set_phase(new_phase)
                await self._notify(
                    title=f"{new_phase.title()} Lux:{lux_str}",
                    message=f"Lighting phase changed from {current_phase} to {new_phase}",
                    sound=True,
                )
                self._reset_delay()
            # else: still waiting out the debounce
        else:
            if new_phase != current_phase:
                self._pending_target = new_phase
                self._pending_since = now
                _LOGGER.info(
                    "Lighting phase pending: [%s] -> [%s]; waiting %s min to confirm",
                    current_phase,
                    new_phase,
                    delay_minutes,
                )

    def _reset_delay(self) -> None:
        self._pending_target = None
        self._pending_since = None

    # ------------------------------------------------------------------
    # Storm / transient darkness overlay (ported from pyscript)
    # ------------------------------------------------------------------
    def _update_lux_window(self, lux: float, now: float) -> float:
        self._lux_samples.append((now, lux))
        cutoff = now - (self.storm_window_minutes * 60)
        self._lux_samples = [(t, v) for t, v in self._lux_samples if t >= cutoff]
        values = [v for _, v in self._lux_samples] or [lux]
        return max(values)

    def _get_storm_cutoff(self, lux: float, now: float) -> float:
        baseline = self._update_lux_window(lux, now)
        pct = self._get_threshold(NUMBER_STORM_LUX_PERCENT) / 100.0
        return baseline * pct

    async def _set_storm_dark(self, is_dark: bool, cutoff: Optional[float] = None) -> None:
        if self.storm_entity is None:
            return
        if bool(self.storm_entity.is_on) == is_dark:
            return
        await self.storm_entity.async_set_is_on(is_dark)
        lux = self._get_lux()
        lux_str = f"{lux:.0f}" if lux is not None else "n/a"
        cutoff_str = f"{cutoff:.0f}" if cutoff is not None else "n/a"
        await self._notify(
            title=f"Storm[{'ON' if is_dark else 'OFF'}] Lux:{lux_str}",
            message=f"Storm mode is [{'ON' if is_dark else 'OFF'}] cutoff [{cutoff_str}]",
        )

    async def _async_update_storm(self) -> None:
        current_phase = self._current_phase()

        if current_phase not in STORM_ELIGIBLE_PHASES:
            self._reset_storm_delay()
            await self._set_storm_dark(False)
            return

        lux = self._get_lux()
        if lux is None:
            return

        now = time.time()
        relative_cutoff = self._get_storm_cutoff(lux, now)
        afternoon_threshold = self._get_threshold(NUMBER_LUX_AFTERNOON)
        is_dark_now = (lux < relative_cutoff) and (lux < afternoon_threshold)

        currently_on = bool(self.storm_entity and self.storm_entity.is_on)
        candidate = is_dark_now

        if candidate == currently_on:
            self._reset_storm_delay()
            return

        delay_needed = (
            self.storm_enter_delay_seconds if candidate else self.storm_exit_delay_seconds
        )

        if self._pending_storm_target != candidate:
            self._pending_storm_target = candidate
            self._pending_storm_since = now
            _LOGGER.info(
                "Storm pending: [%s] lux=%.0f cutoff=%.0f -> %s, waiting %ss",
                current_phase,
                lux,
                relative_cutoff,
                "DARK" if candidate else "CLEAR",
                delay_needed,
            )
            return

        elapsed = now - self._pending_storm_since
        if elapsed >= delay_needed:
            await self._set_storm_dark(candidate, relative_cutoff)
            self._reset_storm_delay()
        # else: still waiting out the delay

    def _reset_storm_delay(self) -> None:
        self._pending_storm_target = None
        self._pending_storm_since = None
