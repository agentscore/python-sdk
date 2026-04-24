from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

Grade = Literal["A", "B", "C", "D", "F"]
EntityType = Literal["agent", "service", "hybrid", "wallet", "bot", "unknown", "individual", "entity"]
ReputationStatus = Literal["scored", "stale", "known_unscored"]
VerificationLevel = Literal["none", "wallet_claimed", "kyc_verified"]


class _SubjectRequired(TypedDict):
    chains: list[str]


class Subject(_SubjectRequired, total=False):
    address: str
    credential_prefix: str


class Classification(TypedDict):
    entity_type: EntityType
    confidence: float | None
    is_known: bool
    is_known_erc8004_agent: bool
    has_candidate_payment_activity: bool
    has_verified_payment_activity: bool
    reasons: list[str]


class Score(TypedDict):
    value: float | None
    grade: Grade | None
    scored_at: str | None
    status: ReputationStatus
    version: str


class _ChainScoreRequired(TypedDict):
    value: float | None
    grade: Grade | None
    scored_at: str | None
    status: ReputationStatus
    version: str


class ChainScore(_ChainScoreRequired, total=False):
    confidence: float | None
    dimensions: dict[str, float] | None


class Identity(TypedDict):
    ens_name: str | None
    website_url: str | None
    github_url: str | None


class Activity(TypedDict):
    total_candidate_transactions: int
    total_verified_transactions: int
    as_candidate_payer: int
    as_candidate_payee: int
    as_verified_payer: int
    as_verified_payee: int
    counterparties_count: int
    active_days: int
    active_months: int
    first_candidate_tx_at: str | None
    last_candidate_tx_at: str | None
    first_verified_tx_at: str | None
    last_verified_tx_at: str | None


class Reputation(TypedDict):
    feedback_count: int
    client_count: int
    trust_avg: float | None
    uptime_avg: float | None
    activity_avg: float | None
    last_feedback_at: str | None


class EvidenceSummary(TypedDict):
    metadata_kind: str | None
    has_a2a_agent_card: bool
    website_url: str | None
    website_reachable: bool
    website_mentions_mcp: bool
    website_mentions_x402: bool
    github_url: str | None
    github_stars: int | None


class RedactedClassification(TypedDict):
    entity_type: EntityType


class _OperatorScoreRequired(TypedDict):
    score: float
    grade: Grade


class OperatorScore(_OperatorScoreRequired, total=False):
    agent_count: int
    chains_active: list[str]


class AgentSummary(TypedDict):
    token_id: int
    chain: str
    name: str | None
    score: float
    grade: Grade


class _ChainEntryRequired(TypedDict):
    chain: str
    score: ChainScore
    classification: Classification | RedactedClassification


class ChainEntry(_ChainEntryRequired, total=False):
    identity: Identity
    activity: Activity
    evidence_summary: EvidenceSummary


class _ReputationResponseRequired(TypedDict):
    subject: Subject
    score: Score
    chains: list[ChainEntry]
    data_semantics: str
    caveats: list[str]
    updated_at: str | None


class ReputationResponse(_ReputationResponseRequired, total=False):
    reputation: Reputation
    operator_score: OperatorScore
    agents: list[AgentSummary]
    verification_level: VerificationLevel


class _OperatorVerificationRequired(TypedDict):
    level: VerificationLevel


class OperatorVerification(_OperatorVerificationRequired, total=False):
    operator_type: str | None
    verified_at: str | None


class PolicyCheck(TypedDict, total=False):
    rule: str
    passed: bool
    required: object
    actual: object


class PolicyResult(TypedDict):
    all_passed: bool
    checks: list[PolicyCheck]


class DecisionPolicy(TypedDict, total=False):
    require_kyc: bool
    require_sanctions_clear: bool
    min_age: int
    blocked_jurisdictions: list[str]
    allowed_jurisdictions: list[str]


class _AssessResponseRequired(TypedDict):
    decision: str | None
    decision_reasons: list[str]
    identity_method: str
    on_the_fly: bool
    updated_at: str | None


class PolicyExplanation(TypedDict, total=False):
    rule: str
    passed: bool
    required: object
    actual: object
    message: str
    how_to_remedy: str | None


class AssessResponse(_AssessResponseRequired, total=False):
    operator_verification: OperatorVerification
    resolved_operator: str | None
    verify_url: str
    policy_result: PolicyResult | None
    explanation: NotRequired[list[PolicyExplanation]]


class SessionCreateRequest(TypedDict, total=False):
    context: str
    product_name: str


class _SessionCreateResponseRequired(TypedDict):
    session_id: str
    poll_secret: str
    verify_url: str
    poll_url: str
    expires_at: str


class SessionCreateResponse(_SessionCreateResponseRequired, total=False):
    # Cross-merchant memory hint on first session creation (TEC-227).
    agent_memory: AgentMemoryHint


class SessionPollNextSteps(TypedDict, total=False):
    action: str
    user_message: str
    header_name: str
    poll_interval_seconds: int
    eta_message: str
    # Present when action == "contact_support" (e.g. sanctions "flagged" status).
    support_email: str
    support_subject: str


class _SessionPollResponseRequired(TypedDict):
    session_id: str
    status: str


class SessionPollResponse(_SessionPollResponseRequired, total=False):
    operator_token: str
    completed_at: str
    next_steps: NotRequired[SessionPollNextSteps]
    retry_after_seconds: NotRequired[int]
    token_ttl_seconds: NotRequired[int]


class CredentialItem(TypedDict):
    id: str
    label: str | None
    prefix: str
    created_at: str
    expires_at: str | None
    last_used_at: str | None


class CredentialCreateResponse(TypedDict):
    id: str
    label: str | None
    credential: str
    prefix: str
    created_at: str
    expires_at: str | None


class CredentialListResponse(TypedDict):
    credentials: list[CredentialItem]
    account_verification: NotRequired[dict]


Network = Literal["evm", "solana"]
"""Key-derivation family for associate_wallet. EVM covers any EVM chain (Base, Tempo, Ethereum, …)
because EOA addresses derive from the same private key on every EVM chain. Solana lives in its own
namespace with a different key scheme."""


class AssociateWalletResponse(TypedDict):
    associated: bool
    first_seen: bool
    deduped: NotRequired[bool]


# ---------------------------------------------------------------------------
# Denial codes (TEC-226, TEC-218) — added in 1.9.0
# ---------------------------------------------------------------------------


DenialCode = Literal[
    # Pre-1.9.0
    "operator_verification_required",
    "compliance_denied",
    "compliance_error",
    "wallet_not_trusted",
    "missing_identity",
    "identity_verification_required",
    "payment_required",
    "api_error",
    "kyc_required",
    # Added in 1.9.0 (TEC-226)
    "wallet_signer_mismatch",
    "wallet_auth_requires_wallet_signing",
    # Added in 1.9.0 (TEC-218)
    "token_expired",
    "token_revoked",
]
"""Denial codes returned by the gate in 403/402 error bodies. Additive — old codes retained for
backward compat. New codes in 1.9.0 let agents pick the right remediation without natural-language
parsing."""


NextStepsAction = Literal[
    # Pre-1.9.0
    "poll_for_credential",
    "contact_support",
    "retry",
    "retry_once_then_contact_support",
    "regenerate_payment_credential",
    "none",
    "done",
    # Added in 1.9.0
    "send_existing_identity",
    "mint_new_credential",
    "use_operator_token",
    "regenerate_payment_from_linked_wallet",
]
"""Recommended agent action encoded in next_steps.action."""


class AgentMemoryIdentityPaths(TypedDict):
    wallet: str
    operator_token: str


class AgentMemoryHint(TypedDict):
    """Structured hint emitted on bootstrap denials and POST /v1/sessions success (TEC-227).

    LLM-hosted agents should save this to their long-term memory so future AgentScore encounters
    skip the cold-start session flow. Contents are the pattern, not secrets —
    do_not_persist_in_memory names bearer credentials that belong in a credential store.
    """

    save_for_future_agentscore_gates: bool
    pattern_summary: str
    quickstart: str
    identity_check_endpoint: str
    list_wallets_endpoint: NotRequired[str]
    identity_paths: AgentMemoryIdentityPaths
    bootstrap: str
    do_not_persist_in_memory: list[str]
    persist_in_credential_store: list[str]


class _WalletSignerMismatchNextSteps(TypedDict):
    action: Literal["regenerate_payment_from_linked_wallet"]


class WalletSignerMismatchNextSteps(_WalletSignerMismatchNextSteps, total=False):
    user_message: str
    learn_more_url: str


class _WalletSignerMismatchBodyRequired(TypedDict):
    error: dict  # {"code": "wallet_signer_mismatch", "message": str}
    claimed_operator: str
    actual_signer_operator: str | None
    linked_wallets: list[str]
    next_steps: WalletSignerMismatchNextSteps


class WalletSignerMismatchBody(_WalletSignerMismatchBodyRequired, total=False):
    """403 body for X-Wallet-Address + mismatched-signer rejections (TEC-226).

    Returned when the claimed wallet's operator doesn't match the payment signer's operator.
    actual_signer_operator is None if the signer isn't linked to any operator.
    """

    expected_signer: str
    actual_signer: str
    agent_memory: AgentMemoryHint


class _WalletAuthRequiresSigningNextSteps(TypedDict):
    action: Literal["use_operator_token"]


class WalletAuthRequiresSigningNextSteps(_WalletAuthRequiresSigningNextSteps, total=False):
    user_message: str
    signer_capable_rails: list[str]
    learn_more_url: str


class _WalletAuthRequiresSigningBodyRequired(TypedDict):
    error: dict  # {"code": "wallet_auth_requires_wallet_signing", "message": str}
    next_steps: WalletAuthRequiresSigningNextSteps


class WalletAuthRequiresSigningBody(_WalletAuthRequiresSigningBodyRequired, total=False):
    """403 body for X-Wallet-Address + signer-less rail rejections (TEC-226).

    Returned when X-Wallet-Address is used with a payment rail that has no wallet signer
    (SPT, card). Agent should switch to X-Operator-Token for those rails.
    """

    agent_memory: AgentMemoryHint
