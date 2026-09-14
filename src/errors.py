"""IRONCLAD Custom Exception Hierarchy.

Authoritative error taxonomy adhering to AGENT_BEHAVIOR_PROFILE.md and AGENT_LOGIC_SPEC.md.
"""

from typing import Any


class IroncladError(Exception):
    """Base exception for all domain and operational failures in IRONCLAD Sentinel."""

    def __init__(
        self,
        message: str,
        incident_context: dict[str, Any] | None = None,
        node_name: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.incident_context = incident_context or {}
        self.node_name = node_name

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "node_name": self.node_name,
            "incident_context": self.incident_context,
        }


class ToolExecutionError(IroncladError):
    """Raised when an external or deterministic tool fails during execution."""


class StateValidationError(IroncladError):
    """Raised when state mutation violates single-writer boundaries or schema invariants."""


class ApprovalTimeoutError(IroncladError):
    """Raised when a human-in-the-loop decision window expires or fails statutory bounds."""


class ProhibitedActionError(IroncladError):
    """Raised when an unauthorized action or tool boundary violation is attempted."""
