# Wasp in a Box tests

The suite uses `pytest-homeassistant-custom-component`, following the shared
fixtures, parameterized tests, and Syrupy snapshots pattern.

Run commands from the repository root:

```bash
./scripts/setup
uv run --no-sync pytest
uv run --no-sync pytest --cov=custom_components.wasp_in_a_box --cov-report=term-missing
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync mypy
```

VS Code provides `Tests: All with Coverage` (the default test task), `Tests: All`,
and `Tests: Current File`. The coverage task also writes an HTML report to
`htmlcov/index.html`.

The GitHub `Tests` workflow runs on relevant pushes and pull requests to `main`,
and can be started manually. It installs dependencies from `uv.lock` and runs
the full suite.

The tests cover:

- Config defaults, custom options, source selectors, and saving options.
- Setup, reload, removal, missing sources, registry updates, and source recovery.
- Occupancy latching, immediate occupancy, source availability, door-close
  delays, open-door timeouts, and timer cancellation.
- Reset behavior, entity targeting, and English action translations.

Source sensors are registered through a shared fixture. `mock_config_entry`
accepts option overrides with indirect parametrization. `setup_integration`
loads the helper and publishes initial source reports. Timer tests advance a
frozen clock and run scheduled callbacks without waiting in real time.

Entity metadata and reset states are captured in `snapshots/*.ambr`. After an
intentional change to those outputs, regenerate and review the snapshots:

```bash
uv run --no-sync pytest tests/test_binary_sensor.py tests/test_services.py --snapshot-update
```
