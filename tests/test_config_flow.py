"""Test wasp_in_a_box config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock

from custom_components.wasp_in_a_box.const import (
    CONF_BOX_ID,
    CONF_DELAY,
    CONF_IMMEDIATE_ON,
    CONF_WASP_ID,
    DEFAULT_DELAY,
    DEFAULT_IMMEDIATE_ON,
    DOMAIN,
)

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .const import DEFAULT_NAME


async def test_form_sensor(hass: HomeAssistant, mock_setup_entry: AsyncMock) -> None:
    """Test we get the form for sensor."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "user"
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: DEFAULT_NAME,
            CONF_WASP_ID: "binary_sensor.test_motion",
            CONF_BOX_ID: "binary_sensor.test_door",
            CONF_DELAY: DEFAULT_DELAY,
            CONF_IMMEDIATE_ON: DEFAULT_IMMEDIATE_ON,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["version"] == 1
    assert result["options"] == {
        CONF_NAME: DEFAULT_NAME,
        CONF_WASP_ID: "binary_sensor.test_motion",
        CONF_BOX_ID: "binary_sensor.test_door",
        CONF_DELAY: DEFAULT_DELAY,
        CONF_IMMEDIATE_ON: DEFAULT_IMMEDIATE_ON,
    }

    assert len(mock_setup_entry.mock_calls) == 1
