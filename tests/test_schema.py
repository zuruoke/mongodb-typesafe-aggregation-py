from __future__ import annotations

import dataclasses
from typing import Any, TypedDict

import pytest
from pydantic import BaseModel, Field
from typing_extensions import NotRequired

from mongodb_typesafe_aggregation import UnknownFieldError
from mongodb_typesafe_aggregation.schema import (
    check_expression,
    check_field,
    check_query,
    field_root,
    fields_of,
)


class Product(TypedDict):
    name: str
    price: float
    stock: NotRequired[int]


class DiscountedProduct(Product):
    discount: float


@dataclasses.dataclass
class Customer:
    name: str
    email: str


class Review(BaseModel):
    id: str = Field(alias="_id")
    rating: int
    text: str


class Book:
    title: str
    year: int


class Ebook(Book):
    size_mb: float


KNOWN = frozenset({"_id", "name", "price", "orders"})


class TestFieldsOf:
    def test_none_means_unknown_shape(self) -> None:
        assert fields_of(None) is None

    def test_typeddict_includes_optional_keys(self) -> None:
        assert fields_of(Product) == frozenset({"_id", "name", "price", "stock"})

    def test_typeddict_includes_inherited_keys(self) -> None:
        assert fields_of(DiscountedProduct) == frozenset(
            {"_id", "name", "price", "stock", "discount"}
        )

    def test_dataclass(self) -> None:
        assert fields_of(Customer) == frozenset({"_id", "name", "email"})

    def test_pydantic_model_uses_aliases(self) -> None:
        assert fields_of(Review) == frozenset({"_id", "rating", "text"})

    def test_annotated_class_includes_inherited_fields(self) -> None:
        assert fields_of(Ebook) == frozenset({"_id", "title", "year", "size_mb"})

    def test_rejects_non_class(self) -> None:
        with pytest.raises(TypeError, match="Expected a schema class"):
            fields_of({"name": str})  # type: ignore[arg-type]

    def test_rejects_class_without_fields(self) -> None:
        with pytest.raises(TypeError, match="dict declares no fields"):
            fields_of(dict)


class TestCheckField:
    def test_field_root(self) -> None:
        assert field_root("product.name") == "product"
        assert field_root("name") == "name"

    def test_known_field_passes(self) -> None:
        check_field("price", KNOWN, "$match")

    def test_dotted_path_checks_root_only(self) -> None:
        check_field("orders.quantity", KNOWN, "$match")

    def test_unknown_field_raises_with_suggestion(self) -> None:
        with pytest.raises(UnknownFieldError) as error:
            check_field("prise", KNOWN, "$match")

        assert error.value.field == "prise"
        assert error.value.stage == "$match"
        assert str(error.value) == (
            "Unknown field 'prise' in $match. Did you mean 'price'? "
            "Known fields: _id, name, orders, price."
        )

    def test_unknown_dotted_path_reports_full_path(self) -> None:
        with pytest.raises(UnknownFieldError, match=r"'ordrs' \(from 'ordrs.quantity'\)"):
            check_field("ordrs.quantity", KNOWN, "$match")

    def test_error_is_a_value_error(self) -> None:
        with pytest.raises(ValueError):
            check_field("nope", KNOWN, "$match")

    def test_unknown_shape_skips_check(self) -> None:
        check_field("anything", None, "$match")


class TestCheckQuery:
    def test_plain_fields(self) -> None:
        check_query({"name": "Laptop", "price": {"$gt": 700}}, KNOWN)

    def test_operator_values_are_not_checked(self) -> None:
        check_query({"name": {"$in": ["$notAField"]}}, KNOWN)

    def test_unknown_field_raises(self) -> None:
        with pytest.raises(UnknownFieldError, match="'stock'"):
            check_query({"stock": {"$lt": 10}}, KNOWN)

    @pytest.mark.parametrize("operator", ["$and", "$or", "$nor"])
    def test_logical_operator_clauses_are_checked(self, operator: str) -> None:
        check_query({operator: [{"name": "Laptop"}, {"price": 1}]}, KNOWN)
        with pytest.raises(UnknownFieldError, match="'prce'"):
            check_query({operator: [{"name": "Laptop"}, {"prce": 1}]}, KNOWN)

    def test_nested_logical_operators(self) -> None:
        with pytest.raises(UnknownFieldError, match="'nme'"):
            check_query({"$or": [{"$and": [{"nme": "x"}]}]}, KNOWN)

    def test_expr_is_checked_as_expression(self) -> None:
        check_query({"$expr": {"$gt": ["$price", "$orders.total"]}}, KNOWN)
        with pytest.raises(UnknownFieldError, match="'stock'"):
            check_query({"$expr": {"$gt": ["$price", "$stock"]}}, KNOWN)

    def test_other_top_level_operators_are_skipped(self) -> None:
        check_query({"$text": {"$search": "laptop"}, "$comment": "demo"}, KNOWN)

    def test_unknown_shape_skips_check(self) -> None:
        check_query({"anything": 1}, None)


class TestCheckExpression:
    def test_field_paths(self) -> None:
        check_expression({"$sum": ["$price", "$orders.quantity"]}, KNOWN, "$group")

    def test_unknown_field_path_raises(self) -> None:
        with pytest.raises(UnknownFieldError, match=r"in \$group"):
            check_expression({"$sum": "$quantity"}, KNOWN, "$group")

    @pytest.mark.parametrize(
        "expression",
        [
            "$$ROOT",
            "$$item.price",
            "$",
            "plain string",
            42,
            None,
            {"$literal": "$notAField"},
            {"$function": {"body": "...", "args": ["$notAField"], "lang": "js"}},
        ],
    )
    def test_non_field_values_are_skipped(self, expression: Any) -> None:
        check_expression(expression, KNOWN, "$group")

    def test_object_keys_are_not_checked(self) -> None:
        check_expression({"newField": "$name"}, KNOWN, "$addFields")
