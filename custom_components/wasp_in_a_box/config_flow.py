"""Config flow for wasp_in_a_box integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

import voluptuous as vol

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN
from homeassistant.helpers import selector
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaConfigFlowHandler,
    SchemaFlowFormStep,
)

from .const import (
    CONF_BOX_ID,
    CONF_DELAY,
    CONF_IMMEDIATE_ON,
    CONF_WASP_ID,
    DEFAULT_DELAY,
    DEFAULT_IMMEDIATE_ON,
    DOMAIN,
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_WASP_ID): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=[BINARY_SENSOR_DOMAIN, INPUT_BOOLEAN_DOMAIN],
                multiple=False,
            ),
        ),
        vol.Required(CONF_BOX_ID): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=[BINARY_SENSOR_DOMAIN, INPUT_BOOLEAN_DOMAIN],
                multiple=False,
            ),
        ),
        vol.Required(CONF_DELAY, default=DEFAULT_DELAY): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1,
                max=600,
                step=1,
                mode=selector.NumberSelectorMode.BOX,
            ),
        ),
        vol.Required(
            CONF_IMMEDIATE_ON, default=DEFAULT_IMMEDIATE_ON
        ): selector.BooleanSelector(),
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required("name"): selector.TextSelector(),
    }
).extend(OPTIONS_SCHEMA.schema)

CONFIG_FLOW = {
    "user": SchemaFlowFormStep(CONFIG_SCHEMA),
}

OPTIONS_FLOW = {
    "init": SchemaFlowFormStep(OPTIONS_SCHEMA),
}


class ConfigFlowHandler(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config or options flow for Min/Max."""

    config_flow = CONFIG_FLOW
    options_flow = OPTIONS_FLOW

    VERSION = 1
    MINOR_VERSION = 1

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""
        return cast(str, options["name"]) if "name" in options else ""
