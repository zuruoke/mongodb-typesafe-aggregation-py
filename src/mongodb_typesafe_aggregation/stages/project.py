from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from mongodb_typesafe_aggregation.constants import ID_FIELD
from mongodb_typesafe_aggregation.stages._utils import require_fields
from mongodb_typesafe_aggregation.types import Stage
from mongodb_typesafe_aggregation.types.filter import resolve_filters


def is_exclusion(value: Any) -> bool:
    """Whether a ``$project`` value excludes its field (``0`` or ``False``)."""
    return isinstance(value, (bool, int, float)) and not value


def is_inclusion(value: Any) -> bool:
    """Whether a ``$project`` value includes its field as-is (``1`` or ``True``)."""
    return isinstance(value, (bool, int, float)) and bool(value)


def is_nested_projection(value: Any) -> bool:
    """Whether a ``$project`` value projects an embedded document, e.g. ``{"name": 1}``."""
    return isinstance(value, Mapping) and not any(key.startswith("$") for key in value)


def project_stage(spec: Mapping[str, Any]) -> Stage:
    """Creates a ``$project`` aggregation stage to include, exclude or compute fields.

    Args:
        spec: ``1``/``True`` to include a field, ``0``/``False`` to exclude it, or an
            expression to compute it.

    Returns:
        A MongoDB aggregation stage.

    Raises:
        ValueError: ``spec`` is empty, or mixes exclusions with inclusions or computed fields.
            Only ``_id`` may be excluded alongside them.

    Example:
        >>> project_stage({"_id": 0, "name": 1, "age": 1})
        {'$project': {'_id': 0, 'name': 1, 'age': 1}}
    """
    require_fields(spec, "$project")
    resolved: dict[str, Any] = resolve_filters(spec)

    excluded = [key for key, value in resolved.items() if key != ID_FIELD and is_exclusion(value)]
    kept = [key for key, value in resolved.items() if key != ID_FIELD and not is_exclusion(value)]
    if excluded and kept:
        raise ValueError(
            f"$project cannot mix exclusions {excluded} with inclusions or computed fields "
            f"{kept}; only _id may be excluded alongside them"
        )
    return {"$project": resolved}
