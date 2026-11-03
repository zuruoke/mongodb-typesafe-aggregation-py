# Contributing

Thank you for taking the time to contribute.

## Local Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
git clone --recursive https://github.com/zuruoke/mongodb-typesafe-aggregation-py.git
cd mongodb-typesafe-aggregation-py
uv sync
```

## Development Workflow

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov

# Check types
uv run mypy

# Lint
uv run ruff check

# Format
uv run ruff format

# Build
uv build
```

### Integration tests

Integration tests run pipelines against a real MongoDB. They are skipped unless `MONGODB_URI`
is set, and they create and drop a throwaway database, so they never touch your data.

```bash
# Start a MongoDB, e.g. the demo container (see SUBMODULE_README.md)
cd mongodb-pipeline-demo-py && MONGO_PORT=27018 docker compose up -d && cd ..

MONGODB_URI=mongodb://localhost:27018 uv run pytest -m integration
```

## Branch Convention

| Branch prefix | When to use                           |
| ------------- | ------------------------------------- |
| `feat/`       | New stage or operator                 |
| `fix/`        | Bug fix                               |
| `docs/`       | Documentation only                    |
| `refactor/`   | Code restructure, no behaviour change |
| `test/`       | New or improved tests                 |
| `chore/`      | Tooling, deps, CI                     |

Branch off `main` and target `main` with your PR.

## Adding a New Pipeline Stage

1. Create `src/mongodb_typesafe_aggregation/stages/my_stage.py` following the existing
   pattern: a `my_stage_stage()` function that validates its input, builds `FilterOperator`
   values with `resolve_filters()`, and returns the stage dict.
2. Export it from `stages/__init__.py` and from the package `__init__.py`.
3. Add the method to `PipelineBuilder` in `builder.py`. Check every field the stage reads
   against the current schema (`check_field`, `check_query` or `check_expression`), and pass
   the new set of known fields to `_add()` if the stage changes the document shape.
4. Write test cases in `tests/test_stages.py` and `tests/test_builder.py`, including the field
   checks and the shape afterwards.
5. Add an example to the demo (`mongodb-pipeline-demo-py`) and check it against MongoDB.
6. Document it in `README.md`, and in `CHANGELOG.md` under an `[Unreleased]` section.

## Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(stages): add $sortByCount stage
fix(filter): handle None in exists operator
docs: update API reference table
```

## Pull Request Checklist

- [ ] Tests pass (`uv run pytest`)
- [ ] Types check (`uv run mypy`)
- [ ] No lint or format errors (`uv run ruff check && uv run ruff format --check`)
- [ ] New behaviour is covered by a test
- [ ] `CHANGELOG.md` updated under `[Unreleased]`

## Releasing (Maintainers)

One-time setup: on PyPI, add a [trusted publisher](https://docs.pypi.org/trusted-publishers/)
for the project `mongodb-typesafe-aggregation` with owner `zuruoke`, repository
`mongodb-typesafe-aggregation-py`, workflow `release.yml` and environment `pypi`. Create the
`pypi` environment in the GitHub repository settings.

For each release:

1. Update `CHANGELOG.md`: move `[Unreleased]` to the new version with today's date.
2. Bump `__version__` in `src/mongodb_typesafe_aggregation/__init__.py`.
3. Commit, then tag the commit with the same version: `git tag vX.Y.Z`
4. Push the commit and the tag: `git push && git push --tags`
5. The `release.yml` GitHub Action checks that the tag matches `__version__`, runs the checks,
   and publishes to PyPI.
