# agentscore-py

Python client for the AgentScore APIs.

## Identity Model

Two identity paths: `X-Wallet-Address` (wallet-based) and `X-Operator-Token` (credential-based). Wallet addresses accept both EVM (`0x...` 40-hex) and Solana (base58, 32–44 chars) formats — network is auto-detected from the address shape. `assess` responses include `resolved_operator` and `linked_wallets[]` (same-operator sibling wallets, normalized per network — EVM lowercased, Solana base58 verbatim; may mix chains for cross-chain operators). `create_session` and `create_credential` responses include an `agent_memory` cross-merchant pattern hint. `create_session` also returns `next_steps.action="deliver_verify_url_and_poll"` + polling instructions. `poll_session` returns `next_steps.action` values: `continue_polling`, `retry_merchant_request_with_operator_token`, `use_stored_operator_token`, `create_new_session`, `verification_failed`, `contact_support`.

## Methods (sync + async)

- `get_reputation` / `aget_reputation` — cached reputation lookup (free)
- `assess` / `aassess` — identity gate with policy (paid). Accepts `operator_token` for non-wallet agents. Response includes `linked_wallets[]` and `resolved_operator`.
- `create_session` / `acreate_session` — create verification session. Returns `agent_memory` + `next_steps`.
- `poll_session` / `apoll_session` — poll session status, returns credential when verified, plus `next_steps.action`.
- `create_credential` / `acreate_credential` — create operator credential (24h TTL default). Response includes `agent_memory`.
- `list_credentials` / `alist_credentials` — list active credentials
- `revoke_credential` / `arevoke_credential` — revoke a credential
- `associate_wallet` / `aassociate_wallet` — report a signer wallet seen paying under a credential. Accepts optional `idempotency_key` (payment intent id / tx hash) so retries don't inflate transaction_count.
- `telemetry_signer_match` / `atelemetry_signer_match` — fire-and-forget POST to `/v1/telemetry/signer-match`; commerce gate uses this to report `pass` / `wallet_signer_mismatch` / `wallet_auth_requires_wallet_signing` verdicts.

## Errors + observability

Typed error subclasses of `AgentScoreError` so callers can `except` on the specific class without parsing `err.code`: `PaymentRequiredError` (402), `TokenExpiredError` (401 token_expired — exposes parsed `verify_url` / `session_id` / `poll_secret` / `poll_url` / `next_steps` / `agent_memory` instance attributes), `InvalidCredentialError` (401 invalid_credential), `QuotaExceededError` (429 quota_exceeded — don't retry), `RateLimitedError` (429 rate_limited — retry after Retry-After), `TimeoutError` (httpx.TimeoutException — note: subclasses `AgentScoreError`, not the builtin; import explicitly from `agentscore.errors` to disambiguate). All non-timeout `httpx.HTTPError` (ConnectError, ProtocolError, NetworkError, etc.) wrap to `AgentScoreError(code="network_error", status_code=0)` for parity with node-sdk.

`assess()` / `aassess()` responses include an optional `quota` field captured from `X-Quota-Limit` / `X-Quota-Used` / `X-Quota-Reset` response headers, so callers can monitor approach-to-cap proactively before hitting 429.

## Architecture

Single-package Python library published to PyPI.

| File | Purpose |
|------|---------|
| `agentscore/` | Source code |
| `tests/` | pytest tests |

## Tooling

- **uv** — package manager. Use `uv sync`, `uv run`.
- **ruff** — linting + formatting. `uv run ruff check .` and `uv run ruff format --check .`.
- **ty** — type checker (Astral). `uv run ty check agentscore/`.
- **vulture** — dead code detection.
- **pytest** — tests. `uv run pytest tests/`.
- **Lefthook** — git hooks. Pre-commit: ruff. Pre-push: ty + vulture (parallel).

## Key Commands

```bash
uv sync --all-extras
uv run lefthook install   # one-time per clone — wires pre-commit + pre-push
uv run ruff check .
uv run ruff format .
uv run ty check agentscore/
uv run pytest tests/
```

## Workflow

1. Create a branch
2. Make changes
3. Lefthook runs ruff on commit, ty + vulture on push
4. Open a PR — CI runs automatically
5. Merge (squash)

## Rules

- **No silent refactors**
- **Never commit .env files or secrets**
- **Use PRs** — never push directly to main

## Releasing

1. Update `version` in `pyproject.toml`
2. Commit: `git commit -am "chore: bump to vX.Y.Z"`
3. Tag: `git tag vX.Y.Z`
4. Push: `git push && git push origin vX.Y.Z`

The publish workflow runs on `ubuntu-latest` (required for PyPI trusted publishing), builds, publishes to PyPI via OIDC, and creates a GitHub Release.
