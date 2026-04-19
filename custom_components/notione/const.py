"""Constants for the notiOne integration."""

from datetime import timedelta

DOMAIN = "notione"

SCAN_INTERVAL = timedelta(seconds=300)
REQUEST_TIMEOUT = 15
LOW_BATTERY_THRESHOLD = 20

MDI_ICON = "mdi:bluetooth-connect"

TOKEN_URL = "https://auth.notinote.me/oauth/token"
LIST_URL = "https://api.notinote.me/secured/internal/devicelist"

AUTH_LOGIN = "test-oauth-client-id"
AUTH_PASS = "$2y$12$vXOUtEenVFCO1Zgy2YiePuF3WF/sDgNO3YnhRjl49NIDlEbGeSeOu"

GRANT_TYPE = "password"
SCOPE = "NOTI"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/104.0.5112.102 Safari/537.36 OPR/90.0.4480.54"
)