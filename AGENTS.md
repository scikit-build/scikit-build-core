# AGENTS.md

## Project

`scikit-build-core` is a PEP 517 build backend for CMake-based Python packages.
It is built with **hatchling** and stored under `src/scikit_build_core/`.

## Running things

- Prefer `uv run` over bare Python invocations. There is a `uv.lock` checked in.
- Use `uv sync` for a local dev install. `uv run` does this for you.
- `nox` is the task runner.
  - `nox -s tests` — run tests with xdist (`-n auto`).
  - `nox -s tests -- -k test_foo` — single test runner.
  - `nox -s docs` — build Sphinx docs (serve with `nox -s docs -- serve`;
    non-interactive with `nox -s docs -- --non-interactive`).
  - `nox -t gen` — run all code generators (cog for README + schema + config
    reference + API docs).
  - `nox -s minimums` — lowest-direct dependency tests.
- For linting, `prek -a --quiet` is preferred.

## Testing

- Tests live in `tests/`. Sample packages are in `tests/packages/` but **must
  not be recursed into** by pytest (`norecursedirs = ["tests/packages/**"]`).
- `tests/utils` is on `pythonpath` for test utilities.
- Many tests need a virtualenv (fixtures: `isolated`, `virtualenv`). These are
  auto-marked as `virtualenv` and `isolated` by `conftest.py`.
- Important pytest markers: `compile`, `configure`, `fortran`, `integration`,
  `isolated`, `network`, `setuptools`, `upstream`, `virtualenv`.
- `pytest -n auto` is the default parallelism. Some platforms retry on PyPy.

## Code quality

- **Ruff** handles linting and formatting. Do not import banned modules directly
  (e.g. use `scikit_build_core._compat.tomllib` instead of `tomli`/`tomllib`,
  `scikit_build_core._compat.typing.Self` instead of `typing.Self`). See
  `pyproject.toml` `tool.ruff.lint.flake8-tidy-imports.banned-api`.
- **mypy** is strict for `scikit_build_core.*`, less strict for tests. Config in
  `pyproject.toml`.
- **pylint** is sometimes run separately in CI (`nox -s pylint`).
- pre-commit includes `check-sdist`, `validate-pyproject`, JSON schema checks,
  typos, shellcheck, and `sp-repo-review`.

## Generated files

- `README.md` and `docs/reference/configs.md` contain cog-generated sections.
- `src/scikit_build_core/resources/scikit-build.schema.json` is generated from
  the Pydantic-style model.
- Run `nox -t gen` after changing any of these sources, then verify
  `git diff --exit-code` in CI.

## Architecture notes

- `src/scikit_build_core/build/` — PEP 517 entry points.
- `src/scikit_build_core/settings/` — configuration system,
  TOML/env/config-settings reading.
- `src/scikit_build_core/cmake.py` / `src/scikit_build_core/builder/` — CMake
  invocation and builders.
- `src/scikit_build_core/file_api/` — CMake File API reader.
- `src/scikit_build_core/_compat/` — backports (typing, tomllib, importlib).
  Ruff enforces their use.
- `src/scikit_build_core/_vendor/` — vendored `pyproject_metadata`. Do not lint.
- Experimental interfaces (setuptools, hatchling) will likely be split into
  separate packages.
