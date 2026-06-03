"""Validation result dataclasses."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ValidationIssue:
    row_id: str | int
    severity: str
    code: str
    message: str
    field: str | None = None
    value: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationResult:
    rows_read: int
    rows_valid: int
    rows_rejected: int
    issues: list[ValidationIssue] = field(default_factory=list)
    unresolved_entities: list[dict] = field(default_factory=list)
    duplicate_count: int = 0
    status: str = "passed"
