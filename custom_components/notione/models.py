"""Payload models and parsers for notiOne API responses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .const import LOW_BATTERY_THRESHOLD


@dataclass(slots=True)
class NotioneBattery:
    """Normalized battery data used by entities."""

    status: str = "unknown"
    level: int | None = None


@dataclass(slots=True)
class NotioneDevice:
    """Normalized device model parsed from the notiOne API payload."""

    device_id: str
    name: str
    device_type: str | None
    device_version: str | None
    latitude: float | None
    longitude: float | None
    gps_accuracy: int | float | None
    gpstime: datetime | None
    city: str | None
    street: str | None
    entity_picture: str
    battery: NotioneBattery
    mac: str
    zone_id: str | None

    @property
    def has_location(self) -> bool:
        """Whether this device can be represented as a tracker."""

        return self.latitude is not None and self.longitude is not None


def parse_device_payload(raw: dict[str, Any]) -> NotioneDevice:
    """Parse one raw device payload into a normalized model."""

    tracker_id = raw.get("deviceId")
    if tracker_id is None:
        raise ValueError("missing deviceId")

    device_id = str(tracker_id)
    name = raw.get("name") or device_id

    position = raw.get("lastPosition") if isinstance(raw.get("lastPosition"), dict) else {}
    latitude = _as_float(position.get("latitude"))
    longitude = _as_float(position.get("longitude"))
    gps_accuracy = _as_float(position.get("accuracy"))
    gpstime = _parse_gpstime(position.get("gpstime"))
    city = _as_optional_str(position.get("geocodeCity"))
    street = _as_optional_str(position.get("geocodePlace"))

    battery, mac = _extract_battery_and_mac(raw, device_id)
    entity_picture = _normalize_picture_url(raw.get("avatar"))

    return NotioneDevice(
        device_id=device_id,
        name=name,
        device_type=_as_optional_str(raw.get("deviceType")),
        device_version=_as_optional_str(raw.get("deviceVersion")),
        latitude=latitude,
        longitude=longitude,
        gps_accuracy=gps_accuracy,
        gpstime=gpstime,
        city=city,
        street=street,
        entity_picture=entity_picture,
        battery=battery,
        mac=mac,
        zone_id=_as_optional_str(raw.get("zoneId")),
    )


def _extract_battery_and_mac(
    raw: dict[str, Any], default_mac: str
) -> tuple[NotioneBattery, str]:
    """Extract battery and identifier data across GPS and beacon families."""

    battery = NotioneBattery()
    mac = default_mac

    gps_details = raw.get("gpsDetails")
    if isinstance(gps_details, dict):
        raw_imei = gps_details.get("imei")
        if raw_imei is not None:
            mac = str(raw_imei)

        raw_battery = gps_details.get("battery")
        if isinstance(raw_battery, (int, float)) and not isinstance(raw_battery, bool):
            battery.level = int(raw_battery)
            battery.status = (
                "low" if battery.level <= LOW_BATTERY_THRESHOLD else "high"
            )

    notione_details = raw.get("notiOneDetails")
    if isinstance(notione_details, dict):
        raw_mac = notione_details.get("mac")
        if raw_mac:
            mac = str(raw_mac)

        raw_battery = notione_details.get("battery")
        if isinstance(raw_battery, bool):
            # In observed payloads this behaves like a low-battery flag.
            battery.status = "low" if raw_battery else "high"

    return battery, mac


def _parse_gpstime(gpstime_ms: Any) -> datetime | None:
    """Convert API gps timestamp in ms to UTC datetime."""

    if not isinstance(gpstime_ms, (int, float)):
        return None

    return datetime.fromtimestamp(gpstime_ms / 1000.0, tz=timezone.utc)


def _normalize_picture_url(picture_url: Any) -> str:
    """Return only valid HTTP(S) avatar links."""

    if not isinstance(picture_url, str):
        return ""

    if picture_url.startswith(("http://", "https://")):
        return picture_url

    return ""


def _as_optional_str(value: Any) -> str | None:
    """Return a trimmed string value or None."""

    if value is None:
        return None

    value = str(value).strip()
    return value or None


def _as_float(value: Any) -> float | None:
    """Return numeric values as float, otherwise None."""

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)

    return None