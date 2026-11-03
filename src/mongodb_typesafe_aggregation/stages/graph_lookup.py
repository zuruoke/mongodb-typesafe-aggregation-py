from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from mongodb_typesafe_aggregation.stages._utils import compact, require_int
from mongodb_typesafe_aggregation.types import Stage
from mongodb_typesafe_aggregation.types.filter import resolve_filters


def graph_lookup_stage(
    from_: str,
    *,
    start_with: Any,
    connect_from_field: str,
    connect_to_field: str,
    as_: str,
    max_depth: int | None = None,
    depth_field: str | None = None,
    restrict_search_with_match: Mapping[str, Any] | None = None,
) -> Stage:
    """Creates a ``$graphLookup`` aggregation stage to perform a recursive search.

    Args:
        from_: The collection to search.
        start_with: An expression for the value to start the search from, e.g. ``"$managerId"``.
        connect_from_field: The field of ``from_`` documents whose value is followed next.
        connect_to_field: The field of ``from_`` documents matched against that value.
        as_: The name of the array field that receives the documents found.
        max_depth: The maximum recursion depth; ``0`` only follows the first hop.
        depth_field: The name of a field added to each found document with its depth.
        restrict_search_with_match: A query that found documents must also match.

    Returns:
        A MongoDB aggregation stage.

    Raises:
        ValueError: ``max_depth`` is not a non-negative integer.

    Example:
        >>> graph_lookup_stage(
        ...     "users",
        ...     start_with="$managerId",
        ...     connect_from_field="managerId",
        ...     connect_to_field="employeeId",
        ...     as_="subordinates",
        ...     max_depth=2,
        ... )
    """
    if max_depth is not None:
        require_int(max_depth, "$graphLookup maxDepth", minimum=0)

    spec = {
        "from": from_,
        "startWith": start_with,
        "connectFromField": connect_from_field,
        "connectToField": connect_to_field,
        "as": as_,
        **compact(
            maxDepth=max_depth,
            depthField=depth_field,
            restrictSearchWithMatch=restrict_search_with_match,
        ),
    }
    return {"$graphLookup": resolve_filters(spec)}
