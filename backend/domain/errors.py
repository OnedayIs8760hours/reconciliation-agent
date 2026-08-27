from __future__ import annotations


class ReconciliationError(Exception):
    """Base class for user-facing reconciliation workflow errors."""


class BadRequestError(ReconciliationError):
    """The request payload is invalid or cannot be processed."""


class TaskNotFoundError(ReconciliationError):
    """The requested task does not exist."""


class ExternalServiceError(ReconciliationError):
    """A downstream service, such as an LLM provider, failed."""


class WorkflowExecutionError(ReconciliationError):
    """A deterministic reconciliation workflow failed."""
