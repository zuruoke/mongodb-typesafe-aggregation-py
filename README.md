# mongodb-typesafe-aggregation (Python)

[![PyPI version](https://img.shields.io/pypi/v/mongodb-typesafe-aggregation.svg)](https://pypi.org/project/mongodb-typesafe-aggregation/)
[![CI](https://github.com/zuruoke/mongodb-typesafe-aggregation-py/actions/workflows/ci.yml/badge.svg)](https://github.com/zuruoke/mongodb-typesafe-aggregation-py/actions/workflows/ci.yml)
[![Python versions](https://img.shields.io/pypi/pyversions/mongodb-typesafe-aggregation.svg)](https://pypi.org/project/mongodb-typesafe-aggregation/)
[![Downloads](https://static.pepy.tech/badge/mongodb-typesafe-aggregation)](https://pepy.tech/project/mongodb-typesafe-aggregation)
[![Monthly downloads](https://img.shields.io/pypi/dm/mongodb-typesafe-aggregation.svg)](https://pypistats.org/packages/mongodb-typesafe-aggregation)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A type-safe, fluent builder for MongoDB aggregation pipelines. It is the Python version of
[mongodb-typesafe-aggregation](https://github.com/zuruoke/mongodb-typesafe-aggregation) for
TypeScript. Field names are checked against your document class, so a typo fails when the
pipeline is built instead of silently matching nothing.

> **Using TypeScript or JavaScript?** The original builder is
> [`mongodb-typesafe-aggregation` on npm](https://www.npmjs.com/package/mongodb-typesafe-aggregation)
> ([source](https://github.com/zuruoke/mongodb-typesafe-aggregation)).

## Installation

```bash
pip install mongodb-typesafe-aggregation
# or
uv add mongodb-typesafe-aggregation
```

Requires Python 3.10+. There are no runtime dependencies: `build()` returns a plain
`list[dict]`, so it works with PyMongo, async PyMongo, Motor, or any driver that accepts a
pipeline.

## Quick Start

```python
from datetime import datetime
from typing import Literal, TypedDict

from pymongo import MongoClient

from mongodb_typesafe_aggregation import PipelineBuilder
from mongodb_typesafe_aggregation.types.filter import filter


class Order(TypedDict):
    _id: str
    status: Literal["pending", "completed"]
    total: float
    customerId: str
    dueDate: datetime


pipeline = (
    PipelineBuilder(Order).match(status=filter(str).eq("pending")).sort(total=-1).limit(20).build()
)

# Pass to your collection
results = MongoClient().shop.orders.aggregate(pipeline).to_list()
```

## Why

Raw aggregation pipelines have no checks:

```python
# Before: easy to mistype, no autocomplete, fails silently at runtime
[
    {"$match": {"satuts": "pending"}},
    {
        "$addFields": {
            "isLate": {
                "$cond": {"if": {"$gt": ["$dueDate", datetime.now()]}, "then": True, "else": False}
            }
        }
    },
]
```

With `mongodb-typesafe-aggregation`:

```python
# After: typos raise as soon as the stage is added
PipelineBuilder(Order).match(satuts="pending")
# UnknownFieldError: Unknown field 'satuts' in $match. Did you mean 'status'?
#                    Known fields: _id, customerId, dueDate, status, total.

PipelineBuilder(Order).match(status="pending").add_fields(
    isLate=filter(bool).cond({"$gt": ["$dueDate", datetime.now()]}, True, False)
).build()
```

## Type safety in Python

TypeScript can check object keys against a type at compile time (`keyof T`). Python's type
system cannot do that for dict keys, so this library combines two kinds of checks.

**Static (mypy / pyright)**

- `PipelineBuilder(Order)` is a `PipelineBuilder[Order]`, and that type flows through the
  chain.
- `FilterOperator[T]` types its values: `filter(int).gt("100")` and
  `FilterOperator[str]().in_([1, 2])` are type errors.
- Stage options are typed, e.g. `sort` orders (`1`/`-1`), `merge(when_matched=...)` and
  `bucket_auto(granularity=...)`.

**Runtime (when each stage is added)**

- Every field name is checked against the schema: `match` keys (including inside `$and`,
  `$or`, `$nor`), `"$field"` paths inside expressions (`$expr`, `group`, `add_fields`,
  `project`, ...), `sort` keys, `unwind` paths, `lookup(local_field=...)`, `unset`, and
  `merge(on=...)`. Dotted paths are checked by their first segment.
- A typo raises `UnknownFieldError` (a `ValueError`) with the closest match and the list of
  known fields.
- `"$$variables"` and the bodies of `$literal`, `$function` and `$accumulator` are never
  treated as fields.

### Supported schemas

| Schema                         | Fields used                           |
| ------------------------------ | ------------------------------------- |
| `TypedDict`                    | All keys, including `NotRequired`     |
| `@dataclass`                   | All dataclass fields                  |
| Pydantic v2 / v1 model         | Field aliases (the names stored in DB) |
| Plain class with annotations   | Annotated attributes, including bases |

`_id` is always known, because MongoDB adds it to every document.

```python
from dataclasses import dataclass
from pydantic import BaseModel, Field


@dataclass
class Customer:
    name: str
    email: str


class Review(BaseModel):
    id: str = Field(alias="_id")
    product_id: str = Field(alias="productId")
    rating: int


PipelineBuilder(Customer).match(email="a@b.c")
PipelineBuilder(Review).match(productId="p1", rating=filter(int).gte(4))
PipelineBuilder(Review).match(product_id="p1")  # UnknownFieldError: did you mean 'productId'?
```

### The shape follows the pipeline

The builder tracks which fields the documents have after each stage, so checks stay correct
after stages that change the shape:

| Stage                                    | Known fields afterwards                                         |
| ---------------------------------------- | --------------------------------------------------------------- |
| `lookup`, `graph_lookup`                 | current fields + `as_`                                          |
| `add_fields`, `set`                      | current fields + the new keys                                   |
| `unwind`                                 | current fields (+ `include_array_index`)                        |
| `unset`                                  | current fields − the removed ones                               |
| `project`                                | the included/computed fields (+ `_id` unless `_id: 0`), or current − excluded |
| `group`                                  | `_id` + the output fields                                       |
| `bucket`, `bucket_auto`                  | `_id` + the `output` fields, or `_id` + `count`                 |
| `facet`                                  | one field per facet                                             |
| `count`                                  | the count field                                                 |
| `replace_root`                           | the keys of a document literal; unknown for any other expression |
| `match`, `sort`, `skip`, `limit`, `redact`, `union_with`, `merge`, `raw` | unchanged                      |

```python
stats = PipelineBuilder(Order).group(_id="$status", orders={"$sum": 1})
stats.sort(orders=-1)  # ok
stats.sort(total=-1)
# UnknownFieldError: Unknown field 'total' in $sort. Known fields: _id, orders.
```

Stages that only add fields keep the static type `PipelineBuilder[T]`. Stages that replace
the shape return `PipelineBuilder[Any]`. Use `cast()` to declare the new shape, which is the
equivalent of `group<G>()` in TypeScript. The following stages are then checked against it:

```python
class StatusCount(TypedDict):
    _id: str
    orders: int


PipelineBuilder(Order).group(_id="$status", orders={"$sum": 1}).cast(StatusCount)
# PipelineBuilder[StatusCount]
```

### Opting out

- `raw(stage)` adds any stage without checks and assumes it does not change the shape.
  Follow it with `cast()` if it does.
- `PipelineBuilder()` with no schema skips all field checks, until a `cast()`.
- `PipelineBuilder(Order, strict=False)` keeps the static typing but skips all runtime field
  checks, including after `cast()`.

## API Reference

### PipelineBuilder[T]

```python
from mongodb_typesafe_aggregation import PipelineBuilder

PipelineBuilder(schema=None, stages=(), *, strict=True)
```

Every method returns a **new** builder and leaves the original unchanged, so a base pipeline
can be reused:

```python
base = PipelineBuilder(Product).match(active=True)
cheap = base.match(price=filter(float).lt(100))  # base still has one stage
```

Methods that take a field map (`match`, `group`, `add_fields`, `set`, `project`, `sort`,
`facet`) accept a mapping, keyword arguments, or both; a key given in both raises `TypeError`.
Use the mapping for dotted paths and `$` operators. Call `.build()` at the end to get the
`list[dict]` pipeline.

#### Stage methods

| Method                                                                                      | MongoDB Stage  | Notes                                                    |
| ------------------------------------------------------------------------------------------- | -------------- | -------------------------------------------------------- |
| `.match(query, **fields)`                                                                   | `$match`       | Accepts `FilterOperator` values                          |
| `.lookup(from_, *, as_, local_field, foreign_field, let, pipeline)`                         | `$lookup`      | `pipeline` can be a list or a `PipelineBuilder`          |
| `.group(spec, **fields)`                                                                    | `$group`       | Requires `_id`; returns `PipelineBuilder[Any]`           |
| `.add_fields(spec, **fields)`                                                               | `$addFields`   |                                                          |
| `.set(spec, **fields)`                                                                      | `$set`         | Alias for `$addFields` (MongoDB 4.2+)                    |
| `.project(spec, **fields)`                                                                  | `$project`     | Rejects mixed inclusion/exclusion; returns `[Any]`       |
| `.unset(fields)`                                                                            | `$unset`       | Accepts `str` or a list of `str`                         |
| `.sort(spec, **fields)`                                                                     | `$sort`        | Orders must be `1`, `-1` or `{"$meta": ...}`             |
| `.skip(n)`                                                                                  | `$skip`        | `n >= 0`                                                 |
| `.limit(n)`                                                                                 | `$limit`       | `n >= 1`                                                 |
| `.unwind(path, *, include_array_index, preserve_null_and_empty_arrays)`                     | `$unwind`      | `path` must start with `$`; also accepts a spec mapping  |
| `.replace_root(new_root)`                                                                   | `$replaceRoot` | Returns `PipelineBuilder[Any]`                           |
| `.count(field="count")`                                                                     | `$count`       | Returns `PipelineBuilder[dict[str, int]]`                |
| `.facet(spec, **pipelines)`                                                                 | `$facet`       | Each pipeline: list, builder, or `lambda b: b...`        |
| `.union_with(coll, pipeline)`                                                               | `$unionWith`   |                                                          |
| `.graph_lookup(from_, *, start_with, connect_from_field, connect_to_field, as_, max_depth, depth_field, restrict_search_with_match)` | `$graphLookup` |                         |
| `.bucket(group_by, boundaries, *, default, output)`                                         | `$bucket`      | Boundaries must be ascending                             |
| `.bucket_auto(group_by, buckets, *, output, granularity)`                                   | `$bucketAuto`  |                                                          |
| `.redact(expression)`                                                                       | `$redact`      |                                                          |
| `.merge(into, *, on, let, when_matched, when_not_matched)`                                  | `$merge`       | Must be last: adding a stage after it raises             |
| `.raw(stage)`                                                                               | any            | Escape hatch for unsupported stages                      |
| `.cast(schema)`                                                                             | none           | Declares the document shape from here on                 |
| `.build()`                                                                                  | none           | Returns a deep copy of the `list[dict]` pipeline         |

Each stage also has a standalone function (`match_stage`, `lookup_stage`, ...,
`redact_stage`) that returns a single stage dict without field checks.

### FilterOperator[T]

Import:

```python
from mongodb_typesafe_aggregation import FilterOperator
from mongodb_typesafe_aggregation.types.filter import filter

# These two are equivalent
FilterOperator[int]().gt(100).build()
filter(int).gt(100).build()
```

`filter` is not exported from the package root, so that `from mongodb_typesafe_aggregation
import *` does not shadow the builtin.

The builder accepts a `FilterOperator` directly, so `.build()` is optional inside stages:

```python
PipelineBuilder(Product).match(price=filter(float).gt(500))
PipelineBuilder(Product).match(price=filter(float).gt(500).build())  # same pipeline
```

#### Comparison

| Method        | Operator |
| ------------- | -------- |
| `.eq(value)`  | `$eq`    |
| `.ne(value)`  | `$ne`    |
| `.gt(value)`  | `$gt`    |
| `.gte(value)` | `$gte`   |
| `.lt(value)`  | `$lt`    |
| `.lte(value)` | `$lte`   |

#### Array

| Method          | Operator | Notes                                |
| --------------- | -------- | ------------------------------------ |
| `.in_(values)`  | `$in`    | `in` is a Python keyword             |
| `.nin(values)`  | `$nin`   |                                      |
| `.all(values)`  | `$all`   |                                      |
| `.size(n)`      | `$size`  |                                      |

`values` can be any iterable.

#### Element & string

| Method            | Operator  |
| ----------------- | --------- |
| `.exists(bool)`   | `$exists` |
| `.regex(pattern)` | `$regex`  |

#### Expression helpers

| Method                                       | Operator | Use case                           |
| -------------------------------------------- | -------- | ---------------------------------- |
| `.field_eq(field, value)`                    | `$eq`    | `[$field, value]` form for `$cond` |
| `.field_ne(field, value)`                    | `$ne`    | `[$field, value]` form for `$cond` |
| `.cond(condition, then_value, else_value)`   | `$cond`  | Ternary expression                 |

Methods can be chained. Like the builder, each call returns a new operator. Multiple
operators produce a combined object:

```python
filter(int).gte(100).lte(999).build()
# → {'$gte': 100, '$lte': 999}
```

## Examples

### `$match` with multiple operators

```python
PipelineBuilder(Product).match(
    price=filter(float).gte(100).lte(999),
    category=filter(str).in_(["electronics", "furniture"]),
    stock=filter(int).exists(True),
).build()
```

### Dotted paths and logical operators

```python
PipelineBuilder(Product).match({"tags.0": "sale", "$or": [{"stock": 0}, {"active": False}]}).build()
```

### `$lookup` + `$addFields` + `$project`

```python
(
    PipelineBuilder(Product)
    .lookup("orders", local_field="_id", foreign_field="productId", as_="orders")
    .add_fields(
        orderedQuantity={"$sum": "$orders.quantity"},
        remainingStock={"$subtract": ["$stock", {"$sum": "$orders.quantity"}]},
    )
    .project(_id=0, name=1, remainingStock=1)
    .build()
)
```

### `$lookup` with a sub-pipeline

```python
PipelineBuilder(Product).lookup(
    "orders",
    let={"productId": "$_id"},
    pipeline=PipelineBuilder().match({"$expr": {"$eq": ["$productId", "$$productId"]}}).limit(5),
    as_="recentOrders",
).build()
```

### `$group`

```python
(
    PipelineBuilder(Order)
    .group(_id="$status", totalOrders={"$sum": 1}, totalQty={"$sum": "$quantity"})
    .sort(_id=1)
    .build()
)
```

### Conditional field with `$cond`

```python
PipelineBuilder(Product).add_fields(
    isExpensive=filter(bool).cond({"$gt": ["$price", 500]}, {"$literal": True}, False)
).build()
```

### `$facet`

```python
PipelineBuilder(Product).facet(
    expensive=lambda products: products.match(price=filter(float).gte(700)),
    lowStock=[{"$match": {"stock": {"$lt": 20}}}],
    total=lambda products: products.count(),
).build()
```

A function receives a fresh builder for the current documents, so its stages are checked
against the current schema.

### `$graphLookup`

```python
PipelineBuilder(Product).graph_lookup(
    "products",
    start_with="$relatedIds",
    connect_from_field="relatedIds",
    connect_to_field="_id",
    as_="relatedProducts",
    max_depth=2,
).build()
```

### `$bucket`

```python
PipelineBuilder(Product).bucket(
    "$price",
    [0, 300, 1000],
    default="other",
    output={"count": {"$sum": 1}, "names": {"$push": "$name"}},
).build()
```

## Differences from the TypeScript version

| TypeScript                                           | Python                                                                 |
| ---------------------------------------------------- | ---------------------------------------------------------------------- |
| `addFields`, `replaceRoot`, `fieldEq`, ...           | `add_fields`, `replace_root`, `field_eq`, ... (snake_case)              |
| `.in(values)`                                        | `.in_(values)`                                                          |
| `filter<number>()`, `new FilterOperator<number>()`   | `filter(int)`, `FilterOperator[int]()`                                  |
| Spec objects: `lookup({ from, localField, as })`     | Keyword arguments: `lookup(from_, local_field=..., as_=...)`            |
| `group<G>(spec)`                                     | `group(spec).cast(G)`                                                   |
| Field names checked by the compiler (`keyof T`)      | Field names checked at runtime against the schema class                |
| Same-type stages mutate the builder                  | Every method returns a new builder                                     |
| `FilterOperator` values need `.build()`              | `.build()` is optional; builders also accepted as sub-pipelines        |
| `facet` takes stage arrays                           | `facet` also takes builders and `lambda b: ...` branches               |
| No structural validation                             | Raises on invalid sort orders, `skip`/`limit` counts, mixed `$project`, `$group` without `_id`, `$unwind` paths without `$`, stages after `$merge`, unordered `$bucket` boundaries |
| Peer dependency on `mongoose`                        | No dependencies; any driver that accepts a list of stages              |

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and guidelines.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

## License

[MIT](LICENSE)
