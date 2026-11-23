"""Modbus TCP transport for the Acond heat pump."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable

from pymodbus.client import AsyncModbusTcpClient

_LOGGER = logging.getLogger(__name__)

try:  # pymodbus has shipped these names for a long time
    from pymodbus.exceptions import (
        ConnectionException,
        ModbusException,
        ModbusIOException,
    )
except ImportError:  # pragma: no cover - very old pymodbus

    class ModbusException(Exception):  # type: ignore[no-redef]
        """Fallback base exception."""

    class ConnectionException(ModbusException):  # type: ignore[no-redef]
        """Fallback connection exception."""

    class ModbusIOException(ModbusException):  # type: ignore[no-redef]
        """Fallback I/O exception."""


class AcondError(Exception):
    """Base error for the Acond integration."""


class AcondConnectionError(AcondError):
    """Raised when the TCP connection to the heat pump cannot be opened."""


class AcondNoResponseError(AcondError):
    """Raised when the heat pump is reachable but does not answer."""


class AcondModbusError(AcondError):
    """Raised when the heat pump returns a Modbus exception response."""


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
        self._port = int(port)
        self._slave = int(slave)
        self._timeout = float(timeout)
        self._client: AsyncModbusTcpClient | None = None

    async def async_connect(self) -> None:
        """Open the TCP connection if it is not open yet."""
        if self._client is None:
            self._client = AsyncModbusTcpClient(
                self._host, port=self._port, timeout=self._timeout
            )
        if self._client.connected:
            return

        try:
            connected = await self._client.connect()
        except (ConnectionException, OSError) as err:
            self.close()
            raise AcondConnectionError(
                f"Cannot connect to {self._host}:{self._port}: {err}"
            ) from err
        except Exception as err:  # noqa: BLE001 - never leak an unexpected type
            self.close()
            raise AcondConnectionError(
                f"Cannot connect to {self._host}:{self._port}: {err!r}"
            ) from err

        if not connected:
            self.close()
            raise AcondConnectionError(
                f"Cannot connect to {self._host}:{self._port} (connection refused)"
            )

    async def async_read_input_registers(self, address: int, count: int) -> list[int]:
        """Read ``count`` input registers starting at PDU ``address``."""
        return await self._async_call(
            lambda: self._client.read_input_registers(
                address, count=count, **self._unit_kwargs()
            ),
            f"read of {count} input register(s) at {address}",
        )

    async def async_read_holding_registers(self, address: int, count: int) -> list[int]:
        """Read ``count`` holding registers starting at PDU ``address``."""
        return await self._async_call(
            lambda: self._client.read_holding_registers(
                address, count=count, **self._unit_kwargs()
            ),
            f"read of {count} holding register(s) at {address}",
        )

    async def async_write_register(self, address: int, value: int) -> None:
        """Write one holding register (function code 6)."""
        await self._async_call(
            lambda: self._client.write_register(
                address, value, **self._unit_kwargs()
            ),
            f"write of {value} to holding register {address}",
        )

    async def _async_call(
        self, call: Callable[[], Awaitable[Any]], description: str
    ) -> list[int]:
        """Run one Modbus call and translate pymodbus errors."""
        if self._client is None:
            raise AcondConnectionError("Modbus client is not connected")

        try:
            result = await call()
        except ModbusIOException as err:
            self.close()
            raise AcondNoResponseError(f"No response during {description}: {err}") from err
        except (ConnectionException, asyncio.TimeoutError, OSError) as err:
            self.close()
            raise AcondConnectionError(f"Communication error during {description}: {err}") from err
        except ModbusException as err:
            self.close()
            raise AcondModbusError(f"Modbus error during {description}: {err}") from err
        except Exception as err:  # noqa: BLE001
            self.close()
            raise AcondError(f"Unexpected error during {description}: {err!r}") from err

        if result is None:
            raise AcondNoResponseError(f"The heat pump returned no response to {description}")
        if result.isError():
            raise AcondModbusError(f"Modbus exception response to {description}: {result}")
        return list(getattr(result, "registers", []))

    def _unit_kwargs(self) -> dict[str, int]:
        """Return the unit id keyword this pymodbus version understands."""
        return {"device_id" if _uses_device_id() else "slave": self._slave}

    def close(self) -> None:
        """Close the TCP connection."""
        client, self._client = self._client, None
        if client is not None:
            try:
                client.close()
            except Exception:  # noqa: BLE001 - closing must never raise
                _LOGGER.debug("Ignoring error while closing the Modbus connection")


_DETECTED: bool | None = None


def _uses_device_id() -> bool:
    """Detect whether pymodbus expects ``device_id`` instead of ``slave``."""
    global _DETECTED  # noqa: PLW0603 - one-time cache
    if _DETECTED is None:
        import inspect

        try:
            params = inspect.signature(
                AsyncModbusTcpClient.read_input_registers
            ).parameters
        except (TypeError, ValueError):  # pragma: no cover - exotic pymodbus
            params = {}
        _DETECTED = "device_id" in params
    return _DETECTED
