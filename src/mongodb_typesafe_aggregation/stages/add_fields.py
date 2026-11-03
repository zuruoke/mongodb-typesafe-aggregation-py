from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from mongodb_typesafe_aggregation.stages._utils import require_fields
from mongodb_typesafe_aggregation.types import Stage
from mongodb_typesafe_aggregation.types.filter import resolve_filters


def add_fields_stage(spec: Mapping[str, Any]) -> Stage:
    """Creates an ``$addFields`` aggregation stage to add new fields to documents.

    Args:
        spec: The fields to add to each document, as expressions.

    Returns:
        A MongoDB aggregation stage.

    Example:
        >>> add_fields_stage({"fullName": {"$concat": ["$firstName", " ", "$lastName"]}})
        {'$addFields': {'fullName': {'$concat': ['$firstName', ' ', '$lastName']}}}
    """
    require_fields(spec, "$addFields")
    return {"$addFields": resolve_filters(spec)}
