# rp-edge-status-controller

FastAPI-based TurtleBot server selection monitor. The app visualizes a fixed route over a testbed map, tracks the robot's current waypoint, ranks candidate edge servers for the active segment, and recommends the best next server based on per-segment QoS data.

Developed by JBNU.

## Overview

- Backend: `FastAPI`
- ASGI server: `uvicorn`
- Python workflow: `uv`
- Main app entrypoint: `server.py`
- Dashboard HTML source: `visualize_topology.py`
- Topology source of truth: `testbed_topology.json`

The current topology defines:

- 10 waypoints: `Cone_01` to `Cone_10`
- 5 edge servers: `edge_1` to `edge_5`
- 13 segments with candidate server lists and QoS values
- A fixed route used by the recommendation logic:
  `Cone_08 -> Cone_07 -> Cone_06 -> Cone_05 -> Cone_04 -> Cone_10`

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

Run the controller server:

```bash
uv run uvicorn server:app --reload --host 0.0.0.0 --port 8765 --no-access-log
```

Open:

- Dashboard (local): `http://127.0.0.1:8765/`
- Dashboard (LAN): `http://<controller-host>:8765/`
- Health check (local): `http://127.0.0.1:8765/api/v1/health`

Run the ROS sidecar from your ROS workspace after copying
`ros_packages/rp_edge_status_bridge` into `src/` and building it:

```bash
source /opt/ros/<distro>/setup.bash
cd <your_ros_ws>
colcon build --packages-select rp_edge_status_bridge
source install/setup.bash
ros2 launch rp_edge_status_bridge telemetry_bridge.launch.py controller_url:=http://<controller-host>:8765/api/v1/telemetry
```

## Project Files

- `server.py`: FastAPI app, mock loop, API handlers, server ranking logic
- `visualize_topology.py`: dashboard HTML generator used by the app
- `testbed_topology.json`: waypoints, servers, fixed route, segment candidates, QoS data
- `testbed_topology.py`: helper module that loads topology into Python data structures
- `main.py`: simple smoke-check script that prints the loaded topology summary
- `instructions.txt`: manual testing notes and example requests from the original handoff
- `ros_packages/rp_edge_status_bridge`: ROS 2 sidecar package that forwards ROS topics to the controller
- `topology_overlay.html`: generated output; do not hand-edit

## ROS Sidecar Package

This repo also includes a standalone ROS 2 package at:

- `ros_packages/rp_edge_status_bridge`

The package is intentionally self-contained so you can copy just that folder into an
existing ROS workspace and build it there.

Typical flow:

```bash
cp -r ros_packages/rp_edge_status_bridge <your_ros_ws>/src/
cd <your_ros_ws>
source /opt/ros/<distro>/setup.bash
colcon build --packages-select rp_edge_status_bridge
source install/setup.bash
ros2 launch rp_edge_status_bridge telemetry_bridge.launch.py controller_url:=http://<controller-host>:8765/api/v1/telemetry
```

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
    "current_destination": "Cone_01",
    "waypoint_sequence": ["Cone_09", "Cone_01", "Cone_08", "Cone_07"]
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
- `POST /api/v1/telemetry` accepts `current_destination` plus `waypoint_sequence` for live route updates. Legacy `current_waypoint` posts still work.
- `current_destination` must be present inside `waypoint_sequence`, and adjacent waypoint pairs must match known topology segments.
- Mock mode auto-advances `route_index` every 10 seconds while enabled.
- Posting telemetry disables mock mode. Re-enable it with `POST /api/v1/mock` and `{"enabled": true}`.
- Live telemetry derives current and next segments from the active waypoint sequence. Mock mode still uses the fixed `route` array from `testbed_topology.json`.
- Topology waypoint IDs are now `Cone_*`, derived from `isaacsim_cones_waypoints.json` and projected into the existing dashboard pixel frame.
- `testbed_topology.json` keeps the old `P_*` waypoint block as `//` comments for reference; the loaders ignore comment lines.
- After editing `testbed_topology.json`, reload the topology via the API or restart the app.
- Start `uvicorn` with `--host 0.0.0.0` when other machines need to reach the controller over the LAN.
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
uv run uvicorn server:app --reload --host 0.0.0.0 --port 8765 --no-access-log
```

Then verify:

- `GET /api/v1/health` returns `status: ok`
- Dashboard loads at `/`
- Telemetry and server-health posts update `/api/v1/state`
