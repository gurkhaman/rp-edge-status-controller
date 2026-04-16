# Dynamic Waypoint Sequence Plan

## Goal

Adapt the controller so it can consume TurtleBot route data from ROS and compute segments from the live route, while keeping the existing ranking and Pi control behavior unchanged.

## Inputs From ROS

- `current_destination`
  - Meaning: the next waypoint the robot is heading toward
- `waypoint_sequence`
  - Meaning: the ordered waypoint route for the current run

Example ROS values:

```text
current_destination: Cone_09
waypoint_sequence: Cone_09,Cone_01,Cone_08,Cone_07,Cone_06,Cone_05,Cone_04,Cone_01
```

## What Must Stay The Same

- QoS ranking logic in `build_ranking()`
- Recommended server selection from the ranked candidates
- Pi endpoint sync in `sync_edge_led_status()`
- LED policy in `desired_led_state()`:
  - recommended server -> `on`
  - down server -> `off`
  - all others -> `idle`

Files/functions to preserve semantically:

- `server.py:298` `build_ranking()`
- `server.py:326` `desired_led_state()`
- `server.py:339` `sync_edge_led_status()`
- `server.py:373` `sync_edge_led_statuses()`

## Current Limitation

The controller currently derives `current_segment` and `next_segment` from the fixed `route` stored in `testbed_topology.json`.

Current flow:

1. Telemetry sends `current_waypoint`
2. Controller finds that waypoint inside `topology["route"]`
3. Controller sets `route_index`
4. Controller computes:
   - `current_segment = route[i] -> route[i+1]`
   - `next_segment = route[i+1] -> route[i+2]`

This does not support a random waypoint sequence supplied at runtime.

## Required Changes

### 1. Change the telemetry contract

Replace or extend the current telemetry payload so the controller can receive ROS route data.

Current model:

```json
{
  "robot_id": "turtlebot_1",
  "current_waypoint": "P_08"
}
```

Target model:

```json
{
  "robot_id": "turtlebot_1",
  "current_destination": "Cone_09",
  "waypoint_sequence": ["Cone_09", "Cone_01", "Cone_08", "Cone_07"]
}
```

Implementation notes:

- Add `current_destination: str`
- Add `waypoint_sequence: list[str]`
- Keep `robot_id`
- Remove `current_waypoint` only if no legacy caller still depends on it

Primary file:

- `server.py`

### 2. Store live route data in monitor state

The controller needs runtime route state instead of only `route_index` into a static topology route.

Add monitor state fields similar to:

- `current_destination`
- `waypoint_sequence`

Implementation notes:

- Continue loading topology waypoints, segments, candidate servers, and QoS from `testbed_topology.json`
- Stop relying on `topology["route"]` for live movement logic
- Keep the topology `route` only if needed for fallback, docs, or mock mode

Primary file:

- `server.py`

### 3. Derive segments from the live sequence

Because `current_destination` means the robot's next target, segment calculation must be based on the destination index in the sequence.

If `current_destination` is at index `i` in `waypoint_sequence`:

- `current_segment = waypoint_sequence[i - 1] -> waypoint_sequence[i]`
- `next_segment = waypoint_sequence[i] -> waypoint_sequence[i + 1]`, if present

Implementation notes:

- Validate that `current_destination` exists in `waypoint_sequence`
- Validate that all referenced waypoints exist in topology
- Use the existing `segment_between()` helper to resolve segment metadata
- Preserve bidirectional segment matching exactly as today

Primary file/functions:

- `server.py`
- replace the fixed-route dependency in `build_state()`
- replace `route_index_from_waypoint()` usage in telemetry handling

### 4. Define edge-case behavior

The new segment derivation needs explicit handling for boundary cases.

Cases:

1. `current_destination` is the first item in `waypoint_sequence`
   - No previous waypoint exists
   - Behavior options:
     - treat `current_segment` as unavailable and rank from `next_segment`
     - or reject until a previous waypoint is known
   - Recommended: allow `current_segment = None`, use `next_segment` as the ranking target

2. `current_destination` is the last item in `waypoint_sequence`
   - `next_segment = None`
   - Rank from `current_segment`

3. A waypoint in the sequence is not known by topology
   - Return `400`

4. Two adjacent waypoints in the sequence have no matching segment in topology
   - Return `400`

Primary file:

- `server.py`

### 5. Align waypoint IDs with ROS naming

Implemented:

- Topology waypoint IDs now use `Cone_*`
- `route` and `segments` were updated consistently
- `testbed_topology.json` keeps the old `P_*` waypoint block as `//` comments for reference
- Cone coordinates come from `isaacsim_cones_waypoints.json` and are projected into the existing dashboard pixel frame

Files affected:

- `testbed_topology.json`
- `README.md`
- `instructions.txt`
- `AGENTS.md`
- `visualize_topology.py` for waypoint label formatting assumptions

### 6. Update response fields and dashboard assumptions

The response model and dashboard currently assume route-index-based navigation.

Implementation notes:

- Revisit whether `robot.route_index` still makes sense
- Either:
  - replace it with a dynamic sequence index, or
  - keep the field but redefine it clearly
- Ensure `robot.current_waypoint` is not mislabeled if the controller is actually receiving `current_destination`
- Prefer adding an explicit `current_destination` field if needed to avoid semantic confusion

Files likely affected:

- `server.py`
- `visualize_topology.py`

### 7. Keep mock mode only if it still serves a purpose

Current mock mode auto-advances through the static topology route.

Options:

1. Leave mock mode as-is for local testing against the static route
2. Update mock mode to also operate on a supplied dynamic sequence

Recommended:

- Keep mock mode for now unless it blocks the new runtime path
- Clearly separate mock/static behavior from ROS-driven behavior

Files likely affected:

- `server.py`

### 8. Add a bridge on the ROS machine

The controller is already an HTTP service and does not subscribe to ROS topics directly.

Recommended integration:

1. ROS bridge subscribes to:
   - `/current_destination`
   - `/waypoint_sequence`
2. Bridge converts the sequence string into an ordered list
3. Bridge posts JSON to the controller telemetry endpoint

Reason:

- Lower risk than embedding ROS client logic into `server.py`
- Keeps the controller transport-agnostic

## Suggested Implementation Order

1. Update topology IDs to the ROS naming scheme or add alias support
2. Extend the telemetry payload to accept `current_destination` and `waypoint_sequence`
3. Replace fixed-route segment derivation with sequence-based derivation
4. Update the response model to reflect the new semantics
5. Keep ranking and Pi sync behavior unchanged
6. Update docs and examples
7. Smoke test with sample ROS input

## Smoke Test Scenarios

### Scenario 1: middle of sequence

Input:

```json
{
  "robot_id": "turtlebot_1",
  "current_destination": "Cone_01",
  "waypoint_sequence": ["Cone_09", "Cone_01", "Cone_08", "Cone_07"]
}
```

Expected derivation:

- `current_segment = Cone_09 -> Cone_01`
- `next_segment = Cone_01 -> Cone_08`
- ranking logic unchanged
- Pi states unchanged except for the newly derived segment context

### Scenario 2: first item in sequence

Input:

```json
{
  "robot_id": "turtlebot_1",
  "current_destination": "Cone_09",
  "waypoint_sequence": ["Cone_09", "Cone_01", "Cone_08"]
}
```

Expected derivation:

- `current_segment = None`
- `next_segment = Cone_09 -> Cone_01`
- controller still returns a valid recommendation if the fallback policy allows it

### Scenario 3: invalid sequence edge

Input contains adjacent waypoints that do not map to a known segment.

Expected result:

- HTTP `400`
- clear error message naming the invalid segment pair

## Out Of Scope

- Changing the QoS scoring formula
- Changing the recommended server selection rule
- Changing Pi endpoint URL shape
- Direct ROS subscription inside the FastAPI app
- Geometry-based segment inference from raw robot coordinates

## Summary

Only the route input and segment derivation need to change.

Keep this pipeline intact:

1. derive segment context
2. rank candidate servers
3. choose `recommended_server`
4. send Pi commands with the existing `on` / `idle` / `off` policy
