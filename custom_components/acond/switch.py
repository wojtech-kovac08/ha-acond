"""Switch platform for the Acond heat pump - summer/winter operation."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    MANUFACTURER,
    MODEL,
    SUMMER_BIT,
    SUMMER_BIT_INVERTED,
)
from .coordinator import AcondCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the season switch (bit 8 of 40006)."""
    coordinator: AcondCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AcondSummerSwitch(coordinator, entry)])


class AcondSummerSwitch(CoordinatorEntity[AcondCoordinator], SwitchEntity):
    """Switch between summer and winter operation."""

    _attr_has_entity_name = True
    _attr_translation_key = "summer_mode"
    _attr_icon = "mdi:weather-sunny"

    def __init__(self, coordinator: AcondCoordinator, entry: ConfigEntry) -> None:
        """Initialise the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_switch_summer"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Acond HP",
            manufacturer=MANUFACTURER,
            model=MODEL,
            configuration_url=f"http://{coordinator.host}",
        )

    @property
    def is_on(self) -> bool | None:
        """Return True when the unit is in summer mode."""
        word = self.coordinator.data.get("settings_word")
        if word is None:
            return None
        bit = bool(int(word) & (1 << SUMMER_BIT))
        return bit != SUMMER_BIT_INVERTED

    async def async_turn_on(self, **kwargs) -> None:
        """Switch to summer mode."""
        await self.coordinator.async_set_summer(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Switch to winter mode."""
        await self.coordinator.async_set_summer(False)
