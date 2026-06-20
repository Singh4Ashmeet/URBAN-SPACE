import assert from "node:assert/strict";
import test from "node:test";
import { renderToStaticMarkup } from "react-dom/server";
import { StatusCard } from "../components/StatusCard";
import { defaultScenario } from "../components/scenario/ScenarioBuilder";

test("StatusCard renders service state", () => {
  const markup = renderToStaticMarkup(
    <StatusCard
      title="Core Service"
      description="Incident API"
      health={{ state: "up", service: "core-api", message: "Healthy" }}
    />
  );

  assert.match(markup, /Core Service/);
  assert.match(markup, /Healthy/);
});

test("default scenario is valid", () => {
  const scenario = defaultScenario();

  assert.equal(scenario.scenario_name.length > 0, true);
  assert.equal(scenario.severity >= 1 && scenario.severity <= 5, true);
  assert.equal(scenario.latitude >= -90 && scenario.latitude <= 90, true);
  assert.equal(scenario.longitude >= -180 && scenario.longitude <= 180, true);
});
