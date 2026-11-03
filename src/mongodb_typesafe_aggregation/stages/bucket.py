from __future__ import annotations

from collections.abc import Mapping, Sequence
from itertools import pairwise
from typing import Any

from mongodb_typesafe_aggregation.stages._utils import compact
from mongodb_typesafe_aggregation.types import Stage
from mongodb_typesafe_aggregation.types.filter import resolve_filters

_UNSET: Any = object()


def bucket_stage(
    group_by: Any,
    boundaries: Sequence[Any],
    *,
    default: Any = _UNSET,
    output: Mapping[str, Any] | None = None,
) -> Stage:
    """Creates a ``$bucket`` aggregation stage to group documents into ranges.

    Args:
        group_by: The expression to group by, e.g. ``"$age"``.
        boundaries: Ascending bucket boundaries. ``[0, 18, 35]`` creates the buckets
            ``[0, 18)`` and ``[18, 35)``.
        default: The ``_id`` of an extra bucket for values outside the boundaries. Without it,
            such a value makes the aggregation fail.
        output: The accumulator for each output field. Defaults to ``{"count": {"$sum": 1}}``.

    Returns:
        A MongoDB aggregation stage.

    Raises:
        ValueError: There are fewer than two boundaries, or they are not ascending.

    Example:
        >>> bucket_stage("$age", [0, 18, 35, 50, 100], default="Unknown")
        {'$bucket': {'groupBy': '$age', 'boundaries': [0, 18, 35, 50, 100], 'default': 'Unknown'}}
    """
    boundaries = list(boundaries)
    if len(boundaries) < 2:
        raise ValueError("$bucket requires at least two boundaries")
    try:
        ascending = all(low < high for low, high in pairwise(boundaries))
    except TypeError:
        ascending = False
    if not ascending:
        raise ValueError(f"$bucket boundaries must be ascending values of one type: {boundaries}")

    spec = {"groupBy": group_by, "boundaries": boundaries}
    if default is not _UNSET:
        spec["default"] = default
    spec.update(compact(output=output))
    return {"$bucket": resolve_filters(spec)}
