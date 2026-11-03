from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal, TypeAlias

from mongodb_typesafe_aggregation.stages._utils import compact
from mongodb_typesafe_aggregation.types import Stage
from mongodb_typesafe_aggregation.types.filter import resolve_filters

WhenMatched: TypeAlias = (
    "Literal['replace', 'keepExisting', 'merge', 'fail'] | Sequence[Mapping[str, Any]]"
)
"""What to do with a result that matches an existing document, or an update pipeline."""

WhenNotMatched: TypeAlias = "Literal['insert', 'discard', 'fail']"
"""What to do with a result that matches no existing document."""


def merge_stage(
    into: str | Mapping[str, str],
    *,
    on: str | Sequence[str] | None = None,
    let: Mapping[str, Any] | None = None,
    when_matched: WhenMatched | None = None,
    when_not_matched: WhenNotMatched | None = None,
) -> Stage:
    """Creates a ``$merge`` aggregation stage to write the results into a collection.

    ``$merge`` must be the last stage of a pipeline.

    Args:
        into: The output collection, or ``{"db": ..., "coll": ...}``.
        on: The field, or fields, that identify a matching document.
        let: Variables for a ``when_matched`` pipeline.
        when_matched: What to do when a result matches an existing document, or an update
            pipeline to apply to it.
        when_not_matched: What to do when a result matches no existing document.

    Returns:
        A MongoDB aggregation stage.

    Example:
        >>> merge_stage("mergedCollection", on="userId")
        {'$merge': {'into': 'mergedCollection', 'on': 'userId'}}
    """
    spec = {
        "into": into if isinstance(into, str) else dict(into),
        **compact(
            on=on if on is None or isinstance(on, str) else list(on),
            let=let,
            whenMatched=when_matched
            if when_matched is None or isinstance(when_matched, str)
            else list(when_matched),
            whenNotMatched=when_not_matched,
        ),
    }
    return {"$merge": resolve_filters(spec)}
