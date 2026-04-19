"""The notione integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, SCAN_INTERVAL
from .coordinator import NotioneDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.DEVICE_TRACKER, Platform.SENSOR]
DEFAULT_SCAN_INTERVAL_SECONDS = int(SCAN_INTERVAL.total_seconds())
MIN_SCAN_INTERVAL_SECONDS = 60


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
	"""Set up the integration from YAML (no-op, ConfigEntry only)."""

	return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
	"""Set up notiOne from a config entry."""

	hass.data.setdefault(DOMAIN, {})

	username = entry.data.get(CONF_USERNAME)
	password = entry.data.get(CONF_PASSWORD)
	if not username or not password:
		_LOGGER.error("Config entry is missing credentials")
		return False

	raw_interval = entry.options.get(
		CONF_SCAN_INTERVAL,
		entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS),
	)

	try:
		interval_seconds = max(MIN_SCAN_INTERVAL_SECONDS, int(raw_interval))
	except (TypeError, ValueError):
		interval_seconds = DEFAULT_SCAN_INTERVAL_SECONDS

	coordinator = NotioneDataUpdateCoordinator(
		hass=hass,
		username=username,
		password=password,
		update_interval=timedelta(seconds=interval_seconds),
	)

	await coordinator.async_config_entry_first_refresh()
	hass.data[DOMAIN][entry.entry_id] = coordinator
	await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
	return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
	"""Unload a config entry."""

	unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
	if unload_ok:
		hass.data[DOMAIN].pop(entry.entry_id, None)
		if not hass.data[DOMAIN]:
			hass.data.pop(DOMAIN)

	return unload_ok
