"""Constants and register map for the Acond heat pump integration.

Everything here is read only - the integration never writes to the unit.
"""

from __future__ import annotations

from dataclasses import dataclass

DOMAIN = "acond"
NAME = "Acond Heat Pump"
MANUFACTURER = "ACOND"
MODEL = "AC781180 / AC781150"

CONF_SLAVE = "slave"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_ENABLE_ENERGY = "enable_energy"
CONF_ENABLE_SILENT = "enable_silent"
CONF_ENABLE_CIRCUIT_2 = "enable_circuit_2"

DEFAULT_PORT = 502
DEFAULT_SLAVE = 1
DEFAULT_SCAN_INTERVAL = 30  # seconds
DEFAULT_TIMEOUT = 5  # seconds

#: Off by default - many units do not implement these registers at all.
DEFAULT_ENABLE_ENERGY = False
#: Off by default - the unit must implement registers 30033/30034.
DEFAULT_ENABLE_SILENT = False
#: On by default, can be switched off for single circuit units.
DEFAULT_ENABLE_CIRCUIT_2 = True

#: Small input register blocks, read independently.
#: (first register offset from 30001, number of registers)
#: Kept short on purpose: a unit that does not implement every address in a
#: long block would reject the whole read.
BLOCKS: tuple[tuple[int, int], ...] = (
    (0, 4),  # 30001-30004 room circuits
    (4, 4),  # 30005-30008 DHW setpoint/actual, status word
    (8, 2),  # 30009-30010 return water, outdoor
    (17, 1),  # 30018 outlet water
    (20, 1),  # 30021 fault code
    (28, 1),  # 30029 COP
    (34, 4),  # 30035-30038 energy heating (2 x DINT)
    (40, 1),  # 30041 SCOP
    (68, 4),  # 30069-30072 energy cooling (2 x DINT)
    (13, 2),  # 30014-30015 HP mode, type of regulation
    (32, 2),  # 30033-30034 silent mode start/stop
)


@dataclass(frozen=True, slots=True)
class ValueSpec:
    """One decoded value of the register map."""

    key: str
    block: int
    offset: int
    kind: str = "i16"  # i16 / u16 / i32
    divisor: int = 1
    device_class: str | None = None
    unit: str | None = None
    precision: int | None = None
    state_class: str | None = None
    icon: str | None = None
    state_map: dict[int, str] | None = None


#: 30014 - HP mode.
HP_MODES: dict[int, str] = {
    0: "Automatika",
    1: "Jen čerpadlo",
    3: "Jen záložní topení",
    4: "Vypnuto",
    5: "Ruční režim",
    6: "Chlazení",
}

#: 30015 - type of regulation.
REGULATION_TYPES: dict[int, str] = {
    0: "AcondTherm",
    1: "Equiterm",
    2: "Ručně",
}

_TEMP = {
    "device_class": "temperature",
    "unit": "°C",
    "precision": 1,
    "state_class": "measurement",
}

VALUES: tuple[ValueSpec, ...] = (
    # --- room circuits -------------------------------------------------
    ValueSpec("setpoint_circuit_1", 0, 0, "i16", 10, **_TEMP),
    ValueSpec("temperature_circuit_1", 0, 1, "i16", 10, **_TEMP),
    ValueSpec("setpoint_circuit_2", 0, 2, "i16", 10, **_TEMP),
    ValueSpec("temperature_circuit_2", 0, 3, "i16", 10, **_TEMP),
    # --- domestic hot water + status ------------------------------------
    ValueSpec("setpoint_dhw", 1, 0, "i16", 10, **_TEMP),
    ValueSpec("temperature_dhw", 1, 1, "i16", 10, **_TEMP),
    ValueSpec(
        "status_word", 1, 2, "u16", precision=0, icon="mdi:information-outline"
    ),
    # --- water / outdoor -----------------------------------------------
    ValueSpec("temperature_return", 2, 0, "i16", 10, **_TEMP),
    ValueSpec("temperature_outdoor", 2, 1, "i16", 10, **_TEMP),
    ValueSpec("temperature_outlet", 3, 0, "i16", 10, **_TEMP),
    # --- fault ----------------------------------------------------------
    ValueSpec("fault_code", 4, 0, "u16", icon="mdi:alert-circle-outline"),
    # --- efficiency -----------------------------------------------------
    ValueSpec("cop", 5, 0, "i16", 10, precision=1, state_class="measurement", icon="mdi:gauge"),
    ValueSpec("scop", 7, 0, "i16", 10, precision=1, state_class="measurement", icon="mdi:gauge"),
    # --- energy counters (DINT, 2 registers, high word first) -----------
    ValueSpec(
        "energy_heating_total", 6, 0, "i32", 10,
        device_class="energy", unit="kWh", precision=1, state_class="total_increasing",
    ),
    ValueSpec(
        "energy_heating_electric_total", 6, 2, "i32", 10,
        device_class="energy", unit="kWh", precision=1, state_class="total_increasing",
    ),
    ValueSpec(
        "energy_cooling_total", 8, 0, "i32", 10,
        device_class="energy", unit="kWh", precision=1, state_class="total_increasing",
    ),
    ValueSpec(
        "energy_cooling_electric_total", 8, 2, "i32", 10,
        device_class="energy", unit="kWh", precision=1, state_class="total_increasing",
    ),
    # --- silent mode (minutes from midnight) ----------------------------
    ValueSpec(
        "silent_start", 10, 0, "u16",
        device_class="duration", unit="min", icon="mdi:weather-night",
    ),
    ValueSpec(
        "silent_stop", 10, 1, "u16",
        device_class="duration", unit="min", icon="mdi:weather-night",
    ),
    # --- HP mode and type of regulation ---------------------------------
    ValueSpec("hp_mode", 9, 0, "i16", icon="mdi:heat-pump", state_map=HP_MODES),
    ValueSpec(
        "regulation_type", 9, 1, "i16", icon="mdi:tune", state_map=REGULATION_TYPES
    ),
)

#: Keys that get their own sensor class instead of the generic one.
CUSTOM_SENSOR_KEYS = frozenset(
    {
        "fault_code",
        "status_word",
        "silent_start",
        "silent_stop",
        "hp_mode",
        "regulation_type",
    }
)

#: Indexes in BLOCKS that carry the optional "energy" values (COP, SCOP, kWh).
ENERGY_BLOCKS = frozenset({5, 6, 7, 8})

#: Indexes in BLOCKS that carry the optional silent mode registers.
SILENT_BLOCKS = frozenset({10})

#: Values of the optional second heating circuit.
CIRCUIT_2_KEYS = frozenset({"setpoint_circuit_2", "temperature_circuit_2"})

#: 30007 - bit -> (key, binary_sensor device class or None)
STATUS_BITS: dict[int, tuple[str, str | None]] = {
    0: ("hp_on", "running"),
    1: ("hp_operation", "running"),
    2: ("hp_failure", "problem"),
    3: ("dhw_heating", "heat"),
    4: ("circulation_1", "running"),
    5: ("circulation_2", "running"),
    6: ("solar_circulation", "running"),
    7: ("pool_circulation", "running"),
    8: ("defrosting", "running"),
    9: ("electric_heater", "heat"),
    10: ("summer_mode", None),
    11: ("brine_circulation", "running"),
    12: ("cooling", "cool"),
    13: ("sg_ready_1", None),
    14: ("sg_ready_2", None),
    15: ("sg_ready_modbus", None),
}

#: 30021 - basic fault dial: value -> (code, description).
FAULT_CODES: dict[int, tuple[str, str]] = {
    0: ("OK", "OK"),
    1: ("A16", "FLOW THROUGH HEAT EXCHANGER LOW"),
    2: ("A12", "DEFROSTING TOO LONG"),
    3: ("A01", "HIGH PRESSURE"),
    4: ("A02", "LOW PRESSURE"),
    5: ("A07", "OUTLET TEMPERATURE LOW"),
    6: ("A03", "COMPRESSOR RUNNING FAULT"),
    7: ("A05", "SUCTION TEMPERATURE HIGH"),
    8: ("--", "RESERVED"),
    9: ("A13", "TOO MANY DEFROSTS"),
    10: ("A04", "GROUND COLLECTOR TEMP. LOW"),
    11: ("A10", "FAN RUNNING FAULT"),
    12: ("A14", "SENSORS BLOCKED"),
    13: ("A08", "HEATING DHW TOO LONG"),
    14: ("A09", "DISCHARGE TEMPERATURE HIGH"),
    15: ("W07", "OUTLET TEMPERATURE LOW"),
    16: ("W01", "ROOM TEMPERATURE LOW"),
    17: ("W02", "RETURN WATER TEMPERATURE LOW"),
    18: ("W00", "OUTLET WATER TEMPERATURE HIGH"),
    19: ("W04", "RETURN WATER TEMPERATURE HIGH"),
    20: ("W05", "SUCTION TEMPERATURE LOW"),
    21: ("W12", "DEFROSTING TOO LONG"),
    22: ("W06", "CONDENSING TEMPERATURE HIGH"),
    23: ("HW1", "DRIVER HARDWARE FAULT [195]"),
    24: ("W09", "IP ADDRESS IS NOT VALID"),
    25: ("SYS", "DRIVER SYSTEM FAULT [196]"),
    26: ("W11", "DHW SANITATION TOO LONG"),
    27: ("W16", "EEV TOO OPEN"),
    28: ("SH1", "SUPERHEAT LOW"),
    29: ("CMP", "DRIVER COMPRESSOR FAULT [197]"),
    30: ("PFC", "DRIVER PFC FAULT [198]"),
    31: ("ELC", "DRIVER MICROELECTRONICS FAULT [199]"),
    32: ("--", "RESERVED"),
    33: ("--", "RESERVED"),
    34: ("--", "RESERVED"),
    35: ("W08", "MAX. NUMBER OF COMP. STARTS"),
    36: ("W17", "EVAPORATING TEMPERATURE LOW"),
    37: ("--", "RESERVED"),
    38: ("--", "RESERVED"),
    39: ("--", "RESERVED"),
    40: ("P05", "ROOM TEMPERATURE SENSOR"),
    41: ("P04", "OUTDOOR TEMPERATURE SENSOR"),
    42: ("P02", "OUTLET WATER TEMPER. SENSOR"),
    43: ("P06", "DOMESTIC HOT WATER SENSOR"),
    44: ("P03", "SUCTION LINE TEMPER. SENSOR"),
    45: ("P01", "RETURN WATER TEMPER. SENSOR"),
    46: ("P07", "EVAPORATOR TEMPERATURE SENSOR"),
    47: ("P09", "ROOM 2 TEMPERATURE SENSOR"),
    48: ("P08", "SOLAR COLLECTOR TEMPER. SENSOR"),
    49: ("P10", "POOL TEMPERATURE SENSOR"),
    50: ("PER", "COMMUNICATION WITH PERIF. LOST"),
    51: ("P11", "MIXING VALVE TEMPERATURE SENSOR"),
    52: ("P15", "LOW PRESSURE SENSOR"),
    53: ("P16", "HIGH PRESSURE SENSOR"),
    54: ("P13", "DISCHARGE LINE TEMPER. SENSOR"),
    55: ("P17", "DOMESTIC HOT WATER SENSOR 2"),
    56: ("A19", "HEATING DHW TOO LONG 2"),
    57: ("--", "RESERVED"),
    58: ("--", "RESERVED"),
    59: ("--", "RESERVED"),
    60: ("A18", "SUCTION TEMP. OR LP DURING DEFROST/COOLING LOW"),
    61: ("A11", "ERR COMMUNICATION WITH DRIVER"),
    62: ("A15", "IGBT OVERHEAT (DRIVER)"),
    63: ("P99", "BLOCKED - UNPAID"),
    64: ("W00", "STUCK RELAY"),
    90: ("W10", "TEMPERATURE OF STORAGE TANK LOW"),
    91: ("W14", "SD CARD FAULT"),
    92: ("W13", "TOO MANY RESTARTS OF PLC"),
    93: ("W15", "BIG DIFFRENCE-RETURN AND DHW TEMPERATURE"),
    94: ("A17", "LOW FLOW DURING DEFROST/COOLING"),
    95: ("ST1", "SOFT FAULT IN THE ENGINE ROOM"),
    96: ("ST2", "SERIOUS FAULT IN THE ENGINE ROOM"),
}

#: Display range of the requested temperature.
TEMP_MIN = 10.0
TEMP_MAX = 30.0

# ---- writable registers -------------------------------------------------
#: circuit -> holding register offset of the requested temperature (40001, 40003).
TARGET_REGISTERS: dict[int, int] = {1: 0, 2: 2}
#: 40005 - requested DHW temperature.
DHW_TARGET_REGISTER = 4
#: 40006 - bitwise HP settings (mode, acknowledgement, season).
SETTINGS_REGISTER = 5
#: Bit 8 of 40006 switches between summer and winter operation.
SUMMER_BIT = 8
#: Set to True if your unit uses the inverted meaning of that bit.
SUMMER_BIT_INVERTED = False

DHW_MIN = 10.0
DHW_MAX = 46.0
