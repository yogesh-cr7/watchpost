import requests

from watchpost.checker import check_all, check_endpoint
from watchpost.config import Endpoint


class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


def test_successful_check():
    endpoint = Endpoint(name="ok", url="https://example.com", expected_status=200)
    fake_get = lambda url, timeout: FakeResponse(200)
    result = check_endpoint(endpoint, http_get=fake_get)
    assert result.success is True
    assert result.status_code == 200
    assert result.error is None
    assert result.latency_ms >= 0
    assert result.timestamp > 0


def test_wrong_status_code_is_a_failure():
    endpoint = Endpoint(name="broken", url="https://example.com", expected_status=200)
    fake_get = lambda url, timeout: FakeResponse(500)
    result = check_endpoint(endpoint, http_get=fake_get)
    assert result.success is False
    assert result.status_code == 500
    assert result.error is None  # the request worked fine, just not the status we wanted


def test_timeout_is_a_failure_with_no_status_code():
    endpoint = Endpoint(name="slow", url="https://example.com")

    def fake_get(url, timeout):
        raise requests.exceptions.Timeout()

    result = check_endpoint(endpoint, http_get=fake_get)
    assert result.success is False
    assert result.status_code is None
    assert result.error == "timed out"


def test_connection_error_is_a_failure():
    endpoint = Endpoint(name="down", url="https://example.com")

    def fake_get(url, timeout):
        raise requests.exceptions.ConnectionError()

    result = check_endpoint(endpoint, http_get=fake_get)
    assert result.error == "connection failed"


def test_check_all_runs_every_endpoint():
    endpoints = [
        Endpoint(name="a", url="https://example.com/a"),
        Endpoint(name="b", url="https://example.com/b"),
    ]
    fake_get = lambda url, timeout: FakeResponse(200)
    results = check_all(endpoints, http_get=fake_get)
    assert len(results) == 2
    assert all(r.success for r in results)
