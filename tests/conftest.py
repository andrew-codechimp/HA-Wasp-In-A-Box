"""Global fixtures for wasp_in_a_box integration."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from custom_components.wasp_in_a_box.const import (
    CONF_BOX_ID,
    CONF_DELAY,
    CONF_IMMEDIATE_ON,
    CONF_WASP_ID,
    DEFAULT_DELAY,
    DEFAULT_IMMEDIATE_ON,
    DOMAIN,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

pytest_plugins = "pytest_homeassistant_custom_component"


# This fixture enables loading custom integrations in all tests.
# Remove to enable selective use of this fixture
@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations."""
    yield


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Automatically path uuid generator."""
    with patch(
        "custom_components.wasp_in_a_box.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture(name="get_config")
async def get_config_to_integration_load() -> dict[str, Any]:
    """Return configuration.

    To override the config, tests can be marked with:
    @pytest.mark.parametrize("get_config", [{...}])
    """
    return {
        CONF_WASP_ID: "binary_sensor.test_motion",
        CONF_BOX_ID: "binary_sensor.test_door",
        CONF_DELAY: DEFAULT_DELAY,
        CONF_IMMEDIATE_ON: DEFAULT_IMMEDIATE_ON,
    }


@pytest.fixture(name="loaded_entry")
async def load_integration(
    hass: HomeAssistant, get_config: dict[str, Any]
) -> MockConfigEntry:
    """Set up the wasp_in_a_box integration in Home Assistant."""
    # Create entity registry entries for the source sensors before setup
    entity_registry = er.async_get(hass)

    entity_registry.async_get_or_create(
        "binary_sensor",
        "test",
        "motion",
        suggested_object_id="test_motion",
    )

    entity_registry.async_get_or_create(
        "binary_sensor",
        "test",
        "door",
        suggested_object_id="test_door",
    )

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        options=get_config,
        entry_id="1",
    )

    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    hass.states.async_set(
        "binary_sensor.test_motion",
        "off",
    )
    hass.states.async_set(
        "binary_sensor.test_door",
        "off",
    )
    await hass.async_block_till_done()

    return config_entry
