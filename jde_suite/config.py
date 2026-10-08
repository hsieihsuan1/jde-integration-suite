"""Configuration from environment variables. No file parsing, no defaults that point at a real host."""
from __future__ import annotations

import os
from dataclasses import dataclass


def _flag(value: str, default: bool) -> bool:
    if value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    base_url: str          # Orchestrator base, e.g. https://host/jderest/v3/orchestrator ("" = use mock)
    user: str
    password: str
    verify_ssl: bool
    stock_orchestrator: str
    meter_orchestrator: str
    default_branch_plant: str

    @property
    def use_mock(self) -> bool:
        return not self.base_url


def load_config(env=None) -> Config:
    env = os.environ if env is None else env
    return Config(
        base_url=env.get("JDE_BASE_URL", "").rstrip("/"),
        user=env.get("JDE_USER", ""),
        password=env.get("JDE_PASSWORD", ""),
        verify_ssl=_flag(env.get("JDE_VERIFY_SSL", ""), True),
        stock_orchestrator=env.get("JDE_STOCK_ORCHESTRATOR", "Stock_Item_Availability"),
        meter_orchestrator=env.get("JDE_METER_ORCHESTRATOR", "JDE_ORCH_Sample_UpdateMeterReadings"),
        default_branch_plant=env.get("JDE_DEFAULT_BRANCH_PLANT", "550"),
    )
