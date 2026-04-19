"""Data update coordinator for the notiOne integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NotioneApiClient, NotioneApiError, NotioneAuthError
from .const import DOMAIN
from .models import NotioneDevice

_LOGGER = logging.getLogger(__name__)


class NotioneDataUpdateCoordinator(DataUpdateCoordinator[dict[str, NotioneDevice]]):
    """Fetch and hold normalized notiOne device data."""

    def __init__(
        self,
        hass: HomeAssistant,
        username: str,
        password: str,
        update_interval: timedelta,
    ) -> None:
        self.api_client = NotioneApiClient(username=username, password=password)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> dict[str, NotioneDevice]:
        """Fetch latest data from API and normalize it."""

        try:
            devices = await self.hass.async_add_executor_job(self.api_client.get_devices)
        except NotioneAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except NotioneApiError as err:
            raise UpdateFailed(str(err)) from err

        return {device.device_id: device for device in devices}