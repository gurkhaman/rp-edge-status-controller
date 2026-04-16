# rp_edge_status_bridge

Minimal ROS 2 sidecar package that subscribes to `current_destination` and
`waypoint_sequence` and forwards changed payloads to the controller over HTTP.

## Move Into A ROS Workspace

Copy this folder into your ROS workspace `src/` directory:

```bash
cp -r rp-edge-status-controller/ros_packages/rp_edge_status_bridge <your_ws>/src/
```

## Build

```bash
source /opt/ros/<distro>/setup.bash
cd <your_ws>
colcon build --packages-select rp_edge_status_bridge
source install/setup.bash
```

## Run

Directly:

```bash
ros2 run rp_edge_status_bridge telemetry_bridge_node --ros-args -p controller_url:=http://<controller-host>:8765/api/v1/telemetry
```

With launch:

```bash
ros2 launch rp_edge_status_bridge telemetry_bridge.launch.py controller_url:=http://<controller-host>:8765/api/v1/telemetry
```

## Topics

- `current_destination` (`std_msgs/msg/String`)
- `waypoint_sequence` (`std_msgs/msg/String`)

## Parameters

- `controller_url`
- `current_destination_topic`
- `waypoint_sequence_topic`
