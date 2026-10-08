"""Minimal JD Edwards Orchestrator client (stdlib only)."""
from __future__ import annotations

import base64
import json
import ssl
import urllib.request
from typing import Any, Dict

from .config import Config


class OrchestratorError(RuntimeError):
    pass


class OrchestratorClient:
    def __init__(self, config: Config, base_url_override: str = "") -> None:
        self.config = config
        self.base_url = (base_url_override or config.base_url).rstrip("/")
        if not self.base_url:
            raise OrchestratorError("No Orchestrator URL. Set JDE_BASE_URL or start the mock server.")

    def call(self, orchestrator: str, payload: Dict[str, Any], device: str = "JDE-SUITE", timeout: int = 30) -> Dict[str, Any]:
        url = f"{self.base_url}/{orchestrator}"
        auth = base64.b64encode(f"{self.config.user}:{self.config.password}".encode()).decode()
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            method="POST",
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "jde-AIS-Auth-Device": device,
            },
        )
        ctx = ssl.create_default_context()
        if not self.config.verify_ssl:
            ctx = ssl._create_unverified_context()
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
                raw = resp.read().decode()
        except Exception as exc:  # network, HTTP, TLS
            raise OrchestratorError(f"Orchestrator call failed: {exc}") from exc
        try:
            return json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise OrchestratorError("Orchestrator returned invalid JSON") from exc

    def item_availability(self, item: str, branch_plant: str) -> Dict[str, Any]:
        return self.call(
            self.config.stock_orchestrator,
            {"Business Unit": branch_plant, "2nd Item Number": item},
            device="STOCK-BOT",
        )

    def update_meters(self, equipment: str, fuel: float, hours: float) -> Dict[str, Any]:
        return self.call(
            self.config.meter_orchestrator,
            {
                "EquipmentNumber": str(equipment),
                "NewFuelMeterReading": round(float(fuel), 2),
                "NewHourMeterReading": round(float(hours), 2),
            },
            device="IOT-DEMO",
        )
