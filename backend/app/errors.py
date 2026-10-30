from typing import Any


class DomainError(Exception):
    code: str = "domain_error"

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class NotFound(DomainError):
    code = "not_found"


class Conflict(DomainError):
    code = "conflict"


class InvalidTransition(DomainError):
    code = "invalid_transition"


class GateBlocked(DomainError):
    code = "gate_blocked"


class ExternalServiceError(DomainError):
    code = "external_service_error"
