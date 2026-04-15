# BECS ITRC 0415

FastAPI-based TurtleBot server selection monitor. The app visualizes a fixed route over a testbed map, tracks the robot's current waypoint, ranks candidate edge servers for the active segment, and recommends the best next server based on per-segment QoS data.

## Overview

- Backend: `FastAPI`
- ASGI server: `uvicorn`
- Python workflow: `uv`
- Main app entrypoint: `server.py`
- Dashboard HTML source: `visualize_topology.py`
- Topology source of truth: `testbed_topology.json`

The current topology defines:

- 10 waypoints: `P_01` to `P_10`
- 5 edge servers: `edge_1` to `edge_5`
- 13 segments with candidate server lists and QoS values
- A fixed route used by the recommendation logic:
  `P_02 -> P_01 -> P_08 -> P_07 -> P_06 -> P_05`

## Quickstart

Requirements:

- `uv` installed
- Python 3.10+

Install dependencies:

```bash
uv sync
```

Run the small topology smoke check:

```bash
uv run python main.py
```

Start the API and dashboard:

```bash
uv run uvicorn server:app --reload --port 8765 --no-access-log
```

Open:

- Dashboard: `http://127.0.0.1:8765/`
- Health check: `http://127.0.0.1:8765/api/v1/health`

## Project Files

- `server.py`: FastAPI app, mock loop, API handlers, server ranking logic
- `visualize_topology.py`: dashboard HTML generator used by the app
- `testbed_topology.json`: waypoints, servers, fixed route, segment candidates, QoS data
- `testbed_topology.py`: helper module that loads topology into Python data structures
- `main.py`: simple smoke-check script that prints the loaded topology summary
- `instructions.txt`: manual testing notes and example requests from the original handoff
- `topology_overlay.html`: generated output; do not hand-edit

## API Summary

Prefer the `/api/v1/*` endpoints. Legacy `/api/*` aliases also exist.

Useful endpoints:

- `GET /api/v1/health`: basic health check
- `GET /api/v1/topology`: returns the loaded topology
- `POST /api/v1/topology/reload`: reloads `testbed_topology.json` into process memory
- `GET /api/v1/state`: returns current monitor state
- `POST /api/v1/mock`: enable or disable mock mode
- `POST /api/v1/mock/advance`: deterministically move one step along the route
- `POST /api/v1/telemetry`: update robot waypoint
- `POST /api/v1/server-health`: mark an edge server up or down

## Example Requests

Health check:

```bash
curl http://127.0.0.1:8765/api/v1/health
```

Post TurtleBot telemetry:

```bash
curl -X POST http://127.0.0.1:8765/api/v1/telemetry \
  -H 'Content-Type: application/json' \
  -d '{
    "robot_id": "turtlebot_1",
    "current_waypoint": "P_08"
  }'
```

Mark a server down:

```bash
curl -X POST http://127.0.0.1:8765/api/v1/server-health \
  -H 'Content-Type: application/json' \
  -d '{
    "server_id": "edge_1",
    "status": "down"
  }'
```

Re-enable mock mode:

```bash
curl -X POST http://127.0.0.1:8765/api/v1/mock \
  -H 'Content-Type: application/json' \
  -d '{
    "enabled": true
  }'
```

Advance mock state by one route step:

```bash
curl -X POST http://127.0.0.1:8765/api/v1/mock/advance
```

Reload topology after editing `testbed_topology.json`:

```bash
curl -X POST http://127.0.0.1:8765/api/v1/topology/reload
```

## Operational Notes

- Run commands from the repository root. Several scripts read and write cwd-relative files.
- `POST /api/v1/telemetry` is waypoint-driven. Send `current_waypoint` such as `P_08`; coordinates are derived from topology data.
- Waypoint IDs are `P_*`, not `WP_*`.
- Mock mode auto-advances `route_index` every 10 seconds while enabled.
- Posting telemetry disables mock mode. Re-enable it with `POST /api/v1/mock` and `{"enabled": true}`.
- Server recommendation is route-relative. The app uses the fixed `route` array from `testbed_topology.json`, not arbitrary graph traversal.
- After editing `testbed_topology.json`, reload the topology via the API or restart the app.
- `visualize_topology.py` is the HTML source. `topology_overlay.html` is generated output.

## Important Quirks

- `POST /api/v1/server-health` should always include `status` with value `"up"` or `"down"`.
- The fallback `availability` path in the code is not usable with the current request model.
- `testbed_topology.py` loads topology at import time. Any already-running Python process must be restarted or reloaded after topology changes.

## Verification

There is no repo-local `pytest`, lint, or typecheck setup.

Recommended smoke checks:

```bash
uv run python main.py
uv run uvicorn server:app --reload --port 8765 --no-access-log
```

Then verify:

- `GET /api/v1/health` returns `status: ok`
- Dashboard loads at `/`
- Telemetry and server-health posts update `/api/v1/state`
