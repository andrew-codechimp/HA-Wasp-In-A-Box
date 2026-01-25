"""Constants for wasp_in_a_box."""

import json
from logging import Logger, getLogger
from pathlib import Path

from homeassistant.const import Platform

LOGGER: Logger = getLogger(__package__)

MIN_HA_VERSION = "2025.11"

manifestfile = Path(__file__).parent / "manifest.json"
with manifestfile.open(encoding="UTF-8") as json_file:
    manifest_data = json.load(json_file)

DOMAIN = manifest_data.get("domain")
NAME = manifest_data.get("name")
VERSION = manifest_data.get("version")
ISSUEURL = manifest_data.get("issue_tracker")
CONFIG_VERSION = 1

PLATFORMS = [Platform.SENSOR]

CONF_WASP_ID = "wasp_id"
CONF_BOX_ID = "box_id"
CONF_DELAY = "delay"

DEFAULT_DELAY = 30
