"""Domain validation and rule failures (no HTTP)."""


class EngineValidationError(ValueError):
    """Raised when an intent or content package fails engine validation."""

    def __init__(self, message: str) -> None:
        """Store a human-readable validation message."""

        super().__init__(message)
        self.message = message
