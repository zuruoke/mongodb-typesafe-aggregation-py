from typing import Any, TypeAlias

Stage: TypeAlias = dict[str, Any]
"""A single aggregation stage, e.g. ``{"$match": {"status": "pending"}}``."""

Pipeline: TypeAlias = list[Stage]
"""A list of aggregation stages, ready to pass to ``collection.aggregate()``."""

__all__ = ["Pipeline", "Stage"]
