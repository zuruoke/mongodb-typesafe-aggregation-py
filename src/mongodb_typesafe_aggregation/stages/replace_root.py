from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from mongodb_typesafe_aggregation.types import Stage
from mongodb_typesafe_aggregation.types.filter import resolve_filters


def replace_root_stage(new_root: str | Mapping[str, Any]) -> Stage:
    """Creates a ``$replaceRoot`` aggregation stage to replace each document with a new one.

    Args:
        new_root: An expression that evaluates to a document, e.g. ``"$supplier"`` or
            ``{"name": "$name", "age": "$age"}``.

    Returns:
        A MongoDB aggregation stage.

    Example:
        >>> replace_root_stage({"name": "$name", "age": "$age"})
        {'$replaceRoot': {'newRoot': {'name': '$name', 'age': '$age'}}}
    """
    return {"$replaceRoot": {"newRoot": resolve_filters(new_root)}}
