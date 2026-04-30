import os

import pytest

from agentscore import AgentScore

API_KEY = os.environ.get("AGENTSCORE_API_KEY")
BASE_URL = os.environ.get("AGENTSCORE_BASE_URL")
TEST_ADDRESS = "0x339559a2d1cd15059365fc7bd36b3047bba480e0"

pytestmark = pytest.mark.skipif(
    not (API_KEY and BASE_URL),
    reason="AGENTSCORE_API_KEY and AGENTSCORE_BASE_URL must both be set",
)


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


def test_assess_flat_decision_shape():
    client = AgentScore(api_key=API_KEY, base_url=BASE_URL)
    result = client.assess(TEST_ADDRESS)

    assert "decision" in result
    assert isinstance(result["decision_reasons"], list)
    assert result["identity_method"] == "wallet"
    assert "operator_verification" in result


def test_assess_policy_deny():
    client = AgentScore(api_key=API_KEY, base_url=BASE_URL)
    result = client.assess(TEST_ADDRESS, policy={"require_kyc": True})

    assert result["decision"] == "deny"
    assert "kyc_required" in result["decision_reasons"]
    assert "verify_url" in result
    assert "/verify" in result["verify_url"]


def test_get_reputation_operator_score():
    client = AgentScore(api_key=API_KEY, base_url=BASE_URL)
    rep = client.get_reputation(TEST_ADDRESS)
    op = rep.get("operator_score")
    if not op:
        pytest.skip("no operator_score on test address")
    assert isinstance(op["score"], int)
    assert isinstance(op["grade"], str)
    assert isinstance(op["agent_count"], int)
    assert isinstance(op["chains_active"], list)


def test_assess_then_get_reputation():
    client = AgentScore(api_key=API_KEY, base_url=BASE_URL)
    assessed = client.assess(TEST_ADDRESS)
    assert "decision" in assessed

    rep = client.get_reputation(TEST_ADDRESS)
    assert "value" in rep["score"]
    assert isinstance(rep["score"]["value"], (int, float))
    assert rep["subject"]["address"].lower() == TEST_ADDRESS.lower()
