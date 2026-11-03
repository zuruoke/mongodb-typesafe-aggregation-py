from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from mongodb_typesafe_aggregation.stages._utils import require_fields
from mongodb_typesafe_aggregation.types import Stage
from mongodb_typesafe_aggregation.types.filter import resolve_filters


def facet_stage(spec: Mapping[str, Sequence[Mapping[str, Any]]]) -> Stage:
    """Creates a ``$facet`` aggregation stage to run several pipelines on the same documents.

    Args:
        spec: The output field name for each pipeline.

    Returns:
        A MongoDB aggregation stage.

    Example:
        >>> facet_stage({"byCategory": [{"$group": {"_id": "$category"}}]})
        {'$facet': {'byCategory': [{'$group': {'_id': '$category'}}]}}
    """
    require_fields(spec, "$facet")
    return {"$facet": {name: resolve_filters(list(pipeline)) for name, pipeline in spec.items()}}
