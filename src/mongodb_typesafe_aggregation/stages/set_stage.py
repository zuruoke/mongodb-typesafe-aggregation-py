"""``$set`` is an alias of ``$addFields`` in MongoDB 4.2+."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from mongodb_typesafe_aggregation.stages._utils import require_fields
from mongodb_typesafe_aggregation.types import Stage
from mongodb_typesafe_aggregation.types.filter import resolve_filters


def set_stage(spec: Mapping[str, Any]) -> Stage:
    """Creates a ``$set`` aggregation stage to add new fields to documents.

    Args:
        spec: The fields to add to each document, as expressions.

    Returns:
        A MongoDB aggregation stage.

    Example:
        >>> set_stage({"newField": "newValue"})
        {'$set': {'newField': 'newValue'}}
    """
    require_fields(spec, "$set")
    return {"$set": resolve_filters(spec)}
