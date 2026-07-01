# Dynamic metadata

Scikit-build-core supports dynamic metadata with four built-in plugins.

:::{note}

Beyond the built-in plugins, your package and third parties can provide their
own. These are fully supported through the standard `[[tool.dynamic-metadata]]`
interface described below. The legacy `tool.scikit-build.metadata` table was
provisional: there, plugins not shipped with scikit-build-core require
`tool.scikit-build.experimental=true`, since that interface was not stable (now
replaced by the new one). We are providing backward compatibility for now.

:::

## The `[[tool.dynamic-metadata]]` table

```{versionadded} 1.0
Support for the standard
[dynamic-metadata](https://dynamic-metadata.readthedocs.io) 0.3 specification.
```

The standard, cross-backend way to configure plugins is the top-level
`[[tool.dynamic-metadata]]` **ordered array of tables**. Each entry names a
`provider` (a module, or `"<module>:<Class>"`); every other key is passed to
that plugin as its settings. Entries run **in order**, so a later entry sees
every field an earlier one produced (no dependency graph, no cycles), and a
plugin can read an already-resolved field with `project[...]`.

```toml
[project]
name = "mypackage"
dynamic = ["version"]

[[tool.dynamic-metadata]]
provider = "scikit_build_core.metadata.regex"
field = "version"
input = "src/mypackage/__init__.py"
```

The field-agnostic plugins (`regex`, `template`) can target any field, chosen
with a `field` setting. A `provider-path` key may point at a local directory so
a plugin can live inside your own project. Following [PEP 808][], a list or
table field can be given a static value in `[project]` _and_ listed in
`dynamic`, in which case a provider only **adds** to it; the single-value fields
(`version`, `description`, `requires-python`, `license`, `readme`) cannot be
both static and dynamic.

[PEP 808]: https://peps.python.org/pep-0808/

:::{warning}

The older `[tool.scikit-build.metadata.<field>]` table (a field-keyed mapping
rather than an ordered array) is superseded by `[[tool.dynamic-metadata]]`. It
still works and is shown in the examples below, but the two forms **cannot be
combined** in one project; use one or the other.

:::

:::{versionchanged} 1.0

The legacy `tool.scikit-build.metadata` table now emits a deprecation warning
unless `minimum-version` is set below `1.0`.

:::

## Built-in plugins

We provide some built-in plugins in `scikit_build_core.metadata`. These work in
either mode, though they always require a `field =` key in the modern
`[[tool.dynamic-metadata]]` mode.

Third party plugins (like those inside the `dynamic-metadata` package) and
custom plugins are fully supported in the new mode.

### `version`: Setuptools-scm

You can use [setuptools-scm](https://github.com/pypa/setuptools-scm) to pull the
version from VCS:

````{tab} `[[tool.dynamic-metadata]]`

```toml
[project]
name = "mypackage"
dynamic = ["version"]

[tool.scikit-build]
sdist.include = ["src/package/_version.py"]

[[tool.dynamic-metadata]]
provider = "scikit_build_core.metadata.setuptools_scm"
field = "version"

[tool.setuptools_scm]  # Section required
write_to = "src/package/_version.py"
```

`````

````{tab} `tool.scikit-build.metadata`

```toml
[project]
name = "mypackage"
dynamic = ["version"]

[tool.scikit-build]
metadata.version.provider = "scikit_build_core.metadata.setuptools_scm"
sdist.include = ["src/package/_version.py"]

[tool.setuptools_scm]  # Section required
write_to = "src/package/_version.py"
```

`````

This sets the python project version according to
[git tags](https://github.com/pypa/setuptools-scm/blob/fb261332d9b46aa5a258042d85baa5aa7b9f4fa2/README.rst#default-versioning-scheme)
or a
[`.git_archival.txt`](https://github.com/pypa/setuptools-scm/blob/fb261332d9b46aa5a258042d85baa5aa7b9f4fa2/README.rst#git-archives)
file, or equivalents for other VCS systems.

If you need to set the CMake project version without scikit-build-core (which
provides `${SKBUILD_PROJECT_VERSION}`), you can use something like
[`DynamicVersion` module](https://github.com/LecrisUT/CMakeExtraUtils/blob/180604da50a3c3588f9d04e4ebc6abb4e5a0d234/cmake/DynamicVersion.md)
from
[github.com/LecrisUT/CMakeExtraUtils](https://github.com/LecrisUT/CMakeExtraUtils):

```cmake
# Import `CMakeExtraUtils` or bundle `DynamicVersion.cmake` from there
include(DynamicVersion)

# Set ${PROJECT_VERSION} according to git tag or `.git_archival.txt`
dynamic_version()

project(MyPackage VERSION ${PROJECT_VERSION})
```

### Regex

If you want to pull a string-valued expression (usually version) from an
existing file, you can use the integrated `regex` plugin to pull the
information.

````{tab} `[[tool.dynamic-metadata]]`

```toml
[project]
name = "mypackage"
dynamic = ["version"]

[[tool.dynamic-metadata]]
provider = "scikit_build_core.metadata.regex"
field = "version"
input = "src/mypackage/__init__.py"
```

`````

````{tab} `tool.scikit-build.metadata`

```toml
[project]
name = "mypackage"
dynamic = ["version"]

[tool.scikit-build.metadata.version]
provider = "scikit_build_core.metadata.regex"
input = "src/mypackage/__init__.py"
```

`````

You can set a custom regex with `regex=`. By default when targeting version, you
get a reasonable regex for python files,
`'(?i)^(__version__|VERSION)(?: ?\: ?str)? *= *([\'"])v?(?P<value>.+?)\2'`. You
can set `result` to a format string to process the matches; the default is
`"{value}"`. You can also specify a regex for `remove=` which will strip any
matches from the final result. A more complex example:

````{tab} `[[tool.dynamic-metadata]]`

```toml
[[tool.dynamic-metadata]]
provider = "scikit_build_core.metadata.regex"
field = "version"
input = "src/mypackage/version.hpp"
regex = '''(?sx)
\#define \s+ VERSION_MAJOR \s+ (?P<major>\d+) .*?
\#define \s+ VERSION_MINOR \s+ (?P<minor>\d+) .*?
\#define \s+ VERSION_PATCH \s+ (?P<patch>\d+) .*?
\#define \s+ VERSION_DEV   \s+ (?P<dev>\d+)   .*?
'''
result = "{major}.{minor}.{patch}dev{dev}"
remove = "dev0"
```

`````

````{tab} `tool.scikit-build.metadata`

```toml
[tool.scikit-build.metadata.version]
provider = "scikit_build_core.metadata.regex"
input = "src/mypackage/version.hpp"
regex = '''(?sx)
\#define \s+ VERSION_MAJOR \s+ (?P<major>\d+) .*?
\#define \s+ VERSION_MINOR \s+ (?P<minor>\d+) .*?
\#define \s+ VERSION_PATCH \s+ (?P<patch>\d+) .*?
\#define \s+ VERSION_DEV   \s+ (?P<dev>\d+)   .*?
'''
result = "{major}.{minor}.{patch}dev{dev}"
remove = "dev0"
```

`````

This will remove the "dev" tag when it is equal to 0.

```{versionchanged} 0.10

Support for `result` and `remove` added.

```

### `readme`: Fancy-pypi-readme

You can use
[hatch-fancy-pypi-readme](https://github.com/hynek/hatch-fancy-pypi-readme) to
render your README:

````{tab} `[[tool.dynamic-metadata]]`

```toml
[project]
name = "mypackage"
dynamic = ["readme"]

[[tool.dynamic-metadata]]
provider = "scikit_build_core.metadata.fancy_pypi_readme"
field = "readme"

# tool.hatch.metadata.hooks.fancy-pypi-readme options here
```

`````

````{tab} `tool.scikit-build.metadata`

```toml
[project]
name = "mypackage"
dynamic = ["readme"]

[tool.scikit-build]
metadata.readme.provider = "scikit_build_core.metadata.fancy_pypi_readme"

# tool.hatch.metadata.hooks.fancy-pypi-readme options here
```

`````

In order to use the version number in readme feature, this must be listed after
the version in the `[[tool.dynamic-metadata]]` mode.

```{versionchanged} 0.11.2

The version number feature now works.
```

### Template

You can access other metadata fields and produce templated outputs.

````{tab} `[[tool.dynamic-metadata]]`

```toml
[[tool.dynamic-metadata]]
provider = "scikit_build_core.metadata.template"
field = "optional-dependencies"
result = {"dev" = ["{project[name]}=={project[version]}"]}
```

`````

````{tab} `tool.scikit-build.metadata`

```toml
[tool.scikit-build.metadata.optional-dependencies]
provider = "scikit_build_core.metadata.template"
result = {"dev" = ["{project[name]}=={project[version]}"]}
```

`````

You can use `project` to access the current metadata values. You can use
`result` to specify the output. The result must match the type of the metadata
field you are writing to.

You can reference other dynamic metadata fields. With the legacy
`tool.scikit-build.metadata` table they are resolved on demand, so the order in
the file does not matter; with `[[tool.dynamic-metadata]]` entries run top to
bottom, so any referenced field must be produced by an earlier entry (or be
static in `[project]`).

```{versionadded} 0.11.2

```

## Custom plugins

```{versionadded} 1.0
Writing a custom dynamic-metadata plugin through the standard
[dynamic-metadata](https://dynamic-metadata.readthedocs.io) 0.3 interface.
```

You can write your own plugins. Full details are in the
[dynamic metadata docs](https://dynamic-metadata.readthedocs.io/en/latest/plugin_authors.html).
Here's a quick overview.

There's one required hook:

```python
def dynamic_metadata(
    settings: Mapping[str, Any],
    project: Mapping[str, Any],
) -> dict[str, Any]: ...  # return a fragment of [project], e.g. {"version": ...}
```

And several optional ones (`build_state`, `dynamic_wheel`, and
`get_requires_for_dynamic_metadata`). You can optionally use a class, as well.

To use a local plugin, you need to set both `provider` and `provider-path`:

```toml
[[tool.dynamic-metadata]]
provider = "my_plugin"
provider-path = "helpers/plugins"
```

## `build-system.requires`: Scikit-build-core's `build.requires`

If you need to inject and manipulate additional `build-system.requires`, you can
use the `build.requires`. This is intended to be used in combination with
[](./overrides.md).

This is not technically a dynamic metadata and thus does not have to have the
`dynamic` field defined, and it is not defined under the `metadata` table, but
similar to the other dynamic metadata it injects the additional
`build-system.requires`.

```toml
[project]
name = "mypackage"

[tool.scikit-build]
build.requires = ["foo"]

[[tool.scikit-build.overrides]]
if.from-sdist = false
build.requires = ["foo @ {root:uri}/foo"]
```

This example shows a common use-case where the package has a default
`build-system.requires` pointing to the package `foo` in the PyPI index, but
when built from the original git checkout or equivalent, the local folder is
used as dependency instead by resolving the `{root:uri}` to a file uri pointing
to the folder where the `pyproject.toml` is located.

```{note}
In order to be compliant with the package index, when building from `sdist`, the
`build.requires` **MUST NOT** have any `@` redirects. This rule may be later
enforced explicitly.
```

```{versionadded} 0.11

```

## Generate files with dynamic metadata

You can write out metadata to file(s) as well. Other info might become available
here in the future, but currently it supports anything available as strings in
metadata. (Note that arrays like this are only supported in TOML configuration.)

```toml
[[tool.scikit-build.generate]]
path = "package/_version.py"
template = '''
version = "${version}"
'''
```

`template` or `template-path` is required; this uses {class}`string.Template`
formatting. There are three options for output location; `location = "install"`
(the default) will go to the wheel, `location = "build"` will go to the CMake
build directory, and `location = "source"` will write out to the source
directory (be sure to .gitignore this file. It will automatically be added to
your SDist includes. It will overwrite existing files).

The path is generally relative to the base of the wheel / build dir / source
dir, depending on which location you pick.
