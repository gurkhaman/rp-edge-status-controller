from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


ROBOT_ID = "turtlebot_1"
HTTP_TIMEOUT_SECONDS = 2.0


class TelemetryBridgeNode(Node):
    def __init__(self) -> None:
        super().__init__("telemetry_bridge")
        self.controller_url = self.declare_parameter(
            "controller_url", "http://127.0.0.1:8765/api/v1/telemetry"
        ).value
        self.current_destination_topic = self.declare_parameter(
            "current_destination_topic", "current_destination"
        ).value
        self.waypoint_sequence_topic = self.declare_parameter(
            "waypoint_sequence_topic", "waypoint_sequence"
        ).value

        self.latest_current_destination: str | None = None
        self.latest_waypoint_sequence: list[str] | None = None
        self.last_sent_payload: dict[str, Any] | None = None

        self.create_subscription(
            String,
            self.current_destination_topic,
            self._handle_current_destination,
            10,
        )
        self.create_subscription(
            String,
            self.waypoint_sequence_topic,
            self._handle_waypoint_sequence,
            10,
        )

        self.get_logger().info(f"Forwarding ROS telemetry to {self.controller_url}")

    def _handle_current_destination(self, msg: String) -> None:
        current_destination = msg.data.strip()
        if not current_destination:
            self.get_logger().error("current_destination was empty")
            return

        self.latest_current_destination = current_destination
        self._maybe_send_payload()

    def _handle_waypoint_sequence(self, msg: String) -> None:
        waypoint_sequence = [item.strip() for item in msg.data.split(",")]
        if not waypoint_sequence or any(not item for item in waypoint_sequence):
            self.get_logger().error("waypoint_sequence was empty or malformed")
            return

        self.latest_waypoint_sequence = waypoint_sequence
        self._maybe_send_payload()

    def _maybe_send_payload(self) -> None:
        payload = self._build_payload()
        if payload is None or payload == self.last_sent_payload:
            return

        if self._post_payload(payload):
            self.last_sent_payload = payload

    def _build_payload(self) -> dict[str, Any] | None:
        if (
            self.latest_current_destination is None
            or self.latest_waypoint_sequence is None
        ):
            return None

        if self.latest_current_destination not in self.latest_waypoint_sequence:
            self.get_logger().error(
                "current_destination is not present in waypoint_sequence"
            )
            return None

        return {
            "robot_id": ROBOT_ID,
            "current_destination": self.latest_current_destination,
            "waypoint_sequence": self.latest_waypoint_sequence,
        }

    def _post_payload(self, payload: dict[str, Any]) -> bool:
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            self.controller_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS):
                return True
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip()
            self.get_logger().error(
                f"controller rejected telemetry with HTTP {exc.code}: {detail}"
            )
        except URLError as exc:
            self.get_logger().error(f"failed to reach controller: {exc.reason}")
        except Exception as exc:
            self.get_logger().error(f"failed to post telemetry: {exc}")

        return False


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = TelemetryBridgeNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
