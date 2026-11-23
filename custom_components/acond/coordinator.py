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

from .api import AcondConnectionError, AcondError, AcondModbusClient, to_signed, to_signed32
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
        #: Blocks the unit refused during the last cycle (offset -> error).
        self.failed_blocks: dict[int, str] = {}

    async def _async_update_data(self) -> AcondData:
        """Read the register blocks and decode every known value.

        Each block is read on its own. A block the unit refuses only makes its
        own values unavailable, the rest keeps working.
        """
        try:
            await self.client.async_connect()
        except (AcondConnectionError, AcondError, OSError) as err:
            self.client.close()
            raise UpdateFailed(f"Cannot connect to the heat pump: {err}") from err

        raw: dict[int, list[int]] = {}
        failed: dict[int, str] = {}

        for start, count in BLOCKS:
            try:
                raw[start] = await self.client.async_read_input_registers(start, count)
            except AcondConnectionError as err:
                # Connection dropped - reconnect once, then give up on the rest.
                failed[start] = str(err)
                _LOGGER.debug("Connection lost while reading %s: %s", 30001 + start, err)
                try:
                    await self.client.async_connect()
                except (AcondError, OSError):
                    break
            except AcondError as err:
                failed[start] = str(err)
                _LOGGER.warning(
                    "Heat pump refused registers %s-%s: %s",
                    30001 + start,
                    30001 + start + count - 1,
                    err,
                )
            except (OSError, asyncio.TimeoutError) as err:
                failed[start] = str(err)

        self.failed_blocks = failed

        if not raw:
            self.client.close()
            raise UpdateFailed(
                "The heat pump did not answer a single register block. "
                f"First error: {next(iter(failed.values()), 'unknown')}"
            )

        data: AcondData = {}
        for spec in VALUES:
            start, _ = BLOCKS[spec.block]
            registers = raw.get(start)
            if registers is None or len(registers) <= spec.offset:
                continue

            if spec.kind == "i32":
                if len(registers) < spec.offset + 2:
                    continue
                value = to_signed32((registers[spec.offset] << 16) | registers[spec.offset + 1])
            elif spec.kind == "u16":
                value = registers[spec.offset]
            else:
                value = to_signed(registers[spec.offset])

            data[spec.key] = value if spec.divisor == 1 else round(value / spec.divisor, 1)

        return data

    async def async_shutdown(self) -> None:
        """Close the Modbus connection."""
        self.client.close()
