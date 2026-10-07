"""Tests for Wasp in a Box setup, reload, and cleanup."""

from unittest.mock import patch

import pytest
from custom_components.wasp_in_a_box.const import (
    CONF_DOOR_CLOSED_DELAY,
    CONF_DOOR_OPEN_TIMEOUT,
    CONF_IMMEDIATE_ON,
    DOMAIN,
    SERVICE_RESET,
)
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from . import advance_time, setup_integration
from .const import DOOR_ENTITY_ID, MOTION_ENTITY_ID, OCCUPANCY_ENTITY_ID


@pytest.mark.usefixtures("source_sensors")
async def test_setup_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test setup creates one occupancy entity and the reset action without a device."""
    await setup_integration(hass, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.LOADED
    entities = er.async_entries_for_config_entry(
        entity_registry, mock_config_entry.entry_id
    )
    assert len(entities) == 1
    assert entities[0].entity_id == OCCUPANCY_ENTITY_ID
    assert entities[0].unique_id == mock_config_entry.entry_id
    assert entities[0].device_id is None
    assert (
        dr.async_entries_for_config_entry(device_registry, mock_config_entry.entry_id)
        == []
    )
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == "off"
    assert hass.services.has_service(DOMAIN, SERVICE_RESET)


@pytest.mark.usefixtures("source_sensors")
@pytest.mark.parametrize(
    "timer",
    [pytest.param("closed", id="close-delay"), pytest.param("open", id="open-timeout")],
)
async def test_unload_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    entity_registry: er.EntityRegistry,
    timer: str,
) -> None:
    """Test unloading cancels pending timers and unsubscribes source listeners."""
    await setup_integration(hass, mock_config_entry)
    hass.states.async_set(DOOR_ENTITY_ID, "on")
    await hass.async_block_till_done()
    door_state = {"closed": "off", "open": "on"}[timer]
    hass.states.async_set(DOOR_ENTITY_ID, door_state)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
    unloaded_state = hass.states.get(OCCUPANCY_ENTITY_ID)
    assert unloaded_state.state == "unavailable"
    hass.states.async_set(MOTION_ENTITY_ID, "on")
    hass.states.async_set(DOOR_ENTITY_ID, "off")
    await advance_time(hass, freezer, 3601)
    assert hass.states.get(OCCUPANCY_ENTITY_ID) == unloaded_state
    with patch.object(hass.config_entries, "async_reload", return_value=True) as reload:
        entity_registry.async_update_entity(
            MOTION_ENTITY_ID, new_entity_id=f"{MOTION_ENTITY_ID}_renamed"
        )
        await hass.async_block_till_done()
        reload.assert_not_awaited()


@pytest.mark.usefixtures("source_sensors")
async def test_remove_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test reloading keeps the entity identity and removal clears its registry entry."""
    await setup_integration(hass, mock_config_entry)
    entity = entity_registry.async_get(OCCUPANCY_ENTITY_ID)
    assert await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert entity_registry.async_get(OCCUPANCY_ENTITY_ID).id == entity.id
    assert await hass.config_entries.async_remove(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(OCCUPANCY_ENTITY_ID) is None
    assert entity_registry.async_get(OCCUPANCY_ENTITY_ID) is None
    assert entity_registry.async_get(MOTION_ENTITY_ID) is not None
    assert entity_registry.async_get(DOOR_ENTITY_ID) is not None


@pytest.mark.usefixtures("source_sensors")
@pytest.mark.parametrize(
    "source_entity_id",
    [
        pytest.param(MOTION_ENTITY_ID, id="motion"),
        pytest.param(DOOR_ENTITY_ID, id="door"),
    ],
)
async def test_source_removal_and_recovery(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    source_entity_id: str,
) -> None:
    """Test source removal preserves the helper and recreation restores availability."""
    await setup_integration(hass, mock_config_entry)
    source = entity_registry.async_get(source_entity_id)
    entity_registry.async_remove(source_entity_id)
    hass.states.async_remove(source_entity_id)
    await hass.async_block_till_done()
    assert (
        hass.config_entries.async_get_entry(mock_config_entry.entry_id)
        is mock_config_entry
    )
    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == "unavailable"
    entity_registry.async_get_or_create(
        source.domain,
        source.platform,
        source.unique_id,
        suggested_object_id=source.entity_id.split(".", 1)[1],
    )
    hass.states.async_set(MOTION_ENTITY_ID, "off", {"report": 1})
    hass.states.async_set(DOOR_ENTITY_ID, "off", {"report": 1})
    await hass.async_block_till_done()
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == "off"


async def test_missing_sources(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test missing sources load unavailable and later reports restore availability."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == "unavailable"
    hass.states.async_set(MOTION_ENTITY_ID, "off")
    hass.states.async_set(DOOR_ENTITY_ID, "off")
    await hass.async_block_till_done()
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == "off"


@pytest.mark.usefixtures("source_sensors")
@pytest.mark.parametrize(
    "source_entity_id",
    [
        pytest.param(MOTION_ENTITY_ID, id="motion"),
        pytest.param(DOOR_ENTITY_ID, id="door"),
    ],
)
async def test_source_registry_updates(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    source_entity_id: str,
) -> None:
    """Test source renaming reloads the helper while metadata changes do not."""
    await setup_integration(hass, mock_config_entry)
    with patch.object(hass.config_entries, "async_reload", return_value=True) as reload:
        entity_registry.async_update_entity(source_entity_id, name="Renamed sensor")
        await hass.async_block_till_done()
        reload.assert_not_awaited()
        entity_registry.async_update_entity(
            source_entity_id, new_entity_id=f"{source_entity_id}_renamed"
        )
        await hass.async_block_till_done()
        reload.assert_awaited_once_with(mock_config_entry.entry_id)


@pytest.mark.usefixtures("source_sensors")
@pytest.mark.parametrize(
    ("immediate_on", "motion", "door", "before", "seconds", "after"),
    [
        pytest.param(False, "on", "off", "off", 10, "on", id="close-delay"),
        pytest.param(True, "off", "on", "on", 60, "off", id="open-timeout"),
    ],
)
async def test_options_reload(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    immediate_on: bool,
    motion: str,
    door: str,
    before: str,
    seconds: int,
    after: str,
) -> None:
    """Test saving options applies immediate occupancy and both timer durations."""
    await setup_integration(hass, mock_config_entry)
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    options = {
        **mock_config_entry.options,
        CONF_DOOR_CLOSED_DELAY: 10,
        CONF_DOOR_OPEN_TIMEOUT: 60,
        CONF_IMMEDIATE_ON: immediate_on,
    }
    options.pop(CONF_NAME)
    await hass.config_entries.options.async_configure(result["flow_id"], options)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.LOADED
    hass.states.async_set(MOTION_ENTITY_ID, "off", {"report": 1})
    hass.states.async_set(DOOR_ENTITY_ID, "on")
    await hass.async_block_till_done()
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == before
    hass.states.async_set(MOTION_ENTITY_ID, motion)
    await hass.async_block_till_done()
    hass.states.async_set(DOOR_ENTITY_ID, door)
    await hass.async_block_till_done()
    await advance_time(hass, freezer, seconds - 1)
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == before
    await advance_time(hass, freezer, 1)
    assert hass.states.get(OCCUPANCY_ENTITY_ID).state == after
