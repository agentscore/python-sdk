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

Bootstrap identity for first-time agents:

```python
session = client.create_session()
print(session["verify_url"], session["poll_secret"])

status = client.poll_session(session["session_id"], session["poll_secret"])
if status["status"] == "verified":
    print(status["operator_token"])  # "opc_..." — use for future requests
```

### Credential Management

```python
cred = client.create_credential(label="my-agent", ttl_days=7)
print(cred["credential"])  # shown once

credentials = client.list_credentials()
client.revoke_credential(cred["id"])
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
