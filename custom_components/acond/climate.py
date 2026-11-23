"""Climate platform for the Acond heat pump (one entity per heating circuit)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    MANUFACTURER,
    MODEL,
    TEMP_MAX,
    TEMP_MIN,
    hvac_mode_from_hp_mode,
)
from .coordinator import AcondCoordinator

#: internal mode name -> Home Assistant mode.
_MODE_TO_HVAC = {
    "off": HVACMode.OFF,
    "heat": HVACMode.HEAT,
    "cool": HVACMode.COOL,
}
_HVAC_TO_MODE = {value: key for key, value in _MODE_TO_HVAC.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one climate entity per heating circuit."""
    coordinator: AcondCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        AcondClimate(coordinator, entry, circuit) for circuit in (1, 2)
    )


class AcondClimate(CoordinatorEntity[AcondCoordinator], ClimateEntity):
    """Heating circuit of the heat pump."""

    _attr_has_entity_name = True
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 1
    _attr_target_temperature_step = 0.1
    _attr_min_temp = TEMP_MIN
    _attr_max_temp = TEMP_MAX
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

    def __init__(
        self,
        coordinator: AcondCoordinator,
        entry: ConfigEntry,
        circuit: int,
    ) -> None:
        """Initialise the climate entity."""
        super().__init__(coordinator)
        self.circuit = circuit
        self._attr_translation_key = f"circuit_{circuit}"
        self._attr_unique_id = f"{entry.entry_id}_climate_{circuit}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Acond HP",
            manufacturer=MANUFACTURER,
            model=MODEL,
            configuration_url=f"http://{coordinator.host}",
        )

    @property
    def current_temperature(self) -> float | None:
        """Return the measured room temperature."""
        value = self.coordinator.data.get(f"temperature_circuit_{self.circuit}")
        return float(value) if value is not None else None

    @property
    def target_temperature(self) -> float | None:
        """Return the requested room temperature."""
        value = self.coordinator.data.get(f"setpoint_circuit_{self.circuit}")
        return float(value) if value is not None else None

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current mode of the heat pump."""
        hp_mode = int(self.coordinator.data.get("hp_mode", 0))
        return _MODE_TO_HVAC[hvac_mode_from_hp_mode(hp_mode)]

    @property
    def hvac_action(self) -> HVACAction:
        """Return what the heat pump is doing right now."""
        mode = self.hvac_mode
        if mode == HVACMode.OFF:
            return HVACAction.OFF

        status = int(self.coordinator.data.get("status", 0))
        running = bool(status & 0b11)  # bit 0 = HP on, bit 1 = HP operation
        if not running:
            return HVACAction.IDLE
        return HVACAction.COOLING if mode == HVACMode.COOL else HVACAction.HEATING

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set a new requested temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self.coordinator.async_set_temperature(self.circuit, float(temperature))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Switch the heat pump mode."""
        mode = _HVAC_TO_MODE.get(hvac_mode)
        if mode is None:
            return
        await self.coordinator.async_set_hvac_mode(mode)
