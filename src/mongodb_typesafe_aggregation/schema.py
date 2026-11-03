"""Reads field names from a document schema and checks field references against them.

A schema is any class that declares fields: a ``TypedDict``, a dataclass, a Pydantic model
(v1 or v2), or a plain annotated class. Python cannot check dict keys against a class at
type-check time the way TypeScript's ``keyof T`` does, so these checks run when a stage is added.
"""

from __future__ import annotations

import dataclasses
import inspect
import sys
from collections.abc import Iterable, Mapping
from typing import Any, TypeAlias

from mongodb_typesafe_aggregation.constants import ID_FIELD
from mongodb_typesafe_aggregation.errors import UnknownFieldError

FieldSet: TypeAlias = "frozenset[str] | None"
"""Known top-level field names, or ``None`` when the shape is unknown and checks are skipped."""

LOGICAL_OPERATORS = frozenset({"$and", "$or", "$nor"})
OPAQUE_OPERATORS = frozenset({"$literal", "$function", "$accumulator"})


def fields_of(schema: type[Any] | None) -> FieldSet:
    """Returns the top-level field names declared by ``schema``, plus ``_id``.

    Pydantic fields are reported by their alias, since that is the name stored in MongoDB.

    Raises:
        TypeError: ``schema`` is not a class, or declares no fields.
    """
    if schema is None:
        return None
    if not isinstance(schema, type):
        raise TypeError(f"Expected a schema class, got {schema!r}")

    names = frozenset(_declared_fields(schema))
    if not names:
        raise TypeError(
            f"{schema.__name__} declares no fields. Pass a TypedDict, dataclass, Pydantic model "
            "or annotated class, or None to skip field checks."
        )
    return names | {ID_FIELD}


def field_root(path: str) -> str:
    """Returns the top-level field of a dotted path: ``"product.name"`` -> ``"product"``."""
    return path.split(".", 1)[0]


def check_field(path: str, known: FieldSet, stage: str) -> None:
    """Raises ``UnknownFieldError`` if the root of ``path`` is not a known field."""
    if known is None:
        return
    root = field_root(path)
    if root not in known:
        raise UnknownFieldError(root, stage, known, path=path)


def check_query(query: Mapping[str, Any], known: FieldSet, stage: str = "$match") -> None:
    """Checks the field names in a query filter, the body of a ``$match`` stage.

    Field keys are checked, including inside ``$and``/``$or``/``$nor`` clauses, and the body
    of ``$expr`` is checked as an aggregation expression. Values are literals in the query
    language, so they are not checked.
    """
    if known is None:
        return
    for key, value in query.items():
        if key in LOGICAL_OPERATORS:
            for clause in value:
                if isinstance(clause, Mapping):
                    check_query(clause, known, stage)
        elif key == "$expr":
            check_expression(value, known, stage)
        elif not key.startswith("$"):
            check_field(key, known, stage)


def check_expression(expression: Any, known: FieldSet, stage: str) -> None:
    """Checks every ``"$field"`` path inside an aggregation expression.

    ``"$$variables"`` and the bodies of ``$literal``, ``$function`` and ``$accumulator`` are
    skipped because they never refer to document fields.
    """
    if known is None:
        return
    if isinstance(expression, str):
        if len(expression) > 1 and expression[0] == "$" and expression[1] != "$":
            check_field(expression[1:], known, stage)
    elif isinstance(expression, Mapping):
        for operator, argument in expression.items():
            if operator not in OPAQUE_OPERATORS:
                check_expression(argument, known, stage)
    elif isinstance(expression, (list, tuple)):
        for item in expression:
            check_expression(item, known, stage)


def _declared_fields(schema: type[Any]) -> Iterable[str]:
    if hasattr(schema, "__required_keys__"):  # TypedDict
        keys: frozenset[str] = schema.__required_keys__ | schema.__optional_keys__
        return keys
    if dataclasses.is_dataclass(schema):
        return [field.name for field in dataclasses.fields(schema)]
    model_fields = getattr(schema, "model_fields", None)  # Pydantic v2
    if isinstance(model_fields, Mapping):
        return [
            info.serialization_alias or info.alias or name for name, info in model_fields.items()
        ]
    v1_fields = getattr(schema, "__fields__", None)  # Pydantic v1
    if isinstance(v1_fields, Mapping):
        return [field.alias for field in v1_fields.values()]
    return [name for klass in schema.__mro__ for name in _own_annotations(klass)]


if sys.version_info >= (3, 14):
    import annotationlib

    def _own_annotations(klass: type[Any]) -> Mapping[str, Any]:
        return annotationlib.get_annotations(klass, format=annotationlib.Format.FORWARDREF)

else:

    def _own_annotations(klass: type[Any]) -> Mapping[str, Any]:
        return inspect.get_annotations(klass)
