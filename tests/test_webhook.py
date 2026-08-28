import pytest
import requests

from watchpost.webhook import WebhookError, build_message, send_alert

from helpers import make_result


class FakeResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"{self.status_code} error")


def test_build_message_for_down_uses_error_when_present():
    result = make_result(success=False, status_code=None, error="connection failed")
    message = build_message("api", "down", result)
    assert "api" in message
    assert "connection failed" in message


def test_build_message_for_down_falls_back_to_status_code():
    result = make_result(success=False, status_code=503, error=None)
    message = build_message("api", "down", result)
    assert "api" in message
    assert "503" in message


def test_build_message_for_up_mentions_recovery():
    result = make_result(success=True, status_code=200)
    message = build_message("api", "up", result)
    assert "api" in message
    assert "200" in message


def test_send_alert_posts_both_text_and_content_keys():
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse(200)

    send_alert("https://example.com/webhook", "DOWN: api (got 500)", http_post=fake_post)

    assert captured["url"] == "https://example.com/webhook"
    assert captured["json"]["text"] == "DOWN: api (got 500)"
    assert captured["json"]["content"] == "DOWN: api (got 500)"


def test_send_alert_raises_webhook_error_on_bad_response():
    fake_post = lambda url, json, timeout: FakeResponse(500)
    with pytest.raises(WebhookError):
        send_alert("https://example.com/webhook", "test", http_post=fake_post)


def test_send_alert_raises_webhook_error_on_connection_failure():
    def fake_post(url, json, timeout):
        raise requests.exceptions.ConnectionError("no route to host")

    with pytest.raises(WebhookError):
        send_alert("https://example.com/webhook", "test", http_post=fake_post)
