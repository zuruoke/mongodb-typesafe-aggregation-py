from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from mongodb_typesafe_aggregation.types import Stage
from mongodb_typesafe_aggregation.types.filter import resolve_filters


def match_stage(query: Mapping[str, Any]) -> Stage:
    """Creates a ``$match`` aggregation stage to filter documents based on a condition.

    Args:
        query: The filter condition to apply to the documents. ``FilterOperator`` values are
            built automatically.

    Returns:
        A MongoDB aggregation stage.

    Example:
        >>> match_stage({"status": "active", "price": filter(int).gt(700)})
        {'$match': {'status': 'active', 'price': {'$gt': 700}}}
    """
    return {"$match": resolve_filters(query)}
