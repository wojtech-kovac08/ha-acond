"""Sensor platform for the Acond heat pump (read only)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    FAULT_CODES,
    MANUFACTURER,
    MODEL,
    NON_SENSOR_KEYS,
    VALUES,
    ValueSpec,
)
from .coordinator import AcondCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Acond sensors."""
    coordinator: AcondCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        AcondSensor(coordinator, entry, spec)
        for spec in VALUES
        if spec.key not in NON_SENSOR_KEYS
    ]
    entities.append(AcondFaultSensor(coordinator, entry))
    async_add_entities(entities)


def _device_info(coordinator: AcondCoordinator, entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Acond HP",
        manufacturer=MANUFACTURER,
        model=MODEL,
        configuration_url=f"http://{coordinator.host}",
    )


class AcondSensor(CoordinatorEntity[AcondCoordinator], SensorEntity):
    """One decoded value from the heat pump."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AcondCoordinator,
        entry: ConfigEntry,
        spec: ValueSpec,
    ) -> None:
        """Initialise the sensor from its register specification."""
        super().__init__(coordinator)
        self.spec = spec
        self._attr_translation_key = spec.key
        self._attr_unique_id = f"{entry.entry_id}_{spec.key}"
        self._attr_device_class = spec.device_class
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_suggested_display_precision = spec.precision
        self._attr_state_class = spec.state_class
        self._attr_icon = spec.icon
        self._attr_device_info = _device_info(coordinator, entry)

    @property
    def native_value(self) -> float | int | None:
        """Return the decoded value."""
        return self.coordinator.data.get(self.spec.key)


class AcondFaultSensor(CoordinatorEntity[AcondCoordinator], SensorEntity):
    """Last fault reported by the heat pump (30021)."""

    _attr_has_entity_name = True
    _attr_translation_key = "fault_code"
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, coordinator: AcondCoordinator, entry: ConfigEntry) -> None:
        """Initialise the fault sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_fault_code"
        self._attr_device_info = _device_info(coordinator, entry)

    @property
    def native_value(self) -> str | None:
        """Return the fault code, e.g. ``A01``."""
        value = self.coordinator.data.get("fault_code")
        if value is None:
            return None
        code, _ = FAULT_CODES.get(int(value), (f"UNKNOWN ({value})", "UNKNOWN"))
        return code

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the numeric value and the human readable description."""
        value = self.coordinator.data.get("fault_code")
        if value is None:
            return {}
        code, description = FAULT_CODES.get(int(value), (f"UNKNOWN ({value})", "UNKNOWN"))
        return {"code": int(value), "description": description, "fault": code}
