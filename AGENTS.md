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
  - `nox -s docs` — serve the HTML docs in interactive mode.
  - `nox --non-interactive -s docs` — build the HTML docs without serving them.
  - `nox -t gen` — run all code generators (cog for README + schema + config
    reference + API docs).
  - `nox -s minimums` — lowest-direct dependency tests.
  - `nox -s pylint` - some slightly-slower lints not included in `prek`
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
- **prek**, a pre-commit rewrite in Rust, includes `check-sdist`,
  `validate-pyproject`, JSON schema checks, typos, shellcheck, and
  `sp-repo-review`.

## Generated files

- `README.md` and `docs/reference/configs.md` contain cog-generated sections.
- `src/scikit_build_core/resources/scikit-build.schema.json` is generated from
  the Pydantic-style model.
- Run `nox -t gen` after changing any of these sources, then verify
  `git diff --exit-code` in CI.

## Architecture notes

`scikit-build-core` is the reference PEP 517 build backend for CMake-based
Python packages. Its job is to bridge the gap between Python's packaging
standards (`pyproject.toml`, SDists, wheels, editable installs) and CMake's
build system. The package is organized into a handful of coherent layers:

### High-level build flow

The entry points live in `src/scikit_build_core/build/__init__.py`. They
implement the standard PEP 517 hooks (`build_wheel`, `build_sdist`,
`build_editable`, `get_requires_for_build_*`, `prepare_metadata_for_build_*`).
The implementations are thin wrappers that:

1. Read `pyproject.toml` and construct a `SettingsReader`.
2. Run setup code (logging, validation).
3. Dispatch to the real workhorse, `_build_wheel_impl` in `build/wheel.py` or
   `build_sdist` in `build/sdist.py`.

For wheels/editable installs, the core flow is:

1. **Parse settings** (`settings/`): merge TOML, env vars, and PEP 517
   `config-settings` into a `ScikitBuildSettings` dataclass.
2. **Resolve metadata** (`build/metadata.py`): use the vendored
   `pyproject_metadata` library to turn `project` table data into
   `StandardMetadata`, including dynamic metadata plugins.
3. **Find CMake** (`cmake.py`, `program_search.py`): search the system (and
   optionally PyPI) for a CMake binary matching the requested version spec.
4. **Configure CMake** (`builder/builder.py`, `cmake.py`): set up the build
   directory, write an init-cache (`CMakeInit.txt`) with SKBUILD\_\* variables,
   and run `cmake -S … -B …`.
5. **Build** (`builder/builder.py`): run `cmake --build` with the correct
   generator (Ninja/Makefiles/MSVC).
6. **Install into wheel** (`builder/builder.py`): run `cmake --install` into a
   staging directory mapped to the wheel layout (`platlib`, `data`, `headers`,
   `scripts`, `metadata`).
7. **Package Python files** (`build/wheel.py`, `build/_pathutil.py`): copy
   discovered Python packages into the wheel, apply inclusion/exclusion rules.
8. **Write the wheel** (`build/_wheelfile.py`): assemble the final `.whl` and
   compute tags.

SDists skip the CMake/build/install steps by default (`sdist.cmake = false`) and
simply create a reproducible tar.gz from the source tree with gitignore
augmentation.

### Settings / configuration system (`settings/`)

This is one of the most carefully-engineered parts of the project. Settings are
modeled as nested dataclasses (`settings/skbuild_model.py`) and then assembled
by a prioritized chain of _sources_ (`settings/sources.py`):

- `EnvSource` — reads `SKBUILD_*` environment variables.
- `ConfSource` — reads PEP 517 `config-settings` (flat dotted keys).
- `TOMLSource` — reads `tool.scikit-build` from `pyproject.toml`.

`SourceChain` merges them with precedence: env vars override config-settings,
which override TOML. Dicts are merged across sources rather than replaced.

`SettingsReader` (`settings/skbuild_read_settings.py`) orchestrates parsing,
handles:

- **Overrides** (`settings/skbuild_overrides.py`): conditional config based on
  state (`wheel`/`sdist`/`editable`), environment, or CMake failure (`failed`).
- **Version-based compatibility**: `minimum-version` gates which features are
  allowed and rewrites deprecated settings.
- **Auto-detection**: `cmake.version = "CMakeLists.txt"` parses the top-level
  `cmake_minimum_required` automatically.
- **Validation**: unrecognized options, strict-config checks, and override-only
  fields.

### CMake integration (`cmake.py`, `builder/`)

`CMake` (`cmake.py`) is a small value object holding the binary path and
version. `CMaker` is the heavy lifter that manages:

- Build directory lifecycle (stale-cache detection via `.skbuild-info.json`).
- Init-cache generation (`CMakeInit.txt`) with all `SKBUILD_*` cache entries.
- Actually running `cmake configure`, `cmake --build`, and `cmake --install`.

`Builder` (`builder/builder.py`) is the higher-level wrapper used by the wheel
build. It sets up:

- Python discovery hints (`PYTHON_EXECUTABLE`, `Python3_EXECUTABLE`, etc.).
- Limited API / Stable ABI logic (`SKBUILD_SOABI`, `SKBUILD_SABI_*`).
- macOS cross-compile support (`ARCHFLAGS` → `CMAKE_OSX_ARCHITECTURES`).
- Entry-point based CMake module/prefix/root injection.
- Generator selection and environment setup (`builder/generator.py`).

`program_search.py` handles discovering CMake, Ninja, and Make binaries on the
system (with optional PyPI fallback wheels).

### CMake File API (`file_api/`)

scikit-build-core writes a _stateless query_ into the build directory before
configuring CMake (`file_api/query.py`). After configuration, it reads the reply
directory and parses the JSON responses into typed dataclasses
(`file_api/model/`): `Index`, `CodeModel`, `Cache`, `CMakeFiles`, `Directory`,
`Toolchains`. This gives programmatic access to the CMake graph without scraping
stdout.

### Metadata (`build/metadata.py`, `_vendor/`)

The project vendors a copy of `pyproject_metadata` (`_vendor/`) to parse the
`[project]` table. `get_standard_metadata()`:

- Runs dynamic metadata plugins (`builder/_load_provider.py`) if configured.
- Validates PEP 621/639 fields.
- Adjusts behavior based on `minimum-version` (e.g. name normalization, metadata
  version 2.2).

### Editable installs (`build/_editable.py`)

Two modes are supported:

- **redirect** (default): A `.pth` file loads an `_<pkg>_editable.py` redirect
  shim (from `resources/_editable_redirect.py`) that uses `sys.meta_path` to map
  imports. Optionally triggers CMake rebuild on import if
  `editable.rebuild = true`.
- **inplace**: A simple `.pth` file pointing at the source package directories.

### Experimental interfaces

- **`hatch/`** — a `BuildHookInterface` plugin (`hatch/plugin.py`) letting
  hatchling drive the CMake build. Currently experimental; it reuses the same
  `Builder`/`CMaker` infrastructure but feeds artifacts back into hatchling
  rather than assembling the wheel directly.
- **`setuptools/`** — a compatibility layer (`setuptools/build_meta.py`) that
  wraps setuptools' build meta and injects CMake/ninja requirements.

### Utilities

- `_compat/` — backports for `tomllib`, `typing.Self`, `importlib.metadata`,
  etc. Ruff enforces their use over direct imports.
- `_logging.py` — rich-based colored output and structured logger.
- `format.py` — template formatting for `generate` settings and string
  substitutions.
- `resources/` — bundled data including the editable redirect shim and
  known-wheels lookup table.

### Key file map

- `src/scikit_build_core/build/` — PEP 517 entry points (`wheel.py`, `sdist.py`,
  `metadata.py`, `_editable.py`).
- `src/scikit_build_core/settings/` — configuration system (`sources.py`,
  `skbuild_model.py`, `skbuild_read_settings.py`, `skbuild_overrides.py`).
- `src/scikit_build_core/cmake.py` — `CMake` / `CMaker` classes.
- `src/scikit_build_core/builder/` — high-level build orchestration
  (`builder.py`, `generator.py`, `get_requires.py`, `wheel_tag.py`,
  `sysconfig.py`).
- `src/scikit_build_core/file_api/` — CMake File API reader (`query.py`,
  `reply.py`, `model/*.py`).
- `src/scikit_build_core/_compat/` — backports (typing, tomllib, importlib).
- `src/scikit_build_core/_vendor/` — vendored `pyproject_metadata`. Do not lint.
- `src/scikit_build_core/resources/` — bundled templates and lookup tables.
- `src/scikit_build_core/hatch/` — experimental hatchling plugin.
- `src/scikit_build_core/setuptools/` — setuptools compatibility shim.

Experimental interfaces (setuptools, hatchling) will likely be split into
separate packages.
