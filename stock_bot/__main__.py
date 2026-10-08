"""Stock lookup from the command line.

  python -m stock_bot "do we have LS501 in branch 550?"
  python -m stock_bot            # interactive prompt

Uses the mock Orchestrator unless JDE_BASE_URL is set. Channel adapters (Telegram, WhatsApp)
are not included; handle_message() is the single entry point an adapter would call.
"""
from __future__ import annotations

import sys

from jde_suite import mock_jde
from jde_suite.client import OrchestratorClient, OrchestratorError
from jde_suite.config import Config, load_config
from jde_suite.query_parser import parse_query
from jde_suite.stock import format_reply, normalize_response


def handle_message(text: str, client: OrchestratorClient, default_branch: str) -> str:
    parsed = parse_query(text, default_branch)
    if parsed["needs_item"]:
        return "Which item? Example: LS501 in branch 550."
    item, plant = str(parsed["item"]), str(parsed["branch_plant"])
    try:
        raw = client.item_availability(item, plant)
        return format_reply(item, plant, normalize_response(raw, item))
    except (OrchestratorError, ValueError) as exc:
        return f"Lookup failed: {exc}"


def build_client():
    config = load_config()
    base = ""
    if config.use_mock:
        _, base = mock_jde.start()
        config = Config(**{**config.__dict__, "user": config.user or "demo", "password": config.password or "demo"})
    return OrchestratorClient(config, base), config


def main(argv=None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    client, config = build_client()
    if argv:
        print(handle_message(" ".join(argv), client, config.default_branch_plant))
        return
    print("Ask about stock (Ctrl-D to quit). Try: LS501 in branch 550")
    for line in sys.stdin:
        if line.strip():
            print(handle_message(line, client, config.default_branch_plant), "\n")


if __name__ == "__main__":
    main()
