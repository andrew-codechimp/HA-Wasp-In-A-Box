"""The test for the wasp_in_the_box sensor platform."""

from homeassistant.components.sensor import ATTR_STATE_CLASS, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component


async def test_helper_sensor(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    """Test the helper sensor."""
    sensor_entity_entry = entity_registry.async_get_or_create(
        "sensor",
        "test_source_sensor",
        "unique",
        suggested_object_id="test_source_sensor",
    )
    assert sensor_entity_entry.entity_id == "sensor.test_source_sensor"

    config = {
        "sensor": {
            "platform": "wasp_in_the_box",
            "name": "test_helper_sensor",
            "entity_id": "sensor.test_source_sensor",
            "unique_id": "very_unique_id",
        }
    }

    assert await async_setup_component(hass, "sensor", config)
    await hass.async_block_till_done()

    hass.states.async_set(sensor_entity_entry.entity_id, "ABC")
    await hass.async_block_till_done()

    state = hass.states.get("sensor.test_helper_sensor")

    assert "ABC" == state.state

    entity = entity_registry.async_get("sensor.test_helper_sensor")
    assert entity.unique_id == "very_unique_id"
