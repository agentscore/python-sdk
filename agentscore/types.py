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
    identity_method: Literal["wallet", "operator_token"]
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
    # Wallets linked to the same operator as the resolved identity. Populated on allow
    # responses; omitted on denials to avoid leaking the linked set for flagged operators.
    # Capped at 100 entries.
    linked_wallets: list[str]
    verify_url: str
    policy_result: PolicyResult | None
    explanation: NotRequired[list[PolicyExplanation]]


class SessionCreateRequest(TypedDict, total=False):
    context: str
    product_name: str


class SessionCreateNextSteps(TypedDict, total=False):
    """Structured action guidance on POST /v1/sessions success.

    action is always ``deliver_verify_url_and_poll`` — tells the agent to share verify_url
    with the user and poll poll_url with X-Poll-Secret until an operator_token is issued.
    """

    action: NextStepsAction
    poll_interval_seconds: int
    poll_secret_header: str
    steps: list[str]
    user_message: str


class _SessionCreateResponseRequired(TypedDict):
    session_id: str
    poll_secret: str
    verify_url: str
    poll_url: str
    expires_at: str


class SessionCreateResponse(_SessionCreateResponseRequired, total=False):
    # Structured next_steps with action=deliver_verify_url_and_poll.
    next_steps: SessionCreateNextSteps
    # Cross-merchant memory hint on first session creation.
    agent_memory: AgentMemoryHint


class SessionPollNextSteps(TypedDict, total=False):
    action: NextStepsAction
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


class _CredentialCreateResponseRequired(TypedDict):
    id: str
    label: str | None
    credential: str
    prefix: str
    created_at: str
    expires_at: str


class CredentialCreateResponse(_CredentialCreateResponseRequired, total=False):
    agent_memory: AgentMemoryHint


class AccountVerification(TypedDict, total=False):
    """Account-level KYC state surfaced by GET /v1/credentials (same shape the API emits)."""

    kyc_status: str
    kyc_verified_at: str | None
    jurisdiction: str | None
    age_verified: bool
    age_bracket: str | None
    sanctions_status: str | None
    operator_type: str | None


class CredentialListResponse(TypedDict):
    credentials: list[CredentialItem]
    account_verification: NotRequired[AccountVerification]


class CredentialRevokeResponse(TypedDict):
    id: str
    revoked: Literal[True]


class _CredentialCreateErrorNextSteps(TypedDict):
    action: NextStepsAction


class CredentialCreateErrorNextSteps(_CredentialCreateErrorNextSteps, total=False):
    user_message: str


class CredentialCreateErrorResponse(TypedDict):
    """409 response body when POST /v1/credentials is called before KYC completes."""

    error: dict  # {"code": "kyc_required", "message": str}
    verify_url: str
    next_steps: CredentialCreateErrorNextSteps


Network = Literal["evm", "solana"]
"""Key-derivation family for associate_wallet. EVM covers any EVM chain (Base, Tempo, Ethereum, …)
because EOA addresses derive from the same private key on every EVM chain. Solana lives in its own
namespace with a different key scheme."""


class AssociateWalletResponse(TypedDict):
    associated: bool
    first_seen: bool
    deduped: NotRequired[bool]
    # Cross-merchant pattern hint. Emitted only on the first wallet capture (first_seen=True)
    # so merchants can relay it once in a 402 body and LLM-hosted agents persist the pattern
    # to long-term memory. Absent on all subsequent captures.
    agent_memory: NotRequired[AgentMemoryHint]


# ---------------------------------------------------------------------------
# Denial codes
# ---------------------------------------------------------------------------


DenialCode = Literal[
    "operator_verification_required",
    "compliance_denied",
    "compliance_error",
    "wallet_not_trusted",
    "missing_identity",
    "identity_verification_required",
    "payment_required",
    "api_error",
    "kyc_required",
    # Wallet-signer binding — claimed X-Wallet-Address must resolve to the same operator
    # as the payment signer; wallet-auth is rejected on rails with no wallet signer.
    "wallet_signer_mismatch",
    "wallet_auth_requires_wallet_signing",
    # Credential is no longer valid (revoked or past its TTL — the two cases share this
    # code deliberately so the API doesn't leak which one). The 401 body carries an
    # auto-minted session so agents recover without holding an API key.
    "token_expired",
]
"""Denial codes returned by the gate in 403/402 error bodies. Lets agents pick the right
remediation without natural-language parsing."""


NextStepsAction = Literal[
    "poll_for_credential",
    "contact_support",
    "retry",
    "retry_once_then_contact_support",
    "regenerate_payment_credential",
    "none",
    "done",
    "use_operator_token",
    "regenerate_payment_from_linked_wallet",
    # Gate-emitted probe strategy — try wallet on signing rails, fall back to stored
    # opc_..., fall back to session flow. Emitted on bare missing_identity 403s.
    "probe_identity_then_session",
    # Wallet signer mismatch — re-sign from expected_signer / any linked_wallets entry,
    # or drop X-Wallet-Address and retry with X-Operator-Token.
    "resign_or_switch_to_operator_token",
    # Non-signing rail (Stripe SPT, card) — drop X-Wallet-Address, use X-Operator-Token.
    "switch_to_operator_token",
    # POST /v1/sessions success — deliver verify_url + poll poll_url.
    "deliver_verify_url_and_poll",
    # Session poll states.
    "continue_polling",
    "retry_merchant_request_with_operator_token",
    "use_stored_operator_token",
    "create_new_session",
    "verification_failed",
    "complete_kyc_then_retry",
]
"""Recommended agent action encoded in next_steps.action."""


class AgentMemoryIdentityPaths(TypedDict):
    wallet: str
    operator_token: str


class AgentMemoryHint(TypedDict):
    """Structured hint emitted on bootstrap denials and POST /v1/sessions success.

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


class _WalletSignerMismatchNextStepsRequired(TypedDict):
    action: NextStepsAction


class WalletSignerMismatchNextSteps(_WalletSignerMismatchNextStepsRequired, total=False):
    user_message: str
    learn_more_url: str


class _WalletSignerMismatchBodyRequired(TypedDict):
    error: dict  # {"code": "wallet_signer_mismatch", "message": str}
    claimed_operator: str
    actual_signer_operator: str | None
    linked_wallets: list[str]


class WalletSignerMismatchBody(_WalletSignerMismatchBodyRequired, total=False):
    """403 body for X-Wallet-Address + mismatched-signer rejections.

    Returned when the claimed wallet's operator doesn't match the payment signer's operator.
    actual_signer_operator is None if the signer isn't linked to any operator.

    Action copy surfaces via one of two paths:
    - ``agent_instructions``: JSON-encoded ``{action, steps, user_message}`` set by the
      gate's default marshaller (action is typically ``resign_or_switch_to_operator_token``).
    - ``next_steps``: structured object set by merchants who override the gate default
      (action may be ``regenerate_payment_from_linked_wallet`` or any NextStepsAction).

    Agents should check for whichever is present.
    """

    expected_signer: str
    actual_signer: str
    agent_instructions: str
    next_steps: WalletSignerMismatchNextSteps
    agent_memory: AgentMemoryHint


class _WalletAuthRequiresSigningNextStepsRequired(TypedDict):
    action: NextStepsAction


class WalletAuthRequiresSigningNextSteps(_WalletAuthRequiresSigningNextStepsRequired, total=False):
    user_message: str
    signer_capable_rails: list[str]
    learn_more_url: str


class _WalletAuthRequiresSigningBodyRequired(TypedDict):
    error: dict  # {"code": "wallet_auth_requires_wallet_signing", "message": str}


class WalletAuthRequiresSigningBody(_WalletAuthRequiresSigningBodyRequired, total=False):
    """403 body for X-Wallet-Address + signer-less rail rejections.

    Returned when X-Wallet-Address is used with a payment rail that has no wallet signer
    (SPT, card). Agent should switch to X-Operator-Token for those rails.

    Action copy surfaces via one of two paths:
    - ``agent_instructions``: JSON-encoded ``{action, steps, user_message}`` set by the
      gate's default marshaller (action is typically ``switch_to_operator_token``).
    - ``next_steps``: structured object set by merchants who override the gate default
      (action may be ``use_operator_token`` or any NextStepsAction).
    """

    agent_instructions: str
    next_steps: WalletAuthRequiresSigningNextSteps
    agent_memory: AgentMemoryHint
