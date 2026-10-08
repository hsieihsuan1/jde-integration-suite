"""Local web server for the IoT demo: serves the map page and proxies meter updates to the Orchestrator.

Credentials stay on the server; the browser never sees them.
Run:  python -m iot_demo.server            (uses the mock unless JDE_BASE_URL is set)
"""
from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from jde_suite import mock_jde
from jde_suite.client import OrchestratorClient, OrchestratorError
from jde_suite.config import Config, load_config

STATIC = Path(__file__).resolve().parent / "static"
EQUIPMENT = "30"
INITIAL = {"fuelReading": 3.0, "hourReading": 3.0}


def make_handler(client: OrchestratorClient, config: Config, mock: bool):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(STATIC), **kw)

        def _json(self, body: dict, status: int = 200) -> None:
            raw = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if self.path == "/api/config":
                return self._json({"equipmentNumber": EQUIPMENT, "orchestrator": config.meter_orchestrator,
                                   "mock": mock, "initialTelemetry": INITIAL})
            return super().do_GET()

        def do_POST(self):
            if self.path != "/api/update-meter-readings":
                return self.send_error(HTTPStatus.NOT_FOUND)
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0") or 0)) or b"{}")
                fuel, hours = float(body["fuelReading"]), float(body["hourReading"])
            except (ValueError, KeyError, TypeError):
                return self._json({"error": "Expected JSON with numeric fuelReading and hourReading"}, 400)
            equipment = str(body.get("equipmentNumber") or EQUIPMENT)
            try:
                result = client.update_meters(equipment, fuel, hours)
            except OrchestratorError as exc:
                return self._json({"error": str(exc)}, 502)
            self._json({"ok": True, "requestPayload": {"EquipmentNumber": equipment,
                        "NewFuelMeterReading": round(fuel, 2), "NewHourMeterReading": round(hours, 2)},
                        "orchestratorResponse": result})

        def log_message(self, fmt, *args):
            print("[iot-demo]", fmt % args)

    return Handler


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8787)
    args = ap.parse_args()
    config = load_config()
    mock = config.use_mock
    base = ""
    if mock:
        _, base = mock_jde.start()
        config = Config(**{**config.__dict__, "user": config.user or "demo", "password": config.password or "demo"})
        print("No JDE_BASE_URL set: using the built-in mock Orchestrator.")
    client = OrchestratorClient(config, base)
    srv = ThreadingHTTPServer((args.host, args.port), make_handler(client, config, mock))
    print(f"IoT demo on http://{args.host}:{args.port}")
    srv.serve_forever()


if __name__ == "__main__":
    main()
