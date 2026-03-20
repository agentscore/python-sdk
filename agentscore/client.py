from __future__ import annotations

from importlib.metadata import version as _pkg_version
from typing import TYPE_CHECKING, Any

import httpx

from agentscore.errors import AgentScoreError

if TYPE_CHECKING:
    from agentscore.types import (
        AgentsListResponse,
        AssessResponse,
        DecisionPolicy,
        ReputationResponse,
        StatsResponse,
    )


class AgentScore:
    """Client for the AgentScore trust and reputation API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.agentscore.sh",
        timeout: float = 10.0,
    ):
        if not api_key:
            raise ValueError("AgentScore API key is required. Get one at https://agentscore.sh/sign-up")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._sync_client: httpx.Client | None = None
        self._async_client: httpx.AsyncClient | None = None

    def _headers(self) -> dict:
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": f"agentscore-py/{_pkg_version('agentscore-py')}",
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

    def _handle_response(self, response: httpx.Response) -> dict:
        if response.status_code >= 400:
            try:
                body = response.json()
                error = body.get("error", {})
                raise AgentScoreError(
                    code=error.get("code", "unknown_error"),
                    message=error.get("message", response.text),
                    status_code=response.status_code,
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

    def get_reputation(self, address: str, chain: str = "base") -> ReputationResponse:
        """Get cached reputation for an address (free, read-only)."""
        params: dict[str, str] = {}
        if chain != "base":
            params["chain"] = chain
        client = self._get_sync_client()
        response = client.get(f"/v1/reputation/{address}", params=params)
        return self._handle_response(response)

    def assess(
        self,
        address: str,
        chain: str = "base",
        refresh: bool = False,
        policy: DecisionPolicy | None = None,
    ) -> AssessResponse:
        """Assess a wallet (paid, writes score on-the-fly)."""
        body: dict[str, Any] = {"address": address}
        if chain != "base":
            body["chain"] = chain
        if refresh:
            body["refresh"] = True
        if policy is not None:
            body["policy"] = dict(policy)
        client = self._get_sync_client()
        response = client.post("/v1/assess", json=body)
        return self._handle_response(response)

    def get_agents(self, **filters: Any) -> AgentsListResponse:
        """Browse ERC-8004 agents (free)."""
        params = {k: str(v).lower() if isinstance(v, bool) else str(v) for k, v in filters.items() if v is not None}
        client = self._get_sync_client()
        response = client.get("/v1/agents", params=params)
        return self._handle_response(response)

    def get_stats(self) -> StatsResponse:
        """Get ecosystem stats (free)."""
        client = self._get_sync_client()
        response = client.get("/v1/stats")
        return self._handle_response(response)

    # --- Async methods ---

    async def aget_reputation(self, address: str, chain: str = "base") -> ReputationResponse:
        """Get cached reputation for an address (free, read-only)."""
        params: dict[str, str] = {}
        if chain != "base":
            params["chain"] = chain
        client = self._get_async_client()
        response = await client.get(f"/v1/reputation/{address}", params=params)
        return self._handle_response(response)

    async def aassess(
        self,
        address: str,
        chain: str = "base",
        refresh: bool = False,
        policy: DecisionPolicy | None = None,
    ) -> AssessResponse:
        """Assess a wallet (paid, writes score on-the-fly)."""
        body: dict[str, Any] = {"address": address}
        if chain != "base":
            body["chain"] = chain
        if refresh:
            body["refresh"] = True
        if policy is not None:
            body["policy"] = dict(policy)
        client = self._get_async_client()
        response = await client.post("/v1/assess", json=body)
        return self._handle_response(response)

    async def aget_agents(self, **filters: Any) -> AgentsListResponse:
        """Browse ERC-8004 agents (free)."""
        params = {k: str(v).lower() if isinstance(v, bool) else str(v) for k, v in filters.items() if v is not None}
        client = self._get_async_client()
        response = await client.get("/v1/agents", params=params)
        return self._handle_response(response)

    async def aget_stats(self) -> StatsResponse:
        """Get ecosystem stats (free)."""
        client = self._get_async_client()
        response = await client.get("/v1/stats")
        return self._handle_response(response)

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
