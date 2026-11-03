"""A type-safe, fluent builder for MongoDB aggregation pipelines."""

from mongodb_typesafe_aggregation.builder import PipelineBuilder
from mongodb_typesafe_aggregation.errors import UnknownFieldError
from mongodb_typesafe_aggregation.stages import (
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
from mongodb_typesafe_aggregation.types import FilterOperator, Pipeline, Stage

__version__ = "0.1.0"

# `filter` is importable from `mongodb_typesafe_aggregation.types.filter`; it is left out here
# so that `from mongodb_typesafe_aggregation import *` does not shadow the builtin.
__all__ = [
    "FilterOperator",
    "Pipeline",
    "PipelineBuilder",
    "Stage",
    "UnknownFieldError",
    "add_fields_stage",
    "bucket_auto_stage",
    "bucket_stage",
    "count_stage",
    "facet_stage",
    "graph_lookup_stage",
    "group_stage",
    "limit_stage",
    "lookup_stage",
    "match_stage",
    "merge_stage",
    "project_stage",
    "redact_stage",
    "replace_root_stage",
    "set_stage",
    "skip_stage",
    "sort_stage",
    "union_with_stage",
    "unset_stage",
    "unwind_stage",
]
