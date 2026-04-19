# notiOne for Home Assistant
[![HACS Custom][hacs-badge]][hacs-badge-url]

Unofficial Home Assistant integration for notiOne cloud devices.

This fork uses the legacy verified notiOne API flow behind a modern Home Assistant config-entry integration.

## Current status

- UI-based setup from Home Assistant settings
- `device_tracker` entities for devices that expose valid GPS coordinates
- battery `sensor` entities when the API returns a numeric battery level
- configurable polling interval from integration options

## Limitations

- The integration relies on an unofficial API and may break if notiOne changes the backend.
- Devices without usable coordinates will not create a `device_tracker` entity.
- YAML credentials are no longer supported; configuration is done from the UI only.

## Installation

### HACS (Custom Repository)

1. Open HACS -> Integrations -> menu -> Custom repositories.
2. Add `https://github.com/mstepuch/ha-notione` as an `Integration` repository.
3. Install `notiOne`.
4. Restart Home Assistant.

### Manual installation

1. Copy the whole `custom_components/notione` directory into `config/custom_components/notione`.
2. Restart Home Assistant.

## Configuration

1. Open Settings -> Devices & Services -> Add Integration.
2. Search for `notiOne`.
3. Enter your notiOne account credentials.
4. Adjust the polling interval in integration options if needed.

The options flow currently accepts scan intervals from 60 to 3600 seconds.

## Entities

- `device_tracker`: one entity per device with a current location
- `sensor`: battery level for devices that expose a numeric percentage

## Documentation

- API research and payload notes: [docs/notione_api.md](docs/notione_api.md)
- Implementation roadmap: [docs/notione_plan.md](docs/notione_plan.md)
- Executor handoff notes: [docs/codex_handoff.md](docs/codex_handoff.md)

## View

![Screenshot](images/notione.png)

## Legacy note

Older revisions used a YAML `device_tracker` platform. The current integration keeps `async_setup` as a compatibility no-op, but real setup is config-entry only.

[hacs-badge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[hacs-badge-url]: https://github.com/custom-components/hacs

