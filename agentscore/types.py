from __future__ import annotations

from typing import Any, Literal, TypedDict

Grade = Literal["A", "B", "C", "D", "F"]
EntityType = Literal["agent", "service", "hybrid", "wallet", "bot", "unknown"]
ReputationStatus = Literal["unknown", "known_unscored", "scored", "stale", "indexing"]


class Subject(TypedDict):
    chain: str
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
    status: ReputationStatus
    value: int | None
    grade: Grade | None
    confidence: float | None
    dimensions: dict[str, float] | None
    scored_at: str | None
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


class ReputationResponse(TypedDict):
    subject: Subject
    classification: Classification
    score: Score
    identity: Identity | None
    activity: Activity | None
    evidence_summary: dict[str, Any] | None
    data_semantics: str
    caveats: list[str]
    updated_at: str | None


class ReputationResponseFull(ReputationResponse, total=False):
    operator_score: OperatorScore
    agents: list[AgentSummary]


class DecisionPolicy(TypedDict, total=False):
    min_grade: Grade
    min_score: int
    require_verified_payment_activity: bool


class AssessResponse(TypedDict):
    subject: Subject
    classification: Classification
    score: Score
    identity: Identity | None
    activity: Activity | None
    evidence_summary: dict[str, Any] | None
    data_semantics: str
    caveats: list[str]
    updated_at: str | None
    decision: str | None
    decision_reasons: list[str]
    on_the_fly: bool


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
