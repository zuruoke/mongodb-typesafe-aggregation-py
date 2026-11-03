from __future__ import annotations

from typing import Any, Literal, TypedDict

import pytest
from pydantic import BaseModel, Field
from typing_extensions import assert_type

from mongodb_typesafe_aggregation import FilterOperator, PipelineBuilder, UnknownFieldError
from mongodb_typesafe_aggregation.types.filter import filter


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

    def test_same_key_in_mapping_and_keyword_arguments_raises(self) -> None:
        with pytest.raises(TypeError, match=r"\['active'\] given both"):
            PipelineBuilder(Product).match({"active": False}, active=True)

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

    def test_supports_built_filter_operator_values(self) -> None:
        pipeline = (
            PipelineBuilder(Product)
            .match({"price": FilterOperator[float]().gt(500).build()})
            .build()
        )
        assert pipeline == [{"$match": {"price": {"$gt": 500}}}]

    def test_builds_filter_operator_values(self) -> None:
        pipeline = (
            PipelineBuilder(Product)
            .match(
                price=filter(float).gte(100).lte(999),
                category=filter(str).in_(["electronics", "furniture"]),
                stock=filter(int).exists(True),
            )
            .build()
        )
        assert pipeline == [
            {
                "$match": {
                    "price": {"$gte": 100, "$lte": 999},
                    "category": {"$in": ["electronics", "furniture"]},
                    "stock": {"$exists": True},
                }
            }
        ]

    def test_builds_filter_operators_inside_logical_operators(self) -> None:
        pipeline = (
            PipelineBuilder(Product)
            .match({"$or": [{"stock": filter(int).lt(5)}, {"active": False}]})
            .build()
        )
        assert pipeline == [{"$match": {"$or": [{"stock": {"$lt": 5}}, {"active": False}]}}]

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

    def test_additive_stages_keep_document_type(self) -> None:
        products = PipelineBuilder(Product)
        assert_type(
            products.lookup("orders", local_field="_id", foreign_field="productId", as_="orders"),
            PipelineBuilder[Product],
        )
        assert_type(products.add_fields(x=1), PipelineBuilder[Product])
        assert_type(products.set(x=1), PipelineBuilder[Product])
        assert_type(products.sort(price=-1).skip(1).limit(1), PipelineBuilder[Product])
        assert_type(products.unset("tags"), PipelineBuilder[Product])

    def test_reshaping_stages_return_any(self) -> None:
        products = PipelineBuilder(Product)
        assert_type(products.group(_id="$category"), PipelineBuilder[Any])
        assert_type(products.project(name=1), PipelineBuilder[Any])
        assert_type(products.unwind("$tags"), PipelineBuilder[Any])
        assert_type(products.count(), PipelineBuilder[dict[str, int]])

    def test_cast_sets_document_type(self) -> None:
        assert_type(
            PipelineBuilder(Product).group(_id="$category").cast(CategoryTotal),
            PipelineBuilder[CategoryTotal],
        )

    def test_sort_order_is_checked_statically_and_at_runtime(self) -> None:
        with pytest.raises(ValueError, match="Invalid"):
            PipelineBuilder(Product).sort(price="desc")  # type: ignore[arg-type]


class CategoryTotal(TypedDict):
    _id: str
    total: int


class TestLookup:
    def test_adds_a_lookup_stage(self) -> None:
        pipeline = (
            PipelineBuilder(Product)
            .lookup("orders", local_field="_id", foreign_field="productId", as_="orders")
            .build()
        )
        assert pipeline == [
            {
                "$lookup": {
                    "from": "orders",
                    "localField": "_id",
                    "foreignField": "productId",
                    "as": "orders",
                }
            }
        ]

    def test_does_not_mutate_the_original_builder(self) -> None:
        base = PipelineBuilder(Product).match(active=True)
        base.lookup("orders", local_field="_id", foreign_field="productId", as_="orders")
        assert base.build() == [{"$match": {"active": True}}]

    def test_as_field_becomes_known(self) -> None:
        pipeline = (
            PipelineBuilder(Product)
            .lookup("orders", local_field="_id", foreign_field="productId", as_="orders")
            .add_fields(ordered={"$sum": "$orders.quantity"})
            .build()
        )
        assert pipeline[1] == {"$addFields": {"ordered": {"$sum": "$orders.quantity"}}}

    def test_checks_local_field(self) -> None:
        with pytest.raises(UnknownFieldError, match=r"'nmae' in \$lookup"):
            PipelineBuilder(Product).lookup(
                "orders", local_field="nmae", foreign_field="productId", as_="orders"
            )

    def test_checks_let_expressions_but_not_the_foreign_pipeline(self) -> None:
        orders = PipelineBuilder().match({"$expr": {"$eq": ["$productId", "$$pid"]}})
        pipeline = (
            PipelineBuilder(Product)
            .lookup("orders", let={"pid": "$_id"}, pipeline=orders, as_="orders")
            .build()
        )
        assert pipeline[0]["$lookup"]["pipeline"] == [
            {"$match": {"$expr": {"$eq": ["$productId", "$$pid"]}}}
        ]

        with pytest.raises(UnknownFieldError, match="'id'"):
            PipelineBuilder(Product).lookup("orders", let={"pid": "$id"}, pipeline=[], as_="o")


class TestGroup:
    def test_adds_a_group_stage(self) -> None:
        pipeline = PipelineBuilder().group({"_id": "$status", "total": {"$sum": 1}}).build()
        assert pipeline == [{"$group": {"_id": "$status", "total": {"$sum": 1}}}]

    def test_keyword_arguments(self) -> None:
        pipeline = PipelineBuilder(Product).group(_id="$category", n={"$sum": 1}).build()
        assert pipeline == [{"$group": {"_id": "$category", "n": {"$sum": 1}}}]

    def test_checks_field_paths(self) -> None:
        with pytest.raises(UnknownFieldError, match=r"'prices' in \$group"):
            PipelineBuilder(Product).group(_id="$category", total={"$sum": "$prices"})

    def test_only_output_fields_are_known_afterwards(self) -> None:
        grouped = PipelineBuilder(Product).group(_id="$category", total={"$sum": "$price"})
        assert grouped.sort(total=-1).build()[-1] == {"$sort": {"total": -1}}

        with pytest.raises(UnknownFieldError, match="Known fields: _id, total"):
            grouped.sort(price=-1)


class TestAddFieldsAndSet:
    def test_adds_an_add_fields_stage(self) -> None:
        pipeline = PipelineBuilder(Product).add_fields({"computed": {"$sum": "$price"}}).build()
        assert pipeline == [{"$addFields": {"computed": {"$sum": "$price"}}}]

    def test_adds_a_set_stage(self) -> None:
        pipeline = PipelineBuilder(Product).set({"label": "test"}).build()
        assert pipeline == [{"$set": {"label": "test"}}]

    def test_builds_filter_operators(self) -> None:
        pipeline = (
            PipelineBuilder(Product)
            .add_fields(
                isExpensive=filter(bool).cond({"$gt": ["$price", 500]}, {"$literal": True}, False)
            )
            .build()
        )
        assert pipeline == [
            {
                "$addFields": {
                    "isExpensive": {
                        "$cond": {
                            "if": {"$gt": ["$price", 500]},
                            "then": {"$literal": True},
                            "else": False,
                        }
                    }
                }
            }
        ]

    @pytest.mark.parametrize("method", ["add_fields", "set"])
    def test_checks_field_paths(self, method: str) -> None:
        with pytest.raises(UnknownFieldError, match="'stok'"):
            getattr(PipelineBuilder(Product), method)(low={"$lt": ["$stok", 5]})

    @pytest.mark.parametrize("method", ["add_fields", "set"])
    def test_new_fields_become_known(self, method: str) -> None:
        builder = getattr(PipelineBuilder(Product), method)({"supplier.name": "x", "low": True})
        assert builder.sort(low=1, supplier=1).build()[-1] == {"$sort": {"low": 1, "supplier": 1}}


class TestProject:
    def test_adds_a_project_stage(self) -> None:
        pipeline = PipelineBuilder(Product).project({"_id": 0, "name": 1, "price": 1}).build()
        assert pipeline == [{"$project": {"_id": 0, "name": 1, "price": 1}}]

    def test_checks_included_fields(self) -> None:
        with pytest.raises(UnknownFieldError, match=r"'nmae' in \$project"):
            PipelineBuilder(Product).project(nmae=1)

    def test_checks_computed_expressions(self) -> None:
        with pytest.raises(UnknownFieldError, match="'stok'"):
            PipelineBuilder(Product).project(remaining={"$subtract": ["$stok", 1]})

    def test_inclusion_keeps_projected_fields_and_id(self) -> None:
        projected = PipelineBuilder(Product).project(name=1, label="$category")
        projected.sort(_id=1, name=1, label=1)

        with pytest.raises(UnknownFieldError, match="Known fields: _id, label, name"):
            projected.sort(price=1)

    def test_excluding_id_removes_it(self) -> None:
        with pytest.raises(UnknownFieldError, match="Known fields: name"):
            PipelineBuilder(Product).project(_id=0, name=1).sort(_id=1)

    def test_exclusion_removes_fields(self) -> None:
        trimmed = PipelineBuilder(Product).project(tags=0, stock=0)
        trimmed.sort(price=1)

        with pytest.raises(UnknownFieldError, match="'tags'"):
            trimmed.sort(tags=1)

    def test_nested_projection(self) -> None:
        pipeline = PipelineBuilder(Product).project(tags={"first": 1}).build()
        assert pipeline == [{"$project": {"tags": {"first": 1}}}]


class TestSort:
    def test_adds_a_sort_stage(self) -> None:
        pipeline = PipelineBuilder(Product).sort({"price": -1}).build()
        assert pipeline == [{"$sort": {"price": -1}}]

    def test_keyword_arguments_keep_order(self) -> None:
        pipeline = PipelineBuilder(Product).sort(category=1, price=-1).build()
        assert list(pipeline[0]["$sort"]) == ["category", "price"]

    def test_checks_fields(self) -> None:
        with pytest.raises(UnknownFieldError, match=r"'prcie' in \$sort. Did you mean 'price'"):
            PipelineBuilder(Product).sort(prcie=-1)


class TestSkipLimitCount:
    def test_skip(self) -> None:
        assert PipelineBuilder(Product).skip(10).build() == [{"$skip": 10}]

    def test_limit(self) -> None:
        assert PipelineBuilder(Product).limit(5).build() == [{"$limit": 5}]

    def test_count(self) -> None:
        pipeline = PipelineBuilder(Product).match(active=True).count("activeTotal").build()
        assert pipeline == [{"$match": {"active": True}}, {"$count": "activeTotal"}]

    def test_count_field_is_the_only_known_field(self) -> None:
        counted = PipelineBuilder(Product).count()
        assert counted.build() == [{"$count": "count"}]

        with pytest.raises(UnknownFieldError, match="Known fields: count"):
            counted.sort(_id=1)


class TestFacet:
    def test_adds_a_facet_stage(self) -> None:
        pipeline = (
            PipelineBuilder().facet({"byCategory": [{"$group": {"_id": "$category"}}]}).build()
        )
        assert pipeline == [{"$facet": {"byCategory": [{"$group": {"_id": "$category"}}]}}]

    def test_accepts_builders_and_functions(self) -> None:
        pipeline = (
            PipelineBuilder(Product)
            .facet(
                expensive=lambda products: products.match(price=filter(float).gte(700)),
                low_stock=PipelineBuilder(Product).match(stock=filter(int).lt(20)),
                total=[{"$count": "n"}],
            )
            .build()
        )
        assert pipeline == [
            {
                "$facet": {
                    "expensive": [{"$match": {"price": {"$gte": 700}}}],
                    "low_stock": [{"$match": {"stock": {"$lt": 20}}}],
                    "total": [{"$count": "n"}],
                }
            }
        ]

    def test_functions_are_checked_against_the_current_shape(self) -> None:
        grouped = PipelineBuilder(Product).group(_id="$category", total={"$sum": 1})
        grouped.facet(top=lambda groups: groups.sort(total=-1))

        with pytest.raises(UnknownFieldError, match="'price'"):
            grouped.facet(top=lambda groups: groups.sort(price=-1))

    def test_facet_names_are_the_only_known_fields(self) -> None:
        with pytest.raises(UnknownFieldError, match="Known fields: a, b"):
            PipelineBuilder(Product).facet(a=[], b=[]).sort(_id=1)

    def test_rejects_a_single_stage(self) -> None:
        with pytest.raises(TypeError, match="Expected a list of stages"):
            PipelineBuilder(Product).facet(a={"$count": "n"})  # type: ignore[arg-type]


class TestUnwind:
    def test_adds_an_unwind_stage_with_a_string_path(self) -> None:
        assert PipelineBuilder(Product).unwind("$tags").build() == [{"$unwind": "$tags"}]

    def test_adds_an_unwind_stage_with_an_object_spec(self) -> None:
        pipeline = (
            PipelineBuilder(Product)
            .unwind({"path": "$tags", "preserveNullAndEmptyArrays": True})
            .build()
        )
        assert pipeline == [{"$unwind": {"path": "$tags", "preserveNullAndEmptyArrays": True}}]

    def test_checks_path(self) -> None:
        with pytest.raises(UnknownFieldError, match=r"'tag' in \$unwind"):
            PipelineBuilder(Product).unwind("$tag")

    def test_array_index_field_becomes_known(self) -> None:
        unwound = PipelineBuilder(Product).unwind("$tags", include_array_index="tagIndex")
        assert unwound.sort(tagIndex=1).build()[-1] == {"$sort": {"tagIndex": 1}}


class TestReplaceRoot:
    def test_adds_a_replace_root_stage(self) -> None:
        pipeline = PipelineBuilder().replace_root({"label": "$name"}).build()
        assert pipeline == [{"$replaceRoot": {"newRoot": {"label": "$name"}}}]

    def test_checks_expression(self) -> None:
        with pytest.raises(UnknownFieldError, match="'nmae'"):
            PipelineBuilder(Product).replace_root({"label": "$nmae"})

    def test_document_literal_keys_become_known(self) -> None:
        with pytest.raises(UnknownFieldError, match="Known fields: label"):
            PipelineBuilder(Product).replace_root({"label": "$name"}).sort(name=1)

    def test_expression_makes_shape_unknown_until_cast(self) -> None:
        replaced = PipelineBuilder(Product).replace_root({"$mergeObjects": ["$$ROOT", {"x": 1}]})
        replaced.sort(anything=1)

        with pytest.raises(UnknownFieldError, match="'region'"):
            replaced.cast(CategoryTotal).sort(region=1)


class TestUnionWith:
    def test_adds_a_union_with_stage(self) -> None:
        pipeline = PipelineBuilder(Product).union_with("archived_products").build()
        assert pipeline == [{"$unionWith": {"coll": "archived_products"}}]

    def test_accepts_a_builder_pipeline(self) -> None:
        pipeline = (
            PipelineBuilder(Product)
            .union_with("archived_products", PipelineBuilder().project(name=1))
            .build()
        )
        assert pipeline == [
            {"$unionWith": {"coll": "archived_products", "pipeline": [{"$project": {"name": 1}}]}}
        ]


class TestUnset:
    def test_adds_an_unset_stage_with_a_string(self) -> None:
        assert PipelineBuilder(Product).unset("active").build() == [{"$unset": "active"}]

    def test_adds_an_unset_stage_with_a_list(self) -> None:
        pipeline = PipelineBuilder(Product).unset(["active", "tags"]).build()
        assert pipeline == [{"$unset": ["active", "tags"]}]

    def test_checks_fields(self) -> None:
        with pytest.raises(UnknownFieldError, match=r"'activ' in \$unset"):
            PipelineBuilder(Product).unset("activ")

    def test_removed_fields_are_no_longer_known(self) -> None:
        with pytest.raises(UnknownFieldError, match="'active'"):
            PipelineBuilder(Product).unset("active").match(active=True)


class TestMerge:
    def test_adds_a_merge_stage(self) -> None:
        pipeline = PipelineBuilder(Product).merge("summary", when_matched="replace").build()
        assert pipeline == [{"$merge": {"into": "summary", "whenMatched": "replace"}}]

    def test_checks_on_fields(self) -> None:
        with pytest.raises(UnknownFieldError, match=r"'sku' in \$merge"):
            PipelineBuilder(Product).merge("summary", on=["_id", "sku"])

    def test_must_be_the_last_stage(self) -> None:
        merged = PipelineBuilder(Product).merge("summary")
        with pytest.raises(ValueError, match="must be the last stage"):
            merged.limit(1)
        with pytest.raises(ValueError, match="must be the last stage"):
            merged.raw({"$limit": 1})


class TestGraphLookup:
    def test_adds_a_graph_lookup_stage(self) -> None:
        pipeline = (
            PipelineBuilder()
            .graph_lookup(
                "employees",
                start_with="$managerId",
                connect_from_field="managerId",
                connect_to_field="_id",
                as_="reports",
                max_depth=3,
            )
            .build()
        )
        assert pipeline == [
            {
                "$graphLookup": {
                    "from": "employees",
                    "startWith": "$managerId",
                    "connectFromField": "managerId",
                    "connectToField": "_id",
                    "as": "reports",
                    "maxDepth": 3,
                }
            }
        ]

    def test_checks_start_with_and_adds_as_field(self) -> None:
        options: dict[str, Any] = {
            "connect_from_field": "relatedIds",
            "connect_to_field": "_id",
            "as_": "related",
        }
        related = PipelineBuilder(Product).graph_lookup("products", start_with="$_id", **options)
        related.sort(related=1)

        with pytest.raises(UnknownFieldError, match=r"'relatedIds' in \$graphLookup"):
            PipelineBuilder(Product).graph_lookup("products", start_with="$relatedIds", **options)


class TestBucket:
    def test_adds_a_bucket_stage(self) -> None:
        pipeline = PipelineBuilder().bucket("$price", [0, 100, 500], default="other").build()
        assert pipeline == [
            {"$bucket": {"groupBy": "$price", "boundaries": [0, 100, 500], "default": "other"}}
        ]

    def test_checks_group_by_and_output(self) -> None:
        with pytest.raises(UnknownFieldError, match="'prcie'"):
            PipelineBuilder(Product).bucket("$prcie", [0, 100])
        with pytest.raises(UnknownFieldError, match="'stok'"):
            PipelineBuilder(Product).bucket("$price", [0, 100], output={"s": {"$sum": "$stok"}})

    def test_known_fields_are_id_and_count_or_output(self) -> None:
        with pytest.raises(UnknownFieldError, match="Known fields: _id, count"):
            PipelineBuilder(Product).bucket("$price", [0, 100]).sort(price=1)
        with pytest.raises(UnknownFieldError, match="Known fields: _id, names"):
            (
                PipelineBuilder(Product)
                .bucket("$price", [0, 100], output={"names": {"$push": "$name"}})
                .sort(price=1)
            )


class TestBucketAuto:
    def test_adds_a_bucket_auto_stage(self) -> None:
        pipeline = PipelineBuilder().bucket_auto("$price", 4).build()
        assert pipeline == [{"$bucketAuto": {"groupBy": "$price", "buckets": 4}}]

    def test_checks_group_by(self) -> None:
        with pytest.raises(UnknownFieldError, match=r"'prcie' in \$bucketAuto"):
            PipelineBuilder(Product).bucket_auto("$prcie", 4)

    def test_known_fields_are_id_and_count(self) -> None:
        bucketed = PipelineBuilder(Product).bucket_auto("$price", 2)
        assert bucketed.sort(count=-1).build()[-1] == {"$sort": {"count": -1}}


class TestRedact:
    def test_adds_a_redact_stage(self) -> None:
        spec = {"$cond": {"if": {"$eq": ["$active", True]}, "then": "$$KEEP", "else": "$$PRUNE"}}
        assert PipelineBuilder(Product).redact(spec).build() == [{"$redact": spec}]

    def test_checks_expression(self) -> None:
        with pytest.raises(UnknownFieldError, match=r"'level' in \$redact"):
            PipelineBuilder(Product).redact(
                {"$cond": [{"$eq": ["$level", 5]}, "$$PRUNE", "$$KEEP"]}
            )


class TestCast:
    def test_declares_the_shape_for_following_stages(self) -> None:
        stats = PipelineBuilder(Product).raw({"$sortByCount": "$category"}).cast(CategoryTotal)
        assert stats.sort(total=-1).build()[-1] == {"$sort": {"total": -1}}

        with pytest.raises(UnknownFieldError, match="'count'"):
            stats.sort(count=-1)

    def test_turns_checks_on_for_a_builder_without_schema(self) -> None:
        with pytest.raises(UnknownFieldError):
            PipelineBuilder().cast(CategoryTotal).sort(nope=1)

    def test_strict_false_keeps_checks_off(self) -> None:
        PipelineBuilder(Product, strict=False).cast(CategoryTotal).sort(nope=1)


class TestChaining:
    def test_preserves_stage_order(self) -> None:
        pipeline = (
            PipelineBuilder(Product).match(active=True).sort(price=-1).skip(0).limit(10).build()
        )
        assert pipeline == [
            {"$match": {"active": True}},
            {"$sort": {"price": -1}},
            {"$skip": 0},
            {"$limit": 10},
        ]

    def test_build_returns_a_new_list_each_time(self) -> None:
        builder = PipelineBuilder(Product).match(active=True)
        first, second = builder.build(), builder.build()
        assert first is not second
        assert first == second

    def test_repr(self) -> None:
        assert repr(PipelineBuilder().limit(1)) == "PipelineBuilder([{'$limit': 1}])"

    def test_full_pipeline_tracks_shape_end_to_end(self) -> None:
        pipeline = (
            PipelineBuilder(Order)
            .match(status="pending")
            .lookup("products", local_field="productId", foreign_field="_id", as_="product")
            .unwind("$product")
            .group(
                _id="$product.category",
                orders={"$sum": 1},
                quantity={"$sum": "$quantity"},
            )
            .sort(quantity=-1)
            .project(_id=0, category="$_id", orders=1, quantity=1)
            .build()
        )
        assert pipeline == [
            {"$match": {"status": "pending"}},
            {
                "$lookup": {
                    "from": "products",
                    "localField": "productId",
                    "foreignField": "_id",
                    "as": "product",
                }
            },
            {"$unwind": "$product"},
            {
                "$group": {
                    "_id": "$product.category",
                    "orders": {"$sum": 1},
                    "quantity": {"$sum": "$quantity"},
                }
            },
            {"$sort": {"quantity": -1}},
            {"$project": {"_id": 0, "category": "$_id", "orders": 1, "quantity": 1}},
        ]
