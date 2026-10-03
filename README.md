# Lighting Phase (custom integration)

![icon](https://github.com/user-attachments/assets/8f66415a-69fe-4664-a994-b8f59355fbd0)

A native Home Assistant Integration to detect Lighting Phase changes based
on a Lux Sensor entity value or the Sun's Elevation at your location. The Lux sensor
is optional. If omitted the Lighting Phase is based purely on Sun Elevation.
If the Lux sensor is used and it goes offline (ie, battery dies) the mode is
automatically changed to Elevation.

Automations can then be created which react to the Lighting Phase change.

* Afternoon: Turn on interior lights
* Dusk: Turn on exterior lights
* Dawn: Turn off exterior lights
* Morning: Turn off interior lights which could have been turned on manually

**Multiple zones are supported.** The integration supports multiple Devices.
Each Device has its own independent config flow to provide separate zones; e.g., a
"Backyard" zone off one lux sensor and a "Front Porch" zone off another (or
elevation-only), each with its own device, entities, and thresholds,
running completely independently.

**Storm Mode** The integration also provides a Storm Mode to determine when it has
become darker outside when not typically expected. This could trigger an automation to turn on
some interior lights (and restore them when Storm Mode is over. Generally using a scene).

## What you get per Lighting Phase Device

| Entity | Type | Notes |
|---|---|---|
| `sensor.lighting_phase` | Sensor (enum) | Read-only in normal operation; `dawn / morning / day / afternoon / dusk / night`. |
| `select.lighting_mode` | Select |  User-settable; `sensor` or `elevation`. Also auto-switched to `elevation` if the lux sensor drops out. |
| `binary_sensor.storm_mode` | Binary sensor | Read-only |
| `number.*` (14 entities) | Number | All lux, elevation, tolerance and storm-percent thresholds. Seeded at setup, freely adjustable afterwards from Lovelace/Settings, and persist across restarts. |

| Service | Notes |
|---|---|
| `lighting_phase.set_phase` | Provided as the "if something goes wrong" manual override (Developer Tools > Services, or call it from an automation/script). It takes a **Zone** (device picker — pick which zone's device this applies to) and a **Phase**. The Zone simply resumes computing forward from whatever phase you force it to; other Zones are untouched. |

## Install

1. Add the custom repository to HACS: `https://github.com/EdDuran/ha_lighting_phase.git`
2. Settings → Devices & Services → **Add Integration** → search "Lighting Phase".
3. Restart Home Assistant
4. Settings → Devices & Services → Lighting Phase and **Add Entity**
5. Walk through the 4-step setup for this zone:
   - **Zone name** (e.g. "Backyard"), lux sensor (optional — leave blank to
     run elevation-only), notify target, phase-change sound.
   - Lux thresholds (dawn/morning/day/afternoon/dusk/night).
   - Elevation thresholds + cross-check tolerance.
   - Storm overlay % + debounce/window/delay timing.
6. Done — a Device named after your Zone appears with all entities above.
7. **Repeat from step 4** for each additional zone. Every run of the config
   flow creates a fully independent instance — its own device, entities,
   coordinator, and lux sensor (or none, for elevation-only).

Per-zone: sensor/notify target and the debounce/storm timing constants can
be changed later from that zone's **Configure** button (options flow).
Threshold *values* don't need that — just edit that zone's number entities
directly.

## Design notes

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
