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
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)

from .api import AcondError, AcondModbusClient
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_SLAVE,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE,
    DOMAIN,
    REGISTER_BLOCK_START,
    REGISTER_COUNT,
)

_LOGGER = logging.getLogger(__name__)


async def _async_probe(host: str, port: int, slave: int) -> None:
    """Try to read the temperature block; raise on failure."""
    client = AcondModbusClient(host, port=port, slave=slave)
    try:
        await client.async_connect()
        await client.async_read_input_registers(REGISTER_BLOCK_START, REGISTER_COUNT)
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
            await self.async_set_unique_id(
                f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}:{user_input[CONF_SLAVE]}"
            )
            self._abort_if_unique_id_configured()

            try:
                await _async_probe(
                    user_input[CONF_HOST],
                    user_input[CONF_PORT],
                    user_input[CONF_SLAVE],
                )
            except AcondError as err:
                _LOGGER.debug("Probe failed: %s", err)
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 - unexpected socket/OS errors
                _LOGGER.exception("Unexpected error while probing the heat pump")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"Acond HP ({user_input[CONF_HOST]})",
                    data=user_input,
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
            try:
                await _async_probe(
                    user_input[CONF_HOST],
                    user_input[CONF_PORT],
                    user_input[CONF_SLAVE],
                )
            except AcondError as err:
                _LOGGER.debug("Probe failed: %s", err)
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error while probing the heat pump")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title="", data=user_input)

        entry = self.hass.config_entries.async_get_entry(self.handler)
        current = {**(entry.data if entry else {}), **(entry.options if entry else {})}
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(current),
            errors=errors,
        )
