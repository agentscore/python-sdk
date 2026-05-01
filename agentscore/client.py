from __future__ import annotations

import asyncio
import logging
import time
from importlib.metadata import version as _pkg_version
from typing import TYPE_CHECKING, Any

import httpx

from agentscore.errors import (
    AgentScoreError,
    InvalidCredentialError,
    PaymentRequiredError,
    QuotaExceededError,
    RateLimitedError,
    TimeoutError,
    TokenExpiredError,
)

logger = logging.getLogger("agentscore")

_IDEMPOTENCY_KEY_MAX = 200
_MAX_RETRY_WAIT_SECONDS = 10.0


def _retry_after_seconds(response: httpx.Response) -> float:
    raw = response.headers.get("retry-after", "1")
    try:
        return min(float(raw), _MAX_RETRY_WAIT_SECONDS)
    except (TypeError, ValueError):
        return 1.0


def _extract_quota(response: httpx.Response) -> dict[str, Any] | None:
    """Parse ``X-Quota-Limit``, ``X-Quota-Used``, ``X-Quota-Reset`` from response headers.

    Returns ``None`` when none of the three are present (Enterprise / unlimited tiers).
    Numeric fields fall back to ``None`` if the header is malformed; reset stays as a
    string ('never' or ISO-8601 timestamp).
    """
    headers = response.headers
    if not hasattr(headers, "get"):
        return None
    limit = headers.get("x-quota-limit")
    used = headers.get("x-quota-used")
    reset = headers.get("x-quota-reset")
    if limit is None and used is None and reset is None:
        return None
    return {"limit": _parse_quota_number(limit), "used": _parse_quota_number(used), "reset": reset}


def _parse_quota_number(raw: str | None) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _do_sync(send_fn: Callable[[], httpx.Response]) -> httpx.Response:
    """Execute the sync request, wrapping every httpx-layer failure in a typed AgentScoreError.

    ``httpx.TimeoutException`` (and subclasses: ConnectTimeout / ReadTimeout / WriteTimeout /
    PoolTimeout) becomes our :class:`TimeoutError`. Every other ``httpx.HTTPError`` (ConnectError,
    NetworkError, ProtocolError, etc.) becomes :class:`AgentScoreError` with ``code='network_error'``
    and ``status_code=0`` — parity with the node-sdk catch-all.
    """
    try:
        return send_fn()
    except httpx.TimeoutException as exc:
        raise TimeoutError(str(exc)) from exc
    except httpx.HTTPError as exc:
        raise AgentScoreError("network_error", str(exc), 0) from exc


async def _do_async(send_fn: Callable[[], Awaitable[httpx.Response]]) -> httpx.Response:
    """Async variant of :func:`_do_sync`."""
    try:
        return await send_fn()
    except httpx.TimeoutException as exc:
        raise TimeoutError(str(exc)) from exc
    except httpx.HTTPError as exc:
        raise AgentScoreError("network_error", str(exc), 0) from exc


def _build_error_from_response(response: httpx.Response) -> AgentScoreError:
    """Map a non-2xx ``httpx.Response`` to the right typed :class:`AgentScoreError` subclass.

    Reads the body to extract ``error.code`` for discrimination + the rest for ``details``.
    Falls through to a generic :class:`AgentScoreError` for codes the SDK doesn't have a
    dedicated subclass for.
    """
    code = "unknown_error"
    message = response.text
    details: dict[str, Any] = {}

    try:
        body = response.json()
        if isinstance(body, dict):
            error = body.get("error", {})
            if isinstance(error, dict):
                code = error.get("code", code)
                message = error.get("message", message)
            # Preserve everything except the parsed `error` block so consumers can read
            # verify_url, linked_wallets, reasons, etc. for granular denial recovery.
            details = {k: v for k, v in body.items() if k != "error"}
    except ValueError:
        # Body wasn't JSON or didn't have the expected shape — keep defaults.
        pass

    if response.status_code == 402:
        return PaymentRequiredError(message, details)
    if response.status_code == 401:
        if code == "token_expired":
            return TokenExpiredError(message, details)
        if code == "invalid_credential":
            return InvalidCredentialError(message, details)
    if response.status_code == 429:
        if code == "quota_exceeded":
            return QuotaExceededError(message, details)
        if code == "rate_limited":
            return RateLimitedError(message, details)
    return AgentScoreError(code, message, response.status_code, details)


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from agentscore.types import (
        AssessResponse,
        AssociateWalletResponse,
        CredentialCreateResponse,
        CredentialListResponse,
        CredentialRevokeResponse,
        DecisionPolicy,
        Network,
        ReputationResponse,
        SessionCreateResponse,
        SessionPollResponse,
    )


class AgentScore:
    """Client for the AgentScore APIs."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.agentscore.sh",
        timeout: float = 10.0,
        user_agent: str | None = None,
    ):
        if not api_key:
            raise ValueError("AgentScore API key is required. Get one at https://agentscore.sh/sign-up")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        default_ua = f"agentscore-py/{_pkg_version('agentscore-py')}"
        self.user_agent = f"{user_agent} ({default_ua})" if user_agent else default_ua
        self._sync_client: httpx.Client | None = None
        self._async_client: httpx.AsyncClient | None = None

    def _headers(self) -> dict:
        return {
            "Accept": "application/json",
            "X-API-Key": self.api_key,
            "User-Agent": self.user_agent,
        }

    def _get_sync_client(self) -> httpx.Client:
        if self._sync_client is None:
            self._sync_client = httpx.Client(
                base_url=self.base_url,
                headers=self._headers(),
                timeout=self.timeout,
            )
        return self._sync_client

    def _get_async_client(self) -> httpx.AsyncClient:
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._headers(),
                timeout=self.timeout,
            )
        return self._async_client

    def _send_sync(self, send_fn: Callable[[], httpx.Response]) -> Any:
        """Issue a request, retry once on 429 honoring retry-after, then parse."""
        response = _do_sync(send_fn)
        if response.status_code == 429:
            time.sleep(_retry_after_seconds(response))
            response = _do_sync(send_fn)
        return self._handle_response(response)

    def _send_sync_with_response(self, send_fn: Callable[[], httpx.Response]) -> tuple[Any, httpx.Response]:
        """Issue a request, retry once on 429, then return ``(parsed_body, response)``.

        Variant of :meth:`_send_sync` that exposes the raw ``httpx.Response`` so callers
        (e.g. :meth:`assess`) can read response headers like ``X-Quota-*``.
        """
        response = _do_sync(send_fn)
        if response.status_code == 429:
            time.sleep(_retry_after_seconds(response))
            response = _do_sync(send_fn)
        return self._handle_response(response), response

    async def _send_async(self, send_fn: Callable[[], Awaitable[httpx.Response]]) -> Any:
        """Async variant of :meth:`_send_sync`."""
        response = await _do_async(send_fn)
        if response.status_code == 429:
            await asyncio.sleep(_retry_after_seconds(response))
            response = await _do_async(send_fn)
        return self._handle_response(response)

    async def _send_async_with_response(
        self, send_fn: Callable[[], Awaitable[httpx.Response]]
    ) -> tuple[Any, httpx.Response]:
        """Async variant of :meth:`_send_sync_with_response`."""
        response = await _do_async(send_fn)
        if response.status_code == 429:
            await asyncio.sleep(_retry_after_seconds(response))
            response = await _do_async(send_fn)
        return self._handle_response(response), response

    def _handle_response(self, response: httpx.Response) -> Any:
        if response.status_code >= 400:
            raise _build_error_from_response(response)
        try:
            return response.json()
        except ValueError as err:
            raise AgentScoreError(
                code="invalid_response",
                message="Server returned invalid JSON on success response",
                status_code=response.status_code,
            ) from err

    # --- Sync methods ---

    def get_reputation(self, address: str, chain: str | None = None) -> ReputationResponse:
        """Get cached reputation for an address (free, read-only). Optionally filter by chain."""
        params: dict[str, str] = {}
        if chain:
            params["chain"] = chain
        client = self._get_sync_client()
        return self._send_sync(lambda: client.get(f"/v1/reputation/{address}", params=params))

    def assess(
        self,
        address: str | None = None,
        chain: str | None = None,
        refresh: bool | None = None,
        policy: DecisionPolicy | None = None,
        operator_token: str | None = None,
    ) -> AssessResponse:
        """Assess a wallet or operator (paid, writes score on-the-fly)."""
        body: dict[str, Any] = {}
        if address:
            body["address"] = address
        if operator_token:
            body["operator_token"] = operator_token
        if chain:
            body["chain"] = chain
        if refresh is not None:
            body["refresh"] = refresh
        if policy is not None:
            body["policy"] = dict(policy)
        client = self._get_sync_client()
        data, response = self._send_sync_with_response(lambda: client.post("/v1/assess", json=body))
        quota = _extract_quota(response)
        if quota is not None:
            data["quota"] = quota
        return data

    def create_session(
        self,
        context: str | None = None,
        product_name: str | None = None,
        address: str | None = None,
        operator_token: str | None = None,
    ) -> SessionCreateResponse:
        """Create an assessment session for deferred scoring.

        ``address`` pre-associates the session with a known wallet (EVM ``0x...`` or
        Solana base58). ``operator_token`` pre-associates with an existing ``opc_...`` —
        e.g. refresh KYC for a credential.
        """
        body: dict[str, Any] = {}
        if context is not None:
            body["context"] = context
        if product_name is not None:
            body["product_name"] = product_name
        if address is not None:
            body["address"] = address
        if operator_token is not None:
            body["operator_token"] = operator_token
        client = self._get_sync_client()
        return self._send_sync(lambda: client.post("/v1/sessions", json=body))

    def poll_session(self, session_id: str, poll_secret: str) -> SessionPollResponse:
        """Poll a session for its current status and result."""
        client = self._get_sync_client()
        return self._send_sync(
            lambda: client.get(
                f"/v1/sessions/{session_id}",
                headers={"X-Poll-Secret": poll_secret},
            ),
        )

    def create_credential(
        self,
        label: str | None = None,
        ttl_days: int | None = None,
    ) -> CredentialCreateResponse:
        """Create a new API credential."""
        body: dict[str, Any] = {}
        if label is not None:
            body["label"] = label
        if ttl_days is not None:
            body["ttl_days"] = ttl_days
        client = self._get_sync_client()
        return self._send_sync(lambda: client.post("/v1/credentials", json=body))

    def list_credentials(self) -> CredentialListResponse:
        """List all API credentials."""
        client = self._get_sync_client()
        return self._send_sync(lambda: client.get("/v1/credentials"))

    def revoke_credential(self, id: str) -> CredentialRevokeResponse:
        """Revoke an API credential by ID."""
        client = self._get_sync_client()
        return self._send_sync(lambda: client.delete(f"/v1/credentials/{id}"))

    def associate_wallet(
        self,
        operator_token: str,
        wallet_address: str,
        network: Network,
        idempotency_key: str | None = None,
    ) -> AssociateWalletResponse:
        """Report that a wallet paid under an operator credential.

        ``network`` is the key-derivation family (``"evm"`` or ``"solana"``) — EVM EOAs share
        identity across every EVM chain (Base, Tempo, Ethereum, …) so one value covers them all.

        ``idempotency_key`` is optional — pass a stable per-payment key (e.g., payment intent id,
        x402 tx hash) so agent retries of the same logical payment don't inflate transaction_count.

        Fire-and-forget friendly — the returned ``first_seen`` boolean is informational only.
        """
        body: dict[str, Any] = {
            "operator_token": operator_token,
            "wallet_address": wallet_address,
            "network": network,
        }
        # Truthy check (not `is not None`) so empty strings don't ship a useless key —
        # only forward when the key actually has content.
        if idempotency_key:
            if len(idempotency_key) > _IDEMPOTENCY_KEY_MAX:
                logger.warning(
                    "associate_wallet: idempotency_key longer than %d chars will be truncated server-side.",
                    _IDEMPOTENCY_KEY_MAX,
                )
            body["idempotency_key"] = idempotency_key
        client = self._get_sync_client()
        return self._send_sync(lambda: client.post("/v1/credentials/wallets", json=body))

    # --- Async methods ---

    async def aget_reputation(self, address: str, chain: str | None = None) -> ReputationResponse:
        """Get cached reputation for an address (free, read-only). Optionally filter by chain."""
        params: dict[str, str] = {}
        if chain:
            params["chain"] = chain
        client = self._get_async_client()
        return await self._send_async(lambda: client.get(f"/v1/reputation/{address}", params=params))

    async def aassess(
        self,
        address: str | None = None,
        chain: str | None = None,
        refresh: bool | None = None,
        policy: DecisionPolicy | None = None,
        operator_token: str | None = None,
    ) -> AssessResponse:
        """Assess a wallet or operator (paid, writes score on-the-fly)."""
        body: dict[str, Any] = {}
        if address:
            body["address"] = address
        if operator_token:
            body["operator_token"] = operator_token
        if chain:
            body["chain"] = chain
        if refresh is not None:
            body["refresh"] = refresh
        if policy is not None:
            body["policy"] = dict(policy)
        client = self._get_async_client()
        data, response = await self._send_async_with_response(lambda: client.post("/v1/assess", json=body))
        quota = _extract_quota(response)
        if quota is not None:
            data["quota"] = quota
        return data

    async def acreate_session(
        self,
        context: str | None = None,
        product_name: str | None = None,
        address: str | None = None,
        operator_token: str | None = None,
    ) -> SessionCreateResponse:
        """Create an assessment session for deferred scoring.

        ``address`` pre-associates the session with a known wallet (EVM ``0x...`` or
        Solana base58). ``operator_token`` pre-associates with an existing ``opc_...`` —
        e.g. refresh KYC for a credential.
        """
        body: dict[str, Any] = {}
        if context is not None:
            body["context"] = context
        if product_name is not None:
            body["product_name"] = product_name
        if address is not None:
            body["address"] = address
        if operator_token is not None:
            body["operator_token"] = operator_token
        client = self._get_async_client()
        return await self._send_async(lambda: client.post("/v1/sessions", json=body))

    async def apoll_session(self, session_id: str, poll_secret: str) -> SessionPollResponse:
        """Poll a session for its current status and result."""
        client = self._get_async_client()
        return await self._send_async(
            lambda: client.get(
                f"/v1/sessions/{session_id}",
                headers={"X-Poll-Secret": poll_secret},
            ),
        )

    async def acreate_credential(
        self,
        label: str | None = None,
        ttl_days: int | None = None,
    ) -> CredentialCreateResponse:
        """Create a new API credential."""
        body: dict[str, Any] = {}
        if label is not None:
            body["label"] = label
        if ttl_days is not None:
            body["ttl_days"] = ttl_days
        client = self._get_async_client()
        return await self._send_async(lambda: client.post("/v1/credentials", json=body))

    async def alist_credentials(self) -> CredentialListResponse:
        """List all API credentials."""
        client = self._get_async_client()
        return await self._send_async(lambda: client.get("/v1/credentials"))

    async def arevoke_credential(self, id: str) -> CredentialRevokeResponse:
        """Revoke an API credential by ID."""
        client = self._get_async_client()
        return await self._send_async(lambda: client.delete(f"/v1/credentials/{id}"))

    async def aassociate_wallet(
        self,
        operator_token: str,
        wallet_address: str,
        network: Network,
        idempotency_key: str | None = None,
    ) -> AssociateWalletResponse:
        """Async variant of :meth:`associate_wallet`."""
        body: dict[str, Any] = {
            "operator_token": operator_token,
            "wallet_address": wallet_address,
            "network": network,
        }
        # Truthy check (not `is not None`) so empty strings don't ship a useless key —
        # only forward when the key actually has content.
        if idempotency_key:
            if len(idempotency_key) > _IDEMPOTENCY_KEY_MAX:
                logger.warning(
                    "aassociate_wallet: idempotency_key longer than %d chars will be truncated server-side.",
                    _IDEMPOTENCY_KEY_MAX,
                )
            body["idempotency_key"] = idempotency_key
        client = self._get_async_client()
        return await self._send_async(lambda: client.post("/v1/credentials/wallets", json=body))

    def telemetry_signer_match(self, payload: dict[str, Any]) -> None:
        """Fire-and-forget telemetry — report a wallet-signer-match verdict.

        Used internally by the commerce gate's ``verify_wallet_signer_match`` helper to track
        aggregate signer-binding behavior across merchants. Does not raise; failures are
        logged at warning level so persistent telemetry outages are visible in ops logs.
        """
        try:
            client = self._get_sync_client()
            client.post("/v1/telemetry/signer-match", json=payload)
        except Exception as err:
            logger.warning("telemetry_signer_match failed: %s", err)

    async def atelemetry_signer_match(self, payload: dict[str, Any]) -> None:
        """Async variant of :meth:`telemetry_signer_match`."""
        try:
            client = self._get_async_client()
            await client.post("/v1/telemetry/signer-match", json=payload)
        except Exception as err:
            logger.warning("atelemetry_signer_match failed: %s", err)

    def close(self):
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None

    async def aclose(self):
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.aclose()
