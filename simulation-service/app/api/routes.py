import asyncio
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from app.models.health import HealthResponse
from app.models.simulation import (
    ImpactAreaRequest,
    ImpactAreaResponse,
    RouteRequest,
    RouteResponse,
    SimulationRequest,
    SimulationResponse,
)
from app.services.simulation_service import (
    calculate_impact_area,
    calculate_route,
    get_scenario,
    list_scenarios,
    run_simulation,
)

router = APIRouter()


@router.get("/api/simulation/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(service="simulation-service", status="UP")


@router.post("/api/simulation/run", response_model=SimulationResponse)
def simulate(request: SimulationRequest) -> SimulationResponse:
    return run_simulation(request)


@router.get("/api/simulation/scenarios", response_model=list[SimulationResponse])
def scenarios() -> list[SimulationResponse]:
    return list_scenarios()


@router.get("/api/simulation/scenarios/{simulation_id}", response_model=SimulationResponse)
def scenario(simulation_id: str) -> SimulationResponse:
    result = get_scenario(simulation_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return result


@router.post("/api/simulation/route", response_model=RouteResponse)
def route(request: RouteRequest) -> RouteResponse:
    return calculate_route(request)


@router.post("/api/simulation/impact-area", response_model=ImpactAreaResponse)
def impact_area(request: ImpactAreaRequest) -> ImpactAreaResponse:
    return calculate_impact_area(request)


@router.websocket("/api/simulation/ws/progress")
async def simulation_progress(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            await websocket.receive_text()
            for status in ["QUEUED", "VALIDATING", "CALCULATING_ROUTE", "CALCULATING_IMPACT", "FINALIZING", "COMPLETED"]:
                await websocket.send_json({"status": status})
                await asyncio.sleep(0.15)
    except WebSocketDisconnect:
        return
