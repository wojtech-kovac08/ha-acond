"""Sensor platform for the Acond heat pump (read only)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CUSTOM_SENSOR_KEYS,
    DOMAIN,
    FAULT_CODES,
    MANUFACTURER,
    MODEL,
    STATUS_BITS,
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
        for spec in coordinator.values
        if spec.key not in CUSTOM_SENSOR_KEYS
    ]

    available = {spec.key for spec in coordinator.values}
    if "fault_code" in available:
        entities.append(AcondFaultSensor(coordinator, entry))
    if "status_word" in available:
        entities.append(AcondStatusSensor(coordinator, entry))
    for key in ("silent_start", "silent_stop"):
        if key in available:
            spec = next(spec for spec in coordinator.values if spec.key == key)
            entities.append(AcondMinutesSensor(coordinator, entry, spec))
    for key in ("hp_mode", "regulation_type"):
        if key in available:
            spec = next(spec for spec in coordinator.values if spec.key == key)
            entities.append(AcondEnumSensor(coordinator, entry, spec))

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
    """One decoded numeric value from the heat pump."""

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
        self._attr_device_class = (
            SensorDeviceClass(spec.device_class) if spec.device_class else None
        )
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_suggested_display_precision = spec.precision
        self._attr_state_class = (
            SensorStateClass(spec.state_class) if spec.state_class else None
        )
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


class AcondStatusSensor(CoordinatorEntity[AcondCoordinator], SensorEntity):
    """Raw status word (30007) with all bits as attributes."""

    _attr_has_entity_name = True
    _attr_translation_key = "status_word"
    _attr_icon = "mdi:information-outline"

    def __init__(self, coordinator: AcondCoordinator, entry: ConfigEntry) -> None:
        """Initialise the status word sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_status_word"
        self._attr_device_info = _device_info(coordinator, entry)

    @property
    def native_value(self) -> int | None:
        """Return the raw 16 bit value."""
        value = self.coordinator.data.get("status_word")
        return int(value) if value is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return every status bit as a boolean attribute."""
        value = self.coordinator.data.get("status_word")
        if value is None:
            return {}
        word = int(value)
        attributes: dict[str, Any] = {"bits": format(word, "016b")}
        for bit, (key, _) in STATUS_BITS.items():
            attributes[key] = bool(word & (1 << bit))
        return attributes


class AcondEnumSensor(CoordinatorEntity[AcondCoordinator], SensorEntity):
    """A register whose values are named (mode, type of regulation)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AcondCoordinator,
        entry: ConfigEntry,
        spec: ValueSpec,
    ) -> None:
        """Initialise the enum sensor."""
        super().__init__(coordinator)
        self.spec = spec
        self._attr_translation_key = spec.key
        self._attr_unique_id = f"{entry.entry_id}_{spec.key}"
        self._attr_icon = spec.icon
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = list((spec.state_map or {}).values())
        self._attr_device_info = _device_info(coordinator, entry)

    @property
    def native_value(self) -> str | None:
        """Return the named value."""
        value = self.coordinator.data.get(self.spec.key)
        if value is None:
            return None
        return (self.spec.state_map or {}).get(int(value))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the raw register value as well."""
        value = self.coordinator.data.get(self.spec.key)
        return {"raw": int(value)} if value is not None else {}


class AcondMinutesSensor(CoordinatorEntity[AcondCoordinator], SensorEntity):
    """Minutes from midnight (silent mode start/stop), with a HH:MM attribute."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AcondCoordinator,
        entry: ConfigEntry,
        spec: ValueSpec,
    ) -> None:
        """Initialise the minutes sensor."""
        super().__init__(coordinator)
        self.spec = spec
        self._attr_translation_key = spec.key
        self._attr_unique_id = f"{entry.entry_id}_{spec.key}"
        self._attr_icon = spec.icon
        self._attr_native_unit_of_measurement = "min"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_device_info = _device_info(coordinator, entry)

    @property
    def native_value(self) -> int | None:
        """Return the value in minutes."""
        value = self.coordinator.data.get(self.spec.key)
        return int(value) if value is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the value as HH:MM."""
        value = self.coordinator.data.get(self.spec.key)
        if value is None:
            return {}
        minutes = int(value)
        return {"time": f"{minutes // 60:02d}:{minutes % 60:02d}"}
