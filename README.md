# HA-Wasp-In-A-Box

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![Downloads][download-latest-shield]]()
[![HACS Installs][hacs-installs-shield]]()
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

Wasp in a Box Helpers for Home Assistant

## Overview

⚠️ This is a pre-release, there may be issues and changes as this is refined, feedback is appreciated.

Wasp in a Box is an automation pattern for enclosed rooms (such as bathrooms) that helps determine reliable occupancy while a person remains inside, even if out of range of the motion senosr or being still.

This helper is designed for single occupancy enclosed spaces where the door is shut when occupied, it will not work for multiple occupancy.

### How it works

This helper overcomes the limitations of PIR motion sensors, which cannot detect stationary occupants. It requires two sensors:

- **Motion sensor** - Detects movement in the room
- **Door sensor** - Monitors door open/closed state

**Occupancy logic**
1. Door opens, then closes
2. Motion is detected
3. Helper remains "occupied" until the door opens again, or the motion sensor has been unoccupied past the timeout period. 

**Open door detection**
If the door is open and the motion sensor has not had motion for the door open timeout period then the room is considered unoccupied.

**Quick exit detection**
If the door opens then closes and the motion sensor clears within the door closed delay period, the room is considered unoccupied (e.g., someone quickly grabbing something without staying).

### Immediate on setting

Control when the helper transitions to "occupied":

- **On** - Helper becomes occupied immediately when the door is opened or motion is detected (good for lighting automation)
- **Off** - Helper becomes occupied after the door closes, motion is detected, and the delay period expires (good for fan automation)


_Please :star: this repo if you find it useful_

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png)](https://www.buymeacoffee.com/codechimp)

![Helper Creation](https://raw.githubusercontent.com/andrew-codechimp/ha-wasp-in-a-box/main/images/helper-create.png "Helper Creation")

## Installation

### HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=andrew-codechimp&repository=HA-Wasp-In-A-Box&category=Integration)

Or search for **Wasp in a Box** within HACS if My Home Assistant does not work for you

Restart Home Assistant

In the HA UI go to "Configuration" -> "Devices & services" -> "Helpers" click "+" and select "Wasp in a Box"

### Manual Installation

<details>
<summary>Show detailed instructions</summary>

Installation via HACS is recommended, but a manual setup is supported.

1. Manually copy custom_components/wasp_in_a_box folder from latest release to custom_components folder in your config folder.
1. Restart Home Assistant.
1. In the HA UI go to "Configuration" -> "Devices & services" -> "Helpers" click "+" and select "Wasp in a Box"

</details>

A new Wasp in a Box helper will be available within Settings/Helpers or click the My link to jump straight there

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=wasp_in_a_box)

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/andrew-codechimp/HA-Wasp-In-A-Box.svg?style=for-the-badge
[commits]: https://github.com/andrew-codechimp/HA-Wasp-In-A-Box/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge
[exampleimg]: example.png
[license-shield]: https://img.shields.io/github/license/andrew-codechimp/HA-Wasp-In-A-Box.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/andrew-codechimp/HA-Wasp-In-A-Box.svg?style=for-the-badge
[releases]: https://github.com/andrew-codechimp/HA-Wasp-In-A-Box/releases
[download-latest-shield]: https://img.shields.io/github/downloads/andrew-codechimp/HA-Wasp-In-A-Box/latest/total?style=for-the-badge
[hacs-installs-shield]: https://img.shields.io/endpoint.svg?url=https%3A%2F%2Flauwbier.nl%2Fhacs%2Fwasp_in_a_box&style=for-the-badge
