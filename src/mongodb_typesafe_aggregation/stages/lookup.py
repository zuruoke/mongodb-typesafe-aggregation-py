from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from mongodb_typesafe_aggregation.stages._utils import compact
from mongodb_typesafe_aggregation.types import Stage
from mongodb_typesafe_aggregation.types.filter import resolve_filters


def lookup_stage(
    from_: str,
    *,
    as_: str,
    local_field: str | None = None,
    foreign_field: str | None = None,
    let: Mapping[str, Any] | None = None,
    pipeline: Sequence[Mapping[str, Any]] | None = None,
) -> Stage:
    """Creates a ``$lookup`` aggregation stage to perform a left outer join with another collection.

    Use ``local_field`` and ``foreign_field`` for an equality match, ``let`` and ``pipeline``
    for a subquery, or both (MongoDB 5.0+).

    Args:
        from_: The collection to join.
        as_: The name of the array field that receives the matching documents.
        local_field: The field of the input documents to match on.
        foreign_field: The field of the ``from_`` documents to match on.
        let: Variables for the ``pipeline``, as expressions over the input documents.
        pipeline: Stages to run on the ``from_`` collection.

    Returns:
        A MongoDB aggregation stage.

    Raises:
        ValueError: Only one of ``local_field`` and ``foreign_field`` is given, or neither
            they nor a ``pipeline`` are given.

    Example:
        >>> lookup_stage("users", local_field="userId", foreign_field="_id", as_="user")
        {'$lookup': {'from': 'users', 'localField': 'userId', 'foreignField': '_id', 'as': 'user'}}
    """
    if (local_field is None) != (foreign_field is None):
        raise ValueError("$lookup requires local_field and foreign_field together")
    if local_field is None and pipeline is None:
        raise ValueError("$lookup requires local_field and foreign_field, a pipeline, or both")

    spec = {
        "from": from_,
        **compact(
            localField=local_field,
            foreignField=foreign_field,
            let=let,
            pipeline=None if pipeline is None else list(pipeline),
        ),
        "as": as_,
    }
    return {"$lookup": resolve_filters(spec)}
