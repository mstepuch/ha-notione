"""Device tracker entities for the notiOne integration."""

from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MDI_ICON
from .coordinator import NotioneDataUpdateCoordinator
from .models import NotioneDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up notiOne tracker entities from a config entry."""

    coordinator: NotioneDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    known_ids: set[str] = set()

    @callback
    def _async_add_missing_entities() -> None:
        new_entities: list[NotioneTrackerEntity] = []

        for device in coordinator.data.values():
            if not device.has_location:
                continue
            if device.device_id in known_ids:
                continue

            known_ids.add(device.device_id)
            new_entities.append(NotioneTrackerEntity(coordinator, device.device_id))

        if new_entities:
            _LOGGER.debug("Adding %s tracker entities", len(new_entities))
            async_add_entities(new_entities)

    _async_add_missing_entities()
    entry.async_on_unload(coordinator.async_add_listener(_async_add_missing_entities))


class NotioneTrackerEntity(
    CoordinatorEntity[NotioneDataUpdateCoordinator],
    TrackerEntity,
):
    """Tracker entity backed by the notiOne data coordinator."""

    _attr_icon = MDI_ICON
    _attr_has_entity_name = True

    def __init__(self, coordinator: NotioneDataUpdateCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = device_id

    @property
    def _device(self) -> NotioneDevice | None:
        return self.coordinator.data.get(self._device_id)

    @property
    def name(self) -> str:
        device = self._device
        if device is None:
            return self._device_id

        return device.name

    @property
    def available(self) -> bool:
        device = self._device
        return super().available and device is not None and device.has_location

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        device = self._device
        if device is None:
            return None

        return device.latitude

    @property
    def longitude(self) -> float | None:
        device = self._device
        if device is None:
            return None

        return device.longitude

    @property
    def location_accuracy(self) -> int:
        device = self._device
        if device is None or device.gps_accuracy is None:
            return 0

        return int(device.gps_accuracy)

    @property
    def entity_picture(self) -> str | None:
        device = self._device
        if device is None or not device.entity_picture:
            return None

        return device.entity_picture

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        device = self._device
        if device is None:
            return {}

        location_parts = [part for part in (device.street, device.city) if part]
        location = ", ".join(location_parts)

        attrs = {
            "beaconid": device.device_id,
            "gpstime": device.gpstime,
            "location": location,
            "battery_status": device.battery.status,
            "deviceVersion": f"notiOne {device.device_version or 'unknown'}",
            "device_type": device.device_type,
            "zone_id": device.zone_id,
        }

        if device.battery.level is not None:
            attrs["battery_level"] = device.battery.level

        return attrs

    @property
    def device_info(self) -> DeviceInfo:
        device = self._device

        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            manufacturer="notiOne",
            model=device.device_version if device else None,
            name=device.name if device else self._device_id,
        )
