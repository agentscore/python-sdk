# agentscore-py

[![PyPI version](https://img.shields.io/pypi/v/agentscore-py.svg)](https://pypi.org/project/agentscore-py/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Python client for the [AgentScore](https://agentscore.sh) trust and reputation API. Score, verify, and assess AI agent wallets in the [x402](https://github.com/coinbase/x402) payment ecosystem and [ERC-8004](https://eips.ethereum.org/EIPS/eip-8004) agent registry.

## Install

```bash
pip install agentscore-py
```

## Quick Start

```python
from agentscore import AgentScore

client = AgentScore(api_key="ask_...")

# Free reputation lookup
rep = client.get_reputation("0x1234...")
print(rep["grade"], rep["score"])

# Trust decision with policy
decision = client.get_decision("0x1234...", min_grade="C", min_transactions=5)
print(decision["decision"]["allow"])
```

### Async

```python
async with AgentScore(api_key="ask_...") as client:
    rep = await client.aget_reputation("0x1234...")
    print(rep["grade"])
```

### Context Manager

```python
with AgentScore(api_key="ask_...") as client:
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
- [ERC-8004 Standard](https://eips.ethereum.org/EIPS/eip-8004)
- [x402 Protocol](https://github.com/coinbase/x402)

## License

[MIT](LICENSE)
