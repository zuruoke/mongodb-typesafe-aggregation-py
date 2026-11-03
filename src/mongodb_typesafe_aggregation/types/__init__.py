from typing import Any, TypeAlias

from mongodb_typesafe_aggregation.types.filter import FilterOperator, filter

Stage: TypeAlias = dict[str, Any]
"""A single aggregation stage, e.g. ``{"$match": {"status": "pending"}}``."""

Pipeline: TypeAlias = list[Stage]
"""A list of aggregation stages, ready to pass to ``collection.aggregate()``."""

__all__ = ["FilterOperator", "Pipeline", "Stage", "filter"]
