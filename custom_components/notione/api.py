"""API client for private notiOne cloud endpoints."""

from __future__ import annotations

import logging
from typing import Any

import requests

from .const import (
    AUTH_LOGIN,
    AUTH_PASS,
    GRANT_TYPE,
    LIST_URL,
    REQUEST_TIMEOUT,
    SCOPE,
    TOKEN_URL,
    USER_AGENT,
)
from .models import NotioneDevice, parse_device_payload

_LOGGER = logging.getLogger(__name__)


class NotioneApiError(Exception):
    """Base exception for API-level failures."""


class NotioneAuthError(NotioneApiError):
    """Authentication failed or token is invalid."""


class NotioneConnectionError(NotioneApiError):
    """Network-level error while talking to notiOne API."""


class NotionePayloadError(NotioneApiError):
    """Payload could not be parsed or did not match expected structure."""


class NotioneApiClient:
    """Thin client used by the tracker platform."""

    def __init__(self, username: str, password: str) -> None:
        self._username = username
        self._password = password

    def get_devices(self) -> list[NotioneDevice]:
        """Return normalized devices parsed from API payloads."""

        access_token = self._get_access_token()
        raw_devices = self._get_device_list(access_token)

        devices = []
        for raw in raw_devices:
            try:
                devices.append(parse_device_payload(raw))
            except ValueError as err:
                _LOGGER.warning("Skipping malformed device payload: %s", err)

        return devices

    def _get_access_token(self) -> str:
        """Authenticate and return OAuth access token."""

        data = {
            "grant_type": GRANT_TYPE,
            "username": self._username,
            "password": self._password,
            "scope": SCOPE,
        }

        try:
            response = requests.post(
                TOKEN_URL,
                data=data,
                allow_redirects=False,
                auth=(AUTH_LOGIN, AUTH_PASS),
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as err:
            raise NotioneConnectionError(
                f"Failed to connect to token endpoint: {err}"
            ) from err

        payload = _decode_json(response)
        if response.status_code >= 400:
            reason = _extract_error_reason(payload)
            raise NotioneAuthError(f"Authentication rejected: {reason}")

        access_token = payload.get("access_token") if isinstance(payload, dict) else None
        if not access_token:
            raise NotionePayloadError("Token response missing access_token")

        return str(access_token)

    def _get_device_list(self, access_token: str) -> list[dict[str, Any]]:
        """Fetch raw device list payload."""

        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": USER_AGENT,
        }

        try:
            response = requests.get(LIST_URL, headers=headers, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as err:
            raise NotioneConnectionError(
                f"Failed to connect to device list endpoint: {err}"
            ) from err

        payload = _decode_json(response)
        if response.status_code in (401, 403):
            raise NotioneAuthError("Access token rejected by device list endpoint")
        if response.status_code >= 400:
            reason = _extract_error_reason(payload)
            raise NotioneApiError(f"Device list request failed: {reason}")

        if not isinstance(payload, dict):
            raise NotionePayloadError("Device list payload is not an object")

        device_list = payload.get("deviceList")
        if not isinstance(device_list, list):
            raise NotionePayloadError("Device list payload missing deviceList array")

        return device_list


def _decode_json(response: requests.Response) -> Any:
    """Decode JSON payload and raise clear errors on failure."""

    try:
        return response.json()
    except ValueError as err:
        raise NotionePayloadError("Response is not valid JSON") from err


def _extract_error_reason(payload: Any) -> str:
    """Extract best-effort error reason from API payload."""

    if isinstance(payload, dict):
        return str(
            payload.get("error_description")
            or payload.get("error")
            or payload.get("message")
            or "unknown"
        )

    return "unknown"