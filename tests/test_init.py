"""Test wasp_in_a_box setup process."""

from __future__ import annotations

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

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import DEFAULT_NAME


async def test_unload_entry(hass: HomeAssistant, loaded_entry: MockConfigEntry) -> None:
    """Test unload an entry."""

    assert loaded_entry.state is ConfigEntryState.LOADED
    assert await hass.config_entries.async_unload(loaded_entry.entry_id)
    await hass.async_block_till_done()
    assert loaded_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test the setup of the helper wasp_in_a_box."""

    # Source entity device config entry
    source_config_entry = MockConfigEntry()
    source_config_entry.add_to_hass(hass)

    # Device entry of the source entities
    source_device_entry = device_registry.async_get_or_create(
        config_entry_id=source_config_entry.entry_id,
        identifiers={("binary_sensor", "test_source")},
    )

    # Wasp entity (motion sensor)
    wasp_entity = entity_registry.async_get_or_create(
        "binary_sensor",
        "test",
        "motion",
        config_entry=source_config_entry,
        device_id=source_device_entry.id,
    )
    await hass.async_block_till_done()
    assert entity_registry.async_get("binary_sensor.test_motion") is not None

    # Box entity (door sensor)
    box_entity = entity_registry.async_get_or_create(
        "binary_sensor",
        "test",
        "door",
        config_entry=source_config_entry,
        device_id=source_device_entry.id,
    )
    await hass.async_block_till_done()
    assert entity_registry.async_get("binary_sensor.test_door") is not None

    # Configure the configuration entry for wasp_in_a_box
    wasp_in_a_box_config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            CONF_WASP_ID: "binary_sensor.test_motion",
            CONF_BOX_ID: "binary_sensor.test_door",
            CONF_DELAY: DEFAULT_DELAY,
            CONF_IMMEDIATE_ON: DEFAULT_IMMEDIATE_ON,
        },
        title=DEFAULT_NAME,
    )
    wasp_in_a_box_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(wasp_in_a_box_config_entry.entry_id)
    await hass.async_block_till_done()

    # Config entry reload
    await hass.config_entries.async_reload(wasp_in_a_box_config_entry.entry_id)
    await hass.async_block_till_done()

    # Confirm the link between the source entity device and the wasp_in_a_box sensor
    wasp_in_a_box_entity = entity_registry.async_get("binary_sensor.waspinabox")
    assert wasp_in_a_box_entity is not None

    # Remove the config entry
    assert await hass.config_entries.async_remove(wasp_in_a_box_config_entry.entry_id)
    await hass.async_block_till_done()

    # Check the state and entity registry entry are removed
    assert hass.states.get(wasp_in_a_box_entity.entity_id) is None
    assert entity_registry.async_get(wasp_in_a_box_entity.entity_id) is None
