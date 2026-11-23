"""Sensor platform for the Acond heat pump."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import AcondCoordinator


@dataclass(frozen=True, kw_only=True)
class AcondSensorEntityDescription(SensorEntityDescription):
    """Description of one Acond temperature sensor."""


SENSORS: tuple[AcondSensorEntityDescription, ...] = (
    AcondSensorEntityDescription(
        key="setpoint_circuit_1",
        translation_key="setpoint_circuit_1",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    AcondSensorEntityDescription(
        key="temperature_circuit_1",
        translation_key="temperature_circuit_1",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    AcondSensorEntityDescription(
        key="setpoint_circuit_2",
        translation_key="setpoint_circuit_2",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    AcondSensorEntityDescription(
        key="temperature_circuit_2",
        translation_key="temperature_circuit_2",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Acond sensors from a config entry."""
    coordinator: AcondCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        AcondSensor(coordinator, entry, description) for description in SENSORS
    )


class AcondSensor(CoordinatorEntity[AcondCoordinator], SensorEntity):
    """A temperature value reported by the heat pump."""

    _attr_has_entity_name = True
    entity_description: AcondSensorEntityDescription

    def __init__(
        self,
        coordinator: AcondCoordinator,
        entry: ConfigEntry,
        description: AcondSensorEntityDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Acond HP",
            manufacturer=MANUFACTURER,
            model=MODEL,
            configuration_url=f"http://{coordinator.host}",
        )

    @property
    def native_value(self) -> float | None:
        """Return the decoded temperature."""
        return self.coordinator.data.get(self.entity_description.key)
