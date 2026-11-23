"""Modbus TCP transport for the Acond heat pump."""

from __future__ import annotations

import inspect
from functools import lru_cache

from pymodbus.client import AsyncModbusTcpClient


class AcondError(Exception):
    """Base error for the Acond integration."""


class AcondConnectionError(AcondError):
    """Raised when the heat pump cannot be reached over Modbus TCP."""


class AcondModbusError(AcondError):
    """Raised when the heat pump returns a Modbus exception."""


@lru_cache(maxsize=1)
def _unit_param() -> str:
    """Return the keyword pymodbus uses for the Modbus unit id.

    pymodbus < 3.7 calls it ``slave``, newer versions call it ``device_id``.
    """
    params = inspect.signature(AsyncModbusTcpClient.read_input_registers).parameters
    for name in ("device_id", "slave", "unit"):
        if name in params:
            return name
    return "slave"


def to_signed(value: int) -> int:
    """Convert an unsigned 16 bit register value to a signed integer."""
    return value - 0x10000 if value > 0x7FFF else value


class AcondModbusClient:
    """Thin async wrapper around pymodbus for one heat pump."""

    def __init__(
        self,
        host: str,
        port: int = 502,
        slave: int = 1,
        timeout: float = 5.0,
    ) -> None:
        self._host = host
        self._port = port
        self._slave = slave
        self._timeout = timeout
        self._client: AsyncModbusTcpClient | None = None

    async def async_connect(self) -> None:
        """Open the TCP connection if it is not open yet."""
        if self._client is None:
            self._client = AsyncModbusTcpClient(
                self._host, port=self._port, timeout=self._timeout
            )
        if self._client.connected:
            return
        if not await self._client.connect():
            self.close()
            raise AcondConnectionError(
                f"Cannot connect to {self._host}:{self._port}"
            )

    async def async_read_input_registers(self, address: int, count: int) -> list[int]:
        """Read ``count`` input registers starting at PDU ``address``."""
        if self._client is None:
            raise AcondConnectionError("Modbus client is not connected")
        result = await self._client.read_input_registers(
            address, count=count, **{_unit_param(): self._slave}
        )
        if result.isError():
            raise AcondModbusError(
                f"Modbus error reading {count} register(s) at {address}: {result}"
            )
        return list(result.registers)

    def close(self) -> None:
        """Close the TCP connection."""
        if self._client is not None:
            self._client.close()
            self._client = None
