"""Sensor platform for wasp_in_a_box."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import voluptuous as vol

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_UNIQUE_ID,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
    AddEntitiesCallback,
)
from homeassistant.helpers.event import (
    async_track_entity_registry_updated_event,
    async_track_state_change_event,
)
from homeassistant.helpers.reload import async_setup_reload_service
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType, StateType
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_LAST_MODIFIED,
    CONF_WASP_ID,
    DOMAIN,
    LOGGER,
    PLATFORMS,
)

ICON = "mdi:home-outline"


async def config_entry_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener, called when the config entry options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> bool:
    """Initialize periodic min/max config entry."""
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    try:
        source_entity_id = er.async_validate_entity_id(
            entity_registry, config_entry.options[CONF_WASP_ID]
        )
    except vol.Invalid:
        # The entity is identified by an unknown entity registry ID
        LOGGER.error(
            "Failed to setup wasp_in_a_box for unknown entity %s",
            config_entry.options[CONF_WASP_ID],
        )
        return False

    source_entity = entity_registry.async_get(source_entity_id)
    device_id = source_entity.device_id if source_entity else None

    async def async_registry_updated(
        event: Event[er.EventEntityRegistryUpdatedData],
    ) -> None:
        """Handle entity registry update."""
        data = event.data
        if data["action"] == "remove":
            await hass.config_entries.async_remove(config_entry.entry_id)

        if data["action"] != "update":
            return

        if "entity_id" in data["changes"]:
            # Entity_id changed, reload the config entry
            await hass.config_entries.async_reload(config_entry.entry_id)

    config_entry.async_on_unload(
        async_track_entity_registry_updated_event(
            hass, source_entity_id, async_registry_updated
        )
    )
    config_entry.async_on_unload(
        config_entry.add_update_listener(config_entry_update_listener)
    )

    async_add_entities(
        [
            WaspInABoxSensor(
                hass,
                source_entity_id,
                config_entry.title,
                config_entry.entry_id,
            )
        ]
    )

    return True


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the wasp_in_a_box sensor."""
    source_entity_id: str = config[CONF_WASP_ID]
    name: str | None = config.get(CONF_NAME)
    unique_id = config.get(CONF_UNIQUE_ID)

    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)

    async_add_entities([WaspInABoxSensor(hass, source_entity_id, name, unique_id)])


class WaspInABoxSensor(SensorEntity, RestoreEntity):
    """Representation of a wasp_in_a_box sensor."""

    _attr_icon = ICON
    _attr_should_poll = False
    _state_had_real_change = False
    _attr_last_modified: str = dt_util.utcnow().isoformat()

    def __init__(
        self,
        hass: HomeAssistant,
        source_entity_id: str,
        name: str | None,
        unique_id: str | None,
    ) -> None:
        """Initialize the min/max sensor."""
        self._attr_unique_id = unique_id
        self._source_entity_id = source_entity_id
        self._attr_name = name
        self._state: Any = None

        registry = er.async_get(hass)
        device_registry = dr.async_get(hass)
        source_entity = registry.async_get(source_entity_id)

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""

        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state:
            last_attrs = last_state.attributes
            if last_attrs and ATTR_LAST_MODIFIED in last_attrs:
                self._attr_last_modified = last_attrs[ATTR_LAST_MODIFIED]

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                self._source_entity_id,
                self._async_wasp_in_a_box_sensor_state_listener,
            )
        )

        registry = er.async_get(self.hass)
        entry = registry.async_get(self._source_entity_id)

        if not entry:
            LOGGER.warning(
                "Unable to find entity %s",
                self._source_entity_id,
            )

        if entry:
            state = await self.async_get_last_state()
            if state is not None and state.state not in [
                STATE_UNKNOWN,
                STATE_UNAVAILABLE,
            ]:
                self._state = state.state

            # Replay current state of source entitiy
            state = self.hass.states.get(self._source_entity_id)
            state_event: Event[EventStateChangedData] = Event(
                "",
                {
                    "entity_id": self._source_entity_id,
                    "new_state": state,
                    "old_state": None,
                },
            )
            self._async_wasp_in_a_box_sensor_state_listener(state_event)

    @property
    def native_value(self) -> StateType | datetime:
        """Return the state of the sensor."""
        value: StateType | datetime = self._state
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the device specific state attributes."""
        attributes: dict[str, Any] = {}

        attributes[ATTR_LAST_MODIFIED] = self._attr_last_modified

        return attributes

    @callback
    def _async_wasp_in_a_box_sensor_state_listener(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Handle the sensor state changes."""
        new_state = event.data["new_state"]

        if (
            new_state is None
            or new_state.state is None
            or new_state.state
            in [
                STATE_UNKNOWN,
                STATE_UNAVAILABLE,
            ]
        ):
            self._state = STATE_UNKNOWN
            return

        if self._state != new_state.state:
            self._attr_last_modified = dt_util.utcnow().isoformat(sep=" ")
        self._state = new_state.state

        self.async_write_ha_state()
