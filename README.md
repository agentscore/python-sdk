# agentscore-py

[![PyPI version](https://img.shields.io/pypi/v/agentscore-py.svg)](https://pypi.org/project/agentscore-py/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Python client for the [AgentScore](https://agentscore.sh) trust and reputation API.

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
```

### Wallet resolution

`assess()` responses include `resolved_operator` and `linked_wallets` — all same-operator sibling wallets (claimed via SIWE or captured via prior `associate_wallet`). The list may mix EVM addresses (`0x...` lowercased) and Solana addresses (base58, case-preserved) for cross-chain operators; merchants doing wallet-signer-match checks should accept a payment signed by any address in the list, regardless of chain. The `address` parameter on `assess()` and `get_reputation()` accepts either format — network is auto-detected from the address shape.

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

### Verify webhook signatures

For merchants who receive HMAC-signed webhooks (Stripe-pattern `t=<unix>,v1=<hex>` header):

```python
from agentscore import verify_webhook_signature

result = verify_webhook_signature(
    payload=raw_request_body,            # raw bytes — capture before any JSON parse
    signature_header=request.headers.get("X-AgentScore-Signature", ""),
    secret=os.environ["AGENTSCORE_WEBHOOK_SECRET"],
)
if not result.valid:
    return {"error": result.reason}, 400
```

`reason` distinguishes transient (`timestamp_too_old`, `timestamp_in_future`) from permanent (`signature_mismatch`, `no_signatures`, `malformed_header`) failures. Default tolerance 300s; pass `tolerance_seconds=0` to skip timestamp checking. Uses `hmac.compare_digest` for constant-time comparison.

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

## Documentation

- [API Reference](https://docs.agentscore.sh)

## License

[MIT](LICENSE)
