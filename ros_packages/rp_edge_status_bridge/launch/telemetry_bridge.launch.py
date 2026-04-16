from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "controller_url",
                default_value="http://127.0.0.1:8765/api/v1/telemetry",
            ),
            DeclareLaunchArgument(
                "current_destination_topic",
                default_value="current_destination",
            ),
            DeclareLaunchArgument(
                "waypoint_sequence_topic",
                default_value="waypoint_sequence",
            ),
            Node(
                package="rp_edge_status_bridge",
                executable="telemetry_bridge_node",
                name="telemetry_bridge",
                output="screen",
                parameters=[
                    {
                        "controller_url": LaunchConfiguration("controller_url"),
                        "current_destination_topic": LaunchConfiguration(
                            "current_destination_topic"
                        ),
                        "waypoint_sequence_topic": LaunchConfiguration(
                            "waypoint_sequence_topic"
                        ),
                    }
                ],
            ),
        ]
    )
