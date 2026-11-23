"""Constants for the Acond heat pump integration."""

from __future__ import annotations

DOMAIN = "acond"
NAME = "Acond Heat Pump"
MANUFACTURER = "ACOND"
MODEL = "Heat pump (Modbus TCP/RTU)"

CONF_SLAVE = "slave"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_PORT = 502
DEFAULT_SLAVE = 1
DEFAULT_SCAN_INTERVAL = 30  # seconds
DEFAULT_TIMEOUT = 5  # seconds

#: First input register (30001) in PDU addressing -> 0.
REGISTER_BLOCK_START = 0
#: 30001..30004 - two room circuits, setpoint + actual value.
REGISTER_COUNT = 4

#: key -> (PDU offset inside the block, divisor)
#: Values are transmitted as INT x10, i.e. 215 = 21.5 °C.
REGISTERS: dict[str, tuple[int, int]] = {
    "setpoint_circuit_1": (0, 10),
    "temperature_circuit_1": (1, 10),
    "setpoint_circuit_2": (2, 10),
    "temperature_circuit_2": (3, 10),
}
