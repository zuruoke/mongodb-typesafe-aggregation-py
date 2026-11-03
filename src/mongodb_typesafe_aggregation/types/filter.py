from __future__ import annotations

import copy
from collections.abc import Iterable, Mapping
from typing import Any, Generic, TypeVar, overload

T = TypeVar("T")


class FilterOperator(Generic[T]):
    """Builds MongoDB query and expression operators with a typed value.

    ``T`` is the type of the value being filtered, so ``FilterOperator[int]().gt("100")`` is
    a type error. Every method returns a new operator, so a partial one can be reused.

    Builders accept a ``FilterOperator`` directly, so calling ``.build()`` is optional.

    Example:
        >>> FilterOperator[int]().gte(100).lte(999).build()
        {'$gte': 100, '$lte': 999}
    """

    def __init__(self) -> None:
        self._operator: dict[str, Any] = {}

    def eq(self, value: T) -> FilterOperator[T]:
        """Creates an equality filter operator (``$eq``).

        Args:
            value: The value to compare against.
        """
        return self._set("$eq", value)

    def field_eq(self, field: str, value: T) -> FilterOperator[T]:
        """Creates a field equality expression for use in conditions (``$eq: [field, value]``).

        Args:
            field: The field to compare, e.g. ``"$role"``.
            value: The value to compare against.
        """
        return self._set("$eq", [field, value])

    def cond(
        self,
        condition: Mapping[str, Any] | FilterOperator[Any],
        then_value: Any,
        else_value: T,
    ) -> FilterOperator[T]:
        """Creates a conditional expression (``$cond``).

        Args:
            condition: The condition to evaluate.
            then_value: The value to return if the condition is true.
            else_value: The value to return if the condition is false.
        """
        return self._set("$cond", {"if": condition, "then": then_value, "else": else_value})

    def gt(self, value: T) -> FilterOperator[T]:
        """Creates a greater than filter operator (``$gt``).

        Args:
            value: The value to compare against.
        """
        return self._set("$gt", value)

    def gte(self, value: T) -> FilterOperator[T]:
        """Creates a greater than or equal to filter operator (``$gte``).

        Args:
            value: The value to compare against.
        """
        return self._set("$gte", value)

    def lt(self, value: T) -> FilterOperator[T]:
        """Creates a less than filter operator (``$lt``).

        Args:
            value: The value to compare against.
        """
        return self._set("$lt", value)

    def lte(self, value: T) -> FilterOperator[T]:
        """Creates a less than or equal to filter operator (``$lte``).

        Args:
            value: The value to compare against.
        """
        return self._set("$lte", value)

    def in_(self, values: Iterable[T]) -> FilterOperator[T]:
        """Creates an in array filter operator (``$in``).

        Named ``in_`` because ``in`` is a Python keyword.

        Args:
            values: The values to match against.
        """
        return self._set("$in", list(values))

    def nin(self, values: Iterable[T]) -> FilterOperator[T]:
        """Creates a not in array filter operator (``$nin``).

        Args:
            values: The values to not match against.
        """
        return self._set("$nin", list(values))

    def ne(self, value: T) -> FilterOperator[T]:
        """Creates a not equal filter operator (``$ne``).

        Args:
            value: The value to compare against.
        """
        return self._set("$ne", value)

    def field_ne(self, field: str, value: T) -> FilterOperator[T]:
        """Creates a field not equal expression for use in conditions (``$ne: [field, value]``).

        Args:
            field: The field to compare, e.g. ``"$status"``.
            value: The value to compare against.
        """
        return self._set("$ne", [field, value])

    def regex(self, pattern: str) -> FilterOperator[T]:
        """Creates a regex filter operator (``$regex``).

        Args:
            pattern: The regex pattern to match against.
        """
        return self._set("$regex", pattern)

    def exists(self, exists: bool) -> FilterOperator[T]:
        """Creates an exists filter operator (``$exists``).

        Args:
            exists: Whether the field should exist.
        """
        return self._set("$exists", exists)

    def all(self, values: Iterable[T]) -> FilterOperator[T]:
        """Creates an all array filter operator (``$all``).

        Args:
            values: The values that must all be present.
        """
        return self._set("$all", list(values))

    def size(self, size: int) -> FilterOperator[T]:
        """Creates a size filter operator (``$size``).

        Args:
            size: The expected size of the array.
        """
        return self._set("$size", size)

    def build(self) -> dict[str, Any]:
        """Builds the final filter operator object."""
        built: dict[str, Any] = resolve_filters(self._operator)
        return built

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._operator!r})"

    def _set(self, operator: str, value: Any) -> FilterOperator[T]:
        new = copy.copy(self)
        new._operator = {**self._operator, operator: value}
        return new


@overload
def filter(value_type: type[T], /) -> FilterOperator[T]: ...


@overload
def filter(value_type: None = None, /) -> FilterOperator[Any]: ...


def filter(value_type: type[T] | None = None, /) -> FilterOperator[Any]:
    """Creates a new filter operator builder.

    A concise alternative to ``FilterOperator[T]()``. The type argument only sets the static
    type of the values; it is not checked at runtime.

    Example:
        >>> filter(int).gt(700).build()
        {'$gt': 700}
    """
    return FilterOperator()


def resolve_filters(value: Any) -> Any:
    """Returns a copy of ``value`` with every ``FilterOperator`` inside it built.

    Mappings become dicts and tuples become lists; any other value is returned unchanged.
    """
    if isinstance(value, FilterOperator):
        return value.build()
    if isinstance(value, Mapping):
        return {key: resolve_filters(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [resolve_filters(item) for item in value]
    return value
