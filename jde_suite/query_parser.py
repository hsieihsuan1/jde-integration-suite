"""Rule-based parser for stock questions like "LS501 in branch 550".

The original project used an LLM for this step with this regex logic only as a fallback.
The LLM call is left out here to keep the demo free of API keys; see README (Limitations).
"""
from __future__ import annotations

import re
from typing import Dict

_BRANCH = re.compile(r"\b(?:BRANCH|PLANT|FILIAL|PLANTA)\s*(\d{2,5})\b|\b(?:IN|NA|NO)\s+(\d{3,5})\b")
_ITEM = re.compile(r"\b([A-Z]{1,6}-?\d{1,10})\b")
_STOPWORDS = {"BRANCH", "PLANT", "FILIAL", "PLANTA"}


def parse_query(text: str, default_branch: str = "550") -> Dict[str, object]:
    upper = text.upper()
    branch_m = _BRANCH.search(upper)
    branch = (branch_m.group(1) or branch_m.group(2)) if branch_m else default_branch
    item = ""
    for m in _ITEM.finditer(upper):
        if m.group(1) not in _STOPWORDS:
            item = m.group(1)
            break
    return {"item": item, "branch_plant": branch, "needs_item": not item}
