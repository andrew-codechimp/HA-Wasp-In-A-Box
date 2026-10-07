"""Helpers for Wasp in a Box tests."""

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import DOOR_ENTITY_ID, MOTION_ENTITY_ID


async def setup_integration(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    """Load the helper and publish initial source reports."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    hass.states.async_set(MOTION_ENTITY_ID, "off")
    hass.states.async_set(DOOR_ENTITY_ID, "off")
    await hass.async_block_till_done()


async def advance_time(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: int
) -> None:
    """Advance the clock and run due timer callbacks."""
    freezer.tick(timedelta(seconds=seconds))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
