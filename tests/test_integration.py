import os

import pytest

from agentscore import AgentScore

API_KEY = os.environ.get("AGENTSCORE_API_KEY")
BASE_URL = os.environ.get("AGENTSCORE_BASE_URL", "http://api.dev.agentscore.internal")
TEST_ADDRESS = "0x339559a2d1cd15059365fc7bd36b3047bba480e0"

pytestmark = pytest.mark.skipif(not API_KEY, reason="AGENTSCORE_API_KEY not set")


def test_get_reputation_shape():
    client = AgentScore(api_key=API_KEY, base_url=BASE_URL)
    rep = client.get_reputation(TEST_ADDRESS)

    assert "chains" in rep["subject"]
    assert isinstance(rep["subject"]["chains"], list)
    assert len(rep["subject"]["chains"]) > 0

    assert "value" in rep["score"]
    assert "grade" in rep["score"]
    assert "scored_at" in rep["score"]
    assert "status" in rep["score"]
    assert "version" in rep["score"]
    assert "confidence" not in rep["score"]
    assert "dimensions" not in rep["score"]

    assert "chains" in rep
    assert isinstance(rep["chains"], list)
    assert len(rep["chains"]) > 0

    chain = rep["chains"][0]
    assert "chain" in chain
    assert "score" in chain
    assert "classification" in chain
    assert "identity" in chain
    assert "activity" in chain
    assert "evidence_summary" in chain

    assert "agents" in rep
    assert isinstance(rep["agents"], list)


def test_get_reputation_chain_filter():
    client = AgentScore(api_key=API_KEY, base_url=BASE_URL)
    rep = client.get_reputation(TEST_ADDRESS, chain="base")

    assert rep["subject"]["chains"] == ["base"]
    assert len(rep["chains"]) == 1
    assert rep["chains"][0]["chain"] == "base"


def test_get_reputation_chain_entry_full_fields():
    client = AgentScore(api_key=API_KEY, base_url=BASE_URL)
    rep = client.get_reputation(TEST_ADDRESS)
    chain = rep["chains"][0]

    assert "confidence" in chain["score"]
    assert "dimensions" in chain["score"]
    assert "as_verified_payer" in chain["activity"]
    assert "active_days" in chain["activity"]
    assert "first_candidate_tx_at" in chain["activity"]


def test_get_reputation_metadata_fields():
    client = AgentScore(api_key=API_KEY, base_url=BASE_URL)
    rep = client.get_reputation(TEST_ADDRESS)

    assert "caveats" in rep
    assert "data_semantics" in rep
    assert "updated_at" in rep


def test_assess_operator_level():
    client = AgentScore(api_key=API_KEY, base_url=BASE_URL)
    result = client.assess(TEST_ADDRESS)

    assert "decision" in result
    assert isinstance(result["decision_reasons"], list)
    assert isinstance(result["chains"], list)
    assert isinstance(result["agents"], list)
    assert "classification" not in result


def test_assess_policy_deny():
    client = AgentScore(api_key=API_KEY, base_url=BASE_URL)
    result = client.assess(TEST_ADDRESS, policy={"min_score": 999})

    assert result["decision"] == "deny"
    assert len(result["decision_reasons"]) > 0


def test_get_reputation_operator_score():
    client = AgentScore(api_key=API_KEY, base_url=BASE_URL)
    rep = client.get_reputation(TEST_ADDRESS)

    if "operator_score" in rep and rep["operator_score"]:
        op = rep["operator_score"]
        assert isinstance(op["score"], int)
        assert isinstance(op["grade"], str)
        assert isinstance(op["agent_count"], int)
        assert isinstance(op["chains_active"], list)


def test_get_reputation_reputation_field():
    client = AgentScore(api_key=API_KEY, base_url=BASE_URL)
    rep = client.get_reputation(TEST_ADDRESS)

    if "reputation" in rep and rep["reputation"]:
        r = rep["reputation"]
        assert isinstance(r["feedback_count"], int)
        assert isinstance(r["client_count"], int)
