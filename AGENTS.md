# Repository Notes

- Run commands from the repo root. `testbed_topology.py` and `visualize_topology.py` read/write cwd-relative files such as `testbed_topology.json` and `topology_overlay.html`.
- Always use `uv` for Python commands in this repo (`uv sync`, `uv run ...`), not system `python` or `pip` directly.

# Entry Points

- `server.py` is the live app entrypoint. Start it with `uv run uvicorn server:app --reload --host 0.0.0.0 --port 8765`. `instructions.txt` uses `--no-access-log` for quieter manual testing.
- `visualize_topology.py` is the source for the dashboard HTML template. `topology_overlay.html` is generated output; do not hand-edit it.
- `main.py` is a small smoke-check script that prints the loaded topology summary.

# Topology Data

- `testbed_topology.json` is the source of truth for waypoints, edge servers, route order, segment candidates, and QoS values.
- Live telemetry derives the current and next segments from the posted waypoint sequence. Mock mode still uses the fixed `route` array in `testbed_topology.json`.
- Topology waypoint IDs are `Cone_*`, derived from `isaacsim_cones_waypoints.json` and projected into the existing dashboard pixel frame.
- `testbed_topology.py` loads `testbed_topology.json` at import time into module globals. After editing the JSON, rerun any script that imported it.
- `server.py` also caches topology in process state. After editing `testbed_topology.json`, call `POST /api/v1/topology/reload` or restart `uvicorn`.

# API Quirks

- Prefer the `/api/v1/*` endpoints. `server.py` also exposes legacy `/api/*` aliases that call the same handlers; `instructions.txt` examples use the legacy paths.
- `POST /api/v1/telemetry` accepts `current_destination` plus `waypoint_sequence` for live route updates. Legacy `current_waypoint` posts still work.
- `testbed_topology.json` keeps the old `P_*` waypoint block as `//` comments for reference; Python loaders ignore comment lines.
- The monitor auto-advances `route_index` every 10 seconds while `mock_enabled` is `true`.
- Posting telemetry to `POST /api/v1/telemetry` disables mock mode (`mock_enabled = false`). Re-enable it with `POST /api/v1/mock` and `{"enabled": true}`.
- Always send `status` (`"up"` or `"down"`) in `POST /api/v1/server-health`. The code path that falls back to `availability` is not usable because `ServerHealthPayload` does not define that field.
- Use `POST /api/v1/mock/advance` for a deterministic one-step state change during manual testing.

# Verification

- There is no repo-local `pytest`, lint, typecheck, formatter, or CI config. Use focused smoke checks instead.
- `uv run python main.py` verifies the topology loads and segments resolve.
- `uv run python visualize_topology.py` rewrites `topology_overlay.html`; despite the defined CLI flags, the current `main()` only writes the file and prints the `uvicorn` command.
- For app checks, run `uv run uvicorn server:app --reload --host 0.0.0.0 --port 8765` and hit `GET /api/v1/health`.

# Ignore

- `dashboard_state.json.tmp` is not referenced anywhere in repo code; do not treat it as live input.
