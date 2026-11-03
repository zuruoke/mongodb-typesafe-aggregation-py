from __future__ import annotations

import difflib
from collections.abc import Iterable


class UnknownFieldError(ValueError):
    """Raised when a stage references a field that the current schema does not declare.

    Attributes:
        field: The unknown top-level field name.
        path: The full path as written, e.g. ``"produt.name"``.
        stage: The stage the field was used in, e.g. ``"$match"``.
        known: The field names the schema does declare.
    """

    def __init__(self, field: str, stage: str, known: Iterable[str], path: str | None = None):
        self.field = field
        self.path = path or field
        self.stage = stage
        self.known = frozenset(known)

        known_sorted = sorted(self.known)
        source = f" (from {self.path!r})" if self.path != field else ""
        message = f"Unknown field {field!r}{source} in {stage}."
        suggestions = difflib.get_close_matches(field, known_sorted, n=1)
        if suggestions:
            message += f" Did you mean {suggestions[0]!r}?"
        message += f" Known fields: {', '.join(known_sorted)}."
        super().__init__(message)
