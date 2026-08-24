from watchpost.checker import CheckResult


def make_result(name="api", success=True, status_code=200, latency_ms=100.0, timestamp=1000.0, error=None):
    return CheckResult(
        endpoint_name=name,
        url="https://example.com",
        success=success,
        status_code=status_code,
        latency_ms=latency_ms,
        timestamp=timestamp,
        error=error,
    )
