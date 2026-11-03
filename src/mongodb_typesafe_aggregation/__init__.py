"""A type-safe, fluent builder for MongoDB aggregation pipelines."""

from mongodb_typesafe_aggregation.builder import PipelineBuilder
from mongodb_typesafe_aggregation.errors import UnknownFieldError
from mongodb_typesafe_aggregation.stages import match_stage
from mongodb_typesafe_aggregation.types import Pipeline, Stage

__version__ = "0.1.0"

__all__ = ["Pipeline", "PipelineBuilder", "Stage", "UnknownFieldError", "match_stage"]
