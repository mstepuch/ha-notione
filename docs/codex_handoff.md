# Codex Handoff Plan

Document date: 2026-04-19

This document is a precise execution handoff for a coding model that will implement the fork refactor.

The goal is not to brainstorm. The goal is to execute in a controlled order with explicit constraints.

## Mandatory reading before coding

Read these files first:

1. [docs/notione_api.md](docs/notione_api.md)
2. [docs/notione_plan.md](docs/notione_plan.md)
3. [custom_components/notione/device_tracker.py](custom_components/notione/device_tracker.py)
4. [custom_components/notione/manifest.json](custom_components/notione/manifest.json)
5. [custom_components/notione/system_health.py](custom_components/notione/system_health.py)

Do not start implementation before understanding those files.

## Mission

Modernize the forked notiOne Home Assistant integration so that:

- it no longer crashes on real payloads
- it uses UI configuration, not manual `configuration.yaml`
- it stays on the verified legacy auth flow for now
- it is architected so the newer auth flow can be added later behind a client abstraction

## Hard constraints

These are not optional.

1. Use the legacy auth flow as the production backend.
   - `POST https://auth.notinote.me/oauth/token`
   - `GET https://api.notinote.me/secured/internal/devicelist`

2. Do not switch the main code path to `/public/user/authorize/login` yet.

3. The integration must become UI-configured.
   - use `ConfigEntry`
   - use `config_flow.py`
   - no normal requirement for YAML credentials

4. Do not commit secrets, test credentials, tokens, or raw account payloads.

5. Do not use insecure HTTP behavior.
   - no `verify=False`
   - no disabled SSL warnings

6. One malformed device payload must never break the whole refresh cycle.

7. Keep the implementation incremental.
   - do not attempt the final perfect architecture in one massive edit
   - land changes in logical stages

## Technical decisions already made

These decisions are settled unless the repository owner explicitly changes them.

### API decision

- Production path: old `oauth/token` flow
- Research path: newer panel login and refresh flow

### Configuration decision

- Target architecture is config-entry only
- YAML may exist only as temporary compatibility logic if explicitly needed later

### Entity decision

First modern version should expose:

- `device_tracker` for devices with valid coordinates
- numeric battery `sensor` for GPS devices with numeric battery values
- optional `binary_sensor` online status if the state proves stable

Do not expose as initial entities:

- non-location devices as `device_tracker`
- beacon boolean battery as a battery entity
- high-churn telemetry like speed, humidity, route metrics

## Repository target shape

The current package is too thin. The target structure should look like this:

```text
custom_components/notione/
  __init__.py
  api.py
  config_flow.py
  const.py
  coordinator.py
  device_tracker.py
  manifest.json
  models.py
  sensor.py
  strings.json
  system_health.py
  translations/
    en.json
```

`binary_sensor.py` and `diagnostics.py` can be deferred if needed.

## Data model that Codex should implement

Create normalized models so entity code never walks raw JSON trees.

Suggested model set:

- `NotionePosition`
  - `latitude: float`
  - `longitude: float`
  - `accuracy: int | float | None`
  - `gps_time: datetime | None`
  - `city: str | None`
  - `place: str | None`

- `NotioneBattery`
  - `level: int | None`
  - `state: bool | None`
  - `low: bool | None`

- `NotioneDevice`
  - `device_id: str`
  - `name: str`
  - `device_type: str`
  - `device_version: str`
  - `state: str | None`
  - `position: NotionePosition | None`
  - `battery: NotioneBattery | None`
  - `image_url: str | None`
  - `mac_or_identifier: str | None`
  - `firmware_version: str | None`
  - `zone_id: str | None`
  - `last_paired_time: datetime | None`
  - `supports_timeline: bool | None`
  - `raw_kind: str`

### Parsing rules

Codex must implement these parsing rules explicitly:

1. If `lastPosition` is `null`, the device is not tracker-capable.
2. If `gpsDetails` exists:
   - battery is numeric
   - use it as battery percentage
3. If `notiOneDetails` exists:
   - battery is boolean-like and semantically unconfirmed
   - do not convert it into a percentage sensor
4. GPS and beacon families are mutually exclusive in the observed payload and should be parsed through separate branches.
5. Invalid or partial payload values should degrade to `None`, not explode.

## Client architecture Codex should implement

Create a dedicated API client in `api.py`.

Suggested responsibilities:

- `async_login()` or sync wrapper during intermediate refactor stage
- `async_fetch_device_list()`
- token handling
- request timeout
- mapping HTTP failures to explicit exceptions

Suggested exceptions:

- `NotioneApiError`
- `NotioneAuthError`
- `NotioneConnectionError`
- `NotionePayloadError`

### HTTP rules

- set explicit timeout on every request
- validate status codes
- validate required keys in responses
- never silently assume `access_token` exists

## Coordinator architecture Codex should implement

Use `DataUpdateCoordinator`.

Coordinator responsibilities:

- authenticate when needed
- fetch current device list
- parse payload into normalized device objects
- expose a stable in-memory mapping keyed by `device_id`

The coordinator must treat failures correctly:

- auth failure should lead to reauth flow, not endless silent retries
- transient network errors should become `UpdateFailed`
- a single malformed device should be logged and skipped, not abort the entire refresh

## Config flow Codex should implement

The modern user path must be UI-only.

### Required fields

- email or username
- password

### Required behavior

- validate credentials during setup
- create a single config entry per account
- support reauth if auth starts failing later
- provide options flow for polling interval
- optionally provide options for enabling diagnostic entities

### Not allowed

- asking the user to edit `configuration.yaml`
- requiring a restart just to enter credentials

## Entity plan Codex should implement

### 1. `device_tracker`

Implement tracker entities only for devices with valid coordinates.

Entity rules:

- unique id based on stable `device_id`
- device info grouped into a Home Assistant device record
- attributes may include:
  - device type
  - device version
  - last GPS time
  - zone id
  - image URL if valid

### 2. `sensor` battery

Implement only for devices with numeric battery level.

Do not create battery sensors for boolean beacon battery until semantics are confirmed.

### 3. `binary_sensor` online

Optional in the first modern pass.

If implemented, mark it diagnostic unless proven otherwise.

### 4. Non-location devices

Do not expose them as trackers.

Safe options:

- ignore for now
- or expose later through opt-in diagnostic entities

## Execution order

Codex should not try to do everything in one step. Follow this order.

## PR 1. Stabilization patch on current code

Objective:

- stop crashes immediately with the smallest reasonable change set

Files to edit:

- [custom_components/notione/device_tracker.py](custom_components/notione/device_tracker.py)
- optionally [README.md](README.md) if behavior notes must be clarified

Required changes:

1. guard `lastPosition`
2. separate GPS and beacon battery parsing
3. add timeout to requests
4. remove insecure SSL behavior
5. add basic HTTP and JSON error handling
6. skip malformed devices instead of crashing the cycle

Acceptance criteria:

- mixed payload with GPS and beacon devices does not crash
- bad auth is logged cleanly
- no `verify=False`

## PR 2. Extract client and parser

Objective:

- remove API logic from entity update loop

Files to add:

- [custom_components/notione/const.py](custom_components/notione/const.py)
- [custom_components/notione/api.py](custom_components/notione/api.py)
- [custom_components/notione/models.py](custom_components/notione/models.py)

Files to edit:

- [custom_components/notione/device_tracker.py](custom_components/notione/device_tracker.py)

Required changes:

1. move endpoints and constants into `const.py`
2. create API client wrapper
3. create normalized data model
4. replace raw JSON traversal with parser output

Acceptance criteria:

- `device_tracker.py` no longer contains raw auth request logic
- parser can be unit-tested without Home Assistant runtime

## PR 3. Migrate to config entry integration

Objective:

- stop relying on YAML platform configuration

Files to add:

- [custom_components/notione/config_flow.py](custom_components/notione/config_flow.py)
- [custom_components/notione/coordinator.py](custom_components/notione/coordinator.py)
- [custom_components/notione/strings.json](custom_components/notione/strings.json)
- [custom_components/notione/translations/en.json](custom_components/notione/translations/en.json)

Files to edit:

- [custom_components/notione/__init__.py](custom_components/notione/__init__.py)
- [custom_components/notione/manifest.json](custom_components/notione/manifest.json)
- [custom_components/notione/device_tracker.py](custom_components/notione/device_tracker.py)

Required changes:

1. implement `ConfigFlow`
2. validate credentials in setup
3. create config entry storage
4. implement `DataUpdateCoordinator`
5. move entity updates to coordinator-backed entities

Acceptance criteria:

- user can set up integration fully through UI
- no primary YAML instructions needed
- tracker entities update through coordinator

## PR 4. Add battery sensor and optional online sensor

Objective:

- expose the first useful non-tracker entities

Files to add:

- [custom_components/notione/sensor.py](custom_components/notione/sensor.py)
- optionally [custom_components/notione/binary_sensor.py](custom_components/notione/binary_sensor.py)

Files to edit:

- [custom_components/notione/manifest.json](custom_components/notione/manifest.json)
- [custom_components/notione/__init__.py](custom_components/notione/__init__.py)

Required changes:

1. numeric battery sensor for GPS devices
2. optional online state entity if stable
3. no battery entity for beacon boolean battery

Acceptance criteria:

- sensor entities are created only when data semantics are valid
- entity spam is avoided

## PR 5. Diagnostics and HACS polish

Objective:

- make the integration supportable and ready for broader use

Files to add or edit:

- [custom_components/notione/system_health.py](custom_components/notione/system_health.py)
- optional [custom_components/notione/diagnostics.py](custom_components/notione/diagnostics.py)
- [README.md](README.md)
- [custom_components/notione/manifest.json](custom_components/notione/manifest.json)

Required changes:

1. better system health
2. redacted diagnostics
3. documentation update to UI config flow
4. metadata cleanup for HACS expectations

Acceptance criteria:

- diagnostics do not leak secrets
- docs no longer center YAML setup

## Testing requirements for Codex

At minimum, add tests for parser logic.

Recommended fixture cases:

1. GPS device with full `lastPosition`
2. beacon device with `lastPosition = null`
3. numeric GPS battery
4. boolean beacon battery
5. missing avatar
6. missing city and place
7. malformed payload missing nested keys

Recommended integration behaviors to test later:

1. config flow success
2. config flow bad credentials
3. coordinator refresh failure handling
4. mixed device list does not crash

## Global acceptance criteria

Codex should consider the task successful only if all of these are true:

1. The integration can be configured from UI.
2. GPS devices with coordinates create tracker entities.
3. Beacon or phone devices without coordinates do not crash the integration.
4. No insecure SSL behavior remains.
5. API and parser code are no longer embedded directly in tracker entity logic.
6. The codebase is structured so the newer auth backend can be added later without rewriting entities.

## Things Codex must not waste time on

Avoid these in the initial implementation:

- switching to the newer auth backend
- timeline history UI
- route visualization
- advanced telemetry entities
- over-designing subscription modeling
- adding many optional entities before the core tracker path is stable

## Suggested prompt for Codex

Use the following brief as the starting instruction set for the coding model:

```text
Read docs/notione_api.md and docs/notione_plan.md first.

Refactor this Home Assistant custom integration in staged steps.

Constraints:
- keep the verified legacy auth flow (oauth/token -> secured/internal/devicelist) as the production path
- do not switch to public/user/authorize/login yet
- target UI-only configuration through ConfigEntry and config_flow
- do not require credentials in configuration.yaml
- remove insecure SSL behavior
- mixed payloads with GPS and beacon/phone devices must not crash refresh
- create tracker entities only for devices with valid coordinates
- create battery sensors only for devices with numeric battery values
- do not expose beacon boolean battery as percentage

Implementation order:
1. Stabilize current payload handling.
2. Extract const/api/models parsing layer.
3. Migrate to coordinator + config flow.
4. Add GPS battery sensor.
5. Improve diagnostics and docs.

Acceptance criteria:
- UI setup works
- GPS devices appear as trackers
- non-location devices do not break updates
- API code is isolated from entity code
- new auth flow can be added later behind the client layer
```

This should be treated as the execution contract.