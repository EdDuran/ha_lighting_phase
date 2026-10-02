# Lighting Phase (custom integration)

A native Home Assistant replacement for the `lighting_phase.py` pyscript.
Instead of manually-created `input_select` / `input_number` helpers, setup
and threshold values live on real integration entities under a device.

**Multiple zones are supported.** Add the integration more than once (each
run of the config flow is a separate zone/instance) to get, e.g., a
"Backyard" zone off one lux sensor and a "Front Porch" zone off another (or
elevation-only), each with its own device, entities, and thresholds,
running completely independently.

## What you get

| Entity | Type | Notes |
|---|---|---|
| `sensor.lighting_phase` | Sensor (enum) | Read-only in normal operation. `dawn / morning / day / afternoon / dusk / night`. |
| `select.lighting_mode` | Select | `sensor` or `elevation`. User-settable; also auto-switched to `elevation` if the lux sensor drops out. |
| `binary_sensor.storm_dark_mode` | Binary sensor | Read-only, computed. Your automations react to this the same way they reacted to `input_boolean.storm_mode`. |
| `number.*` (14 entities) | Number | All lux, elevation, tolerance and storm-percent thresholds. Seeded at setup, freely adjustable afterwards from Lovelace/Settings, and persist across restarts. |

A service, **`lighting_phase.set_phase`**, is provided as the "if something
goes wrong" manual override (Developer Tools > Services, or call it from an
automation/script). It takes a **Zone** (device picker — pick which zone's
device this applies to) and a **Phase**. The coordinator for that zone
simply resumes computing forward from whatever phase you force it to; other
zones are untouched.

## Install

1. Copy the `custom_components/lighting_phase` folder into your Home
   Assistant `config/custom_components/` directory (via Samba, SSH, or the
   Studio Code Server add-on).
2. Restart Home Assistant.
3. Settings → Devices & Services → **Add Integration** → search
   "Lighting Phase".
4. Walk through the 4-step setup for this zone:
   - **Zone name** (e.g. "Backyard"), lux sensor (optional — leave blank to
     run elevation-only), notify target, phase-change sound.
   - Lux thresholds (dawn/morning/day/afternoon/dusk/night).
   - Elevation thresholds + cross-check tolerance.
   - Storm overlay % + debounce/window/delay timing.
5. Done — a device named after your zone appears with all entities above.
6. **Repeat from step 3** for each additional zone. Every run of the config
   flow creates a fully independent instance — its own device, entities,
   coordinator, and lux sensor (or none, for elevation-only).

Per-zone: sensor/notify target and the debounce/storm timing constants can
be changed later from that zone's **Configure** button (options flow).
Threshold *values* don't need that — just edit that zone's number entities
directly.

## Migrating from the pyscript version

- Delete/disable `lighting_phase.py` from `<config>/pyscript/` (or just stop
  loading it) once this integration is running, so you don't have two things
  competing over the same physical lights.
- Old entity IDs (`input_select.lighting_phase_2`,
  `input_number.lux_dawn`, etc.) are **not** reused — this integration's
  entities have their own IDs, prefixed with whatever zone name you gave
  the instance (e.g. `sensor.backyard_lighting_phase`,
  `number.backyard_lighting_phase_lux_dawn`). Update any
  dashboards/automations that referenced the old helpers.
- The pyscript only ever ran one instance. If you want that to become more
  than one zone, set up each zone separately and split your old threshold
  values across them as appropriate.
- Port your old helper values over: open each `number.*` entity for this
  integration and set it to match what your old `input_number` held (or
  just re-set them to your tuned values — they were seeded with placeholder
  defaults during setup).
- `NOTIFY_TARGET` from the script maps to the integration's `notify_target`
  option — same convention: whatever comes after `notify.` (e.g.
  `mobile_app_keith_s_iphone_17`).

## Design notes / where this differs from the pyscript

- **Debounce state doesn't persist.** Like the original (module-level dict,
  reset on reload), a pending-but-unconfirmed transition is lost on HA
  restart/reload and starts fresh. The *committed* phase itself does
  persist (`RestoreEntity`), same as `input_select` did.
- **Reactivity**: the coordinator reacts immediately to changes on the lux
  sensor, plus a 1-minute timer as a safety net (mirroring the pyscript's
  `@time_trigger('period(now, 1min)')`). It does *not* re-run instantly when
  you tweak a number/select entity — the next minute's timer tick will pick
  it up, which is fine since threshold tuning isn't time-critical the way a
  live lux reading is.
- **Storm rolling-window samples** are kept in memory only (matching the
  original's `_lux_samples` module list) and reset on reload/restart.

## Not covered here

This integration only reproduces the pyscript's *state machine*. Whatever
automations/scripts you had that reacted to `input_select.lighting_phase_2`
changing (turning lights on/off, adjusting scenes, etc.) still need to be
repointed at the new `sensor.lighting_phase` entity — that logic was never
part of the pyscript file you shared, so there was nothing here to port.
