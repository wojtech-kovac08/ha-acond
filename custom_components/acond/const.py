"""Constants for the Acond heat pump integration."""

from __future__ import annotations

DOMAIN = "acond"
NAME = "Acond Heat Pump"
MANUFACTURER = "ACOND"
MODEL = "AC781180 / AC781150"

CONF_SLAVE = "slave"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_PORT = 502
DEFAULT_SLAVE = 1
DEFAULT_SCAN_INTERVAL = 30  # seconds
DEFAULT_TIMEOUT = 5  # seconds

#: First input register (30001) in PDU addressing -> 0.
REGISTER_BLOCK_START = 0
#: 30001..30014: temperatures of both circuits, status word and HP mode.
REGISTER_COUNT = 14

#: key -> (PDU offset inside the block, divisor)
#: Values are transmitted as INT x10, i.e. 215 = 21.5 °C.
REGISTERS: dict[str, tuple[int, int]] = {
    "setpoint_circuit_1": (0, 10),
    "temperature_circuit_1": (1, 10),
    "setpoint_circuit_2": (2, 10),
    "temperature_circuit_2": (3, 10),
}

#: 30007 - bitwise heat pump status.
STATUS_OFFSET = 6
#: 30014 - HP mode: 0 auto, 1 HP only, 3 aux only, 4 off, 5 manual, 6 cooling.
HP_MODE_OFFSET = 13

#: circuit -> holding register offset of the requested temperature (40001, 40003).
TARGET_REGISTERS: dict[int, int] = {1: 0, 2: 2}
#: 40006 - bitwise HP settings (mode, acknowledgement).
SETTINGS_REGISTER = 5
#: Bits 0..4 of 40006 select the operating mode.
MODE_BIT_MASK = 0b11111

TEMP_MIN = 10.0
TEMP_MAX = 30.0

#: HP mode value (30014) -> internal mode name.
_HP_MODE_NAMES = {4: "off", 6: "cool"}
_HP_MODE_DEFAULT = "heat"

#: internal mode name -> bit in the 40006 settings word.
#: "heat" uses bit 0 (automatic mode) so that auxiliary heating stays allowed.
_MODE_BITS = {"off": 3, "cool": 4, "heat": 0}


def hvac_mode_from_hp_mode(hp_mode: int) -> str:
    """Return off/cool/heat for the value read from 30014."""
    return _HP_MODE_NAMES.get(hp_mode, _HP_MODE_DEFAULT)


def settings_word_for_mode(current: int, mode: str) -> int:
    """Return the 40006 word with only the mode bits changed."""
    word = current & ~MODE_BIT_MASK
    return word | (1 << _MODE_BITS.get(mode, _MODE_BITS["heat"]))
