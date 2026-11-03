from __future__ import annotations

from typing import Any

from typing_extensions import assert_type

from mongodb_typesafe_aggregation.types.filter import FilterOperator, filter, resolve_filters


class TestComparisonOperators:
    def test_eq_builds_eq_operator(self) -> None:
        assert FilterOperator[int]().eq(42).build() == {"$eq": 42}

    def test_ne_builds_ne_operator(self) -> None:
        assert FilterOperator[str]().ne("inactive").build() == {"$ne": "inactive"}

    def test_gt_builds_gt_operator(self) -> None:
        assert FilterOperator[int]().gt(100).build() == {"$gt": 100}

    def test_gte_builds_gte_operator(self) -> None:
        assert FilterOperator[int]().gte(100).build() == {"$gte": 100}

    def test_lt_builds_lt_operator(self) -> None:
        assert FilterOperator[int]().lt(500).build() == {"$lt": 500}

    def test_lte_builds_lte_operator(self) -> None:
        assert FilterOperator[int]().lte(500).build() == {"$lte": 500}


class TestArrayOperators:
    def test_in_builds_in_operator(self) -> None:
        assert FilterOperator[str]().in_(["a", "b"]).build() == {"$in": ["a", "b"]}

    def test_nin_builds_nin_operator(self) -> None:
        assert FilterOperator[str]().nin(["x", "y"]).build() == {"$nin": ["x", "y"]}

    def test_all_builds_all_operator(self) -> None:
        assert FilterOperator[str]().all(["tag1", "tag2"]).build() == {"$all": ["tag1", "tag2"]}

    def test_size_builds_size_operator(self) -> None:
        assert FilterOperator[str]().size(3).build() == {"$size": 3}

    def test_array_operators_accept_any_iterable(self) -> None:
        assert FilterOperator[str]().in_(("a", "b")).build() == {"$in": ["a", "b"]}
        assert FilterOperator[int]().nin(range(3)).build() == {"$nin": [0, 1, 2]}
        assert FilterOperator[str]().all(iter(["x"])).build() == {"$all": ["x"]}


class TestFieldExpressionOperators:
    def test_field_eq_builds_eq_array_expression(self) -> None:
        assert FilterOperator[str]().field_eq("$role", "admin").build() == {
            "$eq": ["$role", "admin"]
        }

    def test_field_ne_builds_ne_array_expression(self) -> None:
        assert FilterOperator[str]().field_ne("$status", "archived").build() == {
            "$ne": ["$status", "archived"]
        }


class TestStringOperators:
    def test_regex_builds_regex_operator(self) -> None:
        assert FilterOperator[str]().regex("^laptop").build() == {"$regex": "^laptop"}


class TestElementOperators:
    def test_exists_true(self) -> None:
        assert FilterOperator[Any]().exists(True).build() == {"$exists": True}

    def test_exists_false(self) -> None:
        assert FilterOperator[Any]().exists(False).build() == {"$exists": False}


class TestConditionalOperator:
    def test_cond_builds_cond_expression(self) -> None:
        condition = FilterOperator[str]().field_eq("$role", "admin").build()
        result = FilterOperator[bool]().cond(condition, {"$literal": True}, False).build()

        assert result == {
            "$cond": {
                "if": {"$eq": ["$role", "admin"]},
                "then": {"$literal": True},
                "else": False,
            }
        }

    def test_cond_accepts_unbuilt_condition(self) -> None:
        condition = FilterOperator[str]().field_eq("$role", "admin")
        result = FilterOperator[bool]().cond(condition, True, False).build()

        assert result == {"$cond": {"if": {"$eq": ["$role", "admin"]}, "then": True, "else": False}}


class TestFilterFactory:
    def test_returns_a_new_filter_operator(self) -> None:
        assert isinstance(filter(int), FilterOperator)

    def test_works_the_same_as_filter_operator(self) -> None:
        assert filter(int).gt(50).build() == FilterOperator[int]().gt(50).build()

    def test_without_type(self) -> None:
        assert filter().eq("anything").build() == {"$eq": "anything"}


class TestMethodChaining:
    def test_multiple_operators_are_combined(self) -> None:
        assert FilterOperator[int]().gte(100).lte(999).build() == {"$gte": 100, "$lte": 999}

    def test_methods_return_new_operators(self) -> None:
        base = filter(int).gte(100)
        capped = base.lte(999)

        assert base.build() == {"$gte": 100}
        assert capped.build() == {"$gte": 100, "$lte": 999}

    def test_build_returns_a_copy(self) -> None:
        operator = filter(str).in_(["a"])
        operator.build()["$in"].append("b")

        assert operator.build() == {"$in": ["a"]}

    def test_repr(self) -> None:
        assert repr(filter(int).gt(5)) == "FilterOperator({'$gt': 5})"


class TestResolveFilters:
    def test_builds_nested_operators(self) -> None:
        value = {"price": filter(int).gt(1), "$or": [{"stock": filter(int).lt(5)}], "n": (1, 2)}
        assert resolve_filters(value) == {
            "price": {"$gt": 1},
            "$or": [{"stock": {"$lt": 5}}],
            "n": [1, 2],
        }

    def test_leaves_other_values_unchanged(self) -> None:
        marker = object()
        assert resolve_filters(marker) is marker


class TestStaticTypes:
    def test_value_type_flows_through_chain(self) -> None:
        assert_type(filter(int).gt(1).lte(5), FilterOperator[int])
        assert_type(FilterOperator[str]().eq("a"), FilterOperator[str])
        assert_type(filter(), FilterOperator[Any])

    def test_wrong_value_type_is_a_type_error(self) -> None:
        # mypy runs with warn_unused_ignores, so each ignore below fails the type-check if
        # the call stops being an error.
        filter(int).gt("100")  # type: ignore[arg-type]
        FilterOperator[str]().in_([1, 2])  # type: ignore[list-item]
        filter(bool).cond({"$eq": ["$a", 1]}, True, "no")  # type: ignore[arg-type]
