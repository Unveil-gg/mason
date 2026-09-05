"""Structured errors for CLI and JSON mode."""

from __future__ import annotations

from typing import Any


class MasonError(Exception):
    """Actionable Mason failure with a machine-readable payload."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "mason_error",
        hint: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.hint = hint
        self.context = context or {}

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable error object."""
        payload: dict[str, Any] = {
            "success": False,
            "error": {
                "code": self.code,
                "message": self.message,
            },
        }
        if self.hint:
            payload["error"]["hint"] = self.hint
        if self.context:
            payload["error"]["context"] = self.context
        return payload
