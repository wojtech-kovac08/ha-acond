"""Binary sensors for the heat pump status word (30007, read only)."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL, STATUS_BITS
from .coordinator import AcondCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one binary sensor per status bit."""
    coordinator: AcondCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        AcondBinarySensor(coordinator, entry, bit, key, device_class)
        for bit, (key, device_class) in STATUS_BITS.items()
    )


class AcondBinarySensor(CoordinatorEntity[AcondCoordinator], BinarySensorEntity):
    """One bit of the 30007 status word."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AcondCoordinator,
        entry: ConfigEntry,
        bit: int,
        key: str,
        device_class: str | None,
    ) -> None:
        """Initialise the binary sensor."""
        super().__init__(coordinator)
        self.bit = bit
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_class = (
            BinarySensorDeviceClass(device_class) if device_class else None
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Acond HP",
            manufacturer=MANUFACTURER,
            model=MODEL,
            configuration_url=f"http://{coordinator.host}",
        )

    @property
    def is_on(self) -> bool | None:
        """Return True when the status bit is set."""
        status = self.coordinator.data.get("status_word")
        if status is None:
            return None
        return bool(int(status) & (1 << self.bit))
