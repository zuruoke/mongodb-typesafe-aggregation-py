from __future__ import annotations

import copy
from collections.abc import Iterable, Mapping
from typing import Any, Generic, TypeVar, overload

from mongodb_typesafe_aggregation.schema import FieldSet, check_query, fields_of
from mongodb_typesafe_aggregation.stages import match_stage
from mongodb_typesafe_aggregation.types import Pipeline, Stage

T = TypeVar("T")


class PipelineBuilder(Generic[T]):
    """Builder for constructing MongoDB aggregation pipelines.

    Every method returns a new builder and leaves the original untouched, so a partially
    built pipeline can safely be reused as the base of several others.

    Args:
        schema: The document class of the collection: a ``TypedDict``, dataclass, Pydantic
            model or annotated class. Field names used in stages are checked against it, and
            ``UnknownFieldError`` is raised on a typo. ``None`` skips field checks.
        stages: Stages to start from. They are not checked.
        strict: ``False`` keeps the static typing but skips the runtime field checks.

    Example:
        >>> class Order(TypedDict):
        ...     status: str
        ...     total: float
        >>> PipelineBuilder(Order).match(status="pending").build()
        [{'$match': {'status': 'pending'}}]
    """

    @overload
    def __init__(
        self: PipelineBuilder[Any],
        schema: None = None,
        stages: Iterable[Mapping[str, Any]] = (),
        *,
        strict: bool = True,
    ) -> None: ...

    @overload
    def __init__(
        self,
        schema: type[T],
        stages: Iterable[Mapping[str, Any]] = (),
        *,
        strict: bool = True,
    ) -> None: ...

    def __init__(
        self,
        schema: type[T] | None = None,
        stages: Iterable[Mapping[str, Any]] = (),
        *,
        strict: bool = True,
    ) -> None:
        self._stages: Pipeline = [dict(stage) for stage in stages]
        self._fields: FieldSet = fields_of(schema) if strict else None

    def build(self) -> Pipeline:
        """Builds the final aggregation pipeline.

        Returns:
            A deep copy of the stages, so changing the result never affects the builder.
        """
        return copy.deepcopy(self._stages)

    def raw(self, stage: Mapping[str, Any]) -> PipelineBuilder[T]:
        """Adds a stage as-is, without field checks.

        Escape hatch for stages the builder does not cover yet.
        """
        return self._add(dict(stage))

    def match(self, query: Mapping[str, Any] | None = None, /, **fields: Any) -> PipelineBuilder[T]:
        """Adds a ``$match`` stage.

        Conditions can be given as a mapping, as keyword arguments, or both. Use the mapping for
        dotted paths and for operators such as ``$or`` and ``$expr``.

        Raises:
            UnknownFieldError: A field is not declared on the current schema.

        Example:
            >>> builder.match(status="pending")
            >>> builder.match({"price": {"$gt": 700}, "$or": [{"stock": 0}, {"active": False}]})
        """
        stage = match_stage({**(query or {}), **fields})
        check_query(stage["$match"], self._fields)
        return self._add(stage)

    def _add(self, stage: Stage) -> PipelineBuilder[T]:
        builder = copy.copy(self)
        builder._stages = [*self._stages, stage]
        return builder
