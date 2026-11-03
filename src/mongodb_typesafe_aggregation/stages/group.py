from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from mongodb_typesafe_aggregation.constants import ID_FIELD
from mongodb_typesafe_aggregation.types import Stage
from mongodb_typesafe_aggregation.types.filter import resolve_filters


def group_stage(spec: Mapping[str, Any]) -> Stage:
    """Creates a ``$group`` aggregation stage to group documents by a field or expression.

    Args:
        spec: The ``_id`` to group by, and an accumulator for each output field.

    Returns:
        A MongoDB aggregation stage.

    Raises:
        ValueError: ``spec`` has no ``_id``.

    Example:
        >>> group_stage({"_id": "$category", "totalSales": {"$sum": "$sales"}})
        {'$group': {'_id': '$category', 'totalSales': {'$sum': '$sales'}}}
    """
    if ID_FIELD not in spec:
        raise ValueError("$group requires an '_id'; use None to group all documents together")
    return {"$group": resolve_filters(spec)}
