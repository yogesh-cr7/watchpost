class DiagnosisError(Exception):
    """the LLM call itself failed or came back empty - not a reason to fail the whole check run"""


def build_prompt(endpoint_name, result, uptime_pct=None):
    lines = [
        f"An API monitoring check just failed for endpoint '{endpoint_name}'.",
        f"Status code: {result.status_code if result.status_code is not None else 'no response'}",
    ]
    if result.error:
        lines.append(f"Error: {result.error}")
    if result.response_body:
        lines.append(f"Response body (truncated): {result.response_body}")
    if uptime_pct is not None:
        lines.append(f"Uptime over recent checks for this endpoint: {uptime_pct}%")

    lines.append(
        "In 2-3 plain-English sentences, give a developer's best guess at what's "
        "likely wrong and what to check first. Don't just repeat the status code back."
    )
    return "\n".join(lines)


def diagnose_failure(endpoint_name, result, call_model, uptime_pct=None):
    """
    call_model is injected (a function prompt -> str) so this stays fully
    testable without an API key, network call, or cost - see
    make_model_caller for the thin wrapper that hits the real API.
    """
    prompt = build_prompt(endpoint_name, result, uptime_pct)
    try:
        text = call_model(prompt)
    except Exception as e:
        # the anthropic SDK can raise a handful of different error types
        # (auth, rate limit, connection) - wrapping broadly here means the
        # caller only has to catch one thing
        raise DiagnosisError(str(e)) from e

    text = (text or "").strip()
    if not text:
        raise DiagnosisError("model returned an empty response")
    return text


def make_model_caller(api_key=None):
    """
    Returns a call_model(prompt) -> str backed by the real Anthropic API.
    Only this function ever touches the network - everything else takes
    call_model as a parameter.
    """
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)  # falls back to ANTHROPIC_API_KEY env var if None

    def call_model(prompt):
        # haiku is plenty for a short diagnosis - no reason to spend on a
        # bigger model for this. check docs.claude.com/en/docs/about-claude/models
        # if this id has been retired by the time you're reading this
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    return call_model
