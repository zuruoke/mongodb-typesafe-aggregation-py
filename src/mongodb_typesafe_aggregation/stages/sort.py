from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypeAlias

from mongodb_typesafe_aggregation.stages._utils import require_fields
from mongodb_typesafe_aggregation.types import Stage

SortOrder: TypeAlias = "Literal[1, -1] | Mapping[str, Any]"
"""``1`` for ascending, ``-1`` for descending, or a ``{"$meta": ...}`` sort."""


def sort_stage(spec: Mapping[str, SortOrder]) -> Stage:
    """Creates a ``$sort`` aggregation stage to sort documents.

    Args:
        spec: The sort order for each field, applied in the order given.

    Returns:
        A MongoDB aggregation stage.

    Raises:
        ValueError: ``spec`` is empty or has an order other than ``1``, ``-1`` or ``$meta``.

    Example:
        >>> sort_stage({"name": 1})
        {'$sort': {'name': 1}}
    """
    require_fields(spec, "$sort")
    for field, order in spec.items():
        is_direction = not isinstance(order, bool) and order in (1, -1)
        if not is_direction and not (isinstance(order, Mapping) and "$meta" in order):
            raise ValueError(
                f"Invalid $sort order {order!r} for {field!r}; use 1, -1 or {{'$meta': ...}}"
            )
    return {"$sort": dict(spec)}
