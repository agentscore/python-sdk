class AgentScoreError(Exception):
    def __init__(self, code: str, message: str, status_code: int):
        super().__init__(message)
        self.code = code
        self.status_code = status_code

    @property
    def status(self) -> int:
        """Alias for ``status_code`` — parity with node-sdk's attribute name.

        Polyglot codebases can use ``err.status`` regardless of which SDK raised the error.
        """
        return self.status_code
