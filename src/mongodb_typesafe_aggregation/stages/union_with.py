from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from mongodb_typesafe_aggregation.stages._utils import compact
from mongodb_typesafe_aggregation.types import Stage
from mongodb_typesafe_aggregation.types.filter import resolve_filters


def union_with_stage(coll: str, pipeline: Sequence[Mapping[str, Any]] | None = None) -> Stage:
    """Creates a ``$unionWith`` aggregation stage to combine documents from two collections.

    Args:
        coll: The collection whose documents are added to the results.
        pipeline: Stages to run on ``coll`` before the union.

    Returns:
        A MongoDB aggregation stage.

    Example:
        >>> union_with_stage("collection2")
        {'$unionWith': {'coll': 'collection2'}}
    """
    spec = {"coll": coll, **compact(pipeline=None if pipeline is None else list(pipeline))}
    return {"$unionWith": resolve_filters(spec)}
