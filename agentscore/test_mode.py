"""Recognizers for AgentScore reserved test addresses.

AgentScore's ``/v1/assess`` endpoint recognizes seven EVM addresses
(``0x0000…0001`` through ``0x0000…0007``) as test fixtures with deterministic
policy outcomes — KYC verified, sanctions clear, age gates passing — so dev/test
interactions don't burn real KYC credits and produce predictable results.

Use this in test suites and dev/staging tooling to label test-mode interactions
distinctly from production traffic.
"""

from __future__ import annotations

_TEST_ADDRESSES: frozenset[str] = frozenset(
    {
        "0x0000000000000000000000000000000000000001",
        "0x0000000000000000000000000000000000000002",
        "0x0000000000000000000000000000000000000003",
        "0x0000000000000000000000000000000000000004",
        "0x0000000000000000000000000000000000000005",
        "0x0000000000000000000000000000000000000006",
        "0x0000000000000000000000000000000000000007",
    },
)

AGENTSCORE_TEST_ADDRESSES: tuple[str, ...] = tuple(sorted(_TEST_ADDRESSES))
"""The full list of reserved test addresses, exposed for documentation, completion,
and downstream test fixtures."""


def is_agentscore_test_address(address: str | None) -> bool:
    """Recognize one of the seven reserved AgentScore EVM test fixtures.

    Lowercases for comparison so accidentally mixed-case input still matches.
    """
    if not address:
        return False
    return address.lower() in _TEST_ADDRESSES


__all__ = ["AGENTSCORE_TEST_ADDRESSES", "is_agentscore_test_address"]
