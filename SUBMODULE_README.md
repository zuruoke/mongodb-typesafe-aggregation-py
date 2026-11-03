# 🔗 Git Submodule Management Guide

## Table of Contents

1. [Overview](#overview)
2. [Initial Setup](#initial-setup)
3. [Package Integration](#package-integration)
4. [Running the Demo](#running-the-demo)
5. [Development Workflow](#development-workflow)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

## 📖 Overview <a name="overview"></a>

This repository includes `mongodb-pipeline-demo-py` as a git submodule. The demo runs the
library's pipelines against a real MongoDB and compares each one with a hand-written pipeline.
The submodule is listed in `.gitignore` to prevent accidental commits of submodule changes to
the main repository.

**Submodule Repository:** https://github.com/zuruoke/mongodb-pipeline-demo-py.git

## 🚀 Initial Setup <a name="initial-setup"></a>

```bash
# Clone the main repository with submodules
git clone --recursive https://github.com/zuruoke/mongodb-typesafe-aggregation-py.git

# OR if already cloned, initialize submodules
git submodule update --init --recursive
```

## 📦 Package Integration <a name="package-integration"></a>

The demo installs the library from the parent directory in editable mode, the uv equivalent of
`npm install file:../` in the TypeScript demo:

```toml
# mongodb-pipeline-demo-py/pyproject.toml
[tool.uv.sources]
mongodb-typesafe-aggregation = { path = "..", editable = true }
```

- **Live updates:** changes under `../src` are picked up on the next run, with no reinstall.
- **Same imports as users:**
  ```python
  from mongodb_typesafe_aggregation import FilterOperator, PipelineBuilder
  from mongodb_typesafe_aggregation.types.filter import filter
  ```

Check which copy of the library the demo uses:

```bash
cd mongodb-pipeline-demo-py
uv run python -c "import mongodb_typesafe_aggregation as m; print(m.__file__)"
# Should print a path under ../src/mongodb_typesafe_aggregation/
```

## ▶️ Running the Demo <a name="running-the-demo"></a>

```bash
cd mongodb-pipeline-demo-py

# MongoDB uses port 27017 by default. If that port is already taken (for example by another
# project's container, or the TypeScript demo), use another one for every command:
export MONGO_PORT=27018

docker compose up -d                     # start MongoDB
uv sync                                  # install dependencies
uv run python -m src.setup_collections   # reset collections and insert sample data
uv run python -m src.main                # run the demo; exits non-zero if an example fails
```

| Command                                  | Description                                      |
| ---------------------------------------- | ------------------------------------------------ |
| `uv run python -m src.setup_collections` | Reset collections and insert sample data         |
| `uv run python -m src.main`              | Run every example and compare with raw pipelines |
| `uv run python -m src.db`                | Drop the entire database (⚠️ destructive)        |
| `docker compose down`                    | Stop MongoDB                                     |

`MONGODB_URI` overrides the connection string (default `mongodb://localhost:$MONGO_PORT`).

## 🔄 Development Workflow <a name="development-workflow"></a>

```bash
# 1. Make changes to the library
# Edit src/mongodb_typesafe_aggregation/builder.py, add stages, etc.

# 2. Run the library checks
uv run pytest && uv run mypy && uv run ruff check

# 3. Test in the submodule (no reinstall needed)
cd mongodb-pipeline-demo-py
git checkout -b your-name/test-new-stage
# Add an example to src/main.py and its raw pipeline to src/raw_aggregations.py
uv run python -m src.setup_collections && uv run python -m src.main

# 4. Commit in the submodule, then in the main repo
git add . && git commit -m "feat: demo new aggregation stage"
cd ..
git add . && git commit -m "feat: add new aggregation stage"
```

Before pushing:

- [ ] `uv run pytest`, `uv run mypy` and `uv run ruff check` pass
- [ ] `uv run python -m src.main` passes in the submodule
- [ ] New features have an example in the demo

## ✅ Best Practices <a name="best-practices"></a>

1. **Never commit submodule changes to the main repo:** the submodule is in `.gitignore` for
   this reason.
2. **Always create your own branch** in the submodule instead of working on upstream
   branches, and include your name in it.
3. **Re-run `setup_collections`** before the demo if you changed the sample data or ran
   `$merge` examples by hand.

### Common commands

| Action                   | Command                                        |
| ------------------------ | ---------------------------------------------- |
| Navigate to submodule    | `cd mongodb-pipeline-demo-py`                  |
| Check available branches | `git branch -r`                                |
| Switch to branch         | `git checkout origin/<branch>`                 |
| Create your branch       | `git checkout -b your-name/branch`             |
| Return to main repo      | `cd ..`                                        |
| Update submodule         | `git submodule update --remote`                |

## 🔧 Troubleshooting <a name="troubleshooting"></a>

### Submodule directory is empty

```bash
git submodule update --init --recursive mongodb-pipeline-demo-py
```

### Submodule appears modified in main repo

This is expected. The submodule is in `.gitignore` to prevent accidental commits.

### `Error connecting to MongoDB`

The container is not running, or it uses a different port than the demo:

```bash
docker compose ps
echo $MONGO_PORT   # must be the same for docker compose and the demo commands
```

### `Bind for 0.0.0.0:27017 failed: port is already allocated`

Another MongoDB already uses port 27017. Set `MONGO_PORT=27018` (or any free port) and run
`docker compose up -d` again.

### Examples fail with `no documents matched`

The database has not been seeded: run `uv run python -m src.setup_collections`.

### Library changes are not picked up

```bash
uv run python -c "import mongodb_typesafe_aggregation as m; print(m.__file__)"
# If the path is not under ../src, reinstall the editable dependency:
uv sync --reinstall-package mongodb-typesafe-aggregation
```

## 📝 Notes

- The submodule points to: https://github.com/zuruoke/mongodb-pipeline-demo-py.git
- **Package integration:** `[tool.uv.sources]` installs the library from `..` in editable mode.
- **Isolation:** changes in the submodule do not affect the main repository.
- **Shared data:** the demo seeds the same `shop_db` data as the TypeScript demo.
