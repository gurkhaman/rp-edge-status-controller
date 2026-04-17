from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import webbrowser


TOPOLOGY_JSON = "testbed_topology.json"
OUTPUT_HTML = "topology_overlay.html"


class QuietRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


def render_html() -> str:
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TurtleBot Server Selection Monitor</title>
  <style>
    html {
      width: 100%;
      height: 100%;
      overflow: hidden;
    }
    body {
      margin: 0;
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: #101010;
      color: #f4f4f4;
      font-family: Arial, sans-serif;
    }
    .app {
      zoom: 1.5;
      display: grid;
      grid-template-columns: minmax(0, 1fr) 430px;
      width: calc(100vw / 1.5);
      height: calc(100vh / 1.5);
      overflow: hidden;
    }
    .map-pane {
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      min-width: 0;
      min-height: 0;
      background: #000;
    }
    .dashboard {
      border-left: 1px solid #d8d8d8;
      background: #fff;
      color: #151515;
      display: flex;
      flex-direction: column;
      height: 100%;
      padding: 14px 18px 12px;
      overflow: hidden;
      box-sizing: border-box;
    }
    .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      padding: 10px 14px;
      background: #202020;
      border-bottom: 1px solid #383838;
      font-size: 18px;
      font-weight: 800;
    }
    .canvas {
      min-height: 0;
      width: 100%;
      height: 100%;
    }
    svg {
      display: block;
      width: 100%;
      height: 100%;
      background: linear-gradient(rgba(0, 0, 0, 0.34), rgba(0, 0, 0, 0.34)), #000 url("/background.png") center / 100% 100% no-repeat;
    }
    h1, h2 {
      margin: 0;
      line-height: 1.2;
    }
    h1 {
      font-size: 28px;
    }
    h2 {
      margin-top: 14px;
      margin-bottom: 8px;
      font-size: 20px;
      color: #333;
    }
    .status {
      color: #9ee493;
      font-weight: 700;
    }
    .status.error {
      color: #ff8f8f;
    }
    .kv {
      display: grid;
      grid-template-columns: 120px 1fr;
      gap: 8px 10px;
      padding: 10px 0 12px;
      border-bottom: 1px solid #e4e4e4;
      font-size: 16px;
    }
    .key {
      color: #666;
    }
    .value {
      font-weight: 700;
      font-size: 18px;
    }
    .pill-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .pill {
      border: 1px solid #555;
      border-radius: 8px;
      padding: 5px 8px;
      background: #f4f4f4;
      color: #151515;
      font-size: 15px;
      font-weight: 700;
    }
    .pill.down-pill {
      border-color: #f44336;
      color: #f44336;
      background: #fff5f4;
    }
    .server-token {
      display: inline-flex;
      align-items: center;
      border: 1px solid #d0d0d0;
      border-radius: 8px;
      padding: 5px 9px;
      background: #f4f4f4;
      color: #151515;
      font-size: 15px;
      font-weight: 800;
    }
    .server-token.recommended {
      border-color: #45c84f;
      color: #45c84f;
    }
     .ranking-list {
       display: grid;
        gap: 9px;
       width: 100%;
     }
     .ranking-row {
       display: grid;
        grid-template-columns: 76px minmax(0, 1fr) 64px;
       align-items: center;
       gap: 10px;
        padding: 9px 10px;
       border: 1px solid #e2e2e2;
       border-radius: 8px;
       background: #fafafa;
       font-family: Arial, sans-serif;
        font-size: 15px;
       color: #111;
     }
    .rank-bar-track {
      height: 16px;
      background: #e9edf3;
      border-radius: 999px;
      overflow: hidden;
      display: block;
      width: 100%;
    }
    .rank-bar {
      display: block;
      height: 100%;
      border-radius: 999px;
      background: linear-gradient(90deg, #bfc5ce, #8d96a3);
    }
    .ranking-row.recommended-candidate {
      border-color: #bfe8c3;
      background: #f3fcf4;
    }
    .ranking-row.recommended-candidate .rank-bar {
      background: linear-gradient(90deg, #2f9e44, #45c84f);
    }
    .ranking-row.down {
      color: #f44336;
      border-color: #ffc9c3;
      background: #fff5f4;
    }
     .ranking-row.down .rank-bar {
       background: linear-gradient(90deg, #f44336, #ff8a80);
     }
     .full-row-key {
       grid-column: 1 / -1;
     }
    .full-row-value {
      grid-column: 1 / -1;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      font-size: 15px;
    }
    th, td {
      padding: 9px 4px;
      border-bottom: 1px solid #e4e4e4;
      text-align: right;
    }
    th:first-child, td:first-child {
      text-align: left;
    }
    th {
      color: #666;
      font-weight: 700;
    }
    .qos-note {
      margin-top: 10px;
      color: #666;
      font-size: 12px;
    }
    .dashboard > .kv:last-of-type {
      margin-bottom: 10px;
    }
    .metric-cell {
      text-align: center;
    }
    .recommended {
      color: #45c84f;
      font-weight: 700;
    }
    .down {
      color: #f44336;
      font-weight: 700;
    }
    .qos-row-recommended {
      background: #f3fcf4;
    }
    .qos-row-down {
      background: #fff5f4;
    }
    .segment {
      stroke: #00d084;
      stroke-width: 4;
      stroke-linecap: round;
      stroke-opacity: 0.48;
    }
    .segment.current {
      stroke: #3f3f3f;
      stroke-width: 4;
      stroke-opacity: 0.95;
      stroke-dasharray: 18 10;
    }
    .segment.next {
      stroke: #ffcf33;
      stroke-width: 10;
      stroke-opacity: 0.92;
      stroke-dasharray: 18 10;
    }
    .segment-label {
      fill: #002b1a;
      stroke: #fff;
      stroke-width: 3;
      paint-order: stroke;
      font-size: 14px;
      font-weight: 700;
    }
    .segment-label.active {
      stroke-width: 4;
      font-size: 22px;
    }
    .waypoint-pill {
      fill: #f5f5f5;
      stroke: #d0d0d0;
      stroke-width: 1;
      opacity: 0.95;
    }
    .waypoint-pill-text {
      fill: #111;
      font-size: 18px;
      font-weight: 800;
    }
    .waypoint {
      fill: #ffdf3d;
      stroke: #111;
      stroke-width: 4;
    }
    .robot-position {
      fill: #ffffff;
      stroke: #111;
      stroke-width: 5;
    }
    .waypoint-label {
      fill: #111;
      stroke: #fff;
      stroke-width: 3;
      paint-order: stroke;
      font-size: 14px;
      font-weight: 700;
    }
    .waypoint-label.active {
      stroke-width: 5;
      font-size: 23px;
    }
    .edge-server {
      fill: #fff;
      stroke: #111;
      stroke-width: 2;
    }
    .edge-server-toggle {
      cursor: pointer;
    }
    .edge-server-toggle.busy {
      cursor: progress;
    }
    .edge-server.recommended-server {
      stroke: #102a16;
      stroke-width: 4;
    }
    .edge-server.down-server {
      stroke: #f44336;
      stroke-width: 3;
    }
    .edge-icon {
      pointer-events: none;
    }
    .next-halo {
      fill: none;
      stroke: #45c84f;
      stroke-width: 7;
    }
    .warning-halo {
      fill: none;
      stroke: #f44336;
      stroke-width: 7;
    }
    .edge-label {
      fill: #111;
      font-size: 22px;
      font-weight: 800;
    }
    .edge-label-pill {
      fill: #f5f5f5;
      stroke: #d0d0d0;
      stroke-width: 1;
      opacity: 0.95;
    }
    .next-badge {
      fill: #45c84f;
      stroke: #45c84f;
      stroke-width: 1;
    }
    .warning-badge {
      fill: #f44336;
      stroke: #f44336;
      stroke-width: 1;
      animation: downBadgePulse 1.6s ease-in-out infinite;
    }
    .current-badge-text {
      fill: #fff;
      font-size: 21px;
      font-weight: 800;
    }
    .warning-badge-icon {
      pointer-events: none;
    }
    .coord-label {
      display: none;
    }
    @keyframes downBadgePulse {
      0%, 100% {
        fill: #f44336;
        stroke: #f44336;
      }
      50% {
        fill: #d32f2f;
        stroke: #d32f2f;
      }
    }
    @media (max-width: 980px) {
      .app {
        zoom: 1;
        grid-template-columns: 1fr;
        width: 100vw;
        height: 100vh;
      }
      .dashboard {
        border-left: 0;
        border-top: 1px solid #383838;
      }
    }
  </style>
</head>
<body>
  <main class="app">
    <section class="map-pane">
      <div class="toolbar">
        <span>QoS-Aware Edge Server Recommendation</span>
        <span id="status" class="status">waiting</span>
      </div>
      <div class="canvas">
        <svg id="overlay" viewBox="0 0 1536 1024" role="img" aria-label="Topology overlay"></svg>
      </div>
    </section>
    <aside class="dashboard">
      <h1>Server Dashboard</h1>
      <div class="kv">
        <div class="key">Destination</div><div id="waypoint" class="value">-</div>
      </div>

      <h2>Next</h2>
       <div class="kv">
         <div class="key">Segment</div><div id="next-segment" class="value">-</div>
         <div class="key">Next Server</div><div id="recommended-server">-</div>
         <div class="key">Unavailable</div><div id="down-servers" class="pill-row">-</div>
         <div class="key full-row-key">Candidates</div><div id="candidate-servers" class="full-row-value">-</div>
       </div>

       <h2>QoS Ranking</h2>
       <table>
        <thead>
          <tr>
            <th>Server</th>
            <th>Score</th>
            <th>RT (ms)</th>
            <th>TP (Mbps)</th>
          </tr>
        </thead>
        <tbody id="qos-table"></tbody>
       </table>
       <div class="qos-note">* RT: Response Time, TP: Throughput</div>
     </aside>
   </main>

  <script>
    const TOPOLOGY_SOURCE = "__TOPOLOGY_API__";
    const STATE_SOURCE = "__STATE_API__";
    const SVG_NS = "http://www.w3.org/2000/svg";
    const REFRESH_INTERVAL_MS = 1000;
    let lastStatePayload = "";
    let topology = null;
    let state = null;
    const pendingServerUpdates = new Set();

    function makeSvg(tag, attrs, text) {
      const node = document.createElementNS(SVG_NS, tag);
      for (const [key, value] of Object.entries(attrs || {})) {
        node.setAttribute(key, value);
      }
      if (text !== undefined) {
        node.textContent = text;
      }
      return node;
    }

    function addTitle(parent, text) {
      parent.appendChild(makeSvg("title", {}, text));
    }

    function setStatusMessage(message, isError = false) {
      const status = document.getElementById("status");
      status.textContent = message;
      status.classList.toggle("error", isError);
    }

    function addText(svg, text, x, y, className, anchor = "start") {
      svg.appendChild(makeSvg("text", {
        class: className,
        x,
        y,
        "text-anchor": anchor,
      }, text));
    }

    function segmentMatches(segment, target) {
      if (!segment || !target) {
        return false;
      }
      return (
        (segment.from === target.from && segment.to === target.to) ||
        (segment.from === target.to && segment.to === target.from)
      );
    }

    function pillList(values, emptyText = "-") {
      if (!values || values.length === 0) {
        return emptyText;
      }
      return values.map((value) => `<span class="pill">${displayId(value)}</span>`).join("");
    }

    function downPillList(values, emptyText = "-") {
      if (!values || values.length === 0) {
        return emptyText;
      }
      return values.map((value) => `<span class="pill down-pill">${displayId(value)}</span>`).join("");
    }

    function serverToken(value, className = "") {
      if (!value) {
        return "-";
      }
      return `<span class="server-token ${className}">${displayId(value)}</span>`;
    }

    function rankingBars(items) {
      if (!items || items.length === 0) {
        return "-";
      }
      return `<div class="ranking-list">${items.map((item) => {
        const score = item.score < 0 ? 0 : item.score;
        const width = Math.max(6, Math.min(100, score * 100));
        const rowClass = item.status === "down"
          ? "ranking-row down"
          : item.server_id === state.recommended_server
            ? "ranking-row recommended-candidate"
            : "ranking-row";
        return `<div class="${rowClass}">
          <span>${displayId(item.server_id)}</span>
          <span class="rank-bar-track"><span class="rank-bar" style="width: ${width}%"></span></span>
          <span>(${item.score < 0 ? "-" : item.score.toFixed(2)})</span>
        </div>`;
      }).join("")}</div>`;
    }

    function displayId(value) {
      const normalized = String(value || "").replace(/^WP_?/, "P_");
      return normalized.replace(/_/g, " ");
    }

    function displayWaypoint(value) {
      return displayId(value);
    }

    function displaySegment(segment) {
      return displayId(segment.id);
    }

    function rotate180(point, frame) {
      return {
        ...point,
        x: frame.width - point.x,
        y: frame.height - point.y,
      };
    }

    async function postJson(source, payload) {
      const response = await fetch(source, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(`${source}: HTTP ${response.status}`);
      }
      return response.text();
    }

    async function toggleServer(serverId) {
      if (!state || pendingServerUpdates.has(serverId)) {
        return;
      }
      const isDown = new Set(state.down_servers || []).has(serverId);
      const nextStatus = isDown ? "up" : "down";
      pendingServerUpdates.add(serverId);
      renderMap();
      setStatusMessage(`${displayId(serverId)} -> ${nextStatus}...`);
      try {
        const statePayload = await postJson("/api/v1/server-health", {
          server_id: serverId,
          status: nextStatus,
        });
        lastStatePayload = statePayload;
        state = JSON.parse(statePayload);
        renderMap();
        renderDashboard();
        setStatusMessage(`${displayId(serverId)} set ${nextStatus} at ${new Date().toLocaleTimeString()}`);
      } catch (error) {
        setStatusMessage(`toggle failed: ${error.message}`, true);
      } finally {
        pendingServerUpdates.delete(serverId);
        renderMap();
      }
    }

    function shortenLine(start, end, amount) {
      const dx = end.x - start.x;
      const dy = end.y - start.y;
      const length = Math.hypot(dx, dy);
      if (!length || length <= amount * 2) {
        return { start, end };
      }
      const ux = dx / length;
      const uy = dy / length;
      return {
        start: { ...start, x: start.x + ux * amount, y: start.y + uy * amount },
        end: { ...end, x: end.x - ux * amount, y: end.y - uy * amount },
      };
    }

    function renderMap() {
      if (!topology) {
        return;
      }
      const frame = topology.coordinate_frame;
      const svg = document.getElementById("overlay");
      svg.replaceChildren();
      svg.setAttribute("viewBox", `0 0 ${frame.width} ${frame.height}`);

      const waypoints = Object.fromEntries(
        topology.waypoints.map((waypoint) => [waypoint.id, rotate180(waypoint, frame)])
      );
      const edgeServers = topology.edge_servers.map((server) => rotate180(server, frame));

      for (const segment of topology.segments) {
        const start = waypoints[segment.from];
        const end = waypoints[segment.to];
        if (!start || !end) {
          continue;
        }
        let className = null;
        let labelClassName = "segment-label active";
        if (state && segmentMatches(segment, state.current_segment)) {
          className = "segment current";
        } else {
          continue;
        }
        const visibleLine = segment.id === "SEG_07" ? shortenLine(start, end, 36) : { start, end };
        const line = makeSvg("line", {
          class: className,
          x1: visibleLine.start.x,
          y1: visibleLine.start.y,
          x2: visibleLine.end.x,
          y2: visibleLine.end.y,
        });
        addTitle(line, `${displayId(segment.id)}: ${displayId(start.id)} -> ${displayId(end.id)} | ${segment.candidate_servers.map(displayId).join(", ")}`);
        svg.appendChild(line);
        addText(
          svg,
          displayId(segment.id),
          Math.round((start.x + end.x) / 2),
          Math.round((start.y + end.y) / 2) - 8,
          labelClassName,
          "middle",
        );
        addSegmentEndpointPills(svg, start, end, segment.id);
      }

      const recommended = state && state.recommended_server;
      const downServers = new Set((state && state.down_servers) || []);
      for (const server of edgeServers) {
        const serverGroup = makeSvg("g", {
          class: pendingServerUpdates.has(server.id) ? "edge-server-toggle busy" : "edge-server-toggle",
          role: "button",
          tabindex: "0",
          "aria-label": `${displayId(server.id)} toggle power`,
        });
        let className = "edge-server";
        if (downServers.has(server.id)) {
          className += " down-server";
        } else if (server.id === recommended) {
          className += " recommended-server";
        }
        const isDown = downServers.has(server.id);
        const isNext = server.id === recommended && !downServers.has(server.id);
        if (isDown) {
          serverGroup.appendChild(makeSvg("circle", {
            class: "warning-halo",
            cx: server.x,
            cy: server.y,
            r: 40,
          }));
        } else if (isNext) {
          serverGroup.appendChild(makeSvg("circle", {
            class: "next-halo",
            cx: server.x,
            cy: server.y,
            r: 40,
          }));
        }
        const marker = makeSvg("circle", {
          class: className,
          cx: server.x,
          cy: server.y,
          r: 34,
        });
        const nextAction = isDown ? "click to mark up" : "click to mark down";
        addTitle(marker, `${displayId(server.id)} | ${server.label || ""} | ${nextAction}`);
        serverGroup.appendChild(marker);
        serverGroup.appendChild(makeSvg("image", {
          class: "edge-icon",
          href: "/edge_icon.png",
          x: server.x - 24,
          y: server.y - 24,
          width: 48,
          height: 48,
        }));
        if (isDown) {
          serverGroup.appendChild(makeSvg("rect", {
            class: "warning-badge",
            x: server.x - 62,
            y: server.y + 40,
            width: 124,
            height: 40,
            rx: 20,
            ry: 20,
          }));
          serverGroup.appendChild(makeSvg("image", {
            class: "warning-badge-icon",
            href: "/warning_icon.png",
            x: server.x - 45,
            y: server.y + 49,
            width: 22,
            height: 22,
          }));
          addText(serverGroup, "Down", server.x + 20, server.y + 66, "current-badge-text", "middle");
        } else if (isNext) {
          serverGroup.appendChild(makeSvg("rect", {
            class: "next-badge",
            x: server.x - 48,
            y: server.y + 40,
            width: 96,
            height: 40,
            rx: 20,
            ry: 20,
          }));
          addText(serverGroup, "Next", server.x, server.y + 66, "current-badge-text", "middle");
        }
        addEdgeLabelPill(serverGroup, server);
        serverGroup.addEventListener("click", () => {
          void toggleServer(server.id);
        });
        serverGroup.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            void toggleServer(server.id);
          }
        });
        svg.appendChild(serverGroup);
      }

    }

    function waypointShortLabel(waypointId) {
      const match = String(waypointId || "").match(/(\\d+)$/);
      return match ? `C${Number(match[1])}` : displayId(waypointId);
    }

    function addWaypointPill(svg, waypoint, dx, dy) {
      const label = waypointShortLabel(waypoint.id);
      const width = Math.max(46, label.length * 14 + 20);
      const height = 30;
      const centerX = waypoint.x + dx;
      const centerY = waypoint.y + dy;
      const x = centerX - width / 2;
      const y = centerY - height / 2;
      svg.appendChild(makeSvg("rect", {
        class: "waypoint-pill",
        x,
        y,
        width,
        height,
        rx: 10,
        ry: 10,
      }));
      addText(svg, label, centerX, centerY + 6, "waypoint-pill-text", "middle");
    }

    function addSegmentEndpointPills(svg, start, end, segmentId) {
      const dx = end.x - start.x;
      const dy = end.y - start.y;
      if (Math.abs(dy) > Math.abs(dx)) {
        addWaypointPill(svg, start, 0, dy >= 0 ? -22 : 22);
        addWaypointPill(svg, end, 0, dy >= 0 ? 22 : -22);
        return;
      }
      if (segmentId === "SEG_07") {
        addWaypointPill(svg, start, -30, 0);
        addWaypointPill(svg, end, 30, 0);
        return;
      }
      if (start.id === "WP_07" || start.id === "P_07" || start.id === "Cone_05") {
        addWaypointPill(svg, start, -30, 0);
      } else {
        addWaypointPill(svg, start, dx >= 0 ? -30 : 30, 0);
      }
      if (end.id === "WP_07" || end.id === "P_07" || end.id === "Cone_05") {
        addWaypointPill(svg, end, -30, 0);
      } else {
        addWaypointPill(svg, end, dx >= 0 ? 30 : -30, 0);
      }
    }

    function addEdgeLabelPill(svg, server) {
      const label = displayId(server.id);
      const width = Math.max(92, label.length * 14 + 28);
      const height = 36;
      const x = server.x - width / 2;
      const y = server.y - 84;
      svg.appendChild(makeSvg("rect", {
        class: "edge-label-pill",
        x,
        y,
        width,
        height,
        rx: 10,
        ry: 10,
      }));
      addText(svg, label, server.x, y + 25, "edge-label", "middle");
    }

    function renderDashboard() {
      if (!state) {
        return;
      }
      const robot = state.robot || {};
      document.getElementById("waypoint").textContent =
        displayWaypoint(robot.current_destination || robot.current_waypoint) || "-";
      document.getElementById("next-segment").textContent =
        state.next_segment ? displaySegment(state.next_segment) : "-";
      document.getElementById("recommended-server").innerHTML = serverToken(state.recommended_server, "recommended");
      document.getElementById("candidate-servers").innerHTML = rankingBars(state.qos_ranking);
      document.getElementById("down-servers").innerHTML = downPillList(state.down_servers, "-");

      const rows = (state.qos_ranking || []).map((item) => {
        const qos = item.qos || {};
        const rowClass = item.status === "down"
          ? "qos-row-down"
          : item.server_id === state.recommended_server
            ? "qos-row-recommended"
            : "";
        return `<tr class="${rowClass}">
          <td>${displayId(item.server_id)}</td>
          <td>${item.score < 0 ? "-" : item.score.toFixed(3)}</td>
          <td class="metric-cell">${qos.response_time_ms ?? qos.latency_ms ?? "-"}</td>
          <td class="metric-cell">${qos.throughput_mbps ?? qos.bandwidth_mbps ?? "-"}</td>
        </tr>`;
      });
      document.getElementById("qos-table").innerHTML = rows.join("");
    }

    async function fetchText(source) {
      const response = await fetch(`${source}?t=${Date.now()}`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`${source}: HTTP ${response.status}`);
      }
      return response.text();
    }

    async function loadTopology() {
      const payload = await fetchText(TOPOLOGY_SOURCE);
      topology = JSON.parse(payload);
      renderMap();
    }

    async function refreshState() {
      try {
        const statePayload = await fetchText(STATE_SOURCE);
        if (statePayload !== lastStatePayload) {
          lastStatePayload = statePayload;
          state = JSON.parse(statePayload);
        }
        renderMap();
        renderDashboard();
        setStatusMessage(`updated ${new Date().toLocaleTimeString()}`);
      } catch (error) {
        setStatusMessage(`state load failed: ${error.message}`, true);
      }
    }

    loadTopology()
      .then(refreshState)
      .catch((error) => {
        setStatusMessage(`topology load failed: ${error.message}`, true);
      });
    setInterval(refreshState, REFRESH_INTERVAL_MS);
  </script>
</body>
</html>
"""
    return html.replace("__TOPOLOGY_API__", "/api/v1/topology").replace(
        "__STATE_API__", "/api/v1/state"
    )


def write_html() -> Path:
    output_path = Path(OUTPUT_HTML)
    output_path.write_text(render_html(), encoding="utf-8")
    return output_path.resolve()


def serve(port: int, open_browser: bool, verbose: bool) -> None:
    output_path = write_html()
    handler_cls = SimpleHTTPRequestHandler if verbose else QuietRequestHandler
    handler = partial(handler_cls, directory=str(Path.cwd()))
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    url = f"http://127.0.0.1:{server.server_port}/{OUTPUT_HTML}"
    print(f"Wrote {output_path}")
    print(f"Serving {url}")
    print(
        "The browser loads testbed_topology.json once, then advances the route index locally."
    )
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Server stopped.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write the dashboard HTML template.")
    parser.add_argument(
        "--no-open", action="store_true", help="start without opening a browser"
    )
    parser.add_argument(
        "--write-only",
        action="store_true",
        help="write the HTML file without starting the server",
    )
    parser.add_argument(
        "--port", type=int, default=8765, help="local dashboard server port"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="print every HTTP request"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = write_html()
    print(f"Wrote {output_path}")
    print(
        "Run the live dashboard with: uv run uvicorn server:app --reload --host 0.0.0.0 --port 8765"
    )


if __name__ == "__main__":
    main()
