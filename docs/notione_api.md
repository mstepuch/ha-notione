# notiOne API Research

Research date: 2026-04-19

This note documents the private notiOne API used by the current Home Assistant fork and the newer API flow exposed by the official web panel. Findings were validated against a dedicated test account, but sensitive values and account-specific data are intentionally omitted.

## API hosts

- Panel application: `https://panel.notione.com`
- Auth host: `https://auth.notinote.me`
- Secured API host: `https://api.notinote.me`

The official panel bundle exposes these base URLs:

- `tokenUrl = https://auth.notinote.me/public/user/authorize`
- `notinoteUnsecuredApiUrl = https://auth.notinote.me/public/user`
- `notinoteApiUrl = https://api.notinote.me/secured/internal`
- `applicationUrl = https://panel.notione.com`

## Auth flows

### 1. Legacy flow used by the current integration

The current integration in [custom_components/notione/device_tracker.py](custom_components/notione/device_tracker.py) uses this sequence:

1. `POST https://auth.notinote.me/oauth/token`
2. HTTP Basic auth with the client values embedded in the integration
3. Form fields:
   - `grant_type=password`
   - `username=<notione email>`
   - `password=<notione password>`
   - `scope=NOTI`
4. Response contains:
   - `access_token`
   - `refresh_token`
   - `scope`
   - `expires_in`
   - `token_type`

This flow is still working as of 2026-04-19.

### 2. Newer flow referenced by the official panel

The web panel bundle references a different auth flow:

1. `POST https://auth.notinote.me/public/user/authorize/login`
2. HTTP Basic auth with the same client identity embedded in the panel bundle
3. JSON body:
   - `email`
   - `password`
   - `scope`
4. Refresh endpoint:
   - `POST https://auth.notinote.me/public/user/authorize/refresh`
   - JSON body: `refreshToken`, `scope`

The frontend also has an interceptor that:

- matches secured endpoints with `securedEndpointPattern`
- injects `Authorization: Bearer <token>`
- refreshes the session when the token is near expiry

Direct calls to `/public/user/authorize/login` and `/public/user/authorize/refresh` returned HTTP `500` in manual external tests, even with browser-like headers. The endpoints clearly exist in the frontend bundle, but they were not successfully exercised outside the panel app during this investigation.

## Confirmed secured endpoints

Confirmed from frontend bundle and/or live tests:

- `GET /secured/internal/devicelist`
- `GET /secured/internal/devicesamples`
- `PUT /secured/internal/editdevice`
- `GET /secured/internal/account/logout`
- `POST /secured/internal/account/password/change`
- `POST /public/user/password/reset`
- `POST /public/user/password/change`

Behavior observed in live tests:

- secured endpoints return `403` for missing or invalid bearer token
- CORS allows `https://panel.notione.com`
- `devicesamples` expects the `date` query parameter as epoch milliseconds, not `YYYY-MM-DD`

## Confirmed `devicelist` response shape

Live response on the test account returned `totalCount = 2` and `deviceList` containing two different device families:

- GPS device: `deviceType = GPS_PET`, `deviceVersion = TUBE`
- Beacon/phone device: `deviceType = PHONE`, `deviceVersion = BEACON_PHONE`

Sanitized response structure:

```json
{
  "deviceList": [
    {
      "deviceId": 12345,
      "deviceVersion": "TUBE",
      "deviceType": "GPS_PET",
      "name": "...",
      "lastPosition": {
        "accelerometerStatusEnum": "MOVE",
        "accuracy": 0,
        "geocodeCity": "...",
        "geocodePlace": "...",
        "gpsOrientationEnum": "VERTICAL",
        "gpsSnr": 17,
        "gpstime": 1776589995000,
        "humidity": 70,
        "latitude": 0.0,
        "longitude": 0.0,
        "speed": 1,
        "temperature": 20
      },
      "deviceState": "ONLINE",
      "avatar": "https://cdn.signed.avatars.notinote.me/...",
      "ownership": "OWNED",
      "wanted": false,
      "foundMessage": null,
      "notiOneDetails": null,
      "gpsDetails": {
        "battery": 66,
        "imei": 123456789012345,
        "serialNumber": 12345,
        "firmwareVersion": "1.1.1.1",
        "drawingType": "ROUTE",
        "subscription": {
          "deviceId": 12345,
          "subscriptionType": "PLUS_LIFETIME",
          "startDate": "2026-04-09T08:46:55.000Z",
          "endDate": "2126-04-09T08:46:55.000Z",
          "expired": false,
          "status": true,
          "subscriptionExpiration": 4931398015000
        },
        "etollEnabled": false,
        "extendedHistory": false,
        "etollServiceStatus": null,
        "gpsFeatures": {
          "allowLiveMode": false,
          "allowTimeline": true
        },
        "approximateSample": null,
        "akuCharging": false,
        "refreshIntervalSeconds": 10
      },
      "sharedDetailsList": null,
      "lastPairedTime": "2026-04-10T13:51:10.035Z",
      "samplesHistoryLimit": {
        "historyDaysLimit": 9,
        "historyDaysMaxLimit": 9
      },
      "zoneId": "Europe/Warsaw",
      "sharedAccepted": false
    },
    {
      "deviceId": 67890,
      "deviceVersion": "BEACON_PHONE",
      "deviceType": "PHONE",
      "name": "...",
      "lastPosition": null,
      "deviceState": "ONLINE",
      "avatar": null,
      "ownership": "OWNED",
      "wanted": false,
      "foundMessage": null,
      "notiOneDetails": {
        "battery": false,
        "beaconDeviceVersion": 100,
        "deviceNumber": 90005503,
        "firmwareVersion": 0,
        "mac": "00:00:00:00:00:00",
        "major": 1373,
        "minor": 24575,
        "needsUpdate": false,
        "uniqueIdentifier": "..."
      },
      "gpsDetails": null,
      "sharedDetailsList": null,
      "lastPairedTime": "2026-04-10T13:49:36.686Z",
      "samplesHistoryLimit": {
        "historyDaysLimit": 9,
        "historyDaysMaxLimit": 9
      },
      "zoneId": null,
      "sharedAccepted": false
    }
  ],
  "totalCount": 2
}
```

## Confirmed `devicesamples` behavior

Working request pattern:

- `GET /secured/internal/devicesamples?date=<epoch_ms>&deviceId=<id>&version=<deviceVersion>`
- Required headers observed in panel traffic and tests:
  - `Authorization: Bearer <token>`
  - `Zone-Id: Europe/Warsaw`

For the tested device and date, the API returned an empty timeline payload:

```json
{
  "allGroupedSamplesSize": 0,
  "avgSpeed": 0,
  "distance": 0,
  "id": 0,
  "maxSpeed": 0,
  "minSpeed": 0,
  "totalSamples": 0,
  "trackList": []
}
```

## Integration impact

The current Home Assistant implementation in [custom_components/notione/device_tracker.py](custom_components/notione/device_tracker.py) is not robust against real-world payloads returned by the test account.

Confirmed problems:

- `lastPosition` can be `null`, so direct indexing like `dev['lastPosition']['latitude']` will crash for beacon or phone devices.
- `gpsDetails.battery` can be numeric, not boolean. A value like `66` is truthy, so the current `battery_status` logic incorrectly marks it as `low`.
- `notiOneDetails.battery` can be boolean, so GPS and beacon devices do not share the same battery semantics.
- `notiOneDetails` and `gpsDetails` are mutually exclusive in the tested payload.
- `zoneId` is available per device and may be `null`.

## Practical conclusion

There are effectively two usable engineering paths:

1. Keep using the still-working legacy `oauth/token` flow and harden the integration around the real `devicelist` payload.
2. Reverse engineer the panel-auth flow further and switch to `/public/user/authorize/login` plus `/refresh` only after it has been proven callable outside the web frontend.

Right now, path 1 is the only one confirmed end-to-end in direct external tests.