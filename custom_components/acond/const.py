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

DEFAULT_PORT = 502
DEFAULT_SLAVE = 1
DEFAULT_SCAN_INTERVAL = 30  # seconds
DEFAULT_TIMEOUT = 5  # seconds

#: Blocks of input registers, read in this order.
#: (first register offset from 30001, number of registers)
BLOCKS: tuple[tuple[int, int], ...] = (
    (0, 44),  # 30001 .. 30044
    (68, 4),  # 30069 .. 30072
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


_TEMP = {"device_class": "temperature", "unit": "°C", "precision": 1, "state_class": "measurement"}

VALUES: tuple[ValueSpec, ...] = (
    # --- room circuits -------------------------------------------------
    ValueSpec("setpoint_circuit_1", 0, 0, "i16", 10, **_TEMP),
    ValueSpec("temperature_circuit_1", 0, 1, "i16", 10, **_TEMP),
    ValueSpec("setpoint_circuit_2", 0, 2, "i16", 10, **_TEMP),
    ValueSpec("temperature_circuit_2", 0, 3, "i16", 10, **_TEMP),
    # --- domestic hot water --------------------------------------------
    ValueSpec("setpoint_dhw", 0, 4, "i16", 10, **_TEMP),
    ValueSpec("temperature_dhw", 0, 5, "i16", 10, **_TEMP),
    # --- water / outdoor -----------------------------------------------
    ValueSpec("temperature_return", 0, 8, "i16", 10, **_TEMP),
    ValueSpec("temperature_outdoor", 0, 9, "i16", 10, **_TEMP),
    ValueSpec("temperature_outlet", 0, 17, "i16", 10, **_TEMP),
    # --- efficiency -----------------------------------------------------
    ValueSpec("cop", 0, 28, "i16", 10, precision=1, state_class="measurement", icon="mdi:gauge"),
    ValueSpec("scop", 0, 40, "i16", 10, precision=1, state_class="measurement", icon="mdi:gauge"),
    # --- energy counters (DINT, 2 registers, high word first) -----------
    ValueSpec(
        "energy_heating_total", 0, 34, "i32", 10,
        device_class="energy", unit="kWh", precision=1, state_class="total_increasing",
    ),
    ValueSpec(
        "energy_heating_electric_total", 0, 36, "i32", 10,
        device_class="energy", unit="kWh", precision=1, state_class="total_increasing",
    ),
    ValueSpec(
        "energy_cooling_total", 1, 0, "i32", 10,
        device_class="energy", unit="kWh", precision=1, state_class="total_increasing",
    ),
    ValueSpec(
        "energy_cooling_electric_total", 1, 2, "i32", 10,
        device_class="energy", unit="kWh", precision=1, state_class="total_increasing",
    ),
    # --- raw words ------------------------------------------------------
    ValueSpec("status_word", 0, 6, "u16"),
    ValueSpec("fault_code", 0, 20, "u16", icon="mdi:alert-circle-outline"),
)

#: Keys that are used by other platforms instead of plain sensors.
NON_SENSOR_KEYS = frozenset({"status_word", "fault_code"})

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

#: Display range of the requested temperature (attributes only).
TEMP_MIN = 10.0
TEMP_MAX = 30.0
