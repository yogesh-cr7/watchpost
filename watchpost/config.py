from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class Endpoint:
    name: str
    url: str
    method: str = "GET"
    expected_status: int = 200
    timeout: float = 5.0
    interval: int = 60  # seconds between checks - not wired up until the scheduler lands
    latency_threshold_ms: Optional[float] = None  # unset = never flag a slow check


class ConfigError(Exception):
    """anything wrong with the config file itself, not a network problem"""


def load_config(path="config.yaml"):
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"config file not found: {config_path}")

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    # covers a missing key, an empty file, and "endpoints:" with nothing under it
    if not raw or not raw.get("endpoints"):
        raise ConfigError(f"{config_path} has no 'endpoints' key - nothing to watch")

    endpoints = []
    seen_names = set()
    for i, entry in enumerate(raw["endpoints"]):
        # bail loud on a typo'd config instead of silently watching nothing
        if "url" not in entry:
            raise ConfigError(f"endpoint #{i} is missing 'url'")

        name = entry.get("name", entry["url"])
        if name in seen_names:
            raise ConfigError(f"duplicate endpoint name: {name}")
        seen_names.add(name)

        endpoints.append(Endpoint(
            name=name,
            url=entry["url"],
            method=entry.get("method", "GET"),
            expected_status=entry.get("expected_status", 200),
            timeout=entry.get("timeout", 5.0),
            interval=entry.get("interval", 60),
            latency_threshold_ms=entry.get("latency_threshold_ms"),
        ))

    return endpoints
