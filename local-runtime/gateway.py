from __future__ import annotations

import asyncio
import os
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

import httpx
import websockets
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse

CORE_URL = os.environ.get("URBANSHIELD_CORE_URL", "http://127.0.0.1:8080")
SIMULATION_URL = os.environ.get("URBANSHIELD_SIMULATION_URL", "http://127.0.0.1:8002")
AI_URL = os.environ.get("URBANSHIELD_AI_URL", "http://127.0.0.1:8010")
SIMULATION_WS_URL = os.environ.get("URBANSHIELD_SIMULATION_WS_URL", "ws://127.0.0.1:8002/api/simulation/ws/progress")
DEFAULT_ALLOWED_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "URBANSHIELD_ALLOWED_ORIGINS",
        os.environ.get("URBANSHIELD_ALLOWED_ORIGIN", DEFAULT_ALLOWED_ORIGINS),
    ).split(",")
    if origin.strip()
]
MAX_BODY_BYTES = int(os.environ.get("URBANSHIELD_GATEWAY_MAX_BODY_BYTES", "1048576"))
UPSTREAM_TIMEOUT_SECONDS = float(os.environ.get("URBANSHIELD_GATEWAY_UPSTREAM_TIMEOUT", "30"))
RATE_WINDOW_SECONDS = int(os.environ.get("URBANSHIELD_GATEWAY_RATE_WINDOW_SECONDS", "60"))
DEFAULT_RATE_LIMIT = int(os.environ.get("URBANSHIELD_GATEWAY_RATE_LIMIT", "240"))
SIMULATION_RATE_LIMIT = int(os.environ.get("URBANSHIELD_GATEWAY_SIMULATION_RATE_LIMIT", "20"))


@dataclass
class GatewayMetrics:
    started_at: float
    requests_total: int
    errors_total: int
    upstream_failures_total: int
    rate_limited_total: int
    request_durations: dict[str, list[float]]
    status_counts: dict[str, int]
    rate_windows: dict[str, deque[float]]

    def record(self, route: str, status: int, duration_ms: float) -> None:
        self.requests_total += 1
        if status >= 400:
            self.errors_total += 1
        self.status_counts[f"{route}:{status}"] += 1
        values = self.request_durations[route]
        values.append(duration_ms)
        if len(values) > 200:
            del values[:100]

    def record_upstream_failure(self) -> None:
        self.upstream_failures_total += 1

    def allow(self, key: str, limit: int) -> bool:
        now = time.time()
        bucket = self.rate_windows[key]
        while bucket and now - bucket[0] > RATE_WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= limit:
            self.rate_limited_total += 1
            return False
        bucket.append(now)
        return True

    def snapshot(self) -> dict[str, Any]:
        route_latency = {}
        for route, values in self.request_durations.items():
            if values:
                route_latency[route] = {
                    "count": len(values),
                    "average_ms": round(sum(values) / len(values), 2),
                    "max_ms": round(max(values), 2),
                }
        return {
            "uptime_seconds": round(time.time() - self.started_at, 2),
            "requests_total": self.requests_total,
            "errors_total": self.errors_total,
            "upstream_failures_total": self.upstream_failures_total,
            "rate_limited_total": self.rate_limited_total,
            "status_counts": dict(self.status_counts),
            "route_latency": route_latency,
        }


METRICS = GatewayMetrics(
    started_at=time.time(),
    requests_total=0,
    errors_total=0,
    upstream_failures_total=0,
    rate_limited_total=0,
    request_durations=defaultdict(list),
    status_counts=defaultdict(int),
    rate_windows=defaultdict(deque),
)

app = FastAPI(title="UrbanShield Local Gateway", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Correlation-ID"],
    expose_headers=["X-Correlation-ID"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    return response


def elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


def route_target(path: str) -> tuple[str, str, str] | None:
    canonical = [
        ("/api/v1/auth", CORE_URL, "/api/core/auth"),
        ("/api/v1/incidents", CORE_URL, "/api/core/incidents"),
        ("/api/v1/vehicles", CORE_URL, "/api/core/vehicles"),
        ("/api/v1/dispatch/recommend", CORE_URL, "/api/core/dispatch/recommend"),
        ("/api/v1/dispatches", CORE_URL, "/api/core/dispatches"),
        ("/api/v1/dispatch", CORE_URL, "/api/core/dispatch"),
        ("/api/v1/environment", CORE_URL, "/api/core/environment"),
        ("/api/v1/audit", CORE_URL, "/api/core/audit"),
        ("/api/v1/outbox", CORE_URL, "/api/core/outbox"),
        ("/api/v1/simulations", CORE_URL, "/api/core/simulations"),
        ("/api/v1/ai", AI_URL, "/api/ai"),
        ("/api/v1/system/core-health", CORE_URL, "/api/core/health"),
        ("/api/v1/system/metrics", CORE_URL, "/api/core/metrics"),
    ]
    for prefix, base_url, target_prefix in canonical:
        if path == prefix or path.startswith(f"{prefix}/"):
            return prefix, base_url, target_prefix + path[len(prefix):]
    legacy = [
        ("/core", CORE_URL),
        ("/simulation", SIMULATION_URL),
        ("/ai", AI_URL),
    ]
    for prefix, base_url in legacy:
        if path == prefix or path.startswith(f"{prefix}/"):
            return prefix, base_url, path[len(prefix):] or "/"
    return None


def response_headers(correlation_id: str) -> dict[str, str]:
    return {"X-Correlation-ID": correlation_id}


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"service": "gateway", "status": "UP", "metrics": METRICS.snapshot()}


async def service_probe(name: str, base_url: str, path: str) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(f"{base_url}{path}")
        return {"status": "UP" if response.status_code < 500 else "DEGRADED", "http_status": response.status_code, "response_time_ms": elapsed_ms(started)}
    except Exception as error:
        return {"status": "DOWN", "error": str(error), "response_time_ms": elapsed_ms(started)}


@app.get("/health/services")
@app.get("/api/v1/system/health")
async def service_health() -> dict[str, Any]:
    services = {
        "core-api": await service_probe("core-api", CORE_URL, "/api/core/health"),
        "simulation-service": await service_probe("simulation-service", SIMULATION_URL, "/api/simulation/health"),
        "ai-service": await service_probe("ai-service", AI_URL, "/api/ai/health"),
    }
    overall = "UP" if all(item["status"] == "UP" for item in services.values()) else "DEGRADED"
    return {"service": "gateway", "status": overall, "services": services}


@app.get("/metrics")
async def metrics() -> PlainTextResponse:
    snapshot = METRICS.snapshot()
    lines = [
        "# HELP urbanshield_gateway_requests_total Total gateway requests.",
        "# TYPE urbanshield_gateway_requests_total counter",
        f"urbanshield_gateway_requests_total {snapshot['requests_total']}",
        "# HELP urbanshield_gateway_errors_total Total gateway responses with status >= 400.",
        "# TYPE urbanshield_gateway_errors_total counter",
        f"urbanshield_gateway_errors_total {snapshot['errors_total']}",
        "# HELP urbanshield_gateway_upstream_failures_total Total upstream connection failures.",
        "# TYPE urbanshield_gateway_upstream_failures_total counter",
        f"urbanshield_gateway_upstream_failures_total {snapshot['upstream_failures_total']}",
        "# HELP urbanshield_gateway_rate_limited_total Total rate-limited requests.",
        "# TYPE urbanshield_gateway_rate_limited_total counter",
        f"urbanshield_gateway_rate_limited_total {snapshot['rate_limited_total']}",
    ]
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


@app.websocket("/api/v1/simulations/progress")
@app.websocket("/simulation/api/simulation/ws/progress")
async def websocket_proxy(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        async with websockets.connect(SIMULATION_WS_URL) as upstream:
            async def client_to_upstream() -> None:
                while True:
                    message = await websocket.receive_text()
                    await upstream.send(message)

            async def upstream_to_client() -> None:
                async for message in upstream:
                    await websocket.send_text(message)

            await asyncio.gather(client_to_upstream(), upstream_to_client())
    except WebSocketDisconnect:
        return
    except Exception:
        try:
            await websocket.close(code=1011)
        except RuntimeError:
            return


async def proxy_stream(
    method: str,
    target_url: str,
    body: bytes,
    headers: dict[str, str],
    correlation_id: str,
):
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(method, target_url, content=body if body else None, headers=headers) as upstream:
            async for chunk in upstream.aiter_bytes():
                yield chunk


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy(path: str, request: Request) -> Response:
    started = time.perf_counter()
    full_path = "/" + path
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    target = route_target(full_path)
    if target is None:
        METRICS.record("unmatched", 404, elapsed_ms(started))
        return JSONResponse({"error": "No local route", "correlation_id": correlation_id}, status_code=404, headers=response_headers(correlation_id))

    route_name, base_url, upstream_path = target
    client = request.client.host if request.client else "unknown"
    limit = SIMULATION_RATE_LIMIT if request.method == "POST" and full_path in {"/api/v1/simulations/run", "/simulation/api/simulation/run"} else DEFAULT_RATE_LIMIT
    if not METRICS.allow(f"{client}:{route_name}:{request.method}", limit):
        METRICS.record(route_name, 429, elapsed_ms(started))
        return JSONResponse({"error": "Rate limit exceeded", "correlation_id": correlation_id}, status_code=429, headers=response_headers(correlation_id))

    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        METRICS.record(route_name, 413, elapsed_ms(started))
        return JSONResponse({"error": "Request body too large", "correlation_id": correlation_id}, status_code=413, headers=response_headers(correlation_id))

    query = request.url.query
    target_url = f"{base_url}{upstream_path}{('?' + query) if query else ''}"
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", "content-length", "connection"}
    }
    headers["X-Correlation-ID"] = correlation_id

    is_stream = "text/event-stream" in request.headers.get("accept", "") or upstream_path.endswith("/events")
    if is_stream:
        METRICS.record(route_name, 200, elapsed_ms(started))
        return StreamingResponse(
            proxy_stream(request.method, target_url, body, headers, correlation_id),
            media_type="text/event-stream",
            headers=response_headers(correlation_id),
        )

    try:
        async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT_SECONDS) as client_session:
            upstream = await client_session.request(request.method, target_url, content=body if body else None, headers=headers)
    except httpx.RequestError as error:
        METRICS.record_upstream_failure()
        METRICS.record(route_name, 502, elapsed_ms(started))
        return JSONResponse(
            {"error": "Bad Gateway", "message": str(error), "correlation_id": correlation_id},
            status_code=502,
            headers=response_headers(correlation_id),
        )

    response = Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type"),
        headers=response_headers(correlation_id),
    )
    for key, value in upstream.headers.items():
        if key.lower() not in {"transfer-encoding", "connection", "content-encoding", "server", "content-length"}:
            response.headers[key] = value
    METRICS.record(route_name, upstream.status_code, elapsed_ms(started))
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
