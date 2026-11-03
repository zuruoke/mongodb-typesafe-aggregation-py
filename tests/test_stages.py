from __future__ import annotations

from typing import Any

import pytest

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
from mongodb_typesafe_aggregation.types.filter import filter


class TestMatchStage:
    def test_wraps_query(self) -> None:
        assert match_stage({"status": "active"}) == {"$match": {"status": "active"}}

    def test_copies_query(self) -> None:
        query: dict[str, object] = {"status": "active"}
        stage = match_stage(query)
        query["price"] = 1

        assert stage == {"$match": {"status": "active"}}

    def test_builds_filter_operators(self) -> None:
        assert match_stage({"price": filter(int).gt(5)}) == {"$match": {"price": {"$gt": 5}}}


class TestLookupStage:
    def test_equality_match(self) -> None:
        stage = lookup_stage("orders", local_field="_id", foreign_field="productId", as_="orders")
        assert stage == {
            "$lookup": {
                "from": "orders",
                "localField": "_id",
                "foreignField": "productId",
                "as": "orders",
            }
        }

    def test_pipeline_with_let(self) -> None:
        stage = lookup_stage(
            "orders",
            let={"pid": "$_id"},
            pipeline=[{"$match": {"$expr": {"$eq": ["$productId", "$$pid"]}}}],
            as_="orders",
        )
        assert stage == {
            "$lookup": {
                "from": "orders",
                "let": {"pid": "$_id"},
                "pipeline": [{"$match": {"$expr": {"$eq": ["$productId", "$$pid"]}}}],
                "as": "orders",
            }
        }

    def test_requires_both_fields_together(self) -> None:
        with pytest.raises(ValueError, match="together"):
            lookup_stage("orders", local_field="_id", as_="orders")

    def test_requires_fields_or_pipeline(self) -> None:
        with pytest.raises(ValueError, match="a pipeline, or both"):
            lookup_stage("orders", as_="orders")


class TestGroupStage:
    def test_wraps_spec(self) -> None:
        spec = {"_id": "$category", "total": {"$sum": 1}}
        assert group_stage(spec) == {"$group": spec}

    def test_null_id_groups_everything(self) -> None:
        assert group_stage({"_id": None}) == {"$group": {"_id": None}}

    def test_requires_id(self) -> None:
        with pytest.raises(ValueError, match="requires an '_id'"):
            group_stage({"total": {"$sum": 1}})


class TestAddFieldsAndSetStages:
    def test_add_fields_wraps_spec(self) -> None:
        spec = {"computed": {"$sum": "$items"}}
        assert add_fields_stage(spec) == {"$addFields": spec}

    def test_set_wraps_spec(self) -> None:
        assert set_stage({"isActive": True}) == {"$set": {"isActive": True}}

    def test_builds_filter_operators(self) -> None:
        stage = set_stage({"isAdmin": filter(bool).cond({"$eq": ["$role", "admin"]}, True, False)})
        assert stage == {
            "$set": {
                "isAdmin": {
                    "$cond": {"if": {"$eq": ["$role", "admin"]}, "then": True, "else": False}
                }
            }
        }

    @pytest.mark.parametrize("stage_function", [add_fields_stage, set_stage])
    def test_require_fields(self, stage_function: Any) -> None:
        with pytest.raises(ValueError, match="at least one field"):
            stage_function({})


class TestProjectStage:
    def test_wraps_spec(self) -> None:
        assert project_stage({"_id": 0, "name": 1}) == {"$project": {"_id": 0, "name": 1}}

    def test_exclusion(self) -> None:
        assert project_stage({"description": 0, "tags": False}) == {
            "$project": {"description": 0, "tags": False}
        }

    def test_computed_fields_with_id_excluded(self) -> None:
        spec = {"_id": 0, "name": 1, "total": {"$multiply": ["$price", 2]}}
        assert project_stage(spec) == {"$project": spec}

    def test_rejects_mixed_inclusion_and_exclusion(self) -> None:
        with pytest.raises(ValueError, match="cannot mix exclusions"):
            project_stage({"name": 1, "description": 0})

    def test_rejects_computed_field_with_exclusion(self) -> None:
        with pytest.raises(ValueError, match="cannot mix exclusions"):
            project_stage({"description": 0, "label": "$name"})

    def test_requires_fields(self) -> None:
        with pytest.raises(ValueError, match="at least one field"):
            project_stage({})


class TestSortStage:
    def test_wraps_spec(self) -> None:
        assert sort_stage({"price": -1}) == {"$sort": {"price": -1}}

    def test_keeps_field_order(self) -> None:
        assert list(sort_stage({"b": 1, "a": -1})["$sort"]) == ["b", "a"]

    def test_meta_sort(self) -> None:
        spec = {"score": {"$meta": "textScore"}}
        assert sort_stage(spec) == {"$sort": spec}

    @pytest.mark.parametrize("order", [0, 2, "asc", True, {"$x": 1}])
    def test_rejects_invalid_order(self, order: Any) -> None:
        with pytest.raises(ValueError, match="Invalid \\$sort order"):
            sort_stage({"price": order})

    def test_requires_fields(self) -> None:
        with pytest.raises(ValueError, match="at least one field"):
            sort_stage({})


class TestSkipAndLimitStages:
    def test_skip(self) -> None:
        assert skip_stage(10) == {"$skip": 10}
        assert skip_stage(0) == {"$skip": 0}

    def test_limit(self) -> None:
        assert limit_stage(5) == {"$limit": 5}

    @pytest.mark.parametrize("count", [-1, 1.5, "3", True])
    def test_skip_rejects_invalid_count(self, count: Any) -> None:
        with pytest.raises(ValueError, match=r"\$skip requires an integer >= 0"):
            skip_stage(count)

    @pytest.mark.parametrize("count", [0, -1, 2.0, None])
    def test_limit_rejects_invalid_count(self, count: Any) -> None:
        with pytest.raises(ValueError, match=r"\$limit requires an integer >= 1"):
            limit_stage(count)


class TestFacetStage:
    def test_wraps_spec(self) -> None:
        spec = {"byCategory": [{"$group": {"_id": "$category"}}]}
        assert facet_stage(spec) == {"$facet": spec}

    def test_builds_filter_operators(self) -> None:
        stage = facet_stage({"cheap": [{"$match": {"price": filter(int).lt(10)}}]})
        assert stage == {"$facet": {"cheap": [{"$match": {"price": {"$lt": 10}}}]}}

    def test_requires_fields(self) -> None:
        with pytest.raises(ValueError, match="at least one field"):
            facet_stage({})


class TestUnwindStage:
    def test_accepts_a_string_path(self) -> None:
        assert unwind_stage("$items") == {"$unwind": "$items"}

    def test_accepts_an_object_spec(self) -> None:
        spec = {"path": "$items", "preserveNullAndEmptyArrays": True}
        assert unwind_stage(spec) == {"$unwind": spec}

    def test_object_spec_with_only_path_uses_short_form(self) -> None:
        assert unwind_stage({"path": "$items"}) == {"$unwind": "$items"}

    def test_keyword_options(self) -> None:
        stage = unwind_stage(
            "$items", include_array_index="i", preserve_null_and_empty_arrays=False
        )
        assert stage == {
            "$unwind": {
                "path": "$items",
                "includeArrayIndex": "i",
                "preserveNullAndEmptyArrays": False,
            }
        }

    @pytest.mark.parametrize("path", ["items", "$$items", "", {"preserveNullAndEmptyArrays": True}])
    def test_rejects_invalid_path(self, path: Any) -> None:
        with pytest.raises(ValueError, match="must be a field path"):
            unwind_stage(path)


class TestReplaceRootStage:
    def test_wraps_new_root(self) -> None:
        assert replace_root_stage({"label": "$name"}) == {
            "$replaceRoot": {"newRoot": {"label": "$name"}}
        }

    def test_field_path(self) -> None:
        assert replace_root_stage("$supplier") == {"$replaceRoot": {"newRoot": "$supplier"}}


class TestCountStage:
    def test_wraps_field_name(self) -> None:
        assert count_stage("total") == {"$count": "total"}

    def test_default_field_name(self) -> None:
        assert count_stage() == {"$count": "count"}

    @pytest.mark.parametrize("field", ["", "$total", "a.b"])
    def test_rejects_invalid_field_name(self, field: str) -> None:
        with pytest.raises(ValueError, match=r"\$count field"):
            count_stage(field)


class TestUnionWithStage:
    def test_collection_only(self) -> None:
        assert union_with_stage("archived_products") == {
            "$unionWith": {"coll": "archived_products"}
        }

    def test_with_pipeline(self) -> None:
        assert union_with_stage("archived_products", []) == {
            "$unionWith": {"coll": "archived_products", "pipeline": []}
        }


class TestUnsetStage:
    def test_accepts_a_single_string_field(self) -> None:
        assert unset_stage("password") == {"$unset": "password"}

    def test_accepts_a_list_of_fields(self) -> None:
        assert unset_stage(["password", "token"]) == {"$unset": ["password", "token"]}

    def test_accepts_a_tuple_of_fields(self) -> None:
        assert unset_stage(("password",)) == {"$unset": ["password"]}

    @pytest.mark.parametrize("fields", ["", []])
    def test_requires_a_field(self, fields: Any) -> None:
        with pytest.raises(ValueError, match="at least one field"):
            unset_stage(fields)


class TestMergeStage:
    def test_wraps_options(self) -> None:
        stage = merge_stage("summary", when_matched="replace", when_not_matched="insert")
        assert stage == {
            "$merge": {"into": "summary", "whenMatched": "replace", "whenNotMatched": "insert"}
        }

    def test_into_another_database(self) -> None:
        stage = merge_stage({"db": "reports", "coll": "summary"}, on=["region", "month"])
        assert stage == {
            "$merge": {"into": {"db": "reports", "coll": "summary"}, "on": ["region", "month"]}
        }

    def test_when_matched_pipeline(self) -> None:
        stage = merge_stage(
            "summary",
            let={"total": "$total"},
            when_matched=[{"$set": {"total": {"$add": ["$total", "$$total"]}}}],
        )
        assert stage == {
            "$merge": {
                "into": "summary",
                "let": {"total": "$total"},
                "whenMatched": [{"$set": {"total": {"$add": ["$total", "$$total"]}}}],
            }
        }


class TestGraphLookupStage:
    def test_wraps_spec(self) -> None:
        stage = graph_lookup_stage(
            "employees",
            start_with="$managerId",
            connect_from_field="managerId",
            connect_to_field="_id",
            as_="reports",
        )
        assert stage == {
            "$graphLookup": {
                "from": "employees",
                "startWith": "$managerId",
                "connectFromField": "managerId",
                "connectToField": "_id",
                "as": "reports",
            }
        }

    def test_optional_settings(self) -> None:
        stage = graph_lookup_stage(
            "employees",
            start_with="$managerId",
            connect_from_field="managerId",
            connect_to_field="_id",
            as_="reports",
            max_depth=0,
            depth_field="depth",
            restrict_search_with_match={"active": filter(bool).eq(True)},
        )
        assert stage["$graphLookup"]["maxDepth"] == 0
        assert stage["$graphLookup"]["depthField"] == "depth"
        assert stage["$graphLookup"]["restrictSearchWithMatch"] == {"active": {"$eq": True}}

    def test_rejects_negative_max_depth(self) -> None:
        with pytest.raises(ValueError, match="maxDepth requires an integer >= 0"):
            graph_lookup_stage(
                "employees",
                start_with="$managerId",
                connect_from_field="managerId",
                connect_to_field="_id",
                as_="reports",
                max_depth=-1,
            )


class TestBucketStage:
    def test_wraps_spec(self) -> None:
        assert bucket_stage("$price", [0, 100, 500], default="other") == {
            "$bucket": {"groupBy": "$price", "boundaries": [0, 100, 500], "default": "other"}
        }

    def test_default_can_be_none(self) -> None:
        assert bucket_stage("$price", [0, 100], default=None)["$bucket"]["default"] is None

    def test_omits_default_when_not_given(self) -> None:
        assert "default" not in bucket_stage("$price", [0, 100])["$bucket"]

    def test_output(self) -> None:
        stage = bucket_stage("$price", [0, 100], output={"n": {"$sum": 1}})
        assert stage["$bucket"]["output"] == {"n": {"$sum": 1}}

    @pytest.mark.parametrize("boundaries", [[0], [], [100, 0], [0, 0], [0, "a"]])
    def test_rejects_invalid_boundaries(self, boundaries: list[Any]) -> None:
        with pytest.raises(ValueError, match="boundaries"):
            bucket_stage("$price", boundaries)


class TestBucketAutoStage:
    def test_wraps_spec(self) -> None:
        assert bucket_auto_stage("$price", 4) == {
            "$bucketAuto": {"groupBy": "$price", "buckets": 4}
        }

    def test_output_and_granularity(self) -> None:
        stage = bucket_auto_stage("$price", 4, output={"n": {"$sum": 1}}, granularity="R5")
        assert stage["$bucketAuto"]["output"] == {"n": {"$sum": 1}}
        assert stage["$bucketAuto"]["granularity"] == "R5"

    def test_rejects_invalid_bucket_count(self) -> None:
        with pytest.raises(ValueError, match="buckets requires an integer >= 1"):
            bucket_auto_stage("$price", 0)


class TestRedactStage:
    def test_wraps_expression(self) -> None:
        spec = {"$cond": {"if": {"$eq": ["$level", 5]}, "then": "$$DESCEND", "else": "$$PRUNE"}}
        assert redact_stage(spec) == {"$redact": spec}
