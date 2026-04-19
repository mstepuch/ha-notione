"""Sensor entities for the notiOne integration."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NotioneDataUpdateCoordinator
from .models import NotioneDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up notiOne sensor entities from a config entry."""

    coordinator: NotioneDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    known_ids: set[str] = set()

    @callback
    def _async_add_missing_entities() -> None:
        new_entities: list[NotioneBatterySensorEntity] = []

        for device in coordinator.data.values():
            if device.battery.level is None:
                continue
            if device.device_id in known_ids:
                continue

            known_ids.add(device.device_id)
            new_entities.append(NotioneBatterySensorEntity(coordinator, device.device_id))

        if new_entities:
            async_add_entities(new_entities)

    _async_add_missing_entities()
    entry.async_on_unload(coordinator.async_add_listener(_async_add_missing_entities))


class NotioneBatterySensorEntity(
    CoordinatorEntity[NotioneDataUpdateCoordinator],
    SensorEntity,
):
    """Battery level sensor for GPS-family notiOne devices."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_has_entity_name = True
    _attr_name = "Battery"

    def __init__(self, coordinator: NotioneDataUpdateCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_battery"

    @property
    def _device(self) -> NotioneDevice | None:
        return self.coordinator.data.get(self._device_id)

    @property
    def available(self) -> bool:
        device = self._device
        return super().available and device is not None and device.battery.level is not None

    @property
    def native_value(self) -> int | None:
        device = self._device
        if device is None:
            return None

        return device.battery.level

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        device = self._device
        if device is None:
            return {}

        return {
            "battery_status": device.battery.status,
        }

    @property
    def device_info(self) -> DeviceInfo:
        device = self._device

        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            manufacturer="notiOne",
            model=device.device_version if device else None,
            name=device.name if device else self._device_id,
        )