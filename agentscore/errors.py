from typing import Any


class AgentScoreError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        # Response-body fields beyond `error.{code,message}` — e.g. verify_url,
        # linked_wallets, claimed_operator, actual_signer, reasons. Consumers
        # branch on these for granular recovery (see the mcp denial-code rendering
        # in the node sibling for the canonical use). Defaults to {} so callers
        # constructing this error by hand without a body can omit it.
        self.details: dict[str, Any] = details or {}

    @property
    def status(self) -> int:
        """Alias for ``status_code`` — parity with node-sdk's attribute name.

        Polyglot codebases can use ``err.status`` regardless of which SDK raised the error.
        """
        return self.status_code


class PaymentRequiredError(AgentScoreError):
    """HTTP 402 — the endpoint is not enabled for this account."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("payment_required", message, 402, details)


class TokenExpiredError(AgentScoreError):
    """HTTP 401 with ``error.code = 'token_expired'`` — credential is no longer valid.

    Covers both revoked and TTL-expired credentials; the API deliberately doesn't disclose
    which. Body carries an auto-minted verification session — exposed here so callers recover
    without re-parsing ``details``.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("token_expired", message, 401, details)
        d = details or {}
        self.verify_url: str | None = d.get("verify_url") if isinstance(d.get("verify_url"), str) else None
        self.session_id: str | None = d.get("session_id") if isinstance(d.get("session_id"), str) else None
        self.poll_secret: str | None = d.get("poll_secret") if isinstance(d.get("poll_secret"), str) else None
        self.poll_url: str | None = d.get("poll_url") if isinstance(d.get("poll_url"), str) else None
        self.next_steps: Any = d.get("next_steps")
        self.agent_memory: Any = d.get("agent_memory")


class InvalidCredentialError(AgentScoreError):
    """HTTP 401 with ``error.code = 'invalid_credential'`` — operator_token doesn't exist.

    Permanent: no auto-session is issued. Caller should switch tokens or restart.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("invalid_credential", message, 401, details)


class QuotaExceededError(AgentScoreError):
    """HTTP 429 with ``error.code = 'quota_exceeded'`` — account-level cap reached.

    Don't retry; the cap won't lift through retry alone. Distinct from per-second
    :class:`RateLimitedError`.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("quota_exceeded", message, 429, details)


class RateLimitedError(AgentScoreError):
    """HTTP 429 with ``error.code = 'rate_limited'`` — per-second sliding-window cap hit.

    Retry after the interval indicated by the ``Retry-After`` header (typically <= 1s).
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("rate_limited", message, 429, details)


class TimeoutError(AgentScoreError):
    """Request timed out at the network layer (``httpx.TimeoutException``).

    Distinct from generic network errors so callers branch on retry vs surface-to-user
    without parsing message strings. Subclasses :class:`AgentScoreError` (not the builtin
    ``TimeoutError``) so existing ``except AgentScoreError`` blocks still catch it.
    """

    def __init__(self, message: str) -> None:
        super().__init__("timeout", message, 0)
