"""Custom integration to provide wasp_in_a_box helpers for Home Assistant.

For more details about this integration, please refer to
https://github.com/andrew-codechimp/HA-Wasp-In-A-Box
"""

from __future__ import annotations

import voluptuous as vol
from awesomeversion.awesomeversion import AwesomeVersion

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import __version__ as HA_VERSION  # noqa: N812
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.event import async_track_entity_registry_updated_event
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_BOX_ID,
    CONF_WASP_ID,
    DOMAIN,
    LOGGER,
    MIN_HA_VERSION,
    PLATFORMS,
)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(
    hass: HomeAssistant,
    config: ConfigType,
) -> bool:
    """Integration setup."""

    if AwesomeVersion(HA_VERSION) < AwesomeVersion(MIN_HA_VERSION):  # pragma: no cover
        msg = (
            "This integration requires at least Home Assistant version "
            f" {MIN_HA_VERSION}, you are running version {HA_VERSION}."
            " Please upgrade Home Assistant to continue using this integration."
        )
        LOGGER.critical(msg)
        return False

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Min/Max from a config entry."""

    entity_registry = er.async_get(hass)

    def _resolve(option_id: str, label: str) -> str:
        """Resolve an option value (registry-id or entity_id) to an entity_id.

        Falls back to the raw value when the entity is not (yet) in the
        registry, so the helper can still load and listen for the entity
        to appear.
        """
        try:
            return er.async_validate_entity_id(entity_registry, option_id)
        except vol.Invalid:
            LOGGER.warning(
                "%s source entity %s is not in the registry; "
                "helper will be unavailable until it appears",
                label,
                option_id,
            )
            return option_id

    wasp_entity_id = _resolve(entry.options[CONF_WASP_ID], "Motion")
    box_entity_id = _resolve(entry.options[CONF_BOX_ID], "Door")

    async def async_registry_updated(
        event: Event[er.EventEntityRegistryUpdatedData],
    ) -> None:
        """Handle entity registry update.

        On source-sensor removal we do NOT remove the wasp ConfigEntry
        (see issue #32). The helper stays available; its binary sensor
        becomes 'unavailable' until the source is recreated. We reload the
        entry so listeners re-subscribe and the new state is replayed.
        """
        data = event.data
        if data["action"] == "remove":
            await hass.config_entries.async_reload(entry.entry_id)
            return

        if data["action"] != "update":
            return

        if "entity_id" in data["changes"]:
            await hass.config_entries.async_reload(entry.entry_id)

    entry.async_on_unload(
        async_track_entity_registry_updated_event(
            hass, wasp_entity_id, async_registry_updated
        )
    )
    entry.async_on_unload(
        async_track_entity_registry_updated_event(
            hass, box_entity_id, async_registry_updated
        )
    )

    entry.async_on_unload(entry.add_update_listener(config_entry_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def config_entry_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener, called when the config entry options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
