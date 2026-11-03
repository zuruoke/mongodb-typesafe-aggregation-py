from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def compact(**options: Any) -> dict[str, Any]:
    """Returns the options that were given, dropping those left as ``None``."""
    return {key: value for key, value in options.items() if value is not None}


def require_fields(spec: Mapping[str, Any], stage: str) -> None:
    """Raises ``ValueError`` if a stage specification is empty."""
    if not spec:
        raise ValueError(f"{stage} requires at least one field")


def require_int(value: int, stage: str, *, minimum: int) -> None:
    """Raises ``ValueError`` unless ``value`` is an int of at least ``minimum``."""
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{stage} requires an integer >= {minimum}, got {value!r}")
