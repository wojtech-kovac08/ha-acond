"""Climate platform for the Acond heat pump.

The entity is read only: it shows the measured and the requested temperature
of one heating circuit, both read from the input registers. Nothing is written
to the heat pump.
"""

from __future__ import annotations

from homeassistant.components.climate import ClimateEntity, HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL, TEMP_MAX, TEMP_MIN
from .coordinator import AcondCoordinator


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
    """Read only view of one heating circuit."""

    _attr_has_entity_name = True
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 1
    _attr_target_temperature_step = 0.1
    _attr_min_temp = TEMP_MIN
    _attr_max_temp = TEMP_MAX
    #: The unit reports no per-circuit mode through the registers we read.
    _attr_hvac_modes = [HVACMode.HEAT]

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
        """Return the only mode this read only entity reports."""
        return HVACMode.HEAT

    @property
    def available(self) -> bool:
        """Return True while the coordinator has fresh data."""
        return super().available and bool(self.coordinator.data)
