from __future__ import annotations

import json
import subprocess
import sys
import time
import unittest
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]


class GatewayIntegrationTest(unittest.TestCase):
    token: str

    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, "start.py"], cwd=ROOT, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        time.sleep(1)
        login = Request(
            "http://localhost:8000/api/v1/auth/login",
            data=json.dumps({"username": "operator", "password": "UrbanShield123!"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(login, timeout=5) as response:
            cls.token = json.loads(response.read().decode("utf-8"))["accessToken"]

    @classmethod
    def tearDownClass(cls) -> None:
        subprocess.run([sys.executable, "start.py", "--stop"], cwd=ROOT, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    def read_json(self, path: str, auth: bool = False) -> dict:
        headers = {"Authorization": f"Bearer {self.token}"} if auth else {}
        with urlopen(Request(f"http://localhost:8000{path}", headers=headers), timeout=5) as response:
            self.assertEqual(response.status, 200)
            return json.loads(response.read().decode("utf-8"))

    def test_gateway_health(self) -> None:
        payload = self.read_json("/health")
        self.assertEqual(payload["service"], "gateway")
        self.assertEqual(payload["status"], "UP")

    def test_gateway_services_health(self) -> None:
        payload = self.read_json("/health/services")
        self.assertIn(payload["status"], {"UP", "DEGRADED"})
        self.assertIn("core-api", payload["services"])
        self.assertIn("simulation-service", payload["services"])
        self.assertIn("ai-service", payload["services"])

    def test_correlation_id_is_propagated(self) -> None:
        request = Request("http://localhost:8000/core/api/core/health", headers={"X-Correlation-ID": "test-correlation"})
        with urlopen(request, timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get("X-Correlation-ID"), "test-correlation")

    def test_metrics_endpoint(self) -> None:
        with urlopen("http://localhost:8000/metrics", timeout=5) as response:
            self.assertEqual(response.status, 200)
            body = response.read().decode("utf-8")
            self.assertIn("urbanshield_gateway_requests_total", body)

    def test_canonical_auth_and_incidents(self) -> None:
        me = self.read_json("/api/v1/auth/me", auth=True)
        self.assertEqual(me["role"], "OPERATOR")
        incidents = self.read_json("/api/v1/incidents", auth=True)
        self.assertGreaterEqual(incidents["totalElements"], 1)

    def test_ai_fallback_through_gateway(self) -> None:
        health = self.read_json("/api/v1/ai/health", auth=True)
        self.assertTrue(health["fallbackAvailable"])


if __name__ == "__main__":
    unittest.main()