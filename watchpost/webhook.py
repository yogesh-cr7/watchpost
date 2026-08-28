import requests


class WebhookError(Exception):
    """the alert itself failed to send - not a reason to fail the whole check run"""


def build_message(endpoint_name, transition, result):
    if transition == "down":
        reason = result.error if result.error else f"got {result.status_code}"
        return f"DOWN: {endpoint_name} ({reason})"
    return f"RECOVERED: {endpoint_name} ({result.status_code})"


def send_alert(webhook_url, message, http_post=requests.post):
    # sending both keys means this one payload works for a Slack incoming
    # webhook (reads "text") and a Discord webhook (reads "content")
    # without a --platform flag - each just ignores the field it doesn't use
    payload = {"text": message, "content": message}
    try:
        response = http_post(webhook_url, json=payload, timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise WebhookError(str(e)) from e
    return response
