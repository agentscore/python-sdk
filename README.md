# agentscore-py

[![PyPI version](https://img.shields.io/pypi/v/agentscore-py.svg)](https://pypi.org/project/agentscore-py/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Python client for the [AgentScore](https://agentscore.sh) APIs.

## Install

```bash
pip install agentscore-py
```

## Quick Start

```python
from agentscore import AgentScore

client = AgentScore(api_key="as_live_...")

# Look up cached reputation (free)
rep = client.get_reputation("0x1234...")
print(rep["score"]["value"], rep["score"]["grade"])

# Filter to a specific chain
base_rep = client.get_reputation("0x1234...", chain="base")

# Identity gate with policy (paid)
gated = client.assess("0x1234...", policy={
    "require_kyc": True,
    "require_sanctions_clear": True,
    "min_age": 21,
})

if gated["decision"] == "deny":
    print(gated["decision_reasons"])  # ["kyc_required"]
    print(gated.get("verify_url"))    # URL for operator verification

# Check verification level
rep = client.get_reputation("0x1234...")
print(rep.get("verification_level"))  # "none" | "wallet_claimed" | "kyc_verified"
```

### Credential-Based Identity

Agents without wallets can use operator credentials for identity:

```python
result = client.assess(operator_token="opc_...")
print(result["decision"])  # "allow" | "deny"
```

### Verification Sessions

Bootstrap identity for first-time agents. The success body carries structured `next_steps` (with `action: "deliver_verify_url_and_poll"`) and a cross-merchant `agent_memory` hint. Poll responses carry `next_steps.action` from the typed `NextStepsAction` Literal (`continue_polling`, `retry_merchant_request_with_operator_token`, `use_stored_operator_token`, `create_new_session`, `verification_failed`, `contact_support`).

```python
session = client.create_session()
print(session["verify_url"], session["poll_url"], session["poll_secret"])
print(session["next_steps"]["action"])  # "deliver_verify_url_and_poll"

status = client.poll_session(session["session_id"], session["poll_secret"])
if status["status"] == "verified":
    print(status["operator_token"])  # "opc_..." — use for future requests

# Optional pre-association: attach the session to a known wallet or refresh KYC
# for an existing operator credential.
client.create_session(address="0x...")
client.create_session(operator_token="opc_...")  # KYC refresh
```

### Wallet resolution

`assess()` responses include `resolved_operator` and `linked_wallets` — all same-operator sibling wallets (claimed via SIWE or captured via prior `associate_wallet`). The list may mix EVM addresses (`0x...` lowercased) and Solana addresses (base58, case-preserved) for cross-chain operators; merchants doing wallet-signer-match checks should accept a payment signed by any address in the list, regardless of chain. The `address` parameter on `assess()` and `get_reputation()` accepts either format — network is auto-detected from the address shape.

### Server-side signer-match + sanctions screening

Pass `signer={"address", "network"}` on `assess()` / `aassess()` to opt into server-side wallet-signer-match and OFAC SDN wallet-address screening on the same call. The response carries two new verdicts:

```python
result = client.assess(
    "0xclaimed...",
    signer={"address": "0xsigner...", "network": "evm"},
    policy={"require_sanctions_clear": True},
)

# signer_match: wallet-binding verdict
#   kind: 'pass' | 'wallet_signer_mismatch' | 'wallet_auth_requires_wallet_signing'
#   plus claimed_operator / signer_operator / expected_signer / actual_signer /
#   linked_wallets / agent_instructions
match = result.get("signer_match")
if match and match.get("kind") == "wallet_signer_mismatch":
    # signer wallet resolves to a different operator than the claimed address
    ...

# signer_sanctions: OFAC SDN wallet-address verdict (discriminated union)
#   {"status": "clear"} | {"sanctioned": True, "ofac_label", "sdn_uid", "listed_at"}
#   | {"status": "unavailable"}
sanctions = result.get("signer_sanctions")
if sanctions and sanctions.get("sanctioned"):
    print("OFAC hit:", sanctions["ofac_label"], sanctions["sdn_uid"])
```

Under `policy.require_sanctions_clear`, the API flips `decision` to `deny` when `signer_sanctions` is `sanctioned: True` OR `status: "unavailable"` — `decision_reasons` will include `sanctions_flagged` or `sanctions_check_unavailable` respectively (fail-closed; OFAC strict-liability). Without the policy flag, both verdicts are informational.

Pass `signer["address"] = None` for rails without a wallet signer (Stripe SPT, card-only). The API responds with `signer_match["kind"] == "wallet_auth_requires_wallet_signing"` and a parsed `agent_instructions` block telling the agent to switch to `X-Operator-Token` auth — spread the block directly into a 403 body.

### Credential Management

```python
cred = client.create_credential(label="my-agent", ttl_days=7)
print(cred["credential"])  # shown once

credentials = client.list_credentials()
client.revoke_credential(cred["id"])
```

### Report an Agent's Wallet (Cross-Merchant Attribution)

After an agent authenticated via `operator_token` completes a payment, report the signer wallet so AgentScore can build a cross-merchant credential↔wallet profile. Fire-and-forget — `first_seen` is informational only. `network` is the key-derivation family: `"evm"` for any EVM chain (Base, Tempo, Ethereum, …) or `"solana"` for Solana.

```python
client.associate_wallet(
    operator_token="opc_...",
    wallet_address=signer_from_payment,  # e.g. EIP-3009 `from` or Tempo MPP DID address
    network="evm",
    idempotency_key=payment_intent_id,  # optional — agent retries of the same payment no-op
)
```

### Async

All methods have async variants prefixed with `a`:

```python
async with AgentScore(api_key="as_live_...") as client:
    rep = await client.aget_reputation("0x1234...")
    result = await client.aassess("0x1234...", policy={"require_kyc": True})

    # Identity model methods
    session = await client.acreate_session()
    status = await client.apoll_session(session["session_id"], session["poll_secret"])
    cred = await client.acreate_credential(label="my-agent")
    await client.alist_credentials()
    await client.arevoke_credential(cred["id"])
    await client.aassociate_wallet(
        operator_token="opc_...",
        wallet_address="0x...",
        network="evm",
    )
```

### Context Manager

```python
with AgentScore(api_key="as_live_...") as client:
    rep = client.get_reputation("0x1234...")
```

## Configuration

| Parameter     | Default                     | Description              |
|---------------|-----------------------------|--------------------------|
| `api_key`     | `None`                      | API key from [agentscore.sh](https://agentscore.sh) |
| `base_url`    | `https://api.agentscore.sh` | API base URL             |
| `timeout`     | `10.0`                      | Request timeout (seconds)|
| `user_agent`  | `None`                      | Prepended to the default `User-Agent` as `"{user_agent} (agentscore-py/{version})"`. Use to attribute API calls to your app. |

`AgentScoreError.status` is a property aliasing `.status_code` so polyglot codebases can use the same attribute name regardless of which SDK raised the error.

## Error Handling

```python
from agentscore import AgentScore, AgentScoreError

try:
    rep = client.get_reputation("0xinvalid")
except AgentScoreError as e:
    print(e.code, e.status_code, str(e))
```

`AgentScoreError.details` carries the rest of the response body — `verify_url`, `linked_wallets`, `claimed_operator`, `actual_signer`, `expected_signer`, `reasons`, `agent_memory` — so callers can branch on granular denial codes without re-parsing.

### Typed error classes

For status-code-specific recovery, the SDK raises typed subclasses of `AgentScoreError`. All inherit from `AgentScoreError` so existing `except AgentScoreError` still catches them.

| Class | Triggered by | What it adds |
|---|---|---|
| `PaymentRequiredError` | HTTP 402 | The endpoint is not enabled for this account |
| `TokenExpiredError` | HTTP 401 with `error.code = "token_expired"` | Parsed body fields on the instance: `verify_url`, `session_id`, `poll_secret`, `poll_url`, `next_steps`, `agent_memory` — recover without re-parsing `details` |
| `InvalidCredentialError` | HTTP 401 with `error.code = "invalid_credential"` | Permanent — switch tokens or restart |
| `QuotaExceededError` | HTTP 429 with `error.code = "quota_exceeded"` | Account-level cap reached; don't retry |
| `RateLimitedError` | HTTP 429 with `error.code = "rate_limited"` | Per-second sliding-window cap; retry after `Retry-After` |
| `TimeoutError` | `httpx.TimeoutException` (connect/read/write/pool timeout) | Distinct from generic network errors. Note: subclasses `AgentScoreError`, **not** the builtin `TimeoutError` — import explicitly from `agentscore.errors` to disambiguate. |

All non-timeout `httpx.HTTPError` (ConnectError, ProtocolError, NetworkError, etc.) are wrapped as `AgentScoreError(code="network_error", status_code=0)`.

```python
from agentscore import (
    AgentScore, AgentScoreError, TokenExpiredError, QuotaExceededError,
)
from agentscore.errors import TimeoutError as AgentScoreTimeoutError

try:
    client.assess("0xabc...", policy={"require_kyc": True})
except TokenExpiredError as e:
    print("Verify at:", e.verify_url, "poll with:", e.poll_secret)
except QuotaExceededError as e:
    print("Account quota reached — surface to user; don't retry.")
except AgentScoreTimeoutError:
    print("Network timeout — retry with backoff.")
except AgentScoreError as e:
    print(e.code, e.message)
```

## Quota observability

`assess()` (and `aassess()`) responses include an optional `quota` field captured from `X-Quota-Limit` / `X-Quota-Used` / `X-Quota-Reset` response headers. Use it to monitor approach-to-cap proactively (warn at 80%, alert at 95%) before a 429:

```python
result = client.assess("0xabc...", policy={"require_kyc": True})
quota = result.get("quota")
if quota and quota["limit"] and quota["used"]:
    pct = (quota["used"] / quota["limit"]) * 100
    if pct > 80:
        print(f"AgentScore quota at {pct:.1f}% — resets {quota['reset']}")
```

`quota` is absent when the API doesn't emit the headers (Enterprise / unlimited tiers). On a 429 response the SDK raises `QuotaExceededError` / `RateLimitedError` instead of returning a body, so `quota` is only readable on successful calls — drive proactive alerting off the success-path field.

## Telemetry

`telemetry_signer_match(payload)` and `atelemetry_signer_match(payload)` are fire-and-forget POSTs to `/v1/telemetry/signer-match` so AgentScore can track aggregate signer-binding behavior across merchants. Used internally by `agentscore-commerce`'s gate; available directly for custom integrations that perform their own wallet-signer-match checks.

## Documentation

- [API Reference](https://docs.agentscore.sh)

## License

[MIT](LICENSE)
