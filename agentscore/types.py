from __future__ import annotations

from typing import Literal, TypedDict

Grade = Literal["A", "B", "C", "D", "F"]
EntityType = Literal["agent", "service", "hybrid", "wallet", "bot", "unknown"]
ReputationStatus = Literal["unknown", "known_unscored", "scored", "stale", "indexing"]


class Subject(TypedDict):
    chains: list[str]
    address: str


class Classification(TypedDict):
    entity_type: EntityType
    confidence: float | None
    is_known: bool
    is_known_erc8004_agent: bool
    has_candidate_payment_activity: bool
    has_verified_payment_activity: bool
    reasons: list[str]


class Score(TypedDict):
    value: int | None
    grade: Grade | None
    scored_at: str | None
    status: ReputationStatus
    version: str


class ChainScore(TypedDict):
    value: int | None
    grade: Grade | None
    confidence: float | None
    dimensions: dict[str, float] | None
    scored_at: str | None
    status: ReputationStatus
    version: str


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


class EvidenceSummary(TypedDict, total=False):
    candidate_tx_count: int
    confirmed_or_likely_tx: int
    endpoint_count: int
    github_stars: int
    github_url: str | None
    has_a2a_agent_card: bool
    has_ens: bool
    has_github: bool
    has_website: bool
    healthy_endpoints: int
    is_erc8004: bool
    metadata_kind: str | None
    metadata_quality: str | None
    multi_chain_count: int
    reputation_feedback_count: int
    reputation_trust_avg: float | None
    reputation_uptime_avg: float | None
    reputation_activity_avg: float | None
    reputation_client_count: int
    verified_tx_count: int
    website_mentions_mcp: bool
    website_mentions_x402: bool
    website_reachable: bool
    website_url: str | None


class OperatorScore(TypedDict):
    score: int
    grade: Grade
    agent_count: int
    chains_active: list[str]


class AgentSummary(TypedDict):
    token_id: int
    chain: str
    name: str | None
    score: int
    grade: Grade


class ChainEntry(TypedDict):
    chain: str
    score: ChainScore
    classification: Classification
    identity: Identity
    activity: Activity
    evidence_summary: EvidenceSummary


class ReputationResponse(TypedDict):
    subject: Subject
    score: Score
    chains: list[ChainEntry]
    data_semantics: str
    caveats: list[str]
    updated_at: str | None


class ReputationResponseFull(ReputationResponse, total=False):
    operator_score: OperatorScore
    agents: list[AgentSummary]
    reputation: Reputation


class DecisionPolicy(TypedDict, total=False):
    min_grade: Grade
    min_score: int
    require_verified_payment_activity: bool


class AssessResponse(TypedDict):
    subject: Subject
    score: Score
    chains: list[ChainEntry]
    decision: str | None
    decision_reasons: list[str]
    on_the_fly: bool
    data_semantics: str
    caveats: list[str]
    updated_at: str | None
    operator_score: OperatorScore | None
    reputation: Reputation | None
    agents: list[AgentSummary]


class AgentRecord(TypedDict):
    chain: str
    token_id: int
    owner_address: str
    agent_wallet: str | None
    name: str | None
    description: str | None
    metadata_quality: str
    score: int | None
    grade: Grade | None
    entity_type: EntityType | None
    endpoint_count: int
    website_url: str | None
    github_url: str | None
    has_candidate_payment_activity: bool
    has_verified_payment_activity: bool
    agents_sharing_owner: int | None
    updated_at: str


class AgentsListResponse(TypedDict):
    items: list[AgentRecord]
    next_cursor: str | None
    count: int
    version: str


class StatsPayments(TypedDict):
    addresses_with_candidate_payment_activity: int
    addresses_with_verified_payment_activity: int
    total_candidate_transactions: int
    total_verified_transactions: int
    verification_status_summary: dict[str, int]


class StatsERC8004(TypedDict):
    known_agents: int
    by_chain: dict[str, int]
    metadata_quality_distribution: dict[str, int]


class StatsReputation(TypedDict):
    total_addresses: int
    scored_addresses: int
    entity_distribution: dict[str, int]
    score_distribution: dict[str, int]


class StatsResponse(TypedDict, total=False):
    version: str
    as_of_time: str
    data_semantics: str
    erc8004: StatsERC8004
    reputation: StatsReputation
    payments: StatsPayments
    caveats: list[str]
