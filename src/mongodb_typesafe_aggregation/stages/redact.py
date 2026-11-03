from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from mongodb_typesafe_aggregation.types import Stage
from mongodb_typesafe_aggregation.types.filter import resolve_filters


def redact_stage(expression: str | Mapping[str, Any]) -> Stage:
    """Creates a ``$redact`` aggregation stage to restrict document content.

    Args:
        expression: An expression that evaluates to ``"$$DESCEND"``, ``"$$PRUNE"`` or
            ``"$$KEEP"`` at each level of the document.

    Returns:
        A MongoDB aggregation stage.

    Example:
        >>> redact_stage({"$cond": [{"$eq": ["$level", 5]}, "$$PRUNE", "$$DESCEND"]})
        {'$redact': {'$cond': [{'$eq': ['$level', 5]}, '$$PRUNE', '$$DESCEND']}}
    """
    return {"$redact": resolve_filters(expression)}
