from __future__ import annotations

import asyncio
import logging
import time
from importlib.metadata import version as _pkg_version
from typing import TYPE_CHECKING, Any

import httpx

from agentscore.errors import AgentScoreError

logger = logging.getLogger("agentscore")

_IDEMPOTENCY_KEY_MAX = 200
_MAX_RETRY_WAIT_SECONDS = 10.0


def _retry_after_seconds(response: httpx.Response) -> float:
    raw = response.headers.get("retry-after", "1")
    try:
        return min(float(raw), _MAX_RETRY_WAIT_SECONDS)
    except (TypeError, ValueError):
        return 1.0


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
    """Client for the AgentScore trust and reputation API."""

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
        response = send_fn()
        if response.status_code == 429:
            time.sleep(_retry_after_seconds(response))
            response = send_fn()
        return self._handle_response(response)

    async def _send_async(self, send_fn: Callable[[], Awaitable[httpx.Response]]) -> Any:
        """Async variant of :meth:`_send_sync`."""
        response = await send_fn()
        if response.status_code == 429:
            await asyncio.sleep(_retry_after_seconds(response))
            response = await send_fn()
        return self._handle_response(response)

    def _handle_response(self, response: httpx.Response) -> Any:
        if response.status_code == 429:
            retry_after = response.headers.get("retry-after", "1")
            raise AgentScoreError(
                code="rate_limited",
                message=f"Rate limit exceeded. Retry after {retry_after}s",
                status_code=429,
            )
        if response.status_code >= 400:
            try:
                body = response.json()
                error = body.get("error", {}) if isinstance(body, dict) else {}
                # Preserve everything except the parsed `error` block so consumers
                # can read verify_url, linked_wallets, reasons, etc. for granular
                # denial recovery — exposed via AgentScoreError.details.
                details = {k: v for k, v in body.items() if k != "error"} if isinstance(body, dict) else {}
                raise AgentScoreError(
                    code=error.get("code", "unknown_error"),
                    message=error.get("message", response.text),
                    status_code=response.status_code,
                    details=details,
                )
            except ValueError as err:
                raise AgentScoreError(
                    code="unknown_error",
                    message=response.text,
                    status_code=response.status_code,
                ) from err
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
        refresh: bool = False,
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
        if refresh:
            body["refresh"] = True
        if policy is not None:
            body["policy"] = dict(policy)
        client = self._get_sync_client()
        return self._send_sync(lambda: client.post("/v1/assess", json=body))

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
        refresh: bool = False,
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
        if refresh:
            body["refresh"] = True
        if policy is not None:
            body["policy"] = dict(policy)
        client = self._get_async_client()
        return await self._send_async(lambda: client.post("/v1/assess", json=body))

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
