from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypeAlias

from mongodb_typesafe_aggregation.stages._utils import compact, require_int
from mongodb_typesafe_aggregation.types import Stage
from mongodb_typesafe_aggregation.types.filter import resolve_filters

Granularity: TypeAlias = Literal[
    "R5", "R10", "R20", "R40", "R80", "1-2-5", "E6", "E12", "E24", "E48", "E96", "E192", "POWERSOF2"
]
"""A preferred number series for ``$bucketAuto`` boundaries."""


def bucket_auto_stage(
    group_by: Any,
    buckets: int,
    *,
    output: Mapping[str, Any] | None = None,
    granularity: Granularity | None = None,
) -> Stage:
    """Creates a ``$bucketAuto`` aggregation stage to group documents into evenly sized buckets.

    Args:
        group_by: The expression to group by, e.g. ``"$price"``.
        buckets: The number of buckets to create.
        output: The accumulator for each output field. Defaults to ``{"count": {"$sum": 1}}``.
        granularity: A preferred number series for the bucket boundaries.

    Returns:
        A MongoDB aggregation stage.

    Raises:
        ValueError: ``buckets`` is not a positive integer.

    Example:
        >>> bucket_auto_stage("$price", 5, output={"count": {"$sum": 1}})
        {'$bucketAuto': {'groupBy': '$price', 'buckets': 5, 'output': {'count': {'$sum': 1}}}}
    """
    require_int(buckets, "$bucketAuto buckets", minimum=1)
    spec = {
        "groupBy": group_by,
        "buckets": buckets,
        **compact(output=output, granularity=granularity),
    }
    return {"$bucketAuto": resolve_filters(spec)}
