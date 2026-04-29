import json

import httpx
import pytest
import respx

from agentscore import AgentScore
from agentscore.errors import AgentScoreError

BASE_URL = "https://api.agentscore.sh"
API_KEY = "test-api-key"

ADDRESS = "0xabc123"


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


def test_constructor_requires_api_key():
    with pytest.raises(ValueError, match="API key is required"):
        AgentScore(api_key="")


def test_constructor_requires_api_key_none():
    with pytest.raises((ValueError, TypeError)):
        AgentScore(api_key=None)  # type: ignore[arg-type]


def test_constructor_stores_api_key():
    client = AgentScore(api_key=API_KEY)
    assert client.api_key == API_KEY


def test_constructor_default_base_url():
    client = AgentScore(api_key=API_KEY)
    assert client.base_url == BASE_URL


def test_constructor_custom_base_url():
    client = AgentScore(api_key=API_KEY, base_url="https://staging.agentscore.sh/")
    assert client.base_url == "https://staging.agentscore.sh"


def test_constructor_custom_timeout():
    client = AgentScore(api_key=API_KEY, timeout=30.0)
    assert client.timeout == 30.0


def test_constructor_default_timeout():
    client = AgentScore(api_key=API_KEY)
    assert client.timeout == 10.0


# ---------------------------------------------------------------------------
# get_reputation
# ---------------------------------------------------------------------------

REPUTATION_PAYLOAD = {
    "subject": {"chains": ["base"], "address": ADDRESS},
    "score": {
        "value": 75,
        "grade": "B",
        "scored_at": "2024-01-01T00:00:00Z",
        "status": "scored",
        "version": "1",
    },
    "chains": [
        {
            "chain": "base",
            "score": {"value": 75, "grade": "B"},
            "classification": {"entity_type": "wallet", "confidence": 0.9},
            "identity": {},
            "activity": {},
            "evidence_summary": {},
        },
    ],
    "data_semantics": "live",
    "caveats": [],
    "updated_at": "2024-01-01T00:00:00Z",
}


@respx.mock
def test_get_reputation_success():
    respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(return_value=httpx.Response(200, json=REPUTATION_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    result = client.get_reputation(ADDRESS)
    assert result["score"]["grade"] == "B"
    assert result["subject"]["address"] == ADDRESS


@respx.mock
def test_get_reputation_no_chain_param():
    route = respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(
        return_value=httpx.Response(200, json=REPUTATION_PAYLOAD)
    )
    client = AgentScore(api_key=API_KEY)
    client.get_reputation(ADDRESS)
    assert "chain" not in str(route.calls.last.request.url)


@respx.mock
def test_get_reputation_with_chain():
    route = respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(
        return_value=httpx.Response(200, json=REPUTATION_PAYLOAD)
    )
    client = AgentScore(api_key=API_KEY)
    client.get_reputation(ADDRESS, chain="base")
    assert "chain=base" in str(route.calls.last.request.url)


@respx.mock
def test_get_reputation_raises_on_404():
    respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(
        return_value=httpx.Response(404, json={"error": {"code": "not_found", "message": "Address not found"}})
    )
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(AgentScoreError) as exc_info:
        client.get_reputation(ADDRESS)
    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "not_found"


@respx.mock
def test_get_reputation_raises_on_401():
    respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(
        return_value=httpx.Response(401, json={"error": {"code": "unauthorized", "message": "Invalid API key"}})
    )
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(AgentScoreError) as exc_info:
        client.get_reputation(ADDRESS)
    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "unauthorized"


@respx.mock
def test_get_reputation_raises_on_500_non_json():
    respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(AgentScoreError) as exc_info:
        client.get_reputation(ADDRESS)
    assert exc_info.value.status_code == 500
    assert exc_info.value.code == "unknown_error"


# ---------------------------------------------------------------------------
# assess
# ---------------------------------------------------------------------------

ASSESS_PAYLOAD = {
    **REPUTATION_PAYLOAD,
    "decision": "allow",
    "decision_reasons": [],
    "on_the_fly": True,
}


@respx.mock
def test_assess_success():
    respx.post(f"{BASE_URL}/v1/assess").mock(return_value=httpx.Response(200, json=ASSESS_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    result = client.assess(ADDRESS)
    assert result["decision"] == "allow"
    assert result["on_the_fly"] is True


@respx.mock
def test_assess_sends_address_in_body():
    route = respx.post(f"{BASE_URL}/v1/assess").mock(return_value=httpx.Response(200, json=ASSESS_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    client.assess(ADDRESS)
    body = json.loads(route.calls.last.request.content)
    assert body["address"] == ADDRESS


@respx.mock
def test_assess_with_refresh():
    route = respx.post(f"{BASE_URL}/v1/assess").mock(return_value=httpx.Response(200, json=ASSESS_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    client.assess(ADDRESS, refresh=True)
    body = json.loads(route.calls.last.request.content)
    assert body.get("refresh") is True


@respx.mock
def test_assess_with_non_default_chain():
    route = respx.post(f"{BASE_URL}/v1/assess").mock(return_value=httpx.Response(200, json=ASSESS_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    client.assess(ADDRESS, chain="ethereum")
    body = json.loads(route.calls.last.request.content)
    assert body["chain"] == "ethereum"


@respx.mock
def test_assess_no_chain_omits_from_body():
    route = respx.post(f"{BASE_URL}/v1/assess").mock(return_value=httpx.Response(200, json=ASSESS_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    client.assess(ADDRESS)
    body = json.loads(route.calls.last.request.content)
    assert "chain" not in body


@respx.mock
def test_assess_raises_on_402():
    respx.post(f"{BASE_URL}/v1/assess").mock(
        return_value=httpx.Response(
            402,
            json={"error": {"code": "payment_required", "message": "Upgrade required"}},
        )
    )
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(AgentScoreError) as exc_info:
        client.assess(ADDRESS)
    assert exc_info.value.status_code == 402
    assert exc_info.value.code == "payment_required"


# ---------------------------------------------------------------------------
# API key header
# ---------------------------------------------------------------------------

REPUTATION_PAYLOAD_SIMPLE = {
    "subject": {"chains": ["base"], "address": ADDRESS},
    "score": {"value": 75, "grade": "B", "scored_at": "2024-01-01T00:00:00Z", "status": "scored", "version": "1"},
    "data_semantics": "live",
    "caveats": [],
    "updated_at": "2024-01-01T00:00:00Z",
}


@respx.mock
def test_auth_header_is_sent():
    route = respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(
        return_value=httpx.Response(200, json=REPUTATION_PAYLOAD_SIMPLE)
    )
    client = AgentScore(api_key="my-secret-key")
    client.get_reputation(ADDRESS)
    assert route.calls.last.request.headers["x-api-key"] == "my-secret-key"


# ---------------------------------------------------------------------------
# Error: missing error body fields fall back gracefully
# ---------------------------------------------------------------------------


@respx.mock
def test_error_missing_error_key_falls_back():
    respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(
        return_value=httpx.Response(400, json={"message": "bad request"})
    )
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(AgentScoreError) as exc_info:
        client.get_reputation(ADDRESS)
    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "unknown_error"


# ---------------------------------------------------------------------------
# assess: policy forwarding
# ---------------------------------------------------------------------------


@respx.mock
def test_assess_forwards_policy_in_body():
    route = respx.post(f"{BASE_URL}/v1/assess").mock(return_value=httpx.Response(200, json=ASSESS_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    policy = {"require_kyc": True, "min_age": 21}
    client.assess(ADDRESS, policy=policy)
    body = json.loads(route.calls.last.request.content)
    assert body["policy"] == policy


# ---------------------------------------------------------------------------
# Async: aget_reputation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_aget_reputation_success():
    respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(return_value=httpx.Response(200, json=REPUTATION_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    result = await client.aget_reputation(ADDRESS)
    assert result["score"]["grade"] == "B"
    assert result["subject"]["address"] == ADDRESS
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_aget_reputation_raises_on_error():
    respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(
        return_value=httpx.Response(404, json={"error": {"code": "not_found", "message": "Not found"}})
    )
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(AgentScoreError) as exc_info:
        await client.aget_reputation(ADDRESS)
    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "not_found"
    await client.aclose()


# ---------------------------------------------------------------------------
# Async: aassess
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_aassess_success():
    respx.post(f"{BASE_URL}/v1/assess").mock(return_value=httpx.Response(200, json=ASSESS_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    result = await client.aassess(ADDRESS)
    assert result["decision"] == "allow"
    assert result["on_the_fly"] is True
    await client.aclose()


# ---------------------------------------------------------------------------
# Context managers and close
# ---------------------------------------------------------------------------


@respx.mock
def test_sync_context_manager():
    respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(return_value=httpx.Response(200, json=REPUTATION_PAYLOAD))
    with AgentScore(api_key=API_KEY) as client:
        result = client.get_reputation(ADDRESS)
        assert result["score"]["grade"] == "B"
    assert client._sync_client is None


@pytest.mark.asyncio
@respx.mock
async def test_async_context_manager():
    respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(return_value=httpx.Response(200, json=REPUTATION_PAYLOAD))
    async with AgentScore(api_key=API_KEY) as client:
        result = await client.aget_reputation(ADDRESS)
        assert result["score"]["grade"] == "B"
    assert client._async_client is None


@respx.mock
def test_success_response_with_invalid_json():
    """A 200 response with non-JSON body should raise AgentScoreError."""
    respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(
        return_value=httpx.Response(200, text="not json"),
    )
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(AgentScoreError) as exc_info:
        client.get_reputation(ADDRESS)
    assert exc_info.value.code == "invalid_response"
    assert exc_info.value.status_code == 200


def test_close_without_usage():
    """Calling close() when no client was created should not raise."""
    client = AgentScore(api_key=API_KEY)
    client.close()
    assert client._sync_client is None


@pytest.mark.asyncio
async def test_aclose_without_usage():
    """Calling aclose() when no async client was created should not raise."""
    client = AgentScore(api_key=API_KEY)
    await client.aclose()
    assert client._async_client is None


@respx.mock
def test_user_agent_header_includes_version():
    """User-Agent header should include package version."""
    from importlib.metadata import version

    respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(
        return_value=httpx.Response(200, json=REPUTATION_PAYLOAD),
    )
    client = AgentScore(api_key=API_KEY)
    client.get_reputation(ADDRESS)
    request = respx.calls[0].request
    assert request.headers["user-agent"] == f"agentscore-py/{version('agentscore-py')}"


@respx.mock
def test_user_agent_header_prepends_custom_user_agent():
    """Custom user_agent should be rendered as '{custom} ({default})'."""
    from importlib.metadata import version

    respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(
        return_value=httpx.Response(200, json=REPUTATION_PAYLOAD),
    )
    client = AgentScore(api_key=API_KEY, user_agent="my-app/1.2.3")
    client.get_reputation(ADDRESS)
    request = respx.calls[0].request
    expected = f"my-app/1.2.3 (agentscore-py/{version('agentscore-py')})"
    assert request.headers["user-agent"] == expected


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@respx.mock
def test_assess_refresh_false_not_included_in_body():
    route = respx.post(f"{BASE_URL}/v1/assess").mock(return_value=httpx.Response(200, json=ASSESS_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    client.assess(ADDRESS, refresh=False)
    body = json.loads(route.calls.last.request.content)
    assert "refresh" not in body


@respx.mock
def test_double_close():
    respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(return_value=httpx.Response(200, json=REPUTATION_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    client.get_reputation(ADDRESS)
    client.close()
    client.close()
    assert client._sync_client is None


@pytest.mark.asyncio
@respx.mock
async def test_double_aclose():
    respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(return_value=httpx.Response(200, json=REPUTATION_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    await client.aget_reputation(ADDRESS)
    await client.aclose()
    await client.aclose()
    assert client._async_client is None


@pytest.mark.asyncio
@respx.mock
async def test_concurrent_async_calls():
    import asyncio

    respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(return_value=httpx.Response(200, json=REPUTATION_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    results = await asyncio.gather(
        client.aget_reputation(ADDRESS),
        client.aget_reputation(ADDRESS),
        client.aget_reputation(ADDRESS),
    )
    assert len(results) == 3
    for r in results:
        assert r["score"]["grade"] == "B"
    await client.aclose()


@respx.mock
def test_empty_chain_string_not_included_in_params():
    route = respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(
        return_value=httpx.Response(200, json=REPUTATION_PAYLOAD)
    )
    client = AgentScore(api_key=API_KEY)
    client.get_reputation(ADDRESS, chain="")
    assert "chain" not in str(route.calls.last.request.url)


@respx.mock
def test_assess_empty_policy_dict_included_in_body():
    route = respx.post(f"{BASE_URL}/v1/assess").mock(return_value=httpx.Response(200, json=ASSESS_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    client.assess(ADDRESS, policy={})
    body = json.loads(route.calls.last.request.content)
    assert "policy" in body
    assert body["policy"] == {}


@respx.mock
def test_timeout_error_raises_agentscore_error():
    respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(side_effect=httpx.TimeoutException("timed out"))
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(httpx.TimeoutException):
        client.get_reputation(ADDRESS)


@respx.mock
def test_connect_error_raises_agentscore_error():
    respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(side_effect=httpx.ConnectError("connection refused"))
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(httpx.ConnectError):
        client.get_reputation(ADDRESS)


@respx.mock
def test_error_response_no_error_key_fallback():
    respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(
        return_value=httpx.Response(422, json={"detail": "validation failed"})
    )
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(AgentScoreError) as exc_info:
        client.get_reputation(ADDRESS)
    assert exc_info.value.status_code == 422
    assert exc_info.value.code == "unknown_error"


# ---------------------------------------------------------------------------
# Verification / Compliance fields
# ---------------------------------------------------------------------------


REPUTATION_WITH_VERIFICATION = {
    **REPUTATION_PAYLOAD,
    "verification_level": "kyc_verified",
}

ASSESS_WITH_COMPLIANCE = {
    **ASSESS_PAYLOAD,
    "decision": "deny",
    "decision_reasons": ["kyc_required", "sanctions_check_pending"],
    "operator_verification": {
        "level": "none",
        "operator_type": None,
        "claimed_at": None,
        "verified_at": None,
    },
    "verify_url": "https://agentscore.sh/verify/abc123",
    "resolved_operator": "0xoperator456",
}


@respx.mock
def test_get_reputation_returns_verification_level():
    respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(
        return_value=httpx.Response(200, json=REPUTATION_WITH_VERIFICATION)
    )
    client = AgentScore(api_key=API_KEY)
    result = client.get_reputation(ADDRESS)
    assert result["verification_level"] == "kyc_verified"


@respx.mock
def test_get_reputation_omits_verification_level_when_absent():
    respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(return_value=httpx.Response(200, json=REPUTATION_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    result = client.get_reputation(ADDRESS)
    assert "verification_level" not in result


@respx.mock
def test_assess_returns_operator_verification():
    respx.post(f"{BASE_URL}/v1/assess").mock(return_value=httpx.Response(200, json=ASSESS_WITH_COMPLIANCE))
    client = AgentScore(api_key=API_KEY)
    result = client.assess(ADDRESS)
    assert result["operator_verification"]["level"] == "none"
    assert result["operator_verification"]["operator_type"] is None


@respx.mock
def test_assess_returns_verify_url():
    respx.post(f"{BASE_URL}/v1/assess").mock(return_value=httpx.Response(200, json=ASSESS_WITH_COMPLIANCE))
    client = AgentScore(api_key=API_KEY)
    result = client.assess(ADDRESS)
    assert result["verify_url"] == "https://agentscore.sh/verify/abc123"


@respx.mock
def test_assess_returns_resolved_operator():
    respx.post(f"{BASE_URL}/v1/assess").mock(return_value=httpx.Response(200, json=ASSESS_WITH_COMPLIANCE))
    client = AgentScore(api_key=API_KEY)
    result = client.assess(ADDRESS)
    assert result["resolved_operator"] == "0xoperator456"


@respx.mock
def test_assess_omits_verification_fields_when_absent():
    respx.post(f"{BASE_URL}/v1/assess").mock(return_value=httpx.Response(200, json=ASSESS_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    result = client.assess(ADDRESS)
    assert "operator_verification" not in result
    assert "verify_url" not in result
    assert "resolved_operator" not in result


@respx.mock
def test_assess_sends_compliance_policy_fields():
    route = respx.post(f"{BASE_URL}/v1/assess").mock(return_value=httpx.Response(200, json=ASSESS_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    policy = {
        "require_kyc": True,
        "require_sanctions_clear": True,
        "min_age": 90,
        "blocked_jurisdictions": ["KP", "IR"],
    }
    client.assess(ADDRESS, policy=policy)
    body = json.loads(route.calls.last.request.content)
    assert body["policy"]["require_kyc"] is True
    assert body["policy"]["require_sanctions_clear"] is True
    assert body["policy"]["min_age"] == 90
    assert body["policy"]["blocked_jurisdictions"] == ["KP", "IR"]


@pytest.mark.asyncio
@respx.mock
async def test_aget_reputation_returns_verification_level():
    respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(
        return_value=httpx.Response(200, json=REPUTATION_WITH_VERIFICATION)
    )
    client = AgentScore(api_key=API_KEY)
    result = await client.aget_reputation(ADDRESS)
    assert result["verification_level"] == "kyc_verified"
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_aassess_returns_compliance_fields():
    respx.post(f"{BASE_URL}/v1/assess").mock(return_value=httpx.Response(200, json=ASSESS_WITH_COMPLIANCE))
    client = AgentScore(api_key=API_KEY)
    result = await client.aassess(ADDRESS)
    assert result["operator_verification"]["level"] == "none"
    assert result["verify_url"] == "https://agentscore.sh/verify/abc123"
    assert result["resolved_operator"] == "0xoperator456"
    await client.aclose()


# ---------------------------------------------------------------------------
# Integration-style: compliance deny flow
# ---------------------------------------------------------------------------


@respx.mock
def test_full_compliance_deny_flow():
    """Full assess flow with compliance policy returning deny + verify_url."""
    compliance_response = {
        **REPUTATION_PAYLOAD,
        "decision": "deny",
        "decision_reasons": ["kyc_required", "sanctions_check_pending"],
        "on_the_fly": False,
        "operator_verification": {
            "level": "none",
            "operator_type": None,
            "claimed_at": None,
            "verified_at": None,
        },
        "verify_url": "https://agentscore.sh/verify/xyz789",
    }
    route = respx.post(f"{BASE_URL}/v1/assess").mock(return_value=httpx.Response(200, json=compliance_response))
    client = AgentScore(api_key=API_KEY)
    result = client.assess(
        ADDRESS,
        policy={
            "require_kyc": True,
            "require_sanctions_clear": True,
        },
    )
    assert result["decision"] == "deny"
    assert "kyc_required" in result["decision_reasons"]
    assert "sanctions_check_pending" in result["decision_reasons"]
    assert result["verify_url"] == "https://agentscore.sh/verify/xyz789"
    assert result["operator_verification"]["level"] == "none"

    body = json.loads(route.calls.last.request.content)
    assert body["policy"]["require_kyc"] is True
    assert body["policy"]["require_sanctions_clear"] is True


# ---------------------------------------------------------------------------
# Identity model: operator_token in assess/aassess
# ---------------------------------------------------------------------------


@respx.mock
def test_assess_sends_operator_token():
    route = respx.post(f"{BASE_URL}/v1/assess").mock(return_value=httpx.Response(200, json=ASSESS_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    client.assess(operator_token="opc_test_123")
    body = json.loads(route.calls.last.request.content)
    assert body["operator_token"] == "opc_test_123"
    assert "address" not in body


@respx.mock
def test_assess_sends_both_address_and_operator_token():
    route = respx.post(f"{BASE_URL}/v1/assess").mock(return_value=httpx.Response(200, json=ASSESS_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    client.assess(ADDRESS, operator_token="opc_both_456")
    body = json.loads(route.calls.last.request.content)
    assert body["address"] == ADDRESS
    assert body["operator_token"] == "opc_both_456"


@respx.mock
def test_assess_address_only_backwards_compat():
    route = respx.post(f"{BASE_URL}/v1/assess").mock(return_value=httpx.Response(200, json=ASSESS_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    client.assess(ADDRESS)
    body = json.loads(route.calls.last.request.content)
    assert body["address"] == ADDRESS
    assert "operator_token" not in body


@respx.mock
def test_assess_operator_token_with_policy():
    route = respx.post(f"{BASE_URL}/v1/assess").mock(return_value=httpx.Response(200, json=ASSESS_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    client.assess(operator_token="opc_policy", policy={"require_kyc": True})
    body = json.loads(route.calls.last.request.content)
    assert body["operator_token"] == "opc_policy"
    assert "address" not in body
    assert body["policy"]["require_kyc"] is True


@pytest.mark.asyncio
@respx.mock
async def test_aassess_sends_operator_token():
    route = respx.post(f"{BASE_URL}/v1/assess").mock(return_value=httpx.Response(200, json=ASSESS_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    await client.aassess(operator_token="opc_async_test")
    body = json.loads(route.calls.last.request.content)
    assert body["operator_token"] == "opc_async_test"
    assert "address" not in body
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_aassess_sends_both_address_and_operator_token():
    route = respx.post(f"{BASE_URL}/v1/assess").mock(return_value=httpx.Response(200, json=ASSESS_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    await client.aassess(ADDRESS, operator_token="opc_async_both")
    body = json.loads(route.calls.last.request.content)
    assert body["address"] == ADDRESS
    assert body["operator_token"] == "opc_async_both"
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_aassess_address_only_backwards_compat():
    route = respx.post(f"{BASE_URL}/v1/assess").mock(return_value=httpx.Response(200, json=ASSESS_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    await client.aassess(ADDRESS)
    body = json.loads(route.calls.last.request.content)
    assert body["address"] == ADDRESS
    assert "operator_token" not in body
    await client.aclose()


# ---------------------------------------------------------------------------
# create_session
# ---------------------------------------------------------------------------

SESSION_CREATE_PAYLOAD = {
    "session_id": "ses_abc123",
    "poll_secret": "ps_secret456",
    "poll_url": "https://api.agentscore.sh/v1/sessions/ses_abc123",
}


@respx.mock
def test_create_session_success():
    respx.post(f"{BASE_URL}/v1/sessions").mock(return_value=httpx.Response(200, json=SESSION_CREATE_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    result = client.create_session()
    assert result["session_id"] == "ses_abc123"
    assert result["poll_secret"] == "ps_secret456"
    assert result["poll_url"] == "https://api.agentscore.sh/v1/sessions/ses_abc123"


@respx.mock
def test_create_session_with_first_class_fields():
    route = respx.post(f"{BASE_URL}/v1/sessions").mock(return_value=httpx.Response(200, json=SESSION_CREATE_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    client.create_session(
        context="wine purchase verification",
        product_name="Cabernet Reserve 2022",
    )
    body = json.loads(route.calls.last.request.content)
    assert body["context"] == "wine purchase verification"
    assert body["product_name"] == "Cabernet Reserve 2022"


@respx.mock
def test_create_session_omits_none_fields():
    route = respx.post(f"{BASE_URL}/v1/sessions").mock(return_value=httpx.Response(200, json=SESSION_CREATE_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    client.create_session()
    body = json.loads(route.calls.last.request.content)
    assert "context" not in body
    assert "product_name" not in body


@respx.mock
def test_create_session_raises_on_error():
    respx.post(f"{BASE_URL}/v1/sessions").mock(
        return_value=httpx.Response(400, json={"error": {"code": "bad_request", "message": "Invalid body"}})
    )
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(AgentScoreError) as exc_info:
        client.create_session()
    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "bad_request"


@respx.mock
def test_create_session_forwards_address_and_operator_token():
    """Pre-association lets a session refresh KYC for an existing identity."""
    route = respx.post(f"{BASE_URL}/v1/sessions").mock(return_value=httpx.Response(200, json=SESSION_CREATE_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    client.create_session(address="0xabc", operator_token="opc_xyz")
    body = json.loads(route.calls.last.request.content)
    assert body["address"] == "0xabc"
    assert body["operator_token"] == "opc_xyz"


@respx.mock
def test_error_response_populates_details_with_non_error_fields():
    """Non-`error` response-body keys flow into AgentScoreError.details so consumers
    can branch on verify_url, linked_wallets, claimed_operator, etc. for granular recovery."""
    respx.post(f"{BASE_URL}/v1/assess").mock(
        return_value=httpx.Response(
            403,
            json={
                "error": {"code": "wallet_signer_mismatch", "message": "Signer mismatch"},
                "claimed_operator": "op_abc",
                "actual_signer": "0xdef",
                "linked_wallets": ["0xabc", "0xdef"],
            },
        )
    )
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(AgentScoreError) as exc_info:
        client.assess(address="0xabc")
    err = exc_info.value
    assert err.code == "wallet_signer_mismatch"
    assert err.details["claimed_operator"] == "op_abc"
    assert err.details["actual_signer"] == "0xdef"
    assert err.details["linked_wallets"] == ["0xabc", "0xdef"]
    assert "error" not in err.details  # the `error` key is parsed into code/message, not echoed


@respx.mock
def test_error_response_with_no_extra_fields_yields_empty_details():
    respx.post(f"{BASE_URL}/v1/assess").mock(
        return_value=httpx.Response(
            500,
            json={"error": {"code": "internal_error", "message": "Boom"}},
        )
    )
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(AgentScoreError) as exc_info:
        client.assess(address="0xabc")
    assert exc_info.value.details == {}


# ---------------------------------------------------------------------------
# poll_session
# ---------------------------------------------------------------------------

SESSION_POLL_PENDING_PAYLOAD = {
    "session_id": "ses_abc123",
    "status": "pending",
}

SESSION_POLL_COMPLETE_PAYLOAD = {
    "session_id": "ses_abc123",
    "status": "complete",
    "score": {
        "value": 80,
        "grade": "B",
        "scored_at": "2024-01-01T00:00:00Z",
        "status": "scored",
        "version": "1",
    },
    "decision": "allow",
    "decision_reasons": [],
    "subject": {"chains": ["base"], "address": ADDRESS},
}


@respx.mock
def test_poll_session_pending():
    respx.get(f"{BASE_URL}/v1/sessions/ses_abc123").mock(
        return_value=httpx.Response(200, json=SESSION_POLL_PENDING_PAYLOAD)
    )
    client = AgentScore(api_key=API_KEY)
    result = client.poll_session("ses_abc123", "ps_secret456")
    assert result["session_id"] == "ses_abc123"
    assert result["status"] == "pending"


@respx.mock
def test_poll_session_complete():
    respx.get(f"{BASE_URL}/v1/sessions/ses_abc123").mock(
        return_value=httpx.Response(200, json=SESSION_POLL_COMPLETE_PAYLOAD)
    )
    client = AgentScore(api_key=API_KEY)
    result = client.poll_session("ses_abc123", "ps_secret456")
    assert result["status"] == "complete"
    assert result["score"]["grade"] == "B"
    assert result["decision"] == "allow"


@respx.mock
def test_poll_session_sends_poll_secret_header():
    route = respx.get(f"{BASE_URL}/v1/sessions/ses_abc123").mock(
        return_value=httpx.Response(200, json=SESSION_POLL_PENDING_PAYLOAD)
    )
    client = AgentScore(api_key=API_KEY)
    client.poll_session("ses_abc123", "ps_secret456")
    assert route.calls.last.request.headers["x-poll-secret"] == "ps_secret456"


@respx.mock
def test_poll_session_raises_on_404():
    respx.get(f"{BASE_URL}/v1/sessions/ses_bad").mock(
        return_value=httpx.Response(404, json={"error": {"code": "not_found", "message": "Session not found"}})
    )
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(AgentScoreError) as exc_info:
        client.poll_session("ses_bad", "ps_secret456")
    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "not_found"


# ---------------------------------------------------------------------------
# create_credential
# ---------------------------------------------------------------------------

CREDENTIAL_CREATE_PAYLOAD = {
    "id": "cred_abc123",
    "label": "My credential",
    "token": "ak_full_secret_token",
    "prefix": "ak_full",
    "created_at": "2024-01-01T00:00:00Z",
    "expires_at": "2024-04-01T00:00:00Z",
}


@respx.mock
def test_create_credential_success():
    respx.post(f"{BASE_URL}/v1/credentials").mock(return_value=httpx.Response(200, json=CREDENTIAL_CREATE_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    result = client.create_credential(label="My credential", ttl_days=90)
    assert result["id"] == "cred_abc123"
    assert result["token"] == "ak_full_secret_token"
    assert result["label"] == "My credential"


@respx.mock
def test_create_credential_sends_body():
    route = respx.post(f"{BASE_URL}/v1/credentials").mock(
        return_value=httpx.Response(200, json=CREDENTIAL_CREATE_PAYLOAD)
    )
    client = AgentScore(api_key=API_KEY)
    client.create_credential(label="My credential", ttl_days=90)
    body = json.loads(route.calls.last.request.content)
    assert body["label"] == "My credential"
    assert body["ttl_days"] == 90


@respx.mock
def test_create_credential_omits_none_fields():
    route = respx.post(f"{BASE_URL}/v1/credentials").mock(
        return_value=httpx.Response(200, json=CREDENTIAL_CREATE_PAYLOAD)
    )
    client = AgentScore(api_key=API_KEY)
    client.create_credential()
    body = json.loads(route.calls.last.request.content)
    assert "label" not in body
    assert "ttl_days" not in body


@respx.mock
def test_create_credential_raises_on_error():
    respx.post(f"{BASE_URL}/v1/credentials").mock(
        return_value=httpx.Response(403, json={"error": {"code": "forbidden", "message": "Not allowed"}})
    )
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(AgentScoreError) as exc_info:
        client.create_credential()
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "forbidden"


# ---------------------------------------------------------------------------
# list_credentials
# ---------------------------------------------------------------------------

CREDENTIAL_LIST_PAYLOAD = {
    "credentials": [
        {
            "id": "cred_abc123",
            "label": "My credential",
            "prefix": "ak_full",
            "created_at": "2024-01-01T00:00:00Z",
            "expires_at": "2024-04-01T00:00:00Z",
            "last_used_at": None,
        },
        {
            "id": "cred_def456",
            "label": None,
            "prefix": "ak_other",
            "created_at": "2024-02-01T00:00:00Z",
            "expires_at": None,
            "last_used_at": "2024-03-01T00:00:00Z",
        },
    ],
}


@respx.mock
def test_list_credentials_success():
    respx.get(f"{BASE_URL}/v1/credentials").mock(return_value=httpx.Response(200, json=CREDENTIAL_LIST_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    result = client.list_credentials()
    assert len(result["credentials"]) == 2
    assert result["credentials"][0]["id"] == "cred_abc123"
    assert result["credentials"][1]["id"] == "cred_def456"


@respx.mock
def test_list_credentials_empty():
    respx.get(f"{BASE_URL}/v1/credentials").mock(return_value=httpx.Response(200, json={"credentials": []}))
    client = AgentScore(api_key=API_KEY)
    result = client.list_credentials()
    assert result["credentials"] == []


@respx.mock
def test_list_credentials_raises_on_error():
    respx.get(f"{BASE_URL}/v1/credentials").mock(
        return_value=httpx.Response(401, json={"error": {"code": "unauthorized", "message": "Invalid API key"}})
    )
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(AgentScoreError) as exc_info:
        client.list_credentials()
    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "unauthorized"


# ---------------------------------------------------------------------------
# revoke_credential
# ---------------------------------------------------------------------------

CREDENTIAL_REVOKE_PAYLOAD = {"ok": True}


@respx.mock
def test_revoke_credential_success():
    respx.delete(f"{BASE_URL}/v1/credentials/cred_abc123").mock(
        return_value=httpx.Response(200, json=CREDENTIAL_REVOKE_PAYLOAD)
    )
    client = AgentScore(api_key=API_KEY)
    result = client.revoke_credential("cred_abc123")
    assert result["ok"] is True


@respx.mock
def test_revoke_credential_raises_on_404():
    respx.delete(f"{BASE_URL}/v1/credentials/cred_bad").mock(
        return_value=httpx.Response(404, json={"error": {"code": "not_found", "message": "Credential not found"}})
    )
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(AgentScoreError) as exc_info:
        client.revoke_credential("cred_bad")
    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "not_found"


# ---------------------------------------------------------------------------
# Async: acreate_session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_acreate_session_success():
    respx.post(f"{BASE_URL}/v1/sessions").mock(return_value=httpx.Response(200, json=SESSION_CREATE_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    result = await client.acreate_session()
    assert result["session_id"] == "ses_abc123"
    assert result["poll_secret"] == "ps_secret456"
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_acreate_session_with_first_class_fields():
    route = respx.post(f"{BASE_URL}/v1/sessions").mock(return_value=httpx.Response(200, json=SESSION_CREATE_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    await client.acreate_session(
        context="wine purchase verification",
        product_name="Cabernet Reserve 2022",
    )
    body = json.loads(route.calls.last.request.content)
    assert body["context"] == "wine purchase verification"
    assert body["product_name"] == "Cabernet Reserve 2022"
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_acreate_session_forwards_address_and_operator_token():
    route = respx.post(f"{BASE_URL}/v1/sessions").mock(return_value=httpx.Response(200, json=SESSION_CREATE_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    await client.acreate_session(address="0xabc", operator_token="opc_xyz")
    body = json.loads(route.calls.last.request.content)
    assert body["address"] == "0xabc"
    assert body["operator_token"] == "opc_xyz"
    await client.aclose()


# ---------------------------------------------------------------------------
# Async: apoll_session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_apoll_session_success():
    respx.get(f"{BASE_URL}/v1/sessions/ses_abc123").mock(
        return_value=httpx.Response(200, json=SESSION_POLL_COMPLETE_PAYLOAD)
    )
    client = AgentScore(api_key=API_KEY)
    result = await client.apoll_session("ses_abc123", "ps_secret456")
    assert result["status"] == "complete"
    assert result["score"]["grade"] == "B"
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_apoll_session_sends_poll_secret_header():
    route = respx.get(f"{BASE_URL}/v1/sessions/ses_abc123").mock(
        return_value=httpx.Response(200, json=SESSION_POLL_PENDING_PAYLOAD)
    )
    client = AgentScore(api_key=API_KEY)
    await client.apoll_session("ses_abc123", "ps_secret456")
    assert route.calls.last.request.headers["x-poll-secret"] == "ps_secret456"
    await client.aclose()


# ---------------------------------------------------------------------------
# Async: acreate_credential
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_acreate_credential_success():
    respx.post(f"{BASE_URL}/v1/credentials").mock(return_value=httpx.Response(200, json=CREDENTIAL_CREATE_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    result = await client.acreate_credential(label="My credential", ttl_days=90)
    assert result["id"] == "cred_abc123"
    assert result["token"] == "ak_full_secret_token"
    await client.aclose()


# ---------------------------------------------------------------------------
# Async: alist_credentials
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_alist_credentials_success():
    respx.get(f"{BASE_URL}/v1/credentials").mock(return_value=httpx.Response(200, json=CREDENTIAL_LIST_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    result = await client.alist_credentials()
    assert len(result["credentials"]) == 2
    assert result["credentials"][0]["id"] == "cred_abc123"
    await client.aclose()


# ---------------------------------------------------------------------------
# Async: arevoke_credential
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_arevoke_credential_success():
    respx.delete(f"{BASE_URL}/v1/credentials/cred_abc123").mock(
        return_value=httpx.Response(200, json=CREDENTIAL_REVOKE_PAYLOAD)
    )
    client = AgentScore(api_key=API_KEY)
    result = await client.arevoke_credential("cred_abc123")
    assert result["ok"] is True
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_arevoke_credential_raises_on_404():
    respx.delete(f"{BASE_URL}/v1/credentials/cred_bad").mock(
        return_value=httpx.Response(404, json={"error": {"code": "not_found", "message": "Credential not found"}})
    )
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(AgentScoreError) as exc_info:
        await client.arevoke_credential("cred_bad")
    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "not_found"
    await client.aclose()


# ---------------------------------------------------------------------------
# associate_wallet
# ---------------------------------------------------------------------------

ASSOCIATE_TOKEN = "opc_" + "a" * 48
ASSOCIATE_WALLET = "0xabcdef1234567890abcdef1234567890abcdef12"
ASSOCIATE_NETWORK = "evm"


@respx.mock
def test_associate_wallet_returns_first_seen_true():
    respx.post(f"{BASE_URL}/v1/credentials/wallets").mock(
        return_value=httpx.Response(200, json={"associated": True, "first_seen": True}),
    )
    client = AgentScore(api_key=API_KEY)
    result = client.associate_wallet(ASSOCIATE_TOKEN, ASSOCIATE_WALLET, ASSOCIATE_NETWORK)
    assert result == {"associated": True, "first_seen": True}


@respx.mock
def test_associate_wallet_sends_snake_case_body():
    route = respx.post(f"{BASE_URL}/v1/credentials/wallets").mock(
        return_value=httpx.Response(200, json={"associated": True, "first_seen": False}),
    )
    client = AgentScore(api_key=API_KEY)
    client.associate_wallet(ASSOCIATE_TOKEN, ASSOCIATE_WALLET, ASSOCIATE_NETWORK)
    assert route.called
    body = json.loads(route.calls[0].request.content.decode())
    assert body == {
        "operator_token": ASSOCIATE_TOKEN,
        "wallet_address": ASSOCIATE_WALLET,
        "network": ASSOCIATE_NETWORK,
    }


@respx.mock
def test_associate_wallet_forwards_idempotency_key():
    route = respx.post(f"{BASE_URL}/v1/credentials/wallets").mock(
        return_value=httpx.Response(200, json={"associated": True, "first_seen": False, "deduped": True}),
    )
    client = AgentScore(api_key=API_KEY)
    result = client.associate_wallet(ASSOCIATE_TOKEN, ASSOCIATE_WALLET, ASSOCIATE_NETWORK, idempotency_key="pi_abc")
    assert result == {"associated": True, "first_seen": False, "deduped": True}
    body = json.loads(route.calls[0].request.content.decode())
    assert body["idempotency_key"] == "pi_abc"


@respx.mock
def test_associate_wallet_omits_idempotency_key_when_not_provided():
    route = respx.post(f"{BASE_URL}/v1/credentials/wallets").mock(
        return_value=httpx.Response(200, json={"associated": True, "first_seen": True}),
    )
    client = AgentScore(api_key=API_KEY)
    client.associate_wallet(ASSOCIATE_TOKEN, ASSOCIATE_WALLET, ASSOCIATE_NETWORK)
    body = json.loads(route.calls[0].request.content.decode())
    assert "idempotency_key" not in body


@respx.mock
def test_associate_wallet_omits_empty_string_idempotency_key():
    """Empty string is not a valid key — match node-sdk behavior and skip forwarding."""
    route = respx.post(f"{BASE_URL}/v1/credentials/wallets").mock(
        return_value=httpx.Response(200, json={"associated": True, "first_seen": True}),
    )
    client = AgentScore(api_key=API_KEY)
    client.associate_wallet(ASSOCIATE_TOKEN, ASSOCIATE_WALLET, ASSOCIATE_NETWORK, idempotency_key="")
    body = json.loads(route.calls[0].request.content.decode())
    assert "idempotency_key" not in body


@respx.mock
def test_associate_wallet_raises_on_401_invalid_credential():
    """Matches /v1/assess's anti-enumeration status code for unknown credentials."""
    respx.post(f"{BASE_URL}/v1/credentials/wallets").mock(
        return_value=httpx.Response(
            401,
            json={"error": {"code": "invalid_credential", "message": "Operator credential not found"}},
        ),
    )
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(AgentScoreError) as exc_info:
        client.associate_wallet(ASSOCIATE_TOKEN, ASSOCIATE_WALLET, ASSOCIATE_NETWORK)
    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "invalid_credential"


@respx.mock
def test_associate_wallet_raises_on_400_invalid_wallet():
    respx.post(f"{BASE_URL}/v1/credentials/wallets").mock(
        return_value=httpx.Response(
            400,
            json={"error": {"code": "invalid_wallet", "message": "bad wallet"}},
        ),
    )
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(AgentScoreError) as exc_info:
        client.associate_wallet(ASSOCIATE_TOKEN, "0xnope", ASSOCIATE_NETWORK)
    assert exc_info.value.code == "invalid_wallet"


@respx.mock
def test_associate_wallet_raises_on_402_payment_required():
    respx.post(f"{BASE_URL}/v1/credentials/wallets").mock(
        return_value=httpx.Response(
            402,
            json={"error": {"code": "payment_required", "message": "paid only"}},
        ),
    )
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(AgentScoreError) as exc_info:
        client.associate_wallet(ASSOCIATE_TOKEN, ASSOCIATE_WALLET, ASSOCIATE_NETWORK)
    assert exc_info.value.status_code == 402
    assert exc_info.value.code == "payment_required"


@pytest.mark.asyncio
@respx.mock
async def test_aassociate_wallet_returns_first_seen_true():
    respx.post(f"{BASE_URL}/v1/credentials/wallets").mock(
        return_value=httpx.Response(200, json={"associated": True, "first_seen": True}),
    )
    client = AgentScore(api_key=API_KEY)
    result = await client.aassociate_wallet(ASSOCIATE_TOKEN, ASSOCIATE_WALLET, ASSOCIATE_NETWORK)
    assert result == {"associated": True, "first_seen": True}
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_aassociate_wallet_sends_snake_case_body():
    route = respx.post(f"{BASE_URL}/v1/credentials/wallets").mock(
        return_value=httpx.Response(200, json={"associated": True, "first_seen": False}),
    )
    client = AgentScore(api_key=API_KEY)
    await client.aassociate_wallet(ASSOCIATE_TOKEN, ASSOCIATE_WALLET, ASSOCIATE_NETWORK)
    assert route.called
    body = json.loads(route.calls[0].request.content.decode())
    assert body == {
        "operator_token": ASSOCIATE_TOKEN,
        "wallet_address": ASSOCIATE_WALLET,
        "network": ASSOCIATE_NETWORK,
    }
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_aassociate_wallet_forwards_idempotency_key():
    route = respx.post(f"{BASE_URL}/v1/credentials/wallets").mock(
        return_value=httpx.Response(200, json={"associated": True, "first_seen": False, "deduped": True}),
    )
    client = AgentScore(api_key=API_KEY)
    result = await client.aassociate_wallet(
        ASSOCIATE_TOKEN, ASSOCIATE_WALLET, ASSOCIATE_NETWORK, idempotency_key="pi_abc"
    )
    assert result == {"associated": True, "first_seen": False, "deduped": True}
    body = json.loads(route.calls[0].request.content.decode())
    assert body["idempotency_key"] == "pi_abc"
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_aassociate_wallet_omits_empty_string_idempotency_key():
    route = respx.post(f"{BASE_URL}/v1/credentials/wallets").mock(
        return_value=httpx.Response(200, json={"associated": True, "first_seen": True}),
    )
    client = AgentScore(api_key=API_KEY)
    await client.aassociate_wallet(ASSOCIATE_TOKEN, ASSOCIATE_WALLET, ASSOCIATE_NETWORK, idempotency_key="")
    body = json.loads(route.calls[0].request.content.decode())
    assert "idempotency_key" not in body
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_aassociate_wallet_raises_on_401_invalid_credential():
    respx.post(f"{BASE_URL}/v1/credentials/wallets").mock(
        return_value=httpx.Response(
            401,
            json={"error": {"code": "invalid_credential", "message": "Operator credential not found"}},
        ),
    )
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(AgentScoreError) as exc_info:
        await client.aassociate_wallet(ASSOCIATE_TOKEN, ASSOCIATE_WALLET, ASSOCIATE_NETWORK)
    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "invalid_credential"
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_aassociate_wallet_raises_on_402_payment_required():
    respx.post(f"{BASE_URL}/v1/credentials/wallets").mock(
        return_value=httpx.Response(
            402,
            json={"error": {"code": "payment_required", "message": "paid only"}},
        ),
    )
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(AgentScoreError) as exc_info:
        await client.aassociate_wallet(ASSOCIATE_TOKEN, ASSOCIATE_WALLET, ASSOCIATE_NETWORK)
    assert exc_info.value.status_code == 402
    assert exc_info.value.code == "payment_required"
    await client.aclose()


# ---------------------------------------------------------------------------
# 429 retry-once parity with node-sdk (sync + async)
# ---------------------------------------------------------------------------


@respx.mock
def test_assess_retries_once_on_429_then_succeeds(monkeypatch):
    monkeypatch.setattr("agentscore.client.time.sleep", lambda _: None)
    route = respx.post(f"{BASE_URL}/v1/assess").mock(
        side_effect=[
            httpx.Response(429, headers={"retry-after": "0"}, json={}),
            httpx.Response(200, json={"address": ADDRESS, "decision": "allow"}),
        ],
    )
    client = AgentScore(api_key=API_KEY)
    result = client.assess(address=ADDRESS)
    assert route.call_count == 2
    assert result["decision"] == "allow"
    client.close()


@respx.mock
def test_assess_raises_when_429_persists_across_retry(monkeypatch):
    monkeypatch.setattr("agentscore.client.time.sleep", lambda _: None)
    route = respx.post(f"{BASE_URL}/v1/assess").mock(
        return_value=httpx.Response(429, headers={"retry-after": "0"}, json={}),
    )
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(AgentScoreError) as exc_info:
        client.assess(address=ADDRESS)
    assert route.call_count == 2
    assert exc_info.value.status_code == 429
    assert exc_info.value.code == "rate_limited"
    client.close()


@respx.mock
def test_assess_uses_default_wait_when_retry_after_missing(monkeypatch):
    captured: list[float] = []
    monkeypatch.setattr("agentscore.client.time.sleep", lambda s: captured.append(s))
    respx.post(f"{BASE_URL}/v1/assess").mock(
        side_effect=[
            httpx.Response(429, json={}),
            httpx.Response(200, json={"address": ADDRESS, "decision": "allow"}),
        ],
    )
    client = AgentScore(api_key=API_KEY)
    client.assess(address=ADDRESS)
    assert captured == [1.0]
    client.close()


@respx.mock
def test_assess_caps_retry_wait_at_10_seconds(monkeypatch):
    captured: list[float] = []
    monkeypatch.setattr("agentscore.client.time.sleep", lambda s: captured.append(s))
    respx.post(f"{BASE_URL}/v1/assess").mock(
        side_effect=[
            httpx.Response(429, headers={"retry-after": "9999"}, json={}),
            httpx.Response(200, json={"address": ADDRESS, "decision": "allow"}),
        ],
    )
    client = AgentScore(api_key=API_KEY)
    client.assess(address=ADDRESS)
    assert captured == [10.0]
    client.close()


@pytest.mark.asyncio
@respx.mock
async def test_aassess_retries_once_on_429_then_succeeds(monkeypatch):
    async def _no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("agentscore.client.asyncio.sleep", _no_sleep)
    route = respx.post(f"{BASE_URL}/v1/assess").mock(
        side_effect=[
            httpx.Response(429, headers={"retry-after": "0"}, json={}),
            httpx.Response(200, json={"address": ADDRESS, "decision": "allow"}),
        ],
    )
    client = AgentScore(api_key=API_KEY)
    result = await client.aassess(address=ADDRESS)
    assert route.call_count == 2
    assert result["decision"] == "allow"
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_aassess_raises_when_429_persists_across_retry(monkeypatch):
    async def _no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("agentscore.client.asyncio.sleep", _no_sleep)
    route = respx.post(f"{BASE_URL}/v1/assess").mock(
        return_value=httpx.Response(429, headers={"retry-after": "0"}, json={}),
    )
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(AgentScoreError) as exc_info:
        await client.aassess(address=ADDRESS)
    assert route.call_count == 2
    assert exc_info.value.status_code == 429
    await client.aclose()
