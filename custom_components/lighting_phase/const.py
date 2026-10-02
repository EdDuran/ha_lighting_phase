"""Constants for the Lighting Phase integration."""

DOMAIN = "lighting_phase"

# ---------------------------------------------------------------------------
# Config / options entry keys
# ---------------------------------------------------------------------------
CONF_NAME = "name"
CONF_LUX_SENSOR = "lux_sensor"
CONF_NOTIFY_TARGET = "notify_target"
CONF_PHASE_SOUND = "phase_sound"
CONF_DELAY_DARKENING_MIN = "delay_darkening_minutes"
CONF_DELAY_BRIGHTENING_MIN = "delay_brightening_minutes"
CONF_STORM_WINDOW_MIN = "storm_window_minutes"
CONF_STORM_ENTER_DELAY_SEC = "storm_enter_delay_seconds"
CONF_STORM_EXIT_DELAY_SEC = "storm_exit_delay_seconds"

DEFAULT_NAME = "Lighting Phase"

DEFAULT_DELAY_DARKENING_MIN = 1
DEFAULT_DELAY_BRIGHTENING_MIN = 2
DEFAULT_STORM_WINDOW_MIN = 30
DEFAULT_STORM_ENTER_DELAY_SEC = 90
DEFAULT_STORM_EXIT_DELAY_SEC = 300

SUN_ENTITY_ID = "sun.sun"

# ---------------------------------------------------------------------------
# Phase / mode / trend enums
# ---------------------------------------------------------------------------
PHASE_DAWN = "dawn"
PHASE_MORNING = "morning"
PHASE_DAY = "day"
PHASE_AFTERNOON = "afternoon"
PHASE_DUSK = "dusk"
PHASE_NIGHT = "night"

PHASES = [PHASE_DAWN, PHASE_MORNING, PHASE_DAY, PHASE_AFTERNOON, PHASE_DUSK, PHASE_NIGHT]

MODE_SENSOR = "sensor"
MODE_ELEVATION = "elevation"
MODES = [MODE_SENSOR, MODE_ELEVATION]

TREND_RISING = "rising"
TREND_SETTING = "setting"

STORM_ELIGIBLE_PHASES = {PHASE_MORNING, PHASE_DAY, PHASE_AFTERNOON}

# ---------------------------------------------------------------------------
# Number entity keys - these become number.<device>_<key> entities and are
# live user-adjustable in the UI once the integration is set up. Their
# initial value is seeded from the config flow.
# ---------------------------------------------------------------------------
NUMBER_LUX_DAWN = "lux_dawn"
NUMBER_LUX_MORNING = "lux_morning"
NUMBER_LUX_DAY = "lux_day"
NUMBER_LUX_AFTERNOON = "lux_afternoon"
NUMBER_LUX_DUSK = "lux_dusk"
NUMBER_LUX_NIGHT = "lux_night"

NUMBER_ELEV_DAWN = "elev_dawn"
NUMBER_ELEV_MORNING = "elev_morning"
NUMBER_ELEV_DAY = "elev_day"
NUMBER_ELEV_AFTERNOON = "elev_afternoon"
NUMBER_ELEV_DUSK = "elev_dusk"
NUMBER_ELEV_NIGHT = "elev_night"

NUMBER_ELEV_TOLERANCE = "elev_tolerance"
NUMBER_STORM_LUX_PERCENT = "storm_lux_percent"

LUX_NUMBER_KEYS = [
    NUMBER_LUX_DAWN,
    NUMBER_LUX_MORNING,
    NUMBER_LUX_DAY,
    NUMBER_LUX_AFTERNOON,
    NUMBER_LUX_DUSK,
    NUMBER_LUX_NIGHT,
]
ELEV_NUMBER_KEYS = [
    NUMBER_ELEV_DAWN,
    NUMBER_ELEV_MORNING,
    NUMBER_ELEV_DAY,
    NUMBER_ELEV_AFTERNOON,
    NUMBER_ELEV_DUSK,
    NUMBER_ELEV_NIGHT,
]
MISC_NUMBER_KEYS = [NUMBER_ELEV_TOLERANCE, NUMBER_STORM_LUX_PERCENT]

ALL_NUMBER_KEYS = LUX_NUMBER_KEYS + ELEV_NUMBER_KEYS + MISC_NUMBER_KEYS

# Seed values used only at initial config-flow setup. After that, each
# value lives on its own number entity and is fully user-adjustable.
NUMBER_DEFAULTS = {
    NUMBER_LUX_DAWN: 10,
    NUMBER_LUX_MORNING: 50,
    NUMBER_LUX_DAY: 200,
    NUMBER_LUX_AFTERNOON: 150,
    NUMBER_LUX_DUSK: 50,
    NUMBER_LUX_NIGHT: 10,
    NUMBER_ELEV_DAWN: -4,
    NUMBER_ELEV_MORNING: 2,
    NUMBER_ELEV_DAY: 2,
    NUMBER_ELEV_AFTERNOON: 2,
    NUMBER_ELEV_DUSK: -1,
    NUMBER_ELEV_NIGHT: -4,
    NUMBER_ELEV_TOLERANCE: 5,
    NUMBER_STORM_LUX_PERCENT: 50,
}

NUMBER_LABELS = {
    NUMBER_LUX_DAWN: "Lux @ Dawn",
    NUMBER_LUX_MORNING: "Lux @ Morning",
    NUMBER_LUX_DAY: "Lux @ Day",
    NUMBER_LUX_AFTERNOON: "Lux @ Afternoon",
    NUMBER_LUX_DUSK: "Lux @ Dusk",
    NUMBER_LUX_NIGHT: "Lux @ Night",
    NUMBER_ELEV_DAWN: "Elevation @ Dawn",
    NUMBER_ELEV_MORNING: "Elevation @ Morning",
    NUMBER_ELEV_DAY: "Elevation @ Day",
    NUMBER_ELEV_AFTERNOON: "Elevation @ Afternoon",
    NUMBER_ELEV_DUSK: "Elevation @ Dusk",
    NUMBER_ELEV_NIGHT: "Elevation @ Night",
    NUMBER_ELEV_TOLERANCE: "Elevation Cross-Check Tolerance",
    NUMBER_STORM_LUX_PERCENT: "Storm Detection - % of Rolling Peak",
}
