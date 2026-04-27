from typing import Any


class AgentScoreError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        # Response-body fields beyond `error.{code,message}` — e.g. verify_url,
        # linked_wallets, claimed_operator, actual_signer, reasons. Consumers
        # branch on these for granular recovery (see the mcp denial-code rendering
        # in the node sibling for the canonical use). Defaults to {} so callers
        # constructing this error by hand without a body can omit it.
        self.details: dict[str, Any] = details or {}

    @property
    def status(self) -> int:
        """Alias for ``status_code`` — parity with node-sdk's attribute name.

        Polyglot codebases can use ``err.status`` regardless of which SDK raised the error.
        """
        return self.status_code
