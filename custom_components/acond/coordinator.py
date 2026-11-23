"""Data update coordinator for the Acond heat pump."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import (
    AcondConnectionError,
    AcondError,
    AcondModbusClient,
    to_signed,
)
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_SLAVE,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE,
    DEFAULT_TIMEOUT,
    DOMAIN,
    HP_MODE_OFFSET,
    REGISTER_BLOCK_START,
    REGISTER_COUNT,
    REGISTERS,
    SETTINGS_REGISTER,
    STATUS_OFFSET,
    TARGET_REGISTERS,
    settings_word_for_mode,
)

_LOGGER = logging.getLogger(__name__)


class AcondCoordinator(DataUpdateCoordinator[dict[str, float | int]]):
    """Poll the heat pump and keep the decoded register values."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialise the coordinator from the config entry."""
        self.host: str = entry.data[CONF_HOST]
        self.port: int = int(entry.data.get(CONF_PORT, DEFAULT_PORT))
        self.slave: int = int(entry.data.get(CONF_SLAVE, DEFAULT_SLAVE))

        interval = entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=int(interval)),
        )

        self.client = AcondModbusClient(
            self.host,
            port=self.port,
            slave=self.slave,
            timeout=DEFAULT_TIMEOUT,
        )

    async def _async_update_data(self) -> dict[str, float | int]:
        """Read the register block and decode the values."""
        try:
            await self.client.async_connect()
            registers = await self.client.async_read_input_registers(
                REGISTER_BLOCK_START, REGISTER_COUNT
            )
        except (AcondError, OSError, asyncio.TimeoutError) as err:
            self.client.close()
            raise UpdateFailed(f"Communication with the heat pump failed: {err}") from err

        data: dict[str, float | int] = {}
        for key, (offset, divisor) in REGISTERS.items():
            data[key] = round(to_signed(registers[offset]) / divisor, 1)
        data["status"] = registers[STATUS_OFFSET]
        data["hp_mode"] = to_signed(registers[HP_MODE_OFFSET])
        return data

    async def async_set_temperature(self, circuit: int, temperature: float) -> None:
        """Write a new requested temperature for one circuit."""
        if circuit not in TARGET_REGISTERS:
            raise AcondError(f"Unknown circuit {circuit}")

        raw = max(0, int(round(temperature * 10)))
        await self.client.async_connect()
        await self.client.async_write_register(TARGET_REGISTERS[circuit], raw)
        await self.async_request_refresh()

    async def async_set_hvac_mode(self, mode: str) -> None:
        """Switch the heat pump mode, keeping the other settings bits intact."""
        await self.client.async_connect()
        current = await self.client.async_read_holding_registers(SETTINGS_REGISTER, 1)
        await self.client.async_write_register(
            SETTINGS_REGISTER, settings_word_for_mode(current[0], mode)
        )
        await self.async_request_refresh()

    async def async_shutdown(self) -> None:
        """Close the Modbus connection."""
        self.client.close()
