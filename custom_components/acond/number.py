"""Number platform for the Acond heat pump - requested temperatures."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DHW_MAX, DHW_MIN, DOMAIN, MANUFACTURER, MODEL, TEMP_MAX, TEMP_MIN
from .coordinator import AcondCoordinator


@dataclass(frozen=True, kw_only=True)
class AcondNumberDescription(NumberEntityDescription):
    """Description of a requested temperature."""

    circuit: int | None = None


NUMBERS: tuple[AcondNumberDescription, ...] = (
    AcondNumberDescription(
        key="setpoint_circuit_1",
        translation_key="setpoint_circuit_1",
        circuit=1,
        native_min_value=TEMP_MIN,
        native_max_value=TEMP_MAX,
        native_step=0.1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        mode=NumberMode.BOX,
    ),
    AcondNumberDescription(
        key="setpoint_circuit_2",
        translation_key="setpoint_circuit_2",
        circuit=2,
        native_min_value=TEMP_MIN,
        native_max_value=TEMP_MAX,
        native_step=0.1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        mode=NumberMode.BOX,
    ),
    AcondNumberDescription(
        key="setpoint_dhw",
        translation_key="setpoint_dhw",
        circuit=None,
        native_min_value=DHW_MIN,
        native_max_value=DHW_MAX,
        native_step=0.1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        mode=NumberMode.BOX,
        icon="mdi:water-boiler",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the requested temperature numbers."""
    coordinator: AcondCoordinator = hass.data[DOMAIN][entry.entry_id]
    available = {spec.key for spec in coordinator.values}
    async_add_entities(
        AcondNumber(coordinator, entry, description)
        for description in NUMBERS
        if description.key in available
    )


class AcondNumber(CoordinatorEntity[AcondCoordinator], NumberEntity):
    """Requested temperature of a circuit or of the DHW tank."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AcondCoordinator,
        entry: ConfigEntry,
        description: AcondNumberDescription,
    ) -> None:
        """Initialise the number entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_translation_key = description.translation_key
        self._attr_unique_id = f"{entry.entry_id}_number_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Acond HP",
            manufacturer=MANUFACTURER,
            model=MODEL,
            configuration_url=f"http://{coordinator.host}",
        )

    @property
    def native_value(self) -> float | None:
        """Return the temperature currently requested from the unit."""
        value = self.coordinator.data.get(self.entity_description.key)
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Write the new requested temperature."""
        if self.entity_description.circuit is None:
            await self.coordinator.async_set_dhw_temperature(value)
        else:
            await self.coordinator.async_set_temperature(
                self.entity_description.circuit, value
            )
