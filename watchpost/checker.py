import time
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass
class CheckResult:
    endpoint_name: str
    url: str
    success: bool
    status_code: Optional[int]
    latency_ms: Optional[float]
    error: Optional[str] = None


def check_endpoint(endpoint, http_get=requests.get):
    """
    Hits one endpoint and reports what happened. http_get is injected so
    tests can fake the network entirely - real requests.get only shows up
    outside of tests.
    """
    start = time.monotonic()
    try:
        response = http_get(endpoint.url, timeout=endpoint.timeout)
    except requests.exceptions.Timeout:
        return CheckResult(endpoint.name, endpoint.url, False, None, None, "timed out")
    except requests.exceptions.ConnectionError:
        return CheckResult(endpoint.name, endpoint.url, False, None, None, "connection failed")
    except requests.exceptions.RequestException as e:
        return CheckResult(endpoint.name, endpoint.url, False, None, None, str(e))

    latency_ms = round((time.monotonic() - start) * 1000, 1)
    success = response.status_code == endpoint.expected_status
    return CheckResult(endpoint.name, endpoint.url, success, response.status_code, latency_ms)


def check_all(endpoints, http_get=requests.get):
    return [check_endpoint(e, http_get=http_get) for e in endpoints]
