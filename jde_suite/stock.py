"""Turn the raw Item Availability form response into totals and a readable reply."""
from __future__ import annotations

from typing import Any, Dict

FORM_KEY = "fs_DATABROWSE_V4101E"


def parse_number(value: Any) -> float:
    text = str(value if value not in (None, "") else "0").strip().replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def normalize_response(response: Dict[str, Any], item: str) -> Dict[str, Any]:
    form = (response.get("ServiceRequest1") or {}).get(FORM_KEY)
    if not form:
        raise ValueError(f"Response has no {FORM_KEY} block")
    rowset = (((form.get("data") or {}).get("gridData")) or {}).get("rowset") or []
    fields = {
        "on_hand": "F41021_PQOH", "hard": "F41021_HCOM", "soft": "F41021_PCOM",
        "inbound": "F41021_QTRI", "outbound": "F41021_QTRO", "backordered": "F41021_PBCK",
    }
    totals = {k: 0.0 for k in fields}
    locations: Dict[str, Dict[str, Any]] = {}
    for row in rowset:
        loc = str(row.get("F41021_LOCN") or "").strip() or "NO LOCATION"
        plant = str(row.get("F4100_MCU") or "").strip()
        bucket = locations.setdefault(
            f"{plant}|{loc}",
            {"branch_plant": plant, "location": loc, "description": str(row.get("F4101_DSC1") or "").strip(),
             "on_hand": 0.0, "lots": []},
        )
        vals = {k: parse_number(row.get(col)) for k, col in fields.items()}
        for k, v in vals.items():
            totals[k] += v
        bucket["on_hand"] += vals["on_hand"]
        lot = str(row.get("F41021_LOTN") or "").strip()
        if lot or vals["on_hand"]:
            bucket["lots"].append({"lot": lot or "(no lot)", "on_hand": vals["on_hand"]})
    rows = sorted(locations.values(), key=lambda r: (-r["on_hand"], r["location"]))
    available = totals["on_hand"] - totals["hard"] - totals["soft"] - totals["outbound"] + totals["inbound"]
    return {"item": item, "title": form.get("title") or "Item Availability", "rows": rows,
            "detail_lines": len(rowset), "totals": totals, "available": available}


def format_reply(item: str, branch_plant: str, stock: Dict[str, Any]) -> str:
    t = stock["totals"]
    if stock["detail_lines"] == 0:
        return f"No stock records for item {item} in branch/plant {branch_plant}."
    state = "has physical stock" if t["on_hand"] > 0 else "has no physical stock"
    lines = [
        f"Item {item} in branch/plant {branch_plant} {state}.",
        f"On hand: {t['on_hand']:.2f}",
        f"Estimated available: {stock['available']:.2f}  (on hand - hard - soft - outbound + inbound)",
        f"Hard committed: {t['hard']:.2f} | Soft committed: {t['soft']:.2f}",
        f"Inbound: {t['inbound']:.2f} | Outbound: {t['outbound']:.2f} | Backordered: {t['backordered']:.2f}",
    ]
    detail = [(r["location"], l["lot"], l["on_hand"]) for r in stock["rows"] for l in r["lots"] if l["on_hand"] > 0]
    if detail:
        lines.append("")
        lines.append(f"{'Location':<12}{'Lot':<14}{'On hand':>10}")
        for loc, lot, qty in detail:
            lines.append(f"{loc:<12}{lot:<14}{qty:>10.2f}")
    return "\n".join(lines)
