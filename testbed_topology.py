from __future__ import annotations

import json
from dataclasses import dataclass
from math import hypot
from pathlib import Path
from typing import Iterable


TOPOLOGY_JSON = "testbed_topology.json"


@dataclass(frozen=True)
class Waypoint:
    id: str
    x: int
    y: int
    label: str


@dataclass(frozen=True)
class EdgeServer:
    id: str
    x: int
    y: int
    label: str


@dataclass(frozen=True)
class RouteSegment:
    id: str
    from_waypoint: str
    to_waypoint: str
    candidate_servers: tuple[str, str, str]


def load_topology() -> dict:
    return json.loads(Path(TOPOLOGY_JSON).read_text(encoding="utf-8-sig"))


_TOPOLOGY = load_topology()
_FRAME = _TOPOLOGY["coordinate_frame"]

IMAGE_WIDTH = _FRAME["width"]
IMAGE_HEIGHT = _FRAME["height"]
BACKGROUND_IMAGE = _TOPOLOGY["background_image"]

WAYPOINTS: dict[str, Waypoint] = {
    item["id"]: Waypoint(item["id"], item["x"], item["y"], item.get("label", ""))
    for item in _TOPOLOGY["waypoints"]
}

EDGE_SERVERS: dict[str, EdgeServer] = {
    item["id"]: EdgeServer(item["id"], item["x"], item["y"], item.get("label", ""))
    for item in _TOPOLOGY["edge_servers"]
}

ROUTE: tuple[str, ...] = tuple(_TOPOLOGY["route"])

SEGMENTS: tuple[RouteSegment, ...] = tuple(
    RouteSegment(
        item["id"],
        item["from"],
        item["to"],
        tuple(item["candidate_servers"]),
    )
    for item in _TOPOLOGY["segments"]
)


def waypoint_distance(a: Waypoint, b: Waypoint) -> float:
    return hypot(a.x - b.x, a.y - b.y)


def segment_length(segment: RouteSegment) -> float:
    return waypoint_distance(WAYPOINTS[segment.from_waypoint], WAYPOINTS[segment.to_waypoint])


def find_segment(from_waypoint: str, to_waypoint: str) -> RouteSegment:
    for segment in SEGMENTS:
        is_forward = segment.from_waypoint == from_waypoint and segment.to_waypoint == to_waypoint
        is_reverse = segment.from_waypoint == to_waypoint and segment.to_waypoint == from_waypoint
        if is_forward or is_reverse:
            return segment
    raise KeyError(f"No route segment between {from_waypoint!r} and {to_waypoint!r}.")


def route_segment_at(route_index: int) -> RouteSegment:
    if route_index < 0 or route_index >= len(ROUTE) - 1:
        raise IndexError(f"Route index {route_index} is outside the movable route range.")
    return find_segment(ROUTE[route_index], ROUTE[route_index + 1])


def next_segments(current_waypoint: str) -> tuple[RouteSegment, ...]:
    return tuple(
        segment
        for segment in SEGMENTS
        if segment.from_waypoint == current_waypoint or segment.to_waypoint == current_waypoint
    )


def active_candidate_servers(
    segment: RouteSegment, down_servers: Iterable[str] = ()
) -> tuple[str, ...]:
    down = set(down_servers)
    return tuple(server_id for server_id in segment.candidate_servers if server_id not in down)


def recommend_server(
    segment: RouteSegment,
    qos_scores: dict[str, float],
    down_servers: Iterable[str] = (),
) -> str:
    candidates = active_candidate_servers(segment, down_servers)
    if not candidates:
        raise ValueError(f"No active candidate server for {segment.id}.")
    return max(candidates, key=lambda server_id: qos_scores.get(server_id, float("-inf")))
