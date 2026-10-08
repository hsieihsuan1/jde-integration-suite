"""Synthetic stand-in for a JDE Orchestrator server. All data below is made up.

Run alone:  python -m jde_suite.mock_jde   (default 127.0.0.1:8790)
"""
from __future__ import annotations

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# (branch_plant, item) -> rows of (location, lot, on_hand, hard, soft, inbound, outbound, backordered, description)
STOCK = {
    ("550", "LS501"): [
        ("A-01-01", "L2026-001", 120, 20, 10, 0, 5, 0, "Hydraulic filter"),
        ("A-01-02", "L2026-002", 45, 0, 0, 60, 0, 0, "Hydraulic filter"),
        ("B-02-01", "", 0, 0, 0, 0, 0, 12, "Hydraulic filter"),
    ],
    ("550", "LS503"): [("A-03-01", "L2026-010", 8, 8, 0, 0, 0, 0, "Brake pad set")],
    ("560", "GT41021"): [("C-01-01", "L2026-100", 300, 50, 25, 100, 40, 0, "Fuel injector")],
}
METER_LOG = []  # last meter updates, handy for tests


def stock_response(item: str, plant: str) -> dict:
    rows = []
    for loc, lot, oh, hard, soft, inb, outb, back, desc in STOCK.get((plant, item), []):
        rows.append({
            "F4100_MCU": plant, "F41021_LOCN": loc, "F41021_LOTN": lot, "F4101_DSC1": desc,
            "F41021_LOTS": "", "F41021_PBIN": "P",
            "F41021_PQOH": str(oh), "F41021_HCOM": str(hard), "F41021_PCOM": str(soft),
            "F41021_QTRI": str(inb), "F41021_QTRO": str(outb), "F41021_PBCK": str(back),
        })
    return {"ServiceRequest1": {"fs_DATABROWSE_V4101E": {
        "title": "Item Availability (mock)", "data": {"gridData": {"rowset": rows}}}}, "jde__status": "SUCCESS"}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: dict) -> None:
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self) -> None:
        if not self.headers.get("Authorization", "").startswith("Basic "):
            return self._send(403, {"message": "Authorization Failure"})
        length = int(self.headers.get("Content-Length", "0") or 0)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._send(400, {"message": "Bad Request - Invalid Input"})
        name = self.path.rstrip("/").rsplit("/", 1)[-1]
        if name == "Stock_Item_Availability":
            return self._send(200, stock_response(
                str(payload.get("2nd Item Number", "")).upper(), str(payload.get("Business Unit", ""))))
        if name == "JDE_ORCH_Sample_UpdateMeterReadings":
            METER_LOG.append(payload)
            return self._send(200, {"jde__status": "SUCCESS", "EquipmentNumber": payload.get("EquipmentNumber"),
                                    "echo": payload})
        self._send(404, {"message": f"Unknown orchestrator {name}"})

    def log_message(self, fmt, *args):  # quiet
        pass


def start(host: str = "127.0.0.1", port: int = 0):
    """Start in a background thread. Returns (server, base_url). port=0 picks a free port."""
    server = ThreadingHTTPServer((host, port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://{host}:{server.server_address[1]}/jderest/v3/orchestrator"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8790)
    args = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Mock JDE Orchestrator on http://127.0.0.1:{args.port}/jderest/v3/orchestrator")
    srv.serve_forever()
