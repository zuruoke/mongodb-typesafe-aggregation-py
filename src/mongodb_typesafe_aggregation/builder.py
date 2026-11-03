from __future__ import annotations

import copy
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any, Generic, TypeAlias, TypeVar, cast, overload

from mongodb_typesafe_aggregation.constants import DEFAULT_COUNT_FIELD, ID_FIELD
from mongodb_typesafe_aggregation.schema import (
    FieldSet,
    check_expression,
    check_field,
    check_query,
    field_root,
    fields_of,
)
from mongodb_typesafe_aggregation.stages import (
    Granularity,
    SortOrder,
    WhenMatched,
    WhenNotMatched,
    add_fields_stage,
    bucket_auto_stage,
    bucket_stage,
    count_stage,
    facet_stage,
    graph_lookup_stage,
    group_stage,
    limit_stage,
    lookup_stage,
    match_stage,
    merge_stage,
    project_stage,
    redact_stage,
    replace_root_stage,
    set_stage,
    skip_stage,
    sort_stage,
    union_with_stage,
    unset_stage,
    unwind_stage,
)
from mongodb_typesafe_aggregation.stages.bucket import _UNSET
from mongodb_typesafe_aggregation.stages.project import (
    is_exclusion,
    is_inclusion,
    is_nested_projection,
)
from mongodb_typesafe_aggregation.types import Pipeline, Stage

T = TypeVar("T")
G = TypeVar("G")

SubPipeline: TypeAlias = "Sequence[Mapping[str, Any]] | PipelineBuilder[Any]"
"""A list of stages, or a builder whose ``build()`` result is used."""

_SAME: Any = object()
"""Marker for stages that keep the current fields."""


class PipelineBuilder(Generic[T]):
    """Builder for constructing MongoDB aggregation pipelines.

    Every method returns a new builder and leaves the original untouched, so a partially
    built pipeline can safely be reused as the base of several others.

    The builder tracks which fields the documents have after each stage, so field checks keep
    working after stages that change the shape: after ``group()``, only the group's output
    fields are known. Stages that add fields (``lookup``, ``add_fields``, ...) keep the type
    parameter ``T``; stages that replace the shape (``group``, ``project``, ...) return
    ``PipelineBuilder[Any]``. Use ``cast()`` to declare the new shape.

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
        >>> PipelineBuilder(Order).match(status="pending").sort(total=-1).limit(20).build()
        [{'$match': {'status': 'pending'}}, {'$sort': {'total': -1}}, {'$limit': 20}]
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
        self._strict = strict
        self._fields: FieldSet = fields_of(schema) if strict else None
        self._closed = False

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._stages!r})"

    def build(self) -> Pipeline:
        """Builds the final aggregation pipeline.

        Returns:
            A deep copy of the stages, so changing the result never affects the builder.
        """
        return copy.deepcopy(self._stages)

    def cast(self, schema: type[G]) -> PipelineBuilder[G]:
        """Declares the shape of the documents at this point of the pipeline.

        Field checks in the following stages use ``schema``. This is the equivalent of the
        TypeScript ``group<G>()`` type argument.

        Example:
            >>> class StatusCount(TypedDict):
            ...     _id: str
            ...     orders: int
            >>> (
            ...     PipelineBuilder(Order)
            ...     .group({"_id": "$status", "orders": {"$sum": 1}})
            ...     .cast(StatusCount)
            ... )
        """
        builder = copy.copy(self)
        builder._fields = fields_of(schema) if self._strict else None
        return cast("PipelineBuilder[G]", builder)

    def raw(self, stage: Mapping[str, Any]) -> PipelineBuilder[T]:
        """Adds a stage as-is. The escape hatch for stages the builder does not cover.

        The stage is not checked, and the document shape is assumed unchanged. If the stage
        changes it, follow with ``cast()`` to declare the new shape.
        """
        return self._add(dict(stage))

    def match(self, query: Mapping[str, Any] | None = None, /, **fields: Any) -> PipelineBuilder[T]:
        """Adds a ``$match`` stage.

        Conditions can be given as a mapping, as keyword arguments, or both. Use the mapping for
        dotted paths and for operators such as ``$or`` and ``$expr``.

        Raises:
            UnknownFieldError: A field is not declared on the current schema.

        Example:
            >>> builder.match(status="pending", price=filter(float).gt(700))
            >>> builder.match({"supplier.region": "US", "$or": [{"stock": 0}, {"active": False}]})
        """
        stage = match_stage(_combine(query, fields))
        check_query(stage["$match"], self._fields)
        return self._add(stage)

    def lookup(
        self,
        from_: str,
        *,
        as_: str,
        local_field: str | None = None,
        foreign_field: str | None = None,
        let: Mapping[str, Any] | None = None,
        pipeline: SubPipeline | None = None,
    ) -> PipelineBuilder[T]:
        """Adds a ``$lookup`` stage, joining ``from_`` into the array field ``as_``.

        ``local_field`` and the expressions in ``let`` are checked against the current
        schema; ``foreign_field`` and ``pipeline`` refer to the other collection.

        Example:
            >>> builder.lookup("orders", local_field="_id", foreign_field="productId", as_="orders")
        """
        stage = lookup_stage(
            from_,
            as_=as_,
            local_field=local_field,
            foreign_field=foreign_field,
            let=let,
            pipeline=None if pipeline is None else _sub_pipeline(pipeline),
        )
        if local_field is not None:
            check_field(local_field, self._fields, "$lookup")
        check_expression(stage["$lookup"].get("let"), self._fields, "$lookup")
        return self._add(stage, fields=self._extended([as_]))

    def group(
        self, spec: Mapping[str, Any] | None = None, /, **fields: Any
    ) -> PipelineBuilder[Any]:
        """Adds a ``$group`` stage. The documents now have only ``_id`` and the output fields.

        Example:
            >>> builder.group(_id="$status", totalOrders={"$sum": 1})
        """
        stage = group_stage(_combine(spec, fields))
        check_expression(list(stage["$group"].values()), self._fields, "$group")
        return self._add(stage, fields=self._replaced(stage["$group"]))

    def add_fields(
        self, spec: Mapping[str, Any] | None = None, /, **fields: Any
    ) -> PipelineBuilder[T]:
        """Adds an ``$addFields`` stage.

        Example:
            >>> builder.add_fields(orderedQuantity={"$sum": "$orders.quantity"})
        """
        stage = add_fields_stage(_combine(spec, fields))
        check_expression(list(stage["$addFields"].values()), self._fields, "$addFields")
        return self._add(stage, fields=self._extended(stage["$addFields"]))

    def set(self, spec: Mapping[str, Any] | None = None, /, **fields: Any) -> PipelineBuilder[T]:
        """Adds a ``$set`` stage, an alias of ``$addFields`` (MongoDB 4.2+)."""
        stage = set_stage(_combine(spec, fields))
        check_expression(list(stage["$set"].values()), self._fields, "$set")
        return self._add(stage, fields=self._extended(stage["$set"]))

    def project(
        self, spec: Mapping[str, Any] | None = None, /, **fields: Any
    ) -> PipelineBuilder[Any]:
        """Adds a ``$project`` stage.

        Use ``1``/``True`` to include a field, ``0``/``False`` to exclude it, or an expression
        to compute it. The documents now have only the projected fields.

        Example:
            >>> builder.project(_id=0, name=1, remainingStock={"$subtract": ["$stock", 1]})
        """
        stage = project_stage(_combine(spec, fields))
        projection: dict[str, Any] = stage["$project"]

        for key, value in projection.items():
            if is_inclusion(value) or is_exclusion(value) or is_nested_projection(value):
                check_field(key, self._fields, "$project")
            else:
                check_expression(value, self._fields, "$project")

        excluded = {key for key, value in projection.items() if is_exclusion(value)}
        if set(projection) - excluded - {ID_FIELD}:
            kept = {field_root(key) for key in projection if key not in excluded}
            shape = self._replaced(kept, with_id=ID_FIELD not in excluded)
        else:
            shape = self._removed(excluded)
        return self._add(stage, fields=shape)

    def sort(
        self, spec: Mapping[str, SortOrder] | None = None, /, **fields: SortOrder
    ) -> PipelineBuilder[T]:
        """Adds a ``$sort`` stage. Fields are sorted in the order given.

        Example:
            >>> builder.sort(price=-1, name=1)
        """
        stage = sort_stage(_combine(spec, fields))
        for field in stage["$sort"]:
            check_field(field, self._fields, "$sort")
        return self._add(stage)

    def skip(self, count: int) -> PipelineBuilder[T]:
        """Adds a ``$skip`` stage."""
        return self._add(skip_stage(count))

    def limit(self, count: int) -> PipelineBuilder[T]:
        """Adds a ``$limit`` stage."""
        return self._add(limit_stage(count))

    def facet(
        self,
        spec: Mapping[str, SubPipeline | Callable[[PipelineBuilder[T]], PipelineBuilder[Any]]]
        | None = None,
        /,
        **pipelines: SubPipeline | Callable[[PipelineBuilder[T]], PipelineBuilder[Any]],
    ) -> PipelineBuilder[Any]:
        """Adds a ``$facet`` stage, running several pipelines on the same documents.

        Each pipeline can be a list of stages, a builder, or a function that receives a fresh
        builder for the current documents, so its stages are checked against the current
        schema. The documents now have one array field per pipeline.

        Example:
            >>> builder.facet(
            ...     expensive=lambda products: products.match(price=filter(float).gte(700)),
            ...     total=lambda products: products.count(),
            ... )
        """
        branches = _combine(spec, pipelines)
        stage = facet_stage(
            {
                name: _sub_pipeline(branch(self._branch()) if callable(branch) else branch)
                for name, branch in branches.items()
            }
        )
        return self._add(stage, fields=self._replaced(stage["$facet"], with_id=False))

    def unwind(
        self,
        path: str | Mapping[str, Any],
        *,
        include_array_index: str | None = None,
        preserve_null_and_empty_arrays: bool | None = None,
    ) -> PipelineBuilder[Any]:
        """Adds an ``$unwind`` stage, outputting one document per element of the array ``path``.

        Example:
            >>> builder.unwind("$tags")
            >>> builder.unwind("$tags", include_array_index="tagIndex")
        """
        stage = unwind_stage(
            path,
            include_array_index=include_array_index,
            preserve_null_and_empty_arrays=preserve_null_and_empty_arrays,
        )
        spec = stage["$unwind"]
        field_path: str = spec if isinstance(spec, str) else spec["path"]
        check_field(field_path[1:], self._fields, "$unwind")
        index_field = None if isinstance(spec, str) else spec.get("includeArrayIndex")
        return self._add(stage, fields=self._extended([index_field] if index_field else []))

    def replace_root(self, new_root: str | Mapping[str, Any]) -> PipelineBuilder[Any]:
        """Adds a ``$replaceRoot`` stage, replacing each document with ``new_root``.

        When ``new_root`` is a document literal such as ``{"name": "$name"}``, its keys become
        the known fields. Otherwise the new shape is unknown and field checks stop until
        ``cast()`` is used.

        Example:
            >>> builder.replace_root("$supplier").cast(Supplier)
        """
        stage = replace_root_stage(new_root)
        root = stage["$replaceRoot"]["newRoot"]
        check_expression(root, self._fields, "$replaceRoot")
        literal = isinstance(root, Mapping) and not any(key.startswith("$") for key in root)
        return self._add(stage, fields=self._replaced(root, with_id=False) if literal else None)

    def count(self, field: str = DEFAULT_COUNT_FIELD) -> PipelineBuilder[dict[str, int]]:
        """Adds a ``$count`` stage. The result is one document, ``{field: <count>}``."""
        stage = count_stage(field)
        builder = self._add(stage, fields=self._replaced([field], with_id=False))
        return cast("PipelineBuilder[dict[str, int]]", builder)

    def union_with(self, coll: str, pipeline: SubPipeline | None = None) -> PipelineBuilder[T]:
        """Adds a ``$unionWith`` stage, appending the documents of ``coll``.

        Example:
            >>> builder.union_with("archived_products", [{"$project": {"name": 1}}])
        """
        stage = union_with_stage(coll, None if pipeline is None else _sub_pipeline(pipeline))
        return self._add(stage)

    def unset(self, fields: str | Sequence[str]) -> PipelineBuilder[T]:
        """Adds an ``$unset`` stage, removing one or more fields.

        Example:
            >>> builder.unset(["description", "supplier.region"])
        """
        stage = unset_stage(fields)
        names = [fields] if isinstance(fields, str) else list(fields)
        for name in names:
            check_field(name, self._fields, "$unset")
        return self._add(stage, fields=self._removed(names))

    def merge(
        self,
        into: str | Mapping[str, str],
        *,
        on: str | Sequence[str] | None = None,
        let: Mapping[str, Any] | None = None,
        when_matched: WhenMatched | None = None,
        when_not_matched: WhenNotMatched | None = None,
    ) -> PipelineBuilder[T]:
        """Adds a ``$merge`` stage, writing the results into ``into``.

        ``$merge`` must be the last stage: adding another stage after it raises ``ValueError``.

        Example:
            >>> builder.merge("product_summaries", on="_id", when_matched="replace")
        """
        stage = merge_stage(
            into, on=on, let=let, when_matched=when_matched, when_not_matched=when_not_matched
        )
        for field in [on] if isinstance(on, str) else on or []:
            check_field(field, self._fields, "$merge")
        check_expression(stage["$merge"].get("let"), self._fields, "$merge")
        builder = self._add(stage)
        builder._closed = True
        return builder

    def graph_lookup(
        self,
        from_: str,
        *,
        start_with: Any,
        connect_from_field: str,
        connect_to_field: str,
        as_: str,
        max_depth: int | None = None,
        depth_field: str | None = None,
        restrict_search_with_match: Mapping[str, Any] | None = None,
    ) -> PipelineBuilder[T]:
        """Adds a ``$graphLookup`` stage, recursively searching ``from_`` into ``as_``.

        Example:
            >>> builder.graph_lookup(
            ...     "employees",
            ...     start_with="$managerId",
            ...     connect_from_field="managerId",
            ...     connect_to_field="_id",
            ...     as_="reports",
            ... )
        """
        stage = graph_lookup_stage(
            from_,
            start_with=start_with,
            connect_from_field=connect_from_field,
            connect_to_field=connect_to_field,
            as_=as_,
            max_depth=max_depth,
            depth_field=depth_field,
            restrict_search_with_match=restrict_search_with_match,
        )
        check_expression(stage["$graphLookup"]["startWith"], self._fields, "$graphLookup")
        return self._add(stage, fields=self._extended([as_]))

    def bucket(
        self,
        group_by: Any,
        boundaries: Sequence[Any],
        *,
        default: Any = _UNSET,
        output: Mapping[str, Any] | None = None,
    ) -> PipelineBuilder[Any]:
        """Adds a ``$bucket`` stage, grouping documents into ranges of ``group_by``.

        The documents now have ``_id`` (the lower boundary) and the ``output`` fields, or
        ``count`` when there is no ``output``.

        Example:
            >>> builder.bucket("$price", [0, 300, 1000], default="other")
        """
        stage = bucket_stage(group_by, boundaries, default=default, output=output)
        spec = stage["$bucket"]
        check_expression([spec["groupBy"], spec.get("output")], self._fields, "$bucket")
        return self._add(stage, fields=self._replaced(spec.get("output") or [DEFAULT_COUNT_FIELD]))

    def bucket_auto(
        self,
        group_by: Any,
        buckets: int,
        *,
        output: Mapping[str, Any] | None = None,
        granularity: Granularity | None = None,
    ) -> PipelineBuilder[Any]:
        """Adds a ``$bucketAuto`` stage, grouping documents into ``buckets`` even buckets.

        The documents now have ``_id`` (``{"min": ..., "max": ...}``) and the ``output``
        fields, or ``count`` when there is no ``output``.

        Example:
            >>> builder.bucket_auto("$price", 4)
        """
        stage = bucket_auto_stage(group_by, buckets, output=output, granularity=granularity)
        spec = stage["$bucketAuto"]
        check_expression([spec["groupBy"], spec.get("output")], self._fields, "$bucketAuto")
        return self._add(stage, fields=self._replaced(spec.get("output") or [DEFAULT_COUNT_FIELD]))

    def redact(self, expression: str | Mapping[str, Any]) -> PipelineBuilder[T]:
        """Adds a ``$redact`` stage.

        Example:
            >>> active = {"$eq": ["$active", True]}
            >>> builder.redact({"$cond": {"if": active, "then": "$$KEEP", "else": "$$PRUNE"}})
        """
        stage = redact_stage(expression)
        check_expression(stage["$redact"], self._fields, "$redact")
        return self._add(stage)

    def _add(self, stage: Stage, *, fields: FieldSet = _SAME) -> PipelineBuilder[T]:
        if self._closed:
            raise ValueError("$merge must be the last stage of a pipeline")
        builder = copy.copy(self)
        builder._stages = [*self._stages, stage]
        if fields is not _SAME:
            builder._fields = fields
        return builder

    def _branch(self) -> PipelineBuilder[T]:
        """Returns an empty builder for the current documents, for ``$facet`` pipelines."""
        builder = copy.copy(self)
        builder._stages = []
        builder._closed = False
        return builder

    def _extended(self, names: Iterable[str]) -> FieldSet:
        if self._fields is None:
            return None
        return self._fields | {field_root(name) for name in names}

    def _removed(self, names: Iterable[str]) -> FieldSet:
        if self._fields is None:
            return None
        return self._fields - {name for name in names if "." not in name}

    def _replaced(self, names: Iterable[str], *, with_id: bool = True) -> FieldSet:
        if self._fields is None:
            return None
        return frozenset(names) | ({ID_FIELD} if with_id else set())


def _sub_pipeline(pipeline: SubPipeline) -> Pipeline:
    if isinstance(pipeline, PipelineBuilder):
        return pipeline.build()
    if isinstance(pipeline, (str, Mapping)):
        raise TypeError(f"Expected a list of stages or a PipelineBuilder, got {pipeline!r}")
    return [dict(stage) for stage in pipeline]


def _combine(spec: Mapping[str, Any] | None, fields: Mapping[str, Any]) -> dict[str, Any]:
    """Merges a stage's mapping argument with its keyword arguments."""
    duplicates = sorted((spec or {}).keys() & fields.keys())
    if duplicates:
        raise TypeError(f"{duplicates} given both in the mapping and as keyword arguments")
    return {**(spec or {}), **fields}
