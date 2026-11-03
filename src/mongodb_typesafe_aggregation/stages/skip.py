from __future__ import annotations

from mongodb_typesafe_aggregation.stages._utils import require_int
from mongodb_typesafe_aggregation.types import Stage


def skip_stage(count: int) -> Stage:
    """Creates a ``$skip`` aggregation stage to skip the first N documents.

    Args:
        count: The number of documents to skip.

    Returns:
        A MongoDB aggregation stage.

    Raises:
        ValueError: ``count`` is not a non-negative integer.

    Example:
        >>> skip_stage(10)
        {'$skip': 10}
    """
    require_int(count, "$skip", minimum=0)
    return {"$skip": count}
