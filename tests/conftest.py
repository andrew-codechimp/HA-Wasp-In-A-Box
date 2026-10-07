"""Fixtures for Wasp in a Box tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from custom_components.wasp_in_a_box.const import (
    CONF_BOX_ID,
    CONF_DOOR_CLOSED_DELAY,
    CONF_DOOR_OPEN_TIMEOUT,
    CONF_IMMEDIATE_ON,
    CONF_WASP_ID,
    DEFAULT_DOOR_CLOSED_DELAY,
    DEFAULT_IMMEDIATE_ON,
    DEFAULT_OPEN_DOOR_TIMEOUT,
    DOMAIN,
)
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.syrupy import HomeAssistantSnapshotExtension
from syrupy.assertion import SnapshotAssertion

from homeassistant.const import CONF_NAME
from homeassistant.helpers import entity_registry as er

from .const import DEFAULT_NAME, DOOR_ENTITY_ID, MOTION_ENTITY_ID


@pytest.fixture
def snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Use the Home Assistant snapshot serializer."""
    return snapshot.use_extension(HomeAssistantSnapshotExtension)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations in Home Assistant."""


@pytest.fixture(autouse=True)
def freeze_setup_time(freezer: FrozenDateTimeFactory) -> None:
    """Keep snapshot timestamps and timer deadlines stable."""
    freezer.move_to("2026-07-01T12:00:00+00:00")


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Mock integration setup when testing flows in isolation."""
    with patch(
        "custom_components.wasp_in_a_box.async_setup_entry", return_value=True
    ) as mock_setup:
        yield mock_setup


@pytest.fixture
def mock_config_entry(request: pytest.FixtureRequest) -> MockConfigEntry:
    """Create a helper entry with default options and optional overrides."""
    return MockConfigEntry(
        domain=DOMAIN,
        version=1,
        minor_version=1,
        entry_id="wasp-entry",
        title=DEFAULT_NAME,
        data={},
        options={
            CONF_NAME: DEFAULT_NAME,
            CONF_WASP_ID: MOTION_ENTITY_ID,
            CONF_BOX_ID: DOOR_ENTITY_ID,
            CONF_DOOR_CLOSED_DELAY: DEFAULT_DOOR_CLOSED_DELAY,
            CONF_DOOR_OPEN_TIMEOUT: DEFAULT_OPEN_DOOR_TIMEOUT,
            CONF_IMMEDIATE_ON: DEFAULT_IMMEDIATE_ON,
            **getattr(request, "param", {}),
        },
    )


@pytest.fixture
def source_sensors(entity_registry: er.EntityRegistry) -> None:
    """Register the motion and door sensors before loading the helper."""
    entity_registry.async_get_or_create(
        "binary_sensor", "test", "motion", suggested_object_id="test_motion"
    )
    entity_registry.async_get_or_create(
        "binary_sensor", "test", "door", suggested_object_id="test_door"
    )
