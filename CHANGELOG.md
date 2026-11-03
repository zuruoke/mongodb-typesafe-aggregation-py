# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-11-03

First release of the Python version of
[mongodb-typesafe-aggregation](https://github.com/zuruoke/mongodb-typesafe-aggregation).

### Added

#### Pipeline Builder

- `PipelineBuilder[T]`: fluent, immutable builder for MongoDB aggregation pipelines. Every
  method returns a new builder.
- `.build()`: returns a deep copy of the pipeline as `list[dict]`
- `.raw(stage)`: escape hatch for adding any stage without checks
- `.cast(schema)`: declares the document shape after a stage that changes it

#### Pipeline Stages

| Method                | MongoDB Stage  | Description                           |
| --------------------- | -------------- | ------------------------------------- |
| `.match(query)`       | `$match`       | Filter documents                      |
| `.lookup(from_, ...)` | `$lookup`      | Join from another collection          |
| `.group(spec)`        | `$group`       | Group and accumulate                  |
| `.add_fields(spec)`   | `$addFields`   | Add computed fields                   |
| `.set(spec)`          | `$set`         | Alias for `$addFields` (MongoDB 4.2+) |
| `.project(spec)`      | `$project`     | Include/exclude/reshape fields        |
| `.unset(fields)`      | `$unset`       | Remove fields                         |
| `.sort(spec)`         | `$sort`        | Sort documents                        |
| `.skip(n)`            | `$skip`        | Skip N documents                      |
| `.limit(n)`           | `$limit`       | Limit to N documents                  |
| `.unwind(path)`       | `$unwind`      | Deconstruct an array field            |
| `.replace_root(root)` | `$replaceRoot` | Replace root document                 |
| `.count(field)`       | `$count`       | Count matching documents              |
| `.facet(spec)`        | `$facet`       | Multi-faceted aggregation             |
| `.union_with(coll)`   | `$unionWith`   | Union with another collection         |
| `.graph_lookup(...)`  | `$graphLookup` | Recursive graph traversal             |
| `.bucket(...)`        | `$bucket`      | Categorise into buckets               |
| `.bucket_auto(...)`   | `$bucketAuto`  | Auto-distribute into buckets          |
| `.redact(expression)` | `$redact`      | Conditionally include/exclude content |
| `.merge(into, ...)`   | `$merge`       | Write results to another collection   |

Each stage is also available as a standalone function (`match_stage()`, `lookup_stage()`, ...).

#### FilterOperator

`FilterOperator[T]`: typed builder for MongoDB query and expression operators, with the same
methods as the TypeScript version: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in_`, `nin`, `all`,
`size`, `exists`, `regex`, `field_eq`, `field_ne`, `cond`.

Also exports a `filter(type)` factory from `mongodb_typesafe_aggregation.types.filter` as a
concise alternative to `FilterOperator[T]()`. Stages build `FilterOperator` values
automatically, so `.build()` is optional.

#### Schema checks

- Field names are checked against a `TypedDict`, dataclass, Pydantic (v1/v2, by alias) or
  annotated class, including `"$field"` paths inside expressions.
- The known fields are tracked through every stage, so checks stay correct after `group`,
  `project`, `facet`, `lookup` and other shape-changing stages.
- `UnknownFieldError` (a `ValueError`) names the stage, suggests the closest field, and lists
  the known fields.
- `strict=False`, or no schema, skips the runtime checks.

#### Validation

`ValueError` for invalid sort orders, negative `skip` or non-positive `limit`, `$project`
mixing inclusion and exclusion, `$group` without `_id`, `$unwind` paths without `$`,
`$lookup` without a join condition, unordered `$bucket` boundaries, and stages added after
`$merge`.

[0.1.0]: https://github.com/zuruoke/mongodb-typesafe-aggregation-py/releases/tag/v0.1.0
