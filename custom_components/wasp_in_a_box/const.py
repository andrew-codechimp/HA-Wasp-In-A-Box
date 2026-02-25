"""Constants for wasp_in_a_box."""

from logging import Logger, getLogger

from homeassistant.const import Platform

LOGGER: Logger = getLogger(__package__)

MIN_HA_VERSION = "2026.1"

DOMAIN = "wasp_in_a_box"

PLATFORMS = [Platform.BINARY_SENSOR]

CONF_WASP_ID = "wasp_id"
CONF_BOX_ID = "box_id"
CONF_DOOR_CLOSED_DELAY = "door_closed_delay"
CONF_DOOR_OPEN_TIMEOUT = "door_open_timeout"
CONF_IMMEDIATE_ON = "immediate_on"

DEFAULT_DOOR_CLOSED_DELAY = 30
DEFAULT_OPEN_DOOR_TIMEOUT = 300
DEFAULT_IMMEDIATE_ON = True
