"""Tests for Wasp in a Box occupancy, source states, and timers."""

import pytest
from custom_components.wasp_in_a_box.const import (
    ATTR_DOOR_SENSOR_STATE,
    ATTR_MOTION_SENSOR_STATE,
    CONF_IMMEDIATE_ON,
    DEFAULT_DOOR_CLOSED_DELAY,
    DEFAULT_OPEN_DOOR_TIMEOUT,
)
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from . import advance_time, setup_integration
from .const import DOOR_ENTITY_ID, MOTION_ENTITY_ID, OCCUPANCY_ENTITY_ID

pytestmark = pytest.mark.usefixtures("source_sensors")


async def test_entity(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test occupancy state, attributes, naming, and entity registry metadata."""
    await setup_integration(hass, mock_config_entry)
    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize(
    ("mock_config_entry", "motion", "door", "expected"),
    [
        pytest.param({}, "off", "off", "off", id="empty-closed"),
        pytest.param({}, "on", "off", "on", id="motion-closed"),
        pytest.param({}, "off", "on", "on", id="immediate-door-open"),
        pytest.param({}, "on", "on", "on", id="immediate-motion-open"),
        pytest.param({CONF_IMMEDIATE_ON: False}, "off", "on", "off", id="door-open"),
        pytest.param({CONF_IMMEDIATE_ON: False}, "on", "on", "off", id="motion-open"),
        pytest.param(
            {CONF_IMMEDIATE_ON: False},
            "on",
            "off",
            "on",
            id="motion-closed-no-immediate",
        ),
    ],
    indirect=["mock_config_entry"],
)
async def test_occupancy(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    motion: str,
    door: str,
    expected: str,
) -> None:
    """Test motion and door states with immediate occupancy enabled and disabled."""
    await setup_integration(hass, mock_config_entry)
    hass.states.async_set(MOTION_ENTITY_ID, motion)
    hass.states.async_set(DOOR_ENTITY_ID, door)
    await hass.async_block_till_done()
    state = hass.states.get(OCCUPANCY_ENTITY_ID)
    assert state.state == expected
    assert state.attributes[ATTR_MOTION_SENSOR_STATE] == motion
    assert state.attributes[ATTR_DOOR_SENSOR_STATE] == door


async def test_stationary_occupant(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test closed-door occupancy persists after motion clears."""
    await setup_integration(hass, mock_config_entry)
    hass.states.async_set(MOTION_ENTITY_ID, "on")
    await hass.async_block_till_done()
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == "on"
    hass.states.async_set(MOTION_ENTITY_ID, "off")
    await advance_time(hass, freezer, DEFAULT_OPEN_DOOR_TIMEOUT + 1)
    state = hass.states.get(OCCUPANCY_ENTITY_ID)
    assert state.state == "on"
    assert state.attributes[ATTR_MOTION_SENSOR_STATE] == "off"


@pytest.mark.parametrize(
    ("motion", "expected"),
    [
        pytest.param("off", "off", id="quick-exit"),
        pytest.param("on", "on", id="still-occupied"),
    ],
)
async def test_door_closed_delay(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    motion: str,
    expected: str,
) -> None:
    """Test occupancy is recalculated only after the door-close grace period."""
    await setup_integration(hass, mock_config_entry)
    hass.states.async_set(MOTION_ENTITY_ID, "on")
    hass.states.async_set(DOOR_ENTITY_ID, "on")
    await hass.async_block_till_done()
    hass.states.async_set(MOTION_ENTITY_ID, motion)
    await hass.async_block_till_done()
    hass.states.async_set(DOOR_ENTITY_ID, "off")
    await hass.async_block_till_done()
    await advance_time(hass, freezer, DEFAULT_DOOR_CLOSED_DELAY - 1)
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == "on"
    await advance_time(hass, freezer, 1)
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == expected


async def test_door_reopens_cancels_close_delay(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test reopening the door cancels the pending close calculation."""
    await setup_integration(hass, mock_config_entry)
    hass.states.async_set(DOOR_ENTITY_ID, "on")
    await hass.async_block_till_done()
    hass.states.async_set(DOOR_ENTITY_ID, "off")
    await hass.async_block_till_done()
    await advance_time(hass, freezer, 10)
    hass.states.async_set(DOOR_ENTITY_ID, "on")
    await hass.async_block_till_done()
    await advance_time(hass, freezer, DEFAULT_DOOR_CLOSED_DELAY)
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == "on"
    await advance_time(
        hass, freezer, DEFAULT_OPEN_DOOR_TIMEOUT - DEFAULT_DOOR_CLOSED_DELAY
    )
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == "off"


async def test_repeated_door_close_restarts_delay(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test a repeated close event cancels the old timer and starts a full delay."""
    await setup_integration(hass, mock_config_entry)
    hass.states.async_set(DOOR_ENTITY_ID, "on")
    await hass.async_block_till_done()
    open_state = hass.states.get(DOOR_ENTITY_ID)
    hass.states.async_set(DOOR_ENTITY_ID, "off")
    await hass.async_block_till_done()
    closed_state = hass.states.get(DOOR_ENTITY_ID)
    await advance_time(hass, freezer, 10)

    # Replay the close event without an intervening open that would cancel the timer.
    hass.bus.async_fire(
        EVENT_STATE_CHANGED,
        {
            "entity_id": DOOR_ENTITY_ID,
            "old_state": open_state,
            "new_state": closed_state,
        },
    )
    await hass.async_block_till_done()
    await advance_time(hass, freezer, DEFAULT_DOOR_CLOSED_DELAY - 10)
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == "on"
    await advance_time(hass, freezer, 9)
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == "on"
    await advance_time(hass, freezer, 1)
    state = hass.states.get(OCCUPANCY_ENTITY_ID)
    assert state.state == "off"
    assert state.attributes[ATTR_DOOR_SENSOR_STATE] == "off"
    assert state.attributes[ATTR_MOTION_SENSOR_STATE] == "off"


async def test_door_open_timeout(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test an open door without motion clears occupancy when the timeout expires."""
    await setup_integration(hass, mock_config_entry)
    hass.states.async_set(DOOR_ENTITY_ID, "on")
    await hass.async_block_till_done()
    await advance_time(hass, freezer, DEFAULT_OPEN_DOOR_TIMEOUT - 1)
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == "on"
    await advance_time(hass, freezer, 1)
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == "off"


async def test_motion_restarts_open_timeout(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test motion cancels the open timeout and clearing motion starts a new one."""
    await setup_integration(hass, mock_config_entry)
    hass.states.async_set(DOOR_ENTITY_ID, "on")
    await hass.async_block_till_done()
    await advance_time(hass, freezer, DEFAULT_OPEN_DOOR_TIMEOUT - 1)
    hass.states.async_set(MOTION_ENTITY_ID, "on")
    await hass.async_block_till_done()
    await advance_time(hass, freezer, DEFAULT_OPEN_DOOR_TIMEOUT + 1)
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == "on"
    hass.states.async_set(MOTION_ENTITY_ID, "off")
    await hass.async_block_till_done()
    await advance_time(hass, freezer, DEFAULT_OPEN_DOOR_TIMEOUT - 1)
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == "on"
    await advance_time(hass, freezer, 1)
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == "off"


@pytest.mark.parametrize(
    ("source_entity_id", "attribute"),
    [
        pytest.param(MOTION_ENTITY_ID, ATTR_MOTION_SENSOR_STATE, id="motion"),
        pytest.param(DOOR_ENTITY_ID, ATTR_DOOR_SENSOR_STATE, id="door"),
    ],
)
@pytest.mark.parametrize("source_state", ["unknown", "unavailable"])
async def test_source_unavailable_and_recovery(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    source_entity_id: str,
    attribute: str,
    source_state: str,
) -> None:
    """Test invalid source reports make the helper unavailable until recovery."""
    await setup_integration(hass, mock_config_entry)
    hass.states.async_set(source_entity_id, source_state)
    await hass.async_block_till_done()
    state = hass.states.get(OCCUPANCY_ENTITY_ID)
    assert state.state == "unavailable"
    assert attribute not in state.attributes
    hass.states.async_set(source_entity_id, "off")
    await hass.async_block_till_done()
    state = hass.states.get(OCCUPANCY_ENTITY_ID)
    assert state.state == "off"
    assert state.attributes[attribute] == "off"


@pytest.mark.parametrize(
    "source_entity_id",
    [
        pytest.param(MOTION_ENTITY_ID, id="motion"),
        pytest.param(DOOR_ENTITY_ID, id="door"),
    ],
)
async def test_source_state_removed(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, source_entity_id: str
) -> None:
    """Test removal of a source state without a registry change and its recovery."""
    await setup_integration(hass, mock_config_entry)
    hass.states.async_remove(source_entity_id)
    await hass.async_block_till_done()
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == "unavailable"
    hass.states.async_set(source_entity_id, "off")
    await hass.async_block_till_done()
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == "off"
