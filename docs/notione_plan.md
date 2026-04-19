# notiOne Fork Plan

Plan date: 2026-04-19

This document defines how the fork should be repaired, expanded, and prepared for a realistic Home Assistant custom integration path.

For the executor-oriented implementation brief, see [docs/codex_handoff.md](docs/codex_handoff.md).

## Decision

Use the legacy API flow as the production path for the next iteration.

Do not switch the integration to the newer panel auth flow yet.

### Why

- The legacy flow is confirmed working end-to-end in live tests:
  - `POST https://auth.notinote.me/oauth/token`
  - `GET https://api.notinote.me/secured/internal/devicelist`
- The newer panel flow is visible in the web bundle, but direct external calls to:
  - `POST /public/user/authorize/login`
  - `POST /public/user/authorize/refresh`
  returned HTTP `500` in manual tests.
- Rebuilding the integration on an auth flow that cannot yet be reproduced outside the frontend would be fragile and unnecessary.

### Architectural stance

- Short term: ship on the old API because it is proven.
- Medium term: isolate auth and API access behind a client layer so the new flow can be swapped in later.
- Long term: add an experimental implementation of the newer auth flow only after it is independently validated.

## Goals

1. Stop crashes on real notiOne payloads.
2. Support both GPS devices and beacon/phone devices.
3. Move from legacy platform code to a maintainable Home Assistant integration architecture.
4. Prepare the fork for HACS distribution without overcommitting to unstable API assumptions.

## Non-goals for the first refactor

- Do not fully reverse engineer the panel frontend before stabilizing the existing integration.
- Do not build features that require unproven endpoints.
- Do not try to make the first iteration perfect from a UX perspective.

## Current technical problems that must be fixed first

Based on live payloads and code review:

1. `lastPosition` can be `null`.
   - Current code assumes location always exists.
   - Result: beacon/phone devices can crash the whole update loop.

2. Battery semantics differ by device family.
   - GPS devices return numeric battery values.
   - Beacon devices return boolean battery state.
   - Current `battery_status` logic is wrong for both.

3. Auth and API access are inlined into the entity update loop.
   - No isolation.
   - No retry policy.
   - No graceful degradation.

4. The implementation uses a legacy HA pattern.
   - YAML-only platform setup.
   - synchronous `requests`
   - no `ConfigEntry`
   - no `DataUpdateCoordinator`

5. Error handling is almost nonexistent.
   - missing token fields
   - HTTP errors
   - missing JSON keys
   - invalid payload variants

6. Security posture is weak.
   - `verify=False`
   - disabled SSL warnings
   - hardcoded client credential in code

## Recommended target architecture

### Layer 1: API/Auth client

Create a dedicated client module responsible for:

- login
- token refresh, if supported on the chosen flow
- authenticated requests
- request timeout and retry policy
- normalized exceptions

Suggested modules:

- `const.py`
- `api.py`
- `models.py` or `parser.py`
- `coordinator.py`

Rules:

- no Home Assistant entity code inside the HTTP client
- no raw JSON traversal inside entity classes
- one place for endpoint selection and auth strategy

### Layer 2: Payload normalization

Normalize raw API payload into an internal device model.

At minimum the normalized model should handle:

- `device_id`
- `name`
- `device_type`
- `device_version`
- `is_online`
- `last_position` optional
- `battery_level` optional
- `battery_state` optional
- `image_url` optional
- `mac_or_identifier`
- `zone_id`
- `supports_timeline`

The key point is this:

- the parser must understand GPS and beacon/phone payloads as different shapes
- entity code should consume normalized data, not raw JSON branches

### Layer 3: Home Assistant integration

Target stack:

- `manifest.json`
- `__init__.py`
- `config_flow.py`
- `coordinator.py`
- `device_tracker.py`
- optional `sensor.py` later
- `diagnostics.py` later
- `translations/en.json`

Preferred HA pattern:

- `ConfigEntry`
- `DataUpdateCoordinator`
- async HTTP via HA helpers or `aiohttp`
- entity classes that read coordinator data only

## Configuration UX

The target user path is UI-only.

There should be no normal requirement to write credentials in `configuration.yaml`.

### Required approach

- credentials entered through `config_flow.py`
- credentials stored in the Home Assistant config entry
- update interval and optional behavior controlled through an options flow
- reauthentication handled through the UI if login starts failing

### What the user should configure in UI

Initial config flow fields:

- email or username
- password

Options flow fields:

- polling interval
- include non-location devices as diagnostic entities
- enable extra debug or diagnostic entities

### YAML policy

- No primary YAML configuration path.
- At most, optional one-time YAML import can be considered later for backward compatibility.
- The fork should be documented and maintained as a config-entry integration, not a YAML platform.

## Entity exposure plan

The entity model should match what the API can actually guarantee.

The core rule is:

- create location tracker entities only for devices with real coordinates
- do not force beacon or phone devices without coordinates into `device_tracker`

### Entities for Release 1 and Release 2

#### 1. `device_tracker`

Create one `device_tracker` entity per device that has usable `lastPosition` coordinates.

This is the primary entity class.

Expected source payload:

- GPS family devices such as `GPS_PET` and `TUBE`

State and attributes should include:

- latitude and longitude
- GPS accuracy
- last GPS timestamp
- friendly name
- image if available
- device version
- device type

These should be attributes, not separate entities in the first iteration:

- ownership
- zone id
- last paired time
- raw subscription metadata

#### 2. `sensor` battery level

Create a numeric battery sensor only when the API provides a reliable numeric battery value.

That currently means GPS devices with `gpsDetails.battery`.

Why:

- the numeric battery percentage is clearly useful in HA
- it maps naturally to a sensor
- it avoids overloading `device_tracker` attributes with frequently read operational data

Suggested entity:

- `sensor.<device>_battery`

#### 3. `binary_sensor` online status

Create an online status entity for each device family only if the API `deviceState` remains stable across tests.

Suggested semantics:

- `on` when `deviceState == ONLINE`
- `off` otherwise

Suggested entity:

- `binary_sensor.<device>_online`

Recommendation:

- mark this as diagnostic or keep it enabled by default only if it proves useful in normal dashboards

### Diagnostic entities to support later

These should exist only after the core tracker path is stable.

Potential candidates:

- `sensor.<device>_last_update`
- `sensor.<device>_firmware_version`
- `sensor.<device>_subscription_type`
- `binary_sensor.<device>_charging`
- `binary_sensor.<device>_timeline_supported`

Default policy:

- disabled by default in the entity registry
- enabled manually by advanced users

### Entities we should not expose initially

#### 1. Beacon battery boolean as a battery entity

Do not expose a battery percentage or low-battery sensor from `notiOneDetails.battery` until its boolean meaning is confirmed.

Reason:

- the semantics are not yet proven
- a wrong battery entity is worse than no battery entity

#### 2. Non-location devices as `device_tracker`

Do not create `device_tracker` entities for devices whose `lastPosition` is `null`.

Reason:

- a tracker without coordinates is semantically weak in HA
- current payloads show phone or beacon devices can have no location at all
- this is exactly the case that currently crashes the fork

#### 3. High-churn telemetry entities

Do not expose speed, temperature, humidity, route history, or timeline-derived metrics in the first versions.

Reason:

- they are secondary to stable location tracking
- they risk entity spam and noisy dashboards
- they can be added later once polling, payload parsing, and update semantics are proven

## Device-to-entity mapping

### GPS tracker devices

For devices with coordinates and `gpsDetails`:

- create a Home Assistant device record
- create `device_tracker`
- create numeric battery sensor if available
- optionally create online diagnostic entity

### Beacon or phone devices without coordinates

For devices with `notiOneDetails` and `lastPosition = null`:

- do not create `device_tracker`
- optionally create a Home Assistant device record only if we expose at least one diagnostic entity
- make diagnostic entities opt-in through the options flow

This keeps the main user experience clean while still preserving room for advanced support later.

## Recommended first user-facing package

For the first modern UI-based release, expose only:

- `device_tracker` for GPS devices
- `sensor` battery for GPS devices with numeric battery
- optional `binary_sensor` online status if it proves stable

That is the right minimum surface area.

It gives a useful Home Assistant integration without committing us to noisy or weakly defined entities.

## API strategy

### Phase A: Legacy auth as default

Use the verified flow:

- `POST /oauth/token`
- `GET /secured/internal/devicelist`

Implementation rules:

- do not disable SSL verification
- add request timeout
- add explicit HTTP status handling
- treat token acquisition as a separate step from list retrieval

### Phase B: New auth flow as experimental backend

Add the new flow only behind an internal feature flag or separate client implementation.

Conditions for enabling it:

- login works reliably outside the panel frontend
- refresh works reliably outside the panel frontend
- token format and lifecycle are understood
- failure modes are understood

Until those conditions are met, the new flow is research-only.

## Detailed implementation plan

## Stage 0. Stabilization patch

Objective: make the current fork stop breaking on real payloads with the smallest safe diff.

Tasks:

1. Guard all access to `lastPosition`.
2. Skip GPS attributes when location is missing.
3. Normalize battery handling separately for:
   - `gpsDetails.battery` numeric
   - `notiOneDetails.battery` boolean
4. Add timeouts to HTTP calls.
5. Remove `verify=False` and warning suppression.
6. Add basic try/except with clear logging.
7. Prevent one bad device from aborting the entire update cycle.

Expected outcome:

- current YAML platform still works
- no crash on beacon/phone devices
- logs become diagnosable

## Stage 1. Extract client and parser

Objective: remove protocol logic from the platform file.

Tasks:

1. Move constants into `const.py`.
2. Create `api.py` for auth and requests.
3. Create parser or dataclass layer for normalized devices.
4. Replace inline JSON traversal in `device_tracker.py` with parsed objects.
5. Add unit-testable parsing helpers.

Expected outcome:

- API logic is isolated
- swapping auth flow later becomes realistic

## Stage 2. Migrate from legacy setup to modern HA structure

Objective: stop investing in obsolete HA patterns.

Tasks:

1. Introduce `ConfigEntry` support.
2. Add `config_flow.py` with username/password login form.
3. Store credentials in HA config entries.
4. Move refresh scheduling into `DataUpdateCoordinator`.
5. Convert `device_tracker` to coordinator-backed entity classes.

Expected outcome:

- integration behaves like a current Home Assistant integration
- future HACS work becomes much easier

## Stage 3. Device model support

Objective: correctly represent the actual notiOne account payload.

Tasks:

1. Support GPS trackers with coordinates.
2. Support beacon/phone devices with no position.
3. Decide how non-GPS devices should be exposed:
   - hidden from tracker entities
   - or exposed as diagnostic entities later
4. Map useful metadata consistently:
   - firmware version
   - battery
   - ownership
   - paired time
   - subscription info if useful

Recommendation:

- First release should create tracker entities only for devices with usable location data.
- Non-location devices should not crash the integration and should be logged or prepared for later sensor entities.

## Stage 4. Diagnostics and observability

Objective: make the integration maintainable when the private API changes.

Tasks:

1. Add structured debug logging around auth and fetch steps.
2. Add diagnostics support with redacted payload export.
3. Add system health that checks actual auth plus device list fetch readiness.
4. Log API schema anomalies without leaking secrets.

Expected outcome:

- easier debugging when notiOne changes backend behavior

## Stage 5. HACS readiness

Objective: make the integration reviewable and distributable.

Tasks:

1. Ensure manifest and versioning are correct.
2. Remove insecure request patterns.
3. Add translations.
4. Add config flow.
5. Add tests.
6. Update documentation and installation steps.
7. Verify repository layout and HACS metadata.

Gate:

- Do not treat the project as HACS-ready before Stage 2 and Stage 4 are complete.

## Stage 6. Experimental new-auth branch

Objective: prepare for eventual backend migration if the legacy flow disappears.

Tasks:

1. Implement alternative auth client for `/public/user/authorize/login` and `/refresh`.
2. Validate exact required headers and content type.
3. Compare returned token behavior against old flow.
4. Add runtime switch or fallback mechanism only if the new flow is proven.

Recommendation:

- Do this on a separate branch or behind an internal client abstraction.
- Do not block the main refactor on this stage.

## Testing plan

### Parser tests

Create fixture-based tests for:

- GPS device with `lastPosition`
- beacon device with `lastPosition = null`
- missing avatar
- missing city/place
- numeric battery
- boolean battery

### Client tests

Mock:

- token success
- token failure
- device list success
- malformed payload
- timeout
- 401 or 403 responses

### Integration tests

Test:

- config flow login success and failure
- coordinator refresh
- entity creation
- no crash when mixed device families are returned

## Data mapping decisions

These should be explicit, not accidental.

### GPS devices

- create tracker entities
- include coordinates and accuracy
- expose useful diagnostics in attributes only if stable

### Beacon/phone devices without coordinates

Initial recommendation:

- do not create tracker entities for them in the first stabilized version
- record them in logs at debug level
- optionally expose them later as sensors or diagnostics

Reason:

- a device tracker without location is not a useful tracker entity
- forcing it into tracker semantics will create confusing behavior

## Release strategy

### Release 1

Scope:

- Stage 0
- Stage 1
- minimal docs update

Goal:

- current fork stops crashing and handles real payloads safely

### Release 2

Scope:

- Stage 2
- Stage 3
- initial tests

Goal:

- proper modern HA integration on the verified old API

### Release 3

Scope:

- Stage 4
- Stage 5

Goal:

- HACS candidate

### Release 4

Scope:

- Stage 6 if still relevant

Goal:

- optional migration to the newer auth flow

## Final recommendation

Use the old API now.

That is the only flow we have verified from login to real device payloads. The right engineering move is not to bet the refactor on the newer panel auth flow before it is independently reproducible. The correct compromise is:

- implement on the old API
- isolate auth and API access behind a client abstraction
- keep the new API as a research branch, not the production dependency

This gives us a working integration sooner, lowers risk, and preserves a clean migration path if notiOne later removes the legacy auth endpoint.