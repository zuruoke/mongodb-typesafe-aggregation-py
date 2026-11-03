from __future__ import annotations

from collections.abc import Sequence

from mongodb_typesafe_aggregation.types import Stage


def unset_stage(fields: str | Sequence[str]) -> Stage:
    """Creates an ``$unset`` aggregation stage to remove fields from documents.

    Args:
        fields: The field, or fields, to remove from each document.

    Returns:
        A MongoDB aggregation stage.

    Raises:
        ValueError: No fields are given.

    Example:
        >>> unset_stage(["field1", "field2"])
        {'$unset': ['field1', 'field2']}
    """
    if not fields:
        raise ValueError("$unset requires at least one field")
    return {"$unset": fields if isinstance(fields, str) else list(fields)}
