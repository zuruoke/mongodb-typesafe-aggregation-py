from __future__ import annotations

from mongodb_typesafe_aggregation.stages._utils import require_int
from mongodb_typesafe_aggregation.types import Stage


def limit_stage(count: int) -> Stage:
    """Creates a ``$limit`` aggregation stage to limit the number of documents processed.

    Args:
        count: The number of documents to limit the pipeline to.

    Returns:
        A MongoDB aggregation stage.

    Raises:
        ValueError: ``count`` is not a positive integer.

    Example:
        >>> limit_stage(10)
        {'$limit': 10}
    """
    require_int(count, "$limit", minimum=1)
    return {"$limit": count}
