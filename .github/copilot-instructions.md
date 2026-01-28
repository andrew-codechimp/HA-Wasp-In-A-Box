# Wasp in a Box - AI Coding Agent Instructions

## Project Overview

This is a **Home Assistant custom integration** (helper) that implements occupancy detection for single-occupancy enclosed rooms using two binary sensors:
- **Wasp** (motion sensor) - detects movement
- **Box** (door sensor) - tracks door open/closed state

The integration solves the PIR motion sensor limitation of not detecting stationary occupants by maintaining occupancy state after the door closes, even when motion stops.

## Architecture

### Core Components

- **`custom_components/wasp_in_a_box/`** - Main integration package
  - `__init__.py` - Entry setup/unload, entity registry tracking, config entry lifecycle
  - `binary_sensor.py` - Main occupancy logic (state machine with timers)
  - `config_flow.py` - UI configuration using SchemaConfigFlowHandler
  - `const.py` - Constants, loads manifest.json dynamically
  - `manifest.json` - HA integration metadata

### State Machine Logic ([binary_sensor.py](custom_components/wasp_in_a_box/binary_sensor.py))

The `WaspInABoxSensor` class implements a timer-based state machine:

1. **Door closes** → starts `_door_closed_delay_timer` (default 30s)
2. **Motion detected** during/after delay → occupancy = ON
3. **Door opens** while occupied → occupancy remains ON until timeout
4. **Door open + no motion for `_door_open_timeout`** (default 300s) → occupancy = OFF
5. **Quick exit detection**: Door opens→closes, motion clears within delay → occupancy = OFF

Key implementation patterns:
- Timer cancellation before starting new timers (prevents race conditions)
- State replay on sensor initialization (`async_added_to_hass`)
- Async callbacks for timer expiration
- Entity registry validation in setup

## Development Workflow

### Environment Setup
```bash
./scripts/setup           # Run once: creates venv with uv sync
source .venv/bin/activate # Manual activation if needed
```

### Running Home Assistant Locally
```bash
./scripts/develop
# OR use task: "Run Home Assistant on port 8123"
# Runs HA on port 8123 with --debug
# Sets PYTHONPATH to include custom_components/ (no symlinks needed)
```

### Code Quality
```bash
./scripts/lint           # Runs: ruff check --fix, mypy, pytest
# OR use individual tasks:
# - "Ruff: Check & Fix"
# - "Mypy: Type Check"
# - "Pytest: Run All Tests"
```

**Linting is REQUIRED before commits** - project uses extensive Ruff rules (see `pyproject.toml`)

### Testing Patterns ([tests/](tests/))

Tests use `pytest-homeassistant-custom-component`:
```python
from pytest_homeassistant_custom_component.common import MockConfigEntry

# Pattern: Create source entities first, then helper config entry
source_config_entry = MockConfigEntry()
device_registry.async_get_or_create(...)
entity_registry.async_get_or_create("binary_sensor", "test", "motion", ...)
# Then create helper that references those entities
wasp_in_a_box_config_entry = MockConfigEntry(
    domain=DOMAIN,
    options={CONF_WASP_ID: "binary_sensor.test_motion", ...}
)
```

Always test entity registry updates and config entry reloads.

## Project-Specific Conventions

### Constants Management
- **NEVER hardcode domain/version** - import from `const.py`
- `const.py` parses `manifest.json` at import time:
  ```python
  DOMAIN = manifest_data.get("domain")
  VERSION = manifest_data.get("version")
  ```

### Entity Registry Handling
- Use `er.async_validate_entity_id()` - returns entity_id or raises `vol.Invalid`
- Track source entity changes with `async_handle_source_entity_changes()` (removes helper if source removed)
- Always handle registry updates in config entries

### Async Patterns
- Sensor listeners use `@callback` decorator (no async)
- Timer callbacks signature: `def _callback(self, _now: datetime) -> None:`
- Cancel timers before reassigning: `if timer is not None: timer(); timer = None`

### Home Assistant Integration Types
This is an `integration_type: "helper"` (not a device integration):
- No device creation
- Single binary_sensor entity per config entry
- Uses `SchemaConfigFlowHandler` for simple UI config
- Entity selectors require `domain=[BINARY_SENSOR_DOMAIN, INPUT_BOOLEAN_DOMAIN]`

## Dependency Management

- **Package manager**: `uv` (not pip/poetry)
- Python version: Locked to `==3.13.2` in `pyproject.toml`
- HA version: Currently `homeassistant==2026.1.0` (update for new HA releases)
- **All deps in `[dependency-groups]` dev section** - no production deps

## Common Tasks

### Adding New Configuration Options
1. Add constant to `const.py` (with DEFAULT_ prefix)
2. Add to `OPTIONS_SCHEMA` in `config_flow.py` using selector
3. Update `WaspInABoxSensor.__init__()` to accept parameter
4. Update test fixtures in `tests/conftest.py`

### Modifying State Logic
- Update `async_calculate_state()` for logic changes
- Update `_async_wasp_state_listener()` or `_async_box_state_listener()` for sensor event handling
- Add debug logging: `LOGGER.debug("Message: %s", value)` (use lazy formatting)

### Version Bumps
Update `manifest.json` only - `const.py` reads it automatically.

## Critical Gotchas

1. **Don't create devices** - helpers shouldn't register devices
2. **Always use `async_call_later`** - never `asyncio.sleep()` in callbacks
3. **Entity registry IDs can change** - always validate and track updates
4. **State replay on init** - required for correct state after HA restart
5. **Timer cleanup** - must cancel timers in `async_will_remove_from_hass()` to prevent callbacks after entity removal
