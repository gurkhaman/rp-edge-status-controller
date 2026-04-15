from testbed_topology import EDGE_SERVERS, SEGMENTS, WAYPOINTS, segment_length


def main() -> None:
    print("Background coordinate frame: 1536x1024, origin=(top-left)")
    print(f"Waypoints: {len(WAYPOINTS)}")
    print(f"Edge servers: {len(EDGE_SERVERS)}")
    print()

    for segment in SEGMENTS:
        start = WAYPOINTS[segment.from_waypoint]
        end = WAYPOINTS[segment.to_waypoint]
        candidates = ", ".join(segment.candidate_servers)
        print(
            f"{segment.id}: {start.id}({start.x},{start.y}) -> "
            f"{end.id}({end.x},{end.y}), length={segment_length(segment):.1f}px, "
            f"candidates=[{candidates}]"
        )


if __name__ == "__main__":
    main()
