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
    AcondModbusError,
    to_signed,
    to_signed32,
)
from .blocks import BlockTracker, enabled_block_indexes, enabled_values
from .const import (
    BLOCKS,
    CIRCUIT_2_KEYS,
    CONF_ENABLE_CIRCUIT_2,
    CONF_ENABLE_ENERGY,
    CONF_ENABLE_SILENT,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE,
    DEFAULT_ENABLE_CIRCUIT_2,
    DEFAULT_ENABLE_ENERGY,
    DEFAULT_ENABLE_SILENT,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE,
    DEFAULT_TIMEOUT,
    DHW_TARGET_REGISTER,
    DOMAIN,
    ENERGY_BLOCKS,
    SETTINGS_REGISTER,
    SILENT_BLOCKS,
    SUMMER_BIT,
    SUMMER_BIT_INVERTED,
    TARGET_REGISTERS,
    VALUES,
    ValueSpec,
)

_LOGGER = logging.getLogger(__name__)

AcondData = dict[str, float | int]


class AcondCoordinator(DataUpdateCoordinator[AcondData]):
    """Poll the heat pump, decode values and write the few writable registers."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialise the coordinator from the config entry."""
        self.host: str = entry.data[CONF_HOST]
        self.port: int = int(entry.data.get(CONF_PORT, DEFAULT_PORT))
        self.slave: int = int(entry.data.get(CONF_SLAVE, DEFAULT_SLAVE))

        settings = {**entry.data, **entry.options}
        self.energy_enabled: bool = bool(
            settings.get(CONF_ENABLE_ENERGY, DEFAULT_ENABLE_ENERGY)
        )
        self.silent_enabled: bool = bool(
            settings.get(CONF_ENABLE_SILENT, DEFAULT_ENABLE_SILENT)
        )
        self.circuit_2_enabled: bool = bool(
            settings.get(CONF_ENABLE_CIRCUIT_2, DEFAULT_ENABLE_CIRCUIT_2)
        )

        #: Blocks that are switched off by the options.
        self.disabled_blocks: frozenset[int] = frozenset(
            (set() if self.energy_enabled else ENERGY_BLOCKS)
            | (set() if self.silent_enabled else SILENT_BLOCKS)
        )

        interval = settings.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=int(interval)),
        )

        #: Values this entry actually exposes (options can switch some off).
        self.values: tuple[ValueSpec, ...] = enabled_values(
            VALUES,
            CIRCUIT_2_KEYS,
            self.circuit_2_enabled,
            self.disabled_blocks,
        )

        #: Block indexes to poll.
        self.block_indexes: tuple[int, ...] = enabled_block_indexes(
            len(BLOCKS), self.disabled_blocks
        )

        self.client = AcondModbusClient(
            self.host,
            port=self.port,
            slave=self.slave,
            timeout=DEFAULT_TIMEOUT,
        )
        #: Blocks the unit refused during the last cycle (offset -> error).
        self.failed_blocks: dict[int, str] = {}
        #: Remembers blocks the unit does not implement, so they are not retried.
        self.tracker = BlockTracker()

    async def _async_update_data(self) -> AcondData:
        """Read the register blocks and decode every enabled value.

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

        for index in self.block_indexes:
            start, count = BLOCKS[index]
            if not self.tracker.should_read(start):
                continue
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
            except AcondModbusError as err:
                failed[start] = str(err)
                if self.tracker.record_error(start):
                    _LOGGER.warning(
                        "Heat pump does not implement registers %s-%s (%s) - "
                        "they will not be polled until the integration is reloaded",
                        30001 + start,
                        30001 + start + count - 1,
                        err,
                    )
                else:
                    _LOGGER.debug(
                        "Heat pump refused registers %s-%s: %s",
                        30001 + start,
                        30001 + start + count - 1,
                        err,
                    )
            except AcondError as err:
                failed[start] = str(err)
            except (OSError, asyncio.TimeoutError) as err:
                failed[start] = str(err)
            else:
                self.tracker.record_success(start)

        self.failed_blocks = failed

        if not raw:
            self.client.close()
            raise UpdateFailed(
                "The heat pump did not answer a single register block. "
                f"First error: {next(iter(failed.values()), 'unknown')}"
            )

        data: AcondData = {}
        for spec in self.values:
            start, _ = BLOCKS[spec.block]
            registers = raw.get(start)
            if registers is None or len(registers) <= spec.offset:
                continue

            if spec.kind == "i32":
                if len(registers) < spec.offset + 2:
                    continue
                value = to_signed32(
                    (registers[spec.offset] << 16) | registers[spec.offset + 1]
                )
            elif spec.kind == "u16":
                value = registers[spec.offset]
            else:
                value = to_signed(registers[spec.offset])

            data[spec.key] = value if spec.divisor == 1 else round(value / spec.divisor, 1)

        # 40006 - needed by the season switch (and to preserve its other bits).
        try:
            settings = await self.client.async_read_holding_registers(
                SETTINGS_REGISTER, 1
            )
        except (AcondError, OSError, asyncio.TimeoutError) as err:
            _LOGGER.debug("Cannot read the settings word (40006): %s", err)
        else:
            data["settings_word"] = settings[0]

        return data

    # --------------------------------------------------------------- writes
    async def async_set_temperature(self, circuit: int, temperature: float) -> None:
        """Write a requested room temperature (40001 / 40003)."""
        if circuit not in TARGET_REGISTERS:
            raise AcondError(f"Unknown circuit {circuit}")

        raw = max(0, int(round(temperature * 10)))
        await self.client.async_connect()
        await self.client.async_write_register(TARGET_REGISTERS[circuit], raw)
        await self.async_request_refresh()

    async def async_set_dhw_temperature(self, temperature: float) -> None:
        """Write the requested DHW temperature (40005)."""
        raw = max(0, int(round(temperature * 10)))
        await self.client.async_connect()
        await self.client.async_write_register(DHW_TARGET_REGISTER, raw)
        await self.async_request_refresh()

    async def async_set_summer(self, summer: bool) -> None:
        """Set or clear the season bit in 40006, keeping the other bits."""
        await self.client.async_connect()
        current = (await self.client.async_read_holding_registers(SETTINGS_REGISTER, 1))[0]
        wanted = summer != SUMMER_BIT_INVERTED
        word = current | (1 << SUMMER_BIT) if wanted else current & ~(1 << SUMMER_BIT)
        await self.client.async_write_register(SETTINGS_REGISTER, word)
        await self.async_request_refresh()

    async def async_shutdown(self) -> None:
        """Close the Modbus connection."""
        self.client.close()
