"""Tests for Wasp in a Box config and options flows."""

from unittest.mock import AsyncMock

import pytest
from custom_components.wasp_in_a_box.const import (
    CONF_BOX_ID,
    CONF_DOOR_CLOSED_DELAY,
    CONF_DOOR_OPEN_TIMEOUT,
    CONF_IMMEDIATE_ON,
    CONF_WASP_ID,
    DEFAULT_DOOR_CLOSED_DELAY,
    DEFAULT_IMMEDIATE_ON,
    DEFAULT_OPEN_DOOR_TIMEOUT,
    DOMAIN,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .const import DEFAULT_NAME, DOOR_ENTITY_ID, MOTION_ENTITY_ID


@pytest.mark.parametrize(
    "options",
    [
        pytest.param({}, id="defaults"),
        pytest.param(
            {
                CONF_DOOR_CLOSED_DELAY: 10,
                CONF_DOOR_OPEN_TIMEOUT: 60,
                CONF_IMMEDIATE_ON: False,
            },
            id="custom-options",
        ),
        pytest.param(
            {CONF_WASP_ID: "input_boolean.motion", CONF_BOX_ID: "input_boolean.door"},
            id="input-boolean-sources",
        ),
    ],
)
async def test_user_flow(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    options: dict[str, str | int | bool],
) -> None:
    """Test the user flow creates a named helper with defaults or custom options."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] is None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: DEFAULT_NAME,
            CONF_WASP_ID: MOTION_ENTITY_ID,
            CONF_BOX_ID: DOOR_ENTITY_ID,
            **options,
        },
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == DEFAULT_NAME
    assert result["version"] == 1
    assert result["minor_version"] == 1
    assert result["data"] == {}
    assert result["options"] == {
        CONF_NAME: DEFAULT_NAME,
        CONF_WASP_ID: MOTION_ENTITY_ID,
        CONF_BOX_ID: DOOR_ENTITY_ID,
        CONF_DOOR_CLOSED_DELAY: DEFAULT_DOOR_CLOSED_DELAY,
        CONF_DOOR_OPEN_TIMEOUT: DEFAULT_OPEN_DOOR_TIMEOUT,
        CONF_IMMEDIATE_ON: DEFAULT_IMMEDIATE_ON,
        **options,
    }
    mock_setup_entry.assert_awaited_once()


async def test_source_selectors(hass: HomeAssistant) -> None:
    """Test both sources accept one binary sensor or input boolean."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    schema = result["data_schema"].schema
    assert schema[CONF_WASP_ID].config == {
        "domain": ["binary_sensor", "input_boolean"],
        "multiple": False,
        "reorder": False,
    }
    assert schema[CONF_BOX_ID].config == schema[CONF_WASP_ID].config


async def test_options(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Test options suggest saved values and preserve the helper's name and data."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    assert result["errors"] is None
    assert {
        key.schema: key.description["suggested_value"]
        for key in result["data_schema"].schema
    } == {
        key: value
        for key, value in mock_config_entry.options.items()
        if key != CONF_NAME
    }
    options = {
        CONF_WASP_ID: "binary_sensor.other_motion",
        CONF_BOX_ID: "input_boolean.other_door",
        CONF_DOOR_CLOSED_DELAY: 1,
        CONF_DOOR_OPEN_TIMEOUT: 3600,
        CONF_IMMEDIATE_ON: False,
    }
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], options
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options == {CONF_NAME: DEFAULT_NAME, **options}
    assert mock_config_entry.title == DEFAULT_NAME
    assert mock_config_entry.data == {}
