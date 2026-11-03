from __future__ import annotations

from typing import Any, Literal, TypedDict

import pytest
from pydantic import BaseModel, Field
from typing_extensions import assert_type

from mongodb_typesafe_aggregation import PipelineBuilder, UnknownFieldError


class Product(TypedDict):
    _id: str
    name: str
    price: float
    stock: int
    category: str
    tags: list[str]
    active: bool


class Order(BaseModel):
    id: str = Field(alias="_id")
    product_id: str = Field(alias="productId")
    quantity: int
    status: Literal["pending", "completed"]


class TestPipelineBuilder:
    def test_build_returns_empty_list_for_fresh_builder(self) -> None:
        assert PipelineBuilder(Product).build() == []

    def test_accepts_initial_stages(self) -> None:
        assert PipelineBuilder(Product, [{"$limit": 5}]).build() == [{"$limit": 5}]

    def test_initial_stages_are_copied(self) -> None:
        initial: list[dict[str, Any]] = [{"$limit": 5}]
        builder = PipelineBuilder(Product, initial)
        initial.append({"$skip": 1})

        assert builder.build() == [{"$limit": 5}]

    def test_build_returns_a_deep_copy(self) -> None:
        builder = PipelineBuilder(Product).match(tags={"$in": ["sale"]})
        pipeline = builder.build()
        pipeline[0]["$match"]["tags"]["$in"].append("new")
        pipeline.append({"$limit": 1})

        assert builder.build() == [{"$match": {"tags": {"$in": ["sale"]}}}]

    def test_methods_return_new_builders(self) -> None:
        base = PipelineBuilder(Product).match(active=True)
        cheap = base.match(price={"$lt": 100})
        electronics = base.match(category="electronics")

        assert base.build() == [{"$match": {"active": True}}]
        assert cheap.build() == [{"$match": {"active": True}}, {"$match": {"price": {"$lt": 100}}}]
        assert electronics.build() == [
            {"$match": {"active": True}},
            {"$match": {"category": "electronics"}},
        ]

    def test_raw_adds_stage_without_checks(self) -> None:
        pipeline = PipelineBuilder(Product).raw({"$sample": {"size": 3}}).build()
        assert pipeline == [{"$sample": {"size": 3}}]

    def test_schema_must_declare_fields(self) -> None:
        with pytest.raises(TypeError, match="declares no fields"):
            PipelineBuilder(dict)


class TestMatch:
    def test_mapping(self) -> None:
        pipeline = PipelineBuilder(Product).match({"category": "electronics"}).build()
        assert pipeline == [{"$match": {"category": "electronics"}}]

    def test_keyword_arguments(self) -> None:
        pipeline = PipelineBuilder(Product).match(category="electronics", active=True).build()
        assert pipeline == [{"$match": {"category": "electronics", "active": True}}]

    def test_mapping_and_keyword_arguments_are_merged(self) -> None:
        pipeline = PipelineBuilder(Product).match({"price": {"$gt": 500}}, active=True).build()
        assert pipeline == [{"$match": {"price": {"$gt": 500}, "active": True}}]

    def test_query_operators(self) -> None:
        pipeline = (
            PipelineBuilder(Product)
            .match(price={"$gte": 100, "$lte": 999}, category={"$in": ["electronics", "toys"]})
            .build()
        )
        assert pipeline == [
            {
                "$match": {
                    "price": {"$gte": 100, "$lte": 999},
                    "category": {"$in": ["electronics", "toys"]},
                }
            }
        ]

    def test_logical_operators(self) -> None:
        query = {"$or": [{"stock": 0}, {"active": False}]}
        assert PipelineBuilder(Product).match(query).build() == [{"$match": query}]

    def test_expr(self) -> None:
        query = {"$expr": {"$lt": ["$stock", "$price"]}}
        assert PipelineBuilder(Product).match(query).build() == [{"$match": query}]

    def test_dotted_path_on_known_field(self) -> None:
        pipeline = PipelineBuilder(Product).match({"tags.0": "sale"}).build()
        assert pipeline == [{"$match": {"tags.0": "sale"}}]

    def test_unknown_field_raises_with_suggestion(self) -> None:
        with pytest.raises(
            UnknownFieldError, match=r"'categry' in \$match\. Did you mean 'category'"
        ):
            PipelineBuilder(Product).match(categry="electronics")

    def test_unknown_field_in_logical_operator_raises(self) -> None:
        with pytest.raises(UnknownFieldError, match="'stok'"):
            PipelineBuilder(Product).match({"$or": [{"stok": 0}, {"active": False}]})

    def test_unknown_field_in_expr_raises(self) -> None:
        with pytest.raises(UnknownFieldError, match="'prise'"):
            PipelineBuilder(Product).match({"$expr": {"$lt": ["$stock", "$prise"]}})

    def test_pydantic_schema_uses_aliases(self) -> None:
        pipeline = PipelineBuilder(Order).match(productId="p1", status="pending").build()
        assert pipeline == [{"$match": {"productId": "p1", "status": "pending"}}]

        with pytest.raises(UnknownFieldError, match="'product_id'"):
            PipelineBuilder(Order).match(product_id="p1")

    def test_no_schema_skips_checks(self) -> None:
        assert PipelineBuilder().match(anything=1).build() == [{"$match": {"anything": 1}}]

    def test_strict_false_skips_checks(self) -> None:
        pipeline = PipelineBuilder(Product, strict=False).match(anything=1).build()
        assert pipeline == [{"$match": {"anything": 1}}]


class TestStaticTypes:
    def test_schema_sets_document_type(self) -> None:
        assert_type(PipelineBuilder(Product), PipelineBuilder[Product])
        assert_type(PipelineBuilder(Order), PipelineBuilder[Order])

    def test_no_schema_is_any(self) -> None:
        assert_type(PipelineBuilder(), PipelineBuilder[Any])

    def test_match_keeps_document_type(self) -> None:
        assert_type(PipelineBuilder(Product).match(active=True), PipelineBuilder[Product])
