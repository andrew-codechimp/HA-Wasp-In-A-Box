"""Sensor platform for wasp_in_a_box."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_UNIQUE_ID,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
    AddEntitiesCallback,
)
from homeassistant.helpers.event import (
    async_track_entity_registry_updated_event,
    async_track_state_change_event,
)
from homeassistant.helpers.reload import async_setup_reload_service
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    CONF_BOX_ID,
    CONF_WASP_ID,
    DOMAIN,
    LOGGER,
    PLATFORMS,
)


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
    try:
        wasp_entity_id = er.async_validate_entity_id(
            entity_registry, config_entry.options[CONF_WASP_ID]
        )
    except vol.Invalid:
        # The entity is identified by an unknown entity registry ID
        LOGGER.error(
            "Failed to setup wasp_in_a_box for unknown entity %s",
            config_entry.options[CONF_WASP_ID],
        )
        return False

    try:
        box_entity_id = er.async_validate_entity_id(
            entity_registry, config_entry.options[CONF_BOX_ID]
        )
    except vol.Invalid:
        # The entity is identified by an unknown entity registry ID
        LOGGER.error(
            "Failed to setup wasp_in_a_box for unknown entity %s",
            config_entry.options[CONF_BOX_ID],
        )
        return False

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
            hass, wasp_entity_id, async_registry_updated
        )
    )
    config_entry.async_on_unload(
        async_track_entity_registry_updated_event(
            hass, box_entity_id, async_registry_updated
        )
    )
    config_entry.async_on_unload(
        config_entry.add_update_listener(config_entry_update_listener)
    )

    async_add_entities(
        [
            WaspInABoxSensor(
                hass,
                wasp_entity_id,
                box_entity_id,
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
    discovery_info: DiscoveryInfoType | None = None,  # noqa: ARG001
) -> None:
    """Set up the wasp_in_a_box sensor."""
    wasp_entity_id: str = config[CONF_WASP_ID]
    box_entity_id: str = config[CONF_BOX_ID]
    name: str | None = config.get(CONF_NAME)
    unique_id = config.get(CONF_UNIQUE_ID)

    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)

    async_add_entities(
        [WaspInABoxSensor(hass, wasp_entity_id, box_entity_id, name, unique_id)]
    )


class WaspInABoxSensor(BinarySensorEntity):
    """Representation of a wasp_in_a_box sensor."""

    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY
    _attr_should_poll = False
    _state_had_real_change = False
    _wasp_state: str | None = None
    _box_state: str | None = None

    def __init__(
        self,
        hass: HomeAssistant,  # noqa: ARG002
        wasp_entity_id: str,
        box_entity_id: str,
        name: str | None,
        unique_id: str | None,
    ) -> None:
        """Initialize the min/max sensor."""
        self._attr_unique_id = unique_id
        self._wasp_entity_id = wasp_entity_id
        self._box_entity_id = box_entity_id
        self._attr_name = name
        self._state: Any = None

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""

        await super().async_added_to_hass()

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                self._wasp_entity_id,
                self._async_wasp_state_listener,
            )
        )
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                self._box_entity_id,
                self._async_box_state_listener,
            )
        )

        registry = er.async_get(self.hass)
        wasp_entry = registry.async_get(self._wasp_entity_id)
        box_entry = registry.async_get(self._box_entity_id)

        if not wasp_entry:
            LOGGER.warning(
                "Unable to find entity %s",
                self._wasp_entity_id,
            )
        if not box_entry:
            LOGGER.warning(
                "Unable to find entity %s",
                self._box_entity_id,
            )

        if wasp_entry and box_entry:
            # Replay current state of wasp entitiy
            state = self.hass.states.get(self._wasp_entity_id)
            state_event: Event[EventStateChangedData] = Event(
                "",
                {
                    "entity_id": self._wasp_entity_id,
                    "new_state": state,
                    "old_state": None,
                },
            )
            self._async_wasp_state_listener(state_event)

            # Replay current state of box entitiy
            state = self.hass.states.get(self._box_entity_id)
            state_event: Event[EventStateChangedData] = Event(
                "",
                {
                    "entity_id": self._box_entity_id,
                    "new_state": state,
                    "old_state": None,
                },
            )
            self._async_box_state_listener(state_event)

    @property
    def is_on(self) -> bool | None:
        """Return true if occupancy is detected."""
        if self._state in [STATE_UNKNOWN, STATE_UNAVAILABLE, None]:
            return None
        # Convert state to boolean - "on"/"home" means occupied
        return self._state.lower() in ["on", "home", "true", "1"]

    @callback
    def _async_wasp_state_listener(self, event: Event[EventStateChangedData]) -> None:
        """Handle the wasp sensor state changes."""
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
            self._wasp_state = STATE_UNKNOWN
        else:
            self._wasp_state = new_state.state

        self.async_calculate_state()

    @callback
    def _async_box_state_listener(self, event: Event[EventStateChangedData]) -> None:
        """Handle the box sensor state changes."""
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
            self._box_state = STATE_UNKNOWN
        else:
            self._box_state = new_state.state

        self.async_calculate_state()

    @callback
    def async_calculate_state(self) -> None:
        """Calculate the state based on wasp and box states."""
        LOGGER.debug(
            "Calculating state: wasp_state=%s, box_state=%s",
            self._wasp_state,
            self._box_state,
        )

        if STATE_UNKNOWN in {self._wasp_state, self._box_state}:
            self._state = STATE_UNKNOWN
            self.async_write_ha_state()
            return

        if self._wasp_state and self._box_state:
            if self._wasp_state.lower() in [
                "on",
                "home",
                "true",
                "1",
            ] and self._box_state.lower() in [
                "on",
                "home",
                "true",
                "1",
            ]:
                self._state = "on"
            else:
                self._state = "off"

        self.async_write_ha_state()
