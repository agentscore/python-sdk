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
    "subject": {"chain": "base", "address": ADDRESS},
    "classification": {
        "entity_type": "wallet",
        "confidence": 0.9,
        "is_known": True,
        "is_known_erc8004_agent": False,
        "has_candidate_payment_activity": True,
        "has_verified_payment_activity": False,
        "reasons": [],
    },
    "score": {
        "status": "scored",
        "value": 75,
        "grade": "B",
        "confidence": 0.85,
        "dimensions": None,
        "scored_at": "2024-01-01T00:00:00Z",
        "version": "1",
    },
    "identity": None,
    "activity": None,
    "evidence_summary": None,
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
def test_get_reputation_with_non_default_chain():
    route = respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(
        return_value=httpx.Response(200, json=REPUTATION_PAYLOAD)
    )
    client = AgentScore(api_key=API_KEY)
    client.get_reputation(ADDRESS, chain="ethereum")
    assert "chain=ethereum" in str(route.calls.last.request.url)


@respx.mock
def test_get_reputation_default_chain_omitted_from_params():
    route = respx.get(f"{BASE_URL}/v1/reputation/{ADDRESS}").mock(
        return_value=httpx.Response(200, json=REPUTATION_PAYLOAD)
    )
    client = AgentScore(api_key=API_KEY)
    client.get_reputation(ADDRESS, chain="base")
    # chain=base should NOT be included in the query string
    assert "chain" not in str(route.calls.last.request.url)


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
    import json

    body = json.loads(route.calls.last.request.content)
    assert body["address"] == ADDRESS


@respx.mock
def test_assess_with_refresh():
    route = respx.post(f"{BASE_URL}/v1/assess").mock(return_value=httpx.Response(200, json=ASSESS_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    client.assess(ADDRESS, refresh=True)
    import json

    body = json.loads(route.calls.last.request.content)
    assert body.get("refresh") is True


@respx.mock
def test_assess_with_non_default_chain():
    route = respx.post(f"{BASE_URL}/v1/assess").mock(return_value=httpx.Response(200, json=ASSESS_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    client.assess(ADDRESS, chain="ethereum")
    import json

    body = json.loads(route.calls.last.request.content)
    assert body["chain"] == "ethereum"


@respx.mock
def test_assess_default_chain_omitted_from_body():
    route = respx.post(f"{BASE_URL}/v1/assess").mock(return_value=httpx.Response(200, json=ASSESS_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    client.assess(ADDRESS, chain="base")
    import json

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
# get_agents
# ---------------------------------------------------------------------------

AGENTS_PAYLOAD = {
    "items": [
        {
            "chain": "base",
            "token_id": 1,
            "owner_address": "0xowner",
            "agent_wallet": None,
            "name": "Test Agent",
            "description": None,
            "metadata_quality": "complete",
            "score": 80,
            "grade": "A",
            "entity_type": "agent",
            "endpoint_count": 1,
            "website_url": None,
            "github_url": None,
            "has_candidate_payment_activity": True,
            "has_verified_payment_activity": True,
            "agents_sharing_owner": None,
            "updated_at": "2024-01-01T00:00:00Z",
        }
    ],
    "next_cursor": None,
    "count": 1,
    "version": "1",
}


@respx.mock
def test_get_agents_success():
    respx.get(f"{BASE_URL}/v1/agents").mock(return_value=httpx.Response(200, json=AGENTS_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    result = client.get_agents()
    assert result["count"] == 1
    assert result["items"][0]["name"] == "Test Agent"


@respx.mock
def test_get_agents_passes_filters():
    route = respx.get(f"{BASE_URL}/v1/agents").mock(return_value=httpx.Response(200, json=AGENTS_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    client.get_agents(chain="base", grade="A")
    url_str = str(route.calls.last.request.url)
    assert "chain=base" in url_str
    assert "grade=A" in url_str


@respx.mock
def test_get_agents_raises_on_error():
    respx.get(f"{BASE_URL}/v1/agents").mock(
        return_value=httpx.Response(
            500,
            json={"error": {"code": "server_error", "message": "Unexpected error"}},
        )
    )
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(AgentScoreError) as exc_info:
        client.get_agents()
    assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------

STATS_PAYLOAD = {
    "version": "1",
    "as_of_time": "2024-01-01T00:00:00Z",
    "data_semantics": "live",
    "erc8004": {"known_agents": 42, "by_chain": {"base": 42}, "metadata_quality_distribution": {}},
    "reputation": {
        "total_addresses": 1000,
        "scored_addresses": 500,
        "entity_distribution": {},
        "score_distribution": {},
    },
    "payments": {
        "addresses_with_candidate_payment_activity": 200,
        "addresses_with_verified_payment_activity": 100,
        "total_candidate_transactions": 5000,
        "total_verified_transactions": 3000,
        "verification_status_summary": {},
    },
    "caveats": [],
}


@respx.mock
def test_get_stats_success():
    respx.get(f"{BASE_URL}/v1/stats").mock(return_value=httpx.Response(200, json=STATS_PAYLOAD))
    client = AgentScore(api_key=API_KEY)
    result = client.get_stats()
    assert result["erc8004"]["known_agents"] == 42
    assert result["reputation"]["total_addresses"] == 1000


@respx.mock
def test_get_stats_raises_on_error():
    respx.get(f"{BASE_URL}/v1/stats").mock(
        return_value=httpx.Response(
            503,
            json={"error": {"code": "service_unavailable", "message": "Service down"}},
        )
    )
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(AgentScoreError) as exc_info:
        client.get_stats()
    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "service_unavailable"


# ---------------------------------------------------------------------------
# Authorization header
# ---------------------------------------------------------------------------


@respx.mock
def test_auth_header_is_sent():
    route = respx.get(f"{BASE_URL}/v1/stats").mock(return_value=httpx.Response(200, json=STATS_PAYLOAD))
    client = AgentScore(api_key="my-secret-key")
    client.get_stats()
    assert route.calls.last.request.headers["authorization"] == "Bearer my-secret-key"


# ---------------------------------------------------------------------------
# Error: missing error body fields fall back gracefully
# ---------------------------------------------------------------------------


@respx.mock
def test_error_missing_error_key_falls_back():
    respx.get(f"{BASE_URL}/v1/stats").mock(return_value=httpx.Response(400, json={"message": "bad request"}))
    client = AgentScore(api_key=API_KEY)
    with pytest.raises(AgentScoreError) as exc_info:
        client.get_stats()
    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "unknown_error"
