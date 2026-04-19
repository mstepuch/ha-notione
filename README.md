# notiOne Device Tracker
[![GitHub Release][releases-shield]][releases]
[![Hacs Badge][hacs-badge]][hacs-badge-url]
[![PayPal_Me][paypal-me-shield]][paypal-me]

This device tracker uses unofficial API to get data from https://panel.notione.com/

API research and payload notes are available in [docs/notione_api.md](docs/notione_api.md).
Implementation roadmap is in [docs/notione_plan.md](docs/notione_plan.md).

## Setup

1. Install the integration files into `custom_components/notione`.
2. Restart Home Assistant.
3. Go to Settings -> Devices and Services -> Add Integration.
4. Search for `notiOne`.
5. Enter your account credentials in the integration UI.

Polling interval can be changed later in the integration options.

## View
![Screenshot](https://github.com/n4ts/ha-notione/blob/master/images/notione.png?raw=true)

## Legacy note

Older versions used YAML credentials in `configuration.yaml`.
The current integration path is UI-first through config entries.

## Installation

Download [*device_tracker.py*](https://github.com/n4ts/ha-notione/raw/master/custom_components/notione/device_tracker.py), [*system_health.py*](https://github.com/n4ts/ha-notione/raw/master/custom_components/notione/system_health.py), [\_\_init\_\_.py*](https://github.com/n4ts/ha-notione/raw/master/custom_components/notione/__init__.py) and [*manifest.json*](https://github.com/n4ts/ha-notione/raw/master/custom_components/notione/manifest.json) to `config/custom_components/notione` directory:
```bash
mkdir -p custom_components/notione
cd custom_components/notione
wget https://github.com/n4ts/ha-notione/raw/master/custom_components/notione/device_tracker.py
wget https://github.com/n4ts/ha-notione/raw/master/custom_components/notione/system_health.py
wget https://github.com/n4ts/ha-notione/raw/master/custom_components/notione/manifest.json
wget https://github.com/n4ts/ha-notione/raw/master/custom_components/notione/__init__.py
```

[releases]: https://github.com/n4ts/ha-notione/releases
[releases-shield]: https://img.shields.io/github/release/n4ts/ha-notione.svg?style=for-the-badge
[hacs-badge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[hacs-badge-url]: https://github.com/custom-components/hacs
[paypal-me-shield]: https://img.shields.io/badge/PayPal.Me-stanpielak-blue?style=for-the-badge
[paypal-me]: https://www.paypal.me/stanpielak

