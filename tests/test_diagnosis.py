import pytest

from watchpost.diagnosis import DiagnosisError, build_prompt, diagnose_failure

from helpers import make_result


def test_build_prompt_includes_status_and_error():
    result = make_result(success=False, status_code=503, error=None)
    prompt = build_prompt("api", result)
    assert "api" in prompt
    assert "503" in prompt


def test_build_prompt_includes_response_body_when_present():
    result = make_result(success=False, status_code=500, response_body='{"error": "boom"}')
    prompt = build_prompt("api", result)
    assert "boom" in prompt


def test_build_prompt_omits_response_body_section_when_absent():
    result = make_result(success=False, status_code=500, response_body=None)
    prompt = build_prompt("api", result)
    assert "Response body" not in prompt


def test_build_prompt_includes_uptime_when_given():
    result = make_result(success=False, status_code=500)
    prompt = build_prompt("api", result, uptime_pct=42.5)
    assert "42.5" in prompt


def test_diagnose_failure_returns_model_text():
    result = make_result(success=False, status_code=500)
    call_model = lambda prompt: "looks like the upstream service is overloaded"
    diagnosis = diagnose_failure("api", result, call_model)
    assert diagnosis == "looks like the upstream service is overloaded"


def test_diagnose_failure_strips_whitespace():
    result = make_result(success=False, status_code=500)
    call_model = lambda prompt: "  some diagnosis text  \n"
    diagnosis = diagnose_failure("api", result, call_model)
    assert diagnosis == "some diagnosis text"


def test_diagnose_failure_wraps_model_exceptions():
    result = make_result(success=False, status_code=500)

    def call_model(prompt):
        raise RuntimeError("api key invalid")

    with pytest.raises(DiagnosisError):
        diagnose_failure("api", result, call_model)


def test_diagnose_failure_raises_on_empty_response():
    result = make_result(success=False, status_code=500)
    call_model = lambda prompt: "   "
    with pytest.raises(DiagnosisError):
        diagnose_failure("api", result, call_model)
