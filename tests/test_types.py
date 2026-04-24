"""Type-presence checks for denial codes, memory hints, and wallet-signer body types.

The real assertion is that the file type-checks under ty; pytest just exercises
the runtime shape so CI has something to run.
"""

from __future__ import annotations

from typing import get_args

from agentscore import (
    AgentMemoryHint,
    AgentScore,
    AgentScoreError,
    DenialCode,
    NextStepsAction,
    SessionCreateResponse,
    WalletAuthRequiresSigningBody,
    WalletSignerMismatchBody,
)


def test_denial_code_includes_new_values() -> None:
    codes = get_args(DenialCode)
    assert "wallet_signer_mismatch" in codes
    assert "wallet_auth_requires_wallet_signing" in codes
    assert "token_expired" in codes
    # Backward-compat: pre-1.9.0 codes still present.
    assert "operator_verification_required" in codes
    assert "compliance_denied" in codes


def test_next_steps_action_includes_new_values() -> None:
    actions = get_args(NextStepsAction)
    # Probe strategy (gate-emitted missing_identity).
    assert "probe_identity_then_session" in actions
    assert "resign_or_switch_to_operator_token" in actions
    assert "switch_to_operator_token" in actions
    assert "deliver_verify_url_and_poll" in actions
    # Session poll states.
    assert "continue_polling" in actions
    assert "retry_merchant_request_with_operator_token" in actions
    assert "use_stored_operator_token" in actions
    # Backward-compat: pre-1.9.0 actions still present.
    assert "mint_new_credential" in actions
    assert "use_operator_token" in actions
    assert "regenerate_payment_from_linked_wallet" in actions


def test_wallet_signer_mismatch_body_shape() -> None:
    body: WalletSignerMismatchBody = {
        "error": {"code": "wallet_signer_mismatch", "message": "signer does not match claimed wallet"},
        "claimed_operator": "op_abc",
        "actual_signer_operator": None,
        "expected_signer": "0x1111",
        "actual_signer": "0x2222",
        "linked_wallets": ["0x1111", "0x3333"],
        "next_steps": {"action": "regenerate_payment_from_linked_wallet", "user_message": "sign with linked"},
    }
    assert body["error"]["code"] == "wallet_signer_mismatch"
    assert len(body["linked_wallets"]) == 2


def test_wallet_auth_requires_signing_body_shape() -> None:
    body: WalletAuthRequiresSigningBody = {
        "error": {"code": "wallet_auth_requires_wallet_signing", "message": "SPT has no signer"},
        "next_steps": {"action": "use_operator_token", "signer_capable_rails": ["tempo", "x402"]},
    }
    assert body["error"]["code"] == "wallet_auth_requires_wallet_signing"
    assert "tempo" in body["next_steps"]["signer_capable_rails"]


def test_agent_memory_hint_shape() -> None:
    memory: AgentMemoryHint = {
        "save_for_future_agentscore_gates": True,
        "pattern_summary": "AgentScore is a cross-merchant identity layer",
        "quickstart": "https://docs.agentscore.sh/agent-commerce-quickstart",
        "identity_check_endpoint": "https://api.agentscore.sh/v1/credentials",
        "list_wallets_endpoint": "https://api.agentscore.sh/v1/credentials/wallets",
        "identity_paths": {
            "wallet": "send X-Wallet-Address when paying from a linked wallet",
            "operator_token": "send X-Operator-Token for any rail",
        },
        "bootstrap": "follow the session/verify flow if you have neither",
        "do_not_persist_in_memory": ["operator_token", "poll_secret"],
        "persist_in_credential_store": ["operator_token"],
    }
    assert memory["save_for_future_agentscore_gates"] is True
    assert "X-Wallet-Address" in memory["identity_paths"]["wallet"]


def test_session_create_response_accepts_agent_memory() -> None:
    res: SessionCreateResponse = {
        "session_id": "sess_abc",
        "poll_secret": "poll_abc",
        "verify_url": "https://agentscore.sh/verify?session=sess_abc",
        "poll_url": "https://api.agentscore.sh/v1/sessions/sess_abc",
        "expires_at": "2026-04-24T00:00:00Z",
        "agent_memory": {
            "save_for_future_agentscore_gates": True,
            "pattern_summary": "p",
            "quickstart": "q",
            "identity_check_endpoint": "e",
            "identity_paths": {"wallet": "w", "operator_token": "ot"},
            "bootstrap": "b",
            "do_not_persist_in_memory": [],
            "persist_in_credential_store": [],
        },
    }
    assert res["agent_memory"]["save_for_future_agentscore_gates"] is True


def test_sdk_exports_new_symbols() -> None:
    # Importability check — covered above via imports, but also guard the AgentScore class itself.
    assert AgentScore is not None
    assert AgentScoreError is not None
