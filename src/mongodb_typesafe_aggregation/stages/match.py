from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from mongodb_typesafe_aggregation.types import Stage


def match_stage(query: Mapping[str, Any]) -> Stage:
    """Creates a ``$match`` aggregation stage to filter documents based on a condition.

    Args:
        query: The filter condition to apply to the documents.

    Returns:
        A MongoDB aggregation stage.

    Example:
        >>> match_stage({"status": "active"})
        {'$match': {'status': 'active'}}
    """
    return {"$match": dict(query)}
