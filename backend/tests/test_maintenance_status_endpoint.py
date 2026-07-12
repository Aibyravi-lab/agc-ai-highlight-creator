"""AGC-084: public GET /maintenance-status.

Read-only, unauthenticated, minimal shape — {"maintenance": bool}. No
filesystem paths or operator details leak into the response.
"""

import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import observability as observability_router_module


class MaintenanceStatusEndpointTests(unittest.TestCase):

    def setUp(self):
        app = FastAPI()
        app.include_router(observability_router_module.router)
        self.client = TestClient(app)

    def test_returns_false_when_maintenance_off(self):
        with patch.object(
            observability_router_module.MaintenanceService,
            "is_maintenance_mode",
            return_value=False,
        ):
            response = self.client.get("/maintenance-status")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"maintenance": False})

    def test_returns_true_when_maintenance_on(self):
        with patch.object(
            observability_router_module.MaintenanceService,
            "is_maintenance_mode",
            return_value=True,
        ):
            response = self.client.get("/maintenance-status")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"maintenance": True})

    def test_response_shape_is_minimal(self):
        with patch.object(
            observability_router_module.MaintenanceService,
            "is_maintenance_mode",
            return_value=True,
        ):
            response = self.client.get("/maintenance-status")

        self.assertEqual(set(response.json().keys()), {"maintenance"})


if __name__ == "__main__":
    unittest.main()
