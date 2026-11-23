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

from .api import AcondError, AcondModbusClient, to_signed, to_signed32
from .const import (
    BLOCKS,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE,
    DEFAULT_TIMEOUT,
    DOMAIN,
    VALUES,
)

_LOGGER = logging.getLogger(__name__)

AcondData = dict[str, float | int]


class AcondCoordinator(DataUpdateCoordinator[AcondData]):
    """Poll the heat pump and keep the decoded values."""

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

    async def _async_update_data(self) -> AcondData:
        """Read the register blocks and decode every known value."""
        try:
            await self.client.async_connect()
            blocks = [
                await self.client.async_read_input_registers(start, count)
                for start, count in BLOCKS
            ]
        except (AcondError, OSError, asyncio.TimeoutError) as err:
            self.client.close()
            raise UpdateFailed(f"Communication with the heat pump failed: {err}") from err

        data: AcondData = {}
        for spec in VALUES:
            registers = blocks[spec.block]
            if spec.kind == "i32":
                raw = to_signed32((registers[spec.offset] << 16) | registers[spec.offset + 1])
            elif spec.kind == "u16":
                raw = registers[spec.offset]
            else:
                raw = to_signed(registers[spec.offset])

            if spec.divisor == 1:
                data[spec.key] = raw
            else:
                data[spec.key] = round(raw / spec.divisor, 1)
        return data

    async def async_shutdown(self) -> None:
        """Close the Modbus connection."""
        self.client.close()
