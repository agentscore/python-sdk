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
# Authorization header
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
    assert route.calls.last.request.headers["authorization"] == "Bearer my-secret-key"


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
    policy = {"min_grade": "B", "min_score": 50, "require_verified_payment_activity": True}
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
