from __future__ import annotations

from mongodb_typesafe_aggregation.constants import DEFAULT_COUNT_FIELD
from mongodb_typesafe_aggregation.types import Stage


def count_stage(field: str = DEFAULT_COUNT_FIELD) -> Stage:
    """Creates a ``$count`` aggregation stage to count the number of documents.

    Args:
        field: The name of the field that receives the count.

    Returns:
        A MongoDB aggregation stage.

    Raises:
        ValueError: ``field`` is empty, starts with ``$`` or contains ``.``.

    Example:
        >>> count_stage("totalDocuments")
        {'$count': 'totalDocuments'}
    """
    if not field or field.startswith("$") or "." in field:
        raise ValueError(f"$count field must be non-empty without '$' or '.', got {field!r}")
    return {"$count": field}
