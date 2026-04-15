# Repository Notes

- Run commands from the repo root. `testbed_topology.py` and `visualize_topology.py` read/write cwd-relative files such as `testbed_topology.json` and `topology_overlay.html`.
- Install deps with `python3 -m pip install -r requirements.txt`. The only declared runtime deps are `fastapi` and `uvicorn`.

# Entry Points

- `server.py` is the live app entrypoint. Start it with `uvicorn server:app --reload --port 8765`. `instructions.txt` uses `--no-access-log` for quieter manual testing.
- `visualize_topology.py` is the source for the dashboard HTML template. `topology_overlay.html` is generated output; do not hand-edit it.
- `main.py` is a small smoke-check script that prints the loaded topology summary.

# Topology Data

- `testbed_topology.json` is the source of truth for waypoints, edge servers, route order, segment candidates, and QoS values.
- Server recommendation is route-relative: `server.py` always computes the current segment and next segment from the fixed `route` array in `testbed_topology.json`, not from arbitrary graph traversal.
- `testbed_topology.py` loads `testbed_topology.json` at import time into module globals. After editing the JSON, rerun any script that imported it.
- `server.py` also caches topology in process state. After editing `testbed_topology.json`, call `POST /api/v1/topology/reload` or restart `uvicorn`.

# API Quirks

- Prefer the `/api/v1/*` endpoints. `server.py` also exposes legacy `/api/*` aliases that call the same handlers; `instructions.txt` examples use the legacy paths.
- `POST /api/v1/telemetry` is waypoint-ID driven: send `current_waypoint` like `P_08`; the server derives segment context and robot coordinates from topology data.
- API waypoint IDs come from `testbed_topology.json` and are `P_*`, not `WP_*`.
- The monitor auto-advances `route_index` every 10 seconds while `mock_enabled` is `true`.
- Posting telemetry to `POST /api/v1/telemetry` disables mock mode (`mock_enabled = false`). Re-enable it with `POST /api/v1/mock` and `{"enabled": true}`.
- Always send `status` (`"up"` or `"down"`) in `POST /api/v1/server-health`. The code path that falls back to `availability` is not usable because `ServerHealthPayload` does not define that field.
- Use `POST /api/v1/mock/advance` for a deterministic one-step state change during manual testing.

# Verification

- There is no repo-local `pytest`, lint, typecheck, formatter, or CI config. Use focused smoke checks instead.
- `python3 main.py` verifies the topology loads and segments resolve.
- `python3 visualize_topology.py` rewrites `topology_overlay.html`; despite the defined CLI flags, the current `main()` only writes the file and prints the `uvicorn` command.
- For app checks, run `uvicorn server:app --reload --port 8765` and hit `GET /api/v1/health`.

# Ignore

- `dashboard_state.json.tmp` is not referenced anywhere in repo code; do not treat it as live input.
