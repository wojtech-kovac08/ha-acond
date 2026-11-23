"""Config flow for the Acond heat pump integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow

try:  # Home Assistant >= 2024.4
    from homeassistant.config_entries import ConfigFlowResult
except ImportError:  # pragma: no cover - older Home Assistant
    from homeassistant.data_entry_flow import FlowResult as ConfigFlowResult

from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)

from .api import (
    AcondConnectionError,
    AcondError,
    AcondModbusClient,
    AcondModbusError,
    AcondNoResponseError,
)
from .const import (
    BLOCKS,
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
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _normalise(user_input: dict[str, Any]) -> dict[str, Any]:
    """Coerce the form values to the types the Modbus stack expects."""
    return {
        CONF_HOST: str(user_input[CONF_HOST]).strip(),
        CONF_PORT: int(user_input[CONF_PORT]),
        CONF_SLAVE: int(user_input[CONF_SLAVE]),
        CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
        CONF_ENABLE_ENERGY: bool(user_input.get(CONF_ENABLE_ENERGY, DEFAULT_ENABLE_ENERGY)),
        CONF_ENABLE_SILENT: bool(user_input.get(CONF_ENABLE_SILENT, DEFAULT_ENABLE_SILENT)),
        CONF_ENABLE_CIRCUIT_2: bool(
            user_input.get(CONF_ENABLE_CIRCUIT_2, DEFAULT_ENABLE_CIRCUIT_2)
        ),
    }


async def _async_probe(host: str, port: int, slave: int) -> None:
    """Try to read the temperature block; raise AcondError on failure."""
    client = AcondModbusClient(host, port=port, slave=slave)
    try:
        await client.async_connect()
        # Probe only the first block - it is all the config flow needs and it
        # is the block every unit answers.
        start, count = BLOCKS[0]
        await client.async_read_input_registers(start, count)
    finally:
        client.close()


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    data = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=data.get(CONF_HOST, "")): TextSelector(),
            vol.Required(
                CONF_PORT, default=data.get(CONF_PORT, DEFAULT_PORT)
            ): NumberSelector(
                NumberSelectorConfig(
                    min=1, max=65535, step=1, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_SLAVE, default=data.get(CONF_SLAVE, DEFAULT_SLAVE)
            ): NumberSelector(
                NumberSelectorConfig(
                    min=0, max=247, step=1, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=5, max=3600, step=1, mode=NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                CONF_ENABLE_CIRCUIT_2,
                default=data.get(CONF_ENABLE_CIRCUIT_2, DEFAULT_ENABLE_CIRCUIT_2),
            ): BooleanSelector(),
            vol.Required(
                CONF_ENABLE_ENERGY,
                default=data.get(CONF_ENABLE_ENERGY, DEFAULT_ENABLE_ENERGY),
            ): BooleanSelector(),
            vol.Required(
                CONF_ENABLE_SILENT,
                default=data.get(CONF_ENABLE_SILENT, DEFAULT_ENABLE_SILENT),
            ): BooleanSelector(),
        }
    )


class AcondConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the UI configuration of one heat pump."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the connection details."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data = _normalise(user_input)
            await self.async_set_unique_id(
                f"{data[CONF_HOST]}:{data[CONF_PORT]}:{data[CONF_SLAVE]}"
            )
            self._abort_if_unique_id_configured()

            try:
                await _async_probe(data[CONF_HOST], data[CONF_PORT], data[CONF_SLAVE])
            except AcondConnectionError as err:
                _LOGGER.warning(
                    "Cannot reach the heat pump at %s:%s: %s",
                    data[CONF_HOST],
                    data[CONF_PORT],
                    err,
                )
                errors["base"] = "cannot_connect"
            except AcondNoResponseError as err:
                _LOGGER.warning(
                    "Heat pump at %s did not answer: %s", data[CONF_HOST], err
                )
                errors["base"] = "no_response"
            except AcondModbusError as err:
                _LOGGER.warning(
                    "Heat pump at %s answered with an error: %s", data[CONF_HOST], err
                )
                errors["base"] = "modbus_error"
            except Exception:  # noqa: BLE001 - report, do not crash the flow
                _LOGGER.exception("Unexpected error while probing the heat pump")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"Acond HP ({data[CONF_HOST]})",
                    data=data,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return AcondOptionsFlow()


class AcondOptionsFlow(OptionsFlow):
    """Allow changing the connection settings later on."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data = _normalise(user_input)
            try:
                await _async_probe(data[CONF_HOST], data[CONF_PORT], data[CONF_SLAVE])
            except AcondConnectionError as err:
                _LOGGER.warning("Cannot reach the heat pump: %s", err)
                errors["base"] = "cannot_connect"
            except AcondNoResponseError as err:
                _LOGGER.warning("Heat pump did not answer: %s", err)
                errors["base"] = "no_response"
            except AcondModbusError as err:
                _LOGGER.warning("Heat pump answered with an error: %s", err)
                errors["base"] = "modbus_error"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error while probing the heat pump")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title="", data=data)

        entry = self.hass.config_entries.async_get_entry(self.handler)
        current = {**(entry.data if entry else {}), **(entry.options if entry else {})}
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(current),
            errors=errors,
        )
