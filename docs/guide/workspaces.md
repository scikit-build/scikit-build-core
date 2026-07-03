# Workspaces and monorepos

Several packaging frontends let you develop multiple related packages together
from a single repository: [uv workspaces][] share one lockfile across members,
and [Hatch workspaces][] (Hatch 1.16+) list `workspace.members` in an
environment definition. In both cases the members are installed **editable**
into the shared environment through the standard PEP 517/660 build hooks.

Scikit-build-core needs no special support for this: a workspace member that
builds with scikit-build-core is simply an editable install, so everything on
the [editable installs](../configuration/editable.md) page applies unchanged.
This page collects the few things worth knowing when several such members live
side by side.

## Rebuilding after C++/CMake edits (uv)

The one real pitfall is uv's build cache. uv only rebuilds a local or workspace
member when its `pyproject.toml`, `setup.py`, or `setup.cfg` changes (see the
[cache versioning docs][uv cache]). Edits to your C++ or CMake sources do
**not** invalidate the cache, so `uv sync`/`uv run` can happily reuse a stale
extension module. There are two good remedies.

### Option 1: tell uv about your sources with `cache-keys`

Add the source files that should trigger a rebuild to the member's own
`[tool.uv]` table:

```toml
[tool.uv]
cache-keys = [
  { file = "pyproject.toml" },
  { file = "CMakeLists.txt" },
  { file = "src/**/*.cpp" },
  { file = "src/**/*.hpp" },
]
```

Setting `cache-keys` **replaces** the defaults, so keep `pyproject.toml` in the
list. uv now reruns the build whenever any matched file changes.

### Option 2: let scikit-build-core rebuild on import

Enable [`editable.rebuild`](../configuration/editable.md) with a persistent
`build-dir`. The member is then rebuilt on import, which makes the frontend's
caching moot -- you never rely on uv noticing a source change. The rebuild shim
shells out to `cmake` directly and does **not** import scikit-build-core, so it
works even though uv builds members with isolation; it only needs `cmake` on
`PATH` at import time.

You can set this per member in `pyproject.toml`:

```toml
[tool.scikit-build]
build-dir = "build/{wheel_tag}"
editable.rebuild = true
```

See [editable installs](../configuration/editable.md) for the full set of
options (verbosity, manual `__loader__.rebuild()`, inplace mode, and the newer
`editable.rebuild-dir`).

## Per-member configuration

A plain `--config-settings` (or `[tool.uv] config-settings`) applies to
**every** package uv builds, including all workspace members -- rarely what you
want when members have different needs. uv provides
[`--config-settings-package`][uv settings] (and
`tool.uv.config-settings-package`) to target a single member:

```toml
[tool.uv.config-settings-package.my-extension]
"cmake.define.MYLIB_ENABLE_FOO" = "ON"
```

The most robust approach, though, is to keep per-member build configuration in
each member's own `[tool.scikit-build]` table, so it travels with the package
regardless of how it is built.

## Sharing native sources across members

An SDist only contains files under the member's own directory, so a member that
compiles sources living elsewhere in the monorepo (a shared `../../shared`
directory, say) needs those sources pulled in. Scikit-build-core supports two
patterns; both keep the same relative layout working from a git checkout and
from an unpacked SDist.

### Pattern 1: a symlink resolved into the SDist

Put a symlink inside the member pointing at the shared sources, and let the
SDist dereference it:

```console
$ ln -s ../../shared src/shared
```

```toml
[tool.scikit-build]
sdist.resolve-symlinks = "all"  # the default when minimum-version >= 1.0
```

With {confval}`sdist.resolve-symlinks` set to `"all"`, the SDist stores the
symlink target's contents in place of the link. `src/shared` then resolves to
the real files in a checkout and to the copied contents in an SDist, so
`CMakeLists.txt` can reference the same relative path in both cases.

### Pattern 2: `force-include` plus a `from-sdist` override

Alternatively, force-include the outside directory into the SDist.
{confval}`sdist.force-include` source keys may point outside the project root or
be absolute:

```toml
[tool.scikit-build.sdist.force-include]
"../shared" = "shared"
```

Now the sources live at `../shared` relative to the member in a checkout, but at
`shared` inside the SDist. Use an [override](../configuration/overrides.md)
keyed on the `from-sdist` condition to point CMake at the right place in each
layout:

```toml
[[tool.scikit-build.overrides]]
if.from-sdist = false
cmake.define.SHARED_SOURCE_DIR = "../shared"

[[tool.scikit-build.overrides]]
if.from-sdist = true
cmake.define.SHARED_SOURCE_DIR = "shared"
```

:::{versionadded} 1.0

`sdist.force-include` and `sdist.resolve-symlinks`.

:::

<!-- prettier-ignore-start -->

[uv workspaces]: https://docs.astral.sh/uv/concepts/projects/workspaces/
[uv cache]: https://docs.astral.sh/uv/concepts/cache/
[uv settings]: https://docs.astral.sh/uv/reference/settings/
[hatch workspaces]: https://hatch.pypa.io/1.16/how-to/environment/workspace/

<!-- prettier-ignore-end -->
