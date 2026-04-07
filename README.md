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

# On-the-fly assessment with policy (paid)
result = client.assess("0x1234...", policy={"min_grade": "B", "min_score": 35})
print(result["decision"], result["decision_reasons"])

# Compliance assessment with verification policy
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

### Async

```python
async with AgentScore(api_key="as_live_...") as client:
    rep = await client.aget_reputation("0x1234...")
    result = await client.aassess("0x1234...", policy={"min_grade": "B"})
```

### Context Manager

```python
with AgentScore(api_key="as_live_...") as client:
    rep = client.get_reputation("0x1234...")
```

## Configuration

| Parameter  | Default                     | Description              |
|------------|----------------------------|--------------------------|
| `api_key`  | `None`                     | API key from [agentscore.sh](https://agentscore.sh) |
| `base_url` | `https://api.agentscore.sh` | API base URL             |
| `timeout`  | `10.0`                     | Request timeout (seconds)|

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
