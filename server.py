from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.request import urlopen

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from visualize_topology import render_html


TOPOLOGY_JSON = "testbed_topology.json"
BACKGROUND_IMAGE = "image/background.png"
EDGE_ICON_IMAGE = "image/edge_icon.png"
WARNING_ICON_IMAGE = "image/warning_icon.png"
MOCK_INTERVAL_SECONDS = 10
LED_SYNC_TIMEOUT_SECONDS = 0.5
BASE_DIR = Path(__file__).resolve().parent
EDGE_STATUS_BASE_URLS = {
    "edge_1": "http://192.168.1.11:8000",
    "edge_2": "http://192.168.1.12:8000",
    "edge_3": "http://192.168.1.10:8000",
    "edge_4": "http://192.168.1.13:8000",
    "edge_5": "http://192.168.1.14:8000",
}

logger = logging.getLogger(__name__)


# 터틀봇 현재 웨이포인트
class TelemetryPayload(BaseModel):
    robot_id: str = "turtlebot_1"
    current_waypoint: str | None = None


# 다운된 서버 id와 상태
class ServerHealthPayload(BaseModel):
    server_id: str
    status: str | None = None


class MockControlPayload(BaseModel):
    enabled: bool


class SegmentState(BaseModel):
    id: str
    from_waypoint: str = Field(alias="from")
    to_waypoint: str = Field(alias="to")
    candidate_servers: list[str]

    model_config = {"populate_by_name": True}


class RobotState(BaseModel):
    id: str
    route_index: int
    current_waypoint: str
    x: float
    y: float


class RankingItem(BaseModel):
    server_id: str
    status: Literal["active", "down"]
    score: float
    qos: dict[str, float]


class MonitorStateResponse(BaseModel):
    timestamp: str
    source: str
    mock_enabled: bool
    robot: RobotState
    current_segment: SegmentState
    current_assigned_server: str | None = None
    next_segment: SegmentState | None = None
    recommended_server: str | None = None
    down_servers: list[str]
    qos_ranking: list[RankingItem]


class StatusResponse(BaseModel):
    status: str


class MockModeResponse(BaseModel):
    mock_enabled: bool


class HealthResponse(BaseModel):
    status: Literal["ok"]
    timestamp: str


class MonitorState:
    def __init__(self) -> None:
        self.topology = load_topology()
        self.route_index = 0
        self.robot_id = "turtlebot_1"
        self.robot_x: float | None = None
        self.robot_y: float | None = None
        self.down_servers: set[str] = set()
        self.mock_enabled = True

    def reload_topology(self) -> None:
        self.topology = load_topology()
        self.route_index = clamp_route_index(self.topology, self.route_index)

    # 터틀봇 웨이포인트 수신시 처리 로직
    def apply_telemetry(self, telemetry: TelemetryPayload) -> MonitorStateResponse:
        self.mock_enabled = False
        self.robot_id = telemetry.robot_id

        ensure_waypoint_exists(self.topology, telemetry.current_waypoint)
        self.route_index = route_index_from_waypoint(
            self.topology,
            telemetry.current_waypoint,
            self.route_index,
        )

        return self.build_and_sync_state(source="telemetry")

    # 라즈베리파이 서버 다운 상태 수신시 처리 로직
    def apply_server_health(self, payload: ServerHealthPayload) -> MonitorStateResponse:
        # 1. 서버 ID 검증
        valid_servers = {server["id"] for server in self.topology["edge_servers"]}
        if payload.server_id not in valid_servers:
            raise HTTPException(status_code=400, detail="Unknown server_id")

        status = normalize_server_status(payload)
        if status == "down":
            self.down_servers.add(payload.server_id)
        else:
            self.down_servers.discard(payload.server_id)

        return self.build_and_sync_state(source="server-health")

    # 테스트용 (route_index 자동 증가)
    def advance_mock(self) -> MonitorStateResponse:
        self.route_index = (self.route_index + 1) % max(
            1, len(self.topology["route"]) - 1
        )
        return self.build_and_sync_state(source="mock")

    def build_and_sync_state(self, source: str = "memory") -> MonitorStateResponse:
        monitor_state = self.build_state(source=source)
        sync_edge_led_statuses(self.topology, monitor_state)
        return monitor_state

    def build_state(self, source: str = "memory") -> MonitorStateResponse:
        route = self.topology["route"]
        route_index = clamp_route_index(self.topology, self.route_index)
        current_from = route[route_index]
        current_to = route[route_index + 1]
        current_segment = segment_between(self.topology, current_from, current_to)

        if route_index + 2 < len(route):
            next_segment = segment_between(
                self.topology, route[route_index + 1], route[route_index + 2]
            )
        else:
            next_segment = None

        target_segment = next_segment or current_segment
        ranking = build_ranking(
            self.topology,
            target_segment["id"],
            target_segment["candidate_servers"],
            self.down_servers,
        )
        current_ranking = build_ranking(
            self.topology,
            current_segment["id"],
            current_segment["candidate_servers"],
            self.down_servers,
        )

        recommended = next(
            (item.server_id for item in ranking if item.status == "active"), None
        )
        assigned = next(
            (item.server_id for item in current_ranking if item.status == "active"),
            None,
        )
        waypoint = waypoint_by_id(self.topology, current_from)
        robot_x = self.robot_x if self.robot_x is not None else waypoint["x"]
        robot_y = self.robot_y if self.robot_y is not None else waypoint["y"]

        return MonitorStateResponse(
            timestamp=now_iso(),
            source=source,
            mock_enabled=self.mock_enabled,
            robot=RobotState(
                id=self.robot_id,
                route_index=route_index,
                current_waypoint=current_from,
                x=robot_x,
                y=robot_y,
            ),
            current_segment=SegmentState(**current_segment),
            current_assigned_server=assigned,
            next_segment=SegmentState(**next_segment) if next_segment else None,
            recommended_server=recommended,
            down_servers=sorted(self.down_servers),
            qos_ranking=ranking,
        )


def load_topology() -> dict[str, Any]:
    topology = json.loads((BASE_DIR / TOPOLOGY_JSON).read_text(encoding="utf-8-sig"))
    if "edge_servers" not in topology and "servers" in topology:
        topology["edge_servers"] = topology["servers"]
    if "servers" not in topology and "edge_servers" in topology:
        topology["servers"] = topology["edge_servers"]
    return topology


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def clamp_route_index(topology: dict[str, Any], route_index: int) -> int:
    return max(0, min(int(route_index), len(topology["route"]) - 2))


def route_index_from_waypoint(
    topology: dict[str, Any], waypoint_id: str, fallback: int
) -> int:
    try:
        return clamp_route_index(topology, topology["route"].index(waypoint_id))
    except ValueError:
        return clamp_route_index(topology, fallback)


def ensure_waypoint_exists(topology: dict[str, Any], waypoint_id: str) -> None:
    valid_waypoints = {wp["id"] for wp in topology["waypoints"]}
    if waypoint_id not in valid_waypoints:
        raise HTTPException(status_code=400, detail=f"Unknown waypoint: {waypoint_id}")


def waypoint_by_id(topology: dict[str, Any], waypoint_id: str) -> dict[str, Any]:
    for waypoint in topology["waypoints"]:
        if waypoint["id"] == waypoint_id:
            return waypoint
    raise HTTPException(status_code=400, detail=f"Unknown waypoint: {waypoint_id}")


def segment_between(
    topology: dict[str, Any], from_waypoint: str, to_waypoint: str
) -> dict[str, Any]:
    for segment in topology["segments"]:
        is_forward = segment["from"] == from_waypoint and segment["to"] == to_waypoint
        is_reverse = segment["from"] == to_waypoint and segment["to"] == from_waypoint
        if is_forward or is_reverse:
            return {
                "id": segment["id"],
                "from": from_waypoint,
                "to": to_waypoint,
                "candidate_servers": segment["candidate_servers"],
            }
    raise HTTPException(
        status_code=400, detail=f"No segment between {from_waypoint} and {to_waypoint}"
    )


def normalize_server_status(payload: ServerHealthPayload) -> Literal["up", "down"]:
    if payload.status is not None:
        # 2. status normalize
        status = payload.status.lower().strip()
        if status in {"up", "down"}:
            return status
        raise HTTPException(status_code=400, detail="status must be 'up' or 'down'")

    if payload.availability is None:
        raise HTTPException(
            status_code=422, detail="Either status or availability must be provided."
        )
    return "up" if payload.availability > 0 else "down"


def score_qos(qos: dict[str, float]) -> float:
    response_time = qos.get("response_time_ms", qos.get("latency_ms", 100.0))
    throughput = qos.get("throughput_mbps", qos.get("bandwidth_mbps", 0.0))
    response_time_score = max(0.0, 1.0 - response_time / 100.0)
    throughput_score = min(1.0, throughput / 100.0)
    return round(response_time_score * 0.5 + throughput_score * 0.5, 4)


def build_ranking(
    topology: dict[str, Any],
    segment_id: str,
    candidate_servers: list[str],
    down_servers: set[str],
) -> list[RankingItem]:
    ranking: list[RankingItem] = []
    segment_qos = topology.get("segment_qos", {}).get(segment_id, {})
    for server_id in candidate_servers:
        qos = segment_qos.get(server_id)
        if qos is None:
            raise HTTPException(
                status_code=500, detail=f"Missing QoS for {segment_id}/{server_id}"
            )
        status: Literal["active", "down"] = (
            "down" if server_id in down_servers else "active"
        )
        ranking.append(
            RankingItem(
                server_id=server_id,
                status=status,
                score=-1.0 if status == "down" else score_qos(qos),
                qos=qos,
            )
        )
    return sorted(ranking, key=lambda item: item.score, reverse=True)


def desired_led_state(
    server_id: str, monitor_state: MonitorStateResponse
) -> Literal["on", "idle", "off"]:
    if server_id in monitor_state.down_servers:
        return "off"

    # Drive the LED from the route-relative recommendation this app computes.
    if monitor_state.recommended_server == server_id:
        return "on"

    return "idle"


def sync_edge_led_status(
    server_id: str, led_state: Literal["on", "idle", "off"]
) -> None:
    base_url = EDGE_STATUS_BASE_URLS.get(server_id)
    if base_url is None:
        logger.warning("No Pi endpoint configured for %s", server_id)
        return

    endpoint = f"{base_url}/status/{led_state}"
    try:
        with urlopen(endpoint, timeout=LED_SYNC_TIMEOUT_SECONDS) as response:
            response.read()
    except Exception as exc:
        logger.warning(
            "Failed to sync %s to %s via %s: %s", server_id, led_state, endpoint, exc
        )


def sync_edge_led_statuses(
    topology: dict[str, Any], monitor_state: MonitorStateResponse
) -> None:
    for server in topology["edge_servers"]:
        server_id = server["id"]
        sync_edge_led_status(server_id, desired_led_state(server_id, monitor_state))


# 테스트용 (route_index 자동 증가)
async def mock_loop() -> None:
    while True:
        await asyncio.sleep(MOCK_INTERVAL_SECONDS)
        if state.mock_enabled:
            state.advance_mock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(mock_loop())
    try:
        state.build_and_sync_state(source="startup")
        yield
    finally:
        task.cancel()


state = MonitorState()
app = FastAPI(
    title="TurtleBot Server Selection Monitor", version="1.0.0", lifespan=lifespan
)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return render_html()


@app.get("/topology_overlay.html", response_class=HTMLResponse)
def dashboard() -> str:
    return render_html()


@app.get("/background.png")
def background() -> Response:
    return Response((BASE_DIR / BACKGROUND_IMAGE).read_bytes(), media_type="image/png")


@app.get("/edge_icon.png")
def edge_icon() -> Response:
    return Response((BASE_DIR / EDGE_ICON_IMAGE).read_bytes(), media_type="image/png")


@app.get("/warning_icon.png")
def warning_icon() -> Response:
    return Response(
        (BASE_DIR / WARNING_ICON_IMAGE).read_bytes(), media_type="image/png"
    )


@app.get("/api/v1/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return HealthResponse(status="ok", timestamp=now_iso())


@app.get("/api/v1/topology")
def get_topology_v1() -> dict[str, Any]:
    return state.topology


@app.post("/api/v1/topology/reload", response_model=StatusResponse)
def reload_topology_v1() -> StatusResponse:
    state.reload_topology()
    state.build_and_sync_state(source="topology-reload")
    return StatusResponse(status="ok")


@app.get("/api/v1/state", response_model=MonitorStateResponse)
def get_state_v1() -> MonitorStateResponse:
    return state.build_state()


@app.post("/api/v1/mock/advance", response_model=MonitorStateResponse)
def mock_advance_v1() -> MonitorStateResponse:
    return state.advance_mock()


@app.post("/api/v1/mock", response_model=MockModeResponse)
def set_mock_mode_v1(payload: MockControlPayload) -> MockModeResponse:
    state.mock_enabled = payload.enabled
    state.build_and_sync_state(source="mock-toggle")
    return MockModeResponse(mock_enabled=state.mock_enabled)


@app.post("/api/v1/telemetry", response_model=MonitorStateResponse)
def post_telemetry_v1(payload: TelemetryPayload) -> MonitorStateResponse:
    return state.apply_telemetry(payload)


@app.post("/api/v1/server-health", response_model=MonitorStateResponse)
def post_server_health_v1(payload: ServerHealthPayload) -> MonitorStateResponse:
    return state.apply_server_health(payload)


@app.get("/api/topology")
def get_topology() -> dict[str, Any]:
    return get_topology_v1()


@app.post("/api/topology/reload", response_model=StatusResponse)
def reload_topology() -> StatusResponse:
    return reload_topology_v1()


@app.get("/api/state", response_model=MonitorStateResponse)
def get_state() -> MonitorStateResponse:
    return get_state_v1()


@app.post("/api/mock/advance", response_model=MonitorStateResponse)
def mock_advance() -> MonitorStateResponse:
    return mock_advance_v1()


@app.post("/api/mock", response_model=MockModeResponse)
def set_mock_mode(payload: MockControlPayload) -> MockModeResponse:
    return set_mock_mode_v1(payload)


# 터틀봇 현재 웨이포인트 수신
@app.post("/api/telemetry", response_model=MonitorStateResponse)
def post_telemetry(payload: TelemetryPayload) -> MonitorStateResponse:
    return post_telemetry_v1(payload)


# 라즈베리파이 서버 다운 상태 수신
@app.post("/api/server-health", response_model=MonitorStateResponse)
def post_server_health(payload: ServerHealthPayload) -> MonitorStateResponse:
    return post_server_health_v1(payload)
