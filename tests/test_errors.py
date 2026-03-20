import pytest

from agentscore.errors import AgentScoreError


def test_fields_are_stored():
    err = AgentScoreError(code="not_found", message="Address not found", status_code=404)
    assert err.code == "not_found"
    assert err.status_code == 404
    assert str(err) == "Address not found"


def test_is_exception():
    err = AgentScoreError(code="unauthorized", message="Invalid API key", status_code=401)
    assert isinstance(err, Exception)


def test_can_be_raised_and_caught():
    with pytest.raises(AgentScoreError) as exc_info:
        raise AgentScoreError(code="rate_limited", message="Too many requests", status_code=429)

    err = exc_info.value
    assert err.code == "rate_limited"
    assert err.status_code == 429
    assert str(err) == "Too many requests"


def test_string_representation_uses_message():
    err = AgentScoreError(code="server_error", message="Internal server error", status_code=500)
    assert str(err) == "Internal server error"


def test_unknown_error_code():
    err = AgentScoreError(code="unknown_error", message="Something went wrong", status_code=500)
    assert err.code == "unknown_error"
    assert err.status_code == 500
