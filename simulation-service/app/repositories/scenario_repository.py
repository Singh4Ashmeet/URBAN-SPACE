from collections import OrderedDict

from app.models.simulation import SimulationResponse


class ScenarioRepository:
    def __init__(self) -> None:
        self._items: OrderedDict[str, SimulationResponse] = OrderedDict()

    def save(self, result: SimulationResponse) -> SimulationResponse:
        self._items[result.simulation_id] = result
        while len(self._items) > 50:
            self._items.popitem(last=False)
        return result

    def list_recent(self) -> list[SimulationResponse]:
        return list(reversed(self._items.values()))

    def get(self, simulation_id: str) -> SimulationResponse | None:
        return self._items.get(simulation_id)


scenario_repository = ScenarioRepository()
