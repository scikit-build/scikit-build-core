# Wrapping the build backend

PEP 517 lets a project ship its own build backend inside the source tree using
`backend-path`. Such an "in-tree" backend can wrap scikit-build-core: it
re-exports the standard hooks and replaces the ones it wants to change. This is
the escape hatch for build-time logic that needs arbitrary Python.

## Check the built-in options first

Most historic reasons to wrap a backend are built into scikit-build-core:

- Requiring `cmake`/`ninja` from PyPI only when the system copy is missing or
  too old (the classic scikit-build docs used a wrapper for this) is automatic;
  see [](./index.md#cmake-and-ninja-minimum-versions).
- Conditional build requirements based on platform, Python version, environment
  variables, or the build state can use `build.requires` with
  [](./overrides.md); see [](#build-requires).
- Computed project metadata can use [dynamic metadata](./dynamic.md) plugins.
- Conditional build requirements with custom Python code can use
  dynamic-metadata's hook.

Wrap the backend only when your logic doesn't fit those; for example, setting a
dynamic name (which is not allowed by standards, so scikit-build-core doesn't
support it).

## Setting up an in-tree backend

Point `build-backend` at a module found via `backend-path`:

```toml
[build-system]
requires = ["scikit-build-core"]
build-backend = "backend"
backend-path = ["_custom_build"]
```

Then create `_custom_build/backend.py`. Start it with a star import; that
re-exports every hook scikit-build-core provides. This matters because
scikit-build-core does not always define the `prepare_metadata_for_build_*`
hooks (it drops them when `if.failed` overrides are present, since metadata then
depends on the build); the star import follows `__all__`, so your wrapper
exposes exactly the same hooks.

This example adds `swig` to the build requirements only if SWIG is not already
on the system, matching what scikit-build-core does for CMake and Ninja:

```python
import shutil

from scikit_build_core.build import *
from scikit_build_core.build import (
    get_requires_for_build_wheel as _orig_get_requires_for_build_wheel,
)


def get_requires_for_build_wheel(config_settings=None):
    extra = [] if shutil.which("swig") else ["swig"]
    return _orig_get_requires_for_build_wheel(config_settings) + extra
```

The `def` shadows the star-imported name, so the frontend calls your version.
Any hook can be wrapped the same way; for example, `build_wheel` to generate
files before the build starts.

You can do the same thing with dynamic-metadata, keeping the standard backend:

```toml
[[tool.dynamic-metadata]]
provider = {path = "_custom_build", module = "swig_requires"}
```

```python
# _custom_build/swig_requires.py
import shutil


def dynamic_metadata(settings, project):
    return {}


def get_requires_for_dynamic_metadata(settings):
    return [] if shutil.which("swig") else ["swig"]
```

The required `dynamic_metadata` hook returns an empty fragment, so the metadata
is untouched; `get_requires_for_dynamic_metadata` supplies the extra
requirements. See [](./dynamic.md#custom-plugins) for the full plugin interface.

## Caveats

- Commit the backend module; the SDist must contain it or builds from the SDist
  will fail. Scikit-build-core includes git-tracked files by default. It is not
  installed into the wheel.
- Every directory in `backend-path` is prepended to `sys.path` during the build,
  so keep those directories minimal to avoid shadowing installed packages.
- Frontends may run each hook in a separate process; don't rely on module state
  surviving between hooks.
- All `[tool.scikit-build]` configuration still applies as usual.
