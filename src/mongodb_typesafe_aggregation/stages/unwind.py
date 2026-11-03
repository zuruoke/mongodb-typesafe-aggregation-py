from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from mongodb_typesafe_aggregation.stages._utils import compact
from mongodb_typesafe_aggregation.types import Stage


def unwind_stage(
    path: str | Mapping[str, Any],
    *,
    include_array_index: str | None = None,
    preserve_null_and_empty_arrays: bool | None = None,
) -> Stage:
    """Creates an ``$unwind`` aggregation stage to output a document for each array element.

    Args:
        path: The array field path, e.g. ``"$items"``. A full ``{"path": ...}`` specification
            is also accepted.
        include_array_index: The name of a new field that receives the element's index.
        preserve_null_and_empty_arrays: Whether to keep documents whose array is missing,
            null or empty.

    Returns:
        A MongoDB aggregation stage, in the short string form when no options are given.

    Raises:
        ValueError: ``path`` is not a field path starting with ``$``.

    Example:
        >>> unwind_stage("$items")
        {'$unwind': '$items'}
        >>> unwind_stage("$items", preserve_null_and_empty_arrays=True)
        {'$unwind': {'path': '$items', 'preserveNullAndEmptyArrays': True}}
    """
    spec = dict(path) if isinstance(path, Mapping) else {"path": path}
    spec.update(
        compact(
            includeArrayIndex=include_array_index,
            preserveNullAndEmptyArrays=preserve_null_and_empty_arrays,
        )
    )
    field_path = spec.get("path")
    if not isinstance(field_path, str) or not field_path.startswith("$") or field_path[:2] == "$$":
        raise ValueError(f"$unwind path must be a field path starting with '$', got {field_path!r}")
    return {"$unwind": spec if len(spec) > 1 else field_path}
