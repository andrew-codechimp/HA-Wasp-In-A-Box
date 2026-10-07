"""Tests for the Wasp in a Box reset action."""

from unittest.mock import patch

import pytest
from custom_components.wasp_in_a_box.binary_sensor import WaspInABoxSensor
from custom_components.wasp_in_a_box.const import (
    DOMAIN,
    SERVICE_RESET,
)
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy.assertion import SnapshotAssertion

from homeassistant.core import HomeAssistant

from . import advance_time, setup_integration
from .const import DOOR_ENTITY_ID, MOTION_ENTITY_ID, OCCUPANCY_ENTITY_ID

pytestmark = pytest.mark.usefixtures("source_sensors")


async def test_reset(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test reset clears occupancy while preserving source state attributes."""
    await setup_integration(hass, mock_config_entry)
    hass.states.async_set(MOTION_ENTITY_ID, "on")
    await hass.async_block_till_done()
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == "on"
    await hass.services.async_call(
        DOMAIN, SERVICE_RESET, {"entity_id": OCCUPANCY_ENTITY_ID}, blocking=True
    )
    assert hass.states.get(OCCUPANCY_ENTITY_ID) == snapshot
    hass.states.async_set(MOTION_ENTITY_ID, "off")
    await hass.async_block_till_done()
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == "off"
    hass.states.async_set(MOTION_ENTITY_ID, "on")
    await hass.async_block_till_done()
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == "on"


@pytest.mark.parametrize(
    "door_state",
    [pytest.param("off", id="close-delay"), pytest.param("on", id="open-timeout")],
)
async def test_reset_cancels_timers(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    door_state: str,
) -> None:
    """Test reset cancels pending callbacks so they cannot write another state."""
    await setup_integration(hass, mock_config_entry)
    hass.states.async_set(DOOR_ENTITY_ID, "on")
    await hass.async_block_till_done()
    hass.states.async_set(DOOR_ENTITY_ID, door_state)
    await hass.async_block_till_done()
    await hass.services.async_call(
        DOMAIN, SERVICE_RESET, {"entity_id": OCCUPANCY_ENTITY_ID}, blocking=True
    )
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == "off"
    with patch.object(WaspInABoxSensor, "async_write_ha_state") as write_state:
        await advance_time(hass, freezer, 3601)
        write_state.assert_not_called()
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == "off"


async def test_reset_target(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test reset affects only the selected helper when sources are shared."""
    await setup_integration(hass, mock_config_entry)
    other_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Other room",
        data={},
        options=mock_config_entry.options,
    )
    other_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(other_entry.entry_id)
    await hass.async_block_till_done()
    hass.states.async_set(MOTION_ENTITY_ID, "off", {"report": 1})
    hass.states.async_set(DOOR_ENTITY_ID, "off", {"report": 1})
    await hass.async_block_till_done()
    hass.states.async_set(MOTION_ENTITY_ID, "on")
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.other_room").state == "on"
    await hass.services.async_call(
        DOMAIN, SERVICE_RESET, {"entity_id": OCCUPANCY_ENTITY_ID}, blocking=True
    )
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == "off"
    assert hass.states.get("binary_sensor.other_room").state == "on"
