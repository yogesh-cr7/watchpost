import requests

from watchpost.checker import check_all, check_endpoint
from watchpost.config import Endpoint


class FakeResponse:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text


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


def test_response_body_captured_on_failure():
    endpoint = Endpoint(name="broken", url="https://example.com", expected_status=200)
    fake_get = lambda url, timeout: FakeResponse(500, text='{"error": "internal server error"}')
    result = check_endpoint(endpoint, http_get=fake_get)
    assert result.response_body == '{"error": "internal server error"}'


def test_response_body_not_captured_on_success():
    # no point storing it (and bloating history.db) when nothing's wrong
    endpoint = Endpoint(name="ok", url="https://example.com", expected_status=200)
    fake_get = lambda url, timeout: FakeResponse(200, text="all good")
    result = check_endpoint(endpoint, http_get=fake_get)
    assert result.response_body is None


def test_response_body_truncated_to_max_length():
    endpoint = Endpoint(name="broken", url="https://example.com", expected_status=200)
    huge_body = "x" * 5000
    fake_get = lambda url, timeout: FakeResponse(500, text=huge_body)
    result = check_endpoint(endpoint, http_get=fake_get)
    assert len(result.response_body) == 500


def test_response_body_not_captured_on_connection_failure():
    # nothing to read - there was never a response object at all
    endpoint = Endpoint(name="down", url="https://example.com")

    def fake_get(url, timeout):
        raise requests.exceptions.ConnectionError()

    result = check_endpoint(endpoint, http_get=fake_get)
    assert result.response_body is None


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


def test_not_slow_when_no_threshold_set():
    # latency_threshold_ms defaults to None - no threshold means never slow
    endpoint = Endpoint(name="ok", url="https://example.com")
    fake_get = lambda url, timeout: FakeResponse(200)
    result = check_endpoint(endpoint, http_get=fake_get)
    assert result.slow is False


def test_not_slow_when_under_threshold():
    endpoint = Endpoint(name="ok", url="https://example.com", latency_threshold_ms=10_000)
    fake_get = lambda url, timeout: FakeResponse(200)
    result = check_endpoint(endpoint, http_get=fake_get)
    assert result.slow is False


def test_slow_when_latency_exceeds_threshold():
    # a threshold below zero is guaranteed to be exceeded by any real
    # (non-negative) latency, without needing to actually sleep in a test
    endpoint = Endpoint(name="ok", url="https://example.com", latency_threshold_ms=-1)
    fake_get = lambda url, timeout: FakeResponse(200)
    result = check_endpoint(endpoint, http_get=fake_get)
    assert result.success is True
    assert result.slow is True


def test_failure_is_never_marked_slow():
    # a wrong status code is already a failure - slow only applies on top
    # of an otherwise-successful check
    endpoint = Endpoint(name="broken", url="https://example.com",
                         expected_status=200, latency_threshold_ms=-1)
    fake_get = lambda url, timeout: FakeResponse(500)
    result = check_endpoint(endpoint, http_get=fake_get)
    assert result.success is False
    assert result.slow is False
