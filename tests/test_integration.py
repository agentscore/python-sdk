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
