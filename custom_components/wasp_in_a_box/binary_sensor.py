"""Sensor platform for wasp_in_a_box."""

from __future__ import annotations

from datetime import datetime

import voluptuous as vol

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import (
    CALLBACK_TYPE,
    Event,
    EventStateChangedData,
    HomeAssistant,
    callback,
)
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import (
    async_call_later,
    async_track_entity_registry_updated_event,
    async_track_state_change_event,
)

from .const import (
    CONF_BOX_ID,
    CONF_DOOR_CLOSED_DELAY,
    CONF_DOOR_OPEN_TIMEOUT,
    CONF_IMMEDIATE_ON,
    CONF_WASP_ID,
    LOGGER,
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

    delay = config_entry.options[CONF_DOOR_CLOSED_DELAY]
    timeout = config_entry.options[CONF_DOOR_OPEN_TIMEOUT]
    immediate_on = config_entry.options[CONF_IMMEDIATE_ON]

    async_add_entities(
        [
            WaspInABoxSensor(
                hass,
                wasp_entity_id,
                box_entity_id,
                delay,
                timeout,
                immediate_on,
                config_entry.title,
                config_entry.entry_id,
            )
        ]
    )

    return True


class WaspInABoxSensor(BinarySensorEntity):
    """Representation of a wasp_in_a_box sensor."""

    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY
    _attr_should_poll = False
    _state_had_real_change = False
    _wasp_state: str | None = None
    _box_state: str | None = None
    _door_closed_delay_timer: CALLBACK_TYPE | None = None
    _door_open_timeout_timer: CALLBACK_TYPE | None = None
    _motion_was_detected: bool = False

    def __init__(  # noqa: PLR0913
        self,
        hass: HomeAssistant,
        wasp_entity_id: str,
        box_entity_id: str,
        delay: int,
        timeout: int,
        immediate_on: bool,
        name: str | None,
        unique_id: str | None,
    ) -> None:
        """Initialize the min/max sensor."""
        self._attr_unique_id = unique_id
        self._wasp_entity_id = wasp_entity_id
        self._box_entity_id = box_entity_id
        self._delay = delay
        self._timeout = timeout
        self._immediate_on = immediate_on
        self._attr_name = name
        self._state: str | None = None

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
            wasp_state = self.hass.states.get(self._wasp_entity_id)
            wasp_state_event: Event[EventStateChangedData] = Event(
                "",
                {
                    "entity_id": self._wasp_entity_id,
                    "new_state": wasp_state,
                    "old_state": None,
                },
            )
            self._async_wasp_state_listener(wasp_state_event)

            # Replay current state of box entitiy
            box_state = self.hass.states.get(self._box_entity_id)
            box_state_event: Event[EventStateChangedData] = Event(
                "",
                {
                    "entity_id": self._box_entity_id,
                    "new_state": box_state,
                    "old_state": None,
                },
            )
            self._async_box_state_listener(box_state_event)

    async def async_will_remove_from_hass(self) -> None:
        """Handle removal from hass."""
        # Cancel any pending timers to prevent callbacks after removal
        if self._door_closed_delay_timer is not None:
            self._door_closed_delay_timer()
            self._door_closed_delay_timer = None

        if self._door_open_timeout_timer is not None:
            self._door_open_timeout_timer()
            self._door_open_timeout_timer = None

    @property
    def is_on(self) -> bool | None:
        """Return true if occupancy is detected."""
        if self._state in [STATE_UNKNOWN, STATE_UNAVAILABLE, None]:
            return None
        # Convert state to boolean - "on"/"home" means occupied
        return self._state == "on"

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

        # Cancel any existing timeout timer
        if self._door_open_timeout_timer is not None:
            self._door_open_timeout_timer()
            self._door_open_timeout_timer = None

        if self._wasp_state == "off" and self._box_state == "on":
            LOGGER.debug(
                "Motion unoccupied and door open, waiting %s seconds before recalculating",
                self._timeout,
            )
            self._door_open_timeout_timer = async_call_later(
                self.hass, self._timeout, self._async_door_open_timeout_callback
            )

        self.async_calculate_state()

    @callback
    def _async_box_state_listener(self, event: Event[EventStateChangedData]) -> None:
        """Handle the box sensor state changes."""
        new_state = event.data["new_state"]
        old_state = event.data.get("old_state")

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
            # Check if door just closed (transition from open to closed)
            door_just_closed = (
                old_state is not None
                and old_state.state == "on"
                and new_state.state == "off"
            )

            self._box_state = new_state.state

            if door_just_closed:
                # Cancel any existing timer
                if self._door_closed_delay_timer is not None:
                    self._door_closed_delay_timer()
                    self._door_closed_delay_timer = None

                # Set a delay before recalculating state
                LOGGER.debug(
                    "Door closed, waiting %s seconds before recalculating", self._delay
                )
                self._door_closed_delay_timer = async_call_later(
                    self.hass, self._delay, self._async_door_closed_delay_callback
                )
                return

        # Cancel any pending timer if door opens or state becomes unknown
        if self._door_closed_delay_timer is not None:
            self._door_closed_delay_timer()
            self._door_closed_delay_timer = None

        # Cancel any existing timeout timer
        if self._door_open_timeout_timer is not None:
            self._door_open_timeout_timer()
            self._door_open_timeout_timer = None

        if self._wasp_state == "off" and self._box_state == "on":
            LOGGER.debug(
                "Motion unoccupied and door open, waiting %s seconds before recalculating",
                self._timeout,
            )
            self._door_open_timeout_timer = async_call_later(
                self.hass, self._timeout, self._async_door_open_timeout_callback
            )

        self.async_calculate_state()

    @callback
    def _async_door_closed_delay_callback(self, _now: datetime) -> None:
        """Handle the delay timer callback."""
        self._door_closed_delay_timer = None
        LOGGER.debug("Delay expired, recalculating state")
        self._motion_was_detected = False
        self.async_calculate_state()

    @callback
    def _async_door_open_timeout_callback(self, _now: datetime) -> None:
        """Handle the timeout timer callback."""
        self._door_open_timeout_timer = None
        LOGGER.debug("Timeout expired, recalculating state")
        self._wasp_state = "off"
        self._box_state = "off"
        self._motion_was_detected = False

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
            # Room is occupied when door is closed (box 'off') and motion detected (wasp 'on')
            door_closed = self._box_state == "off"
            motion_detected_now = self._wasp_state == "on"
            motion_detected = motion_detected_now or self._motion_was_detected

            if door_closed and motion_detected:
                self._state = "on"
            else:
                self._state = "off"

            if not door_closed and self._immediate_on:
                self._state = "on"

            if motion_detected_now and self._immediate_on:
                self._state = "on"

            self._motion_was_detected = motion_detected

        self.async_write_ha_state()
