# Dynamic metadata

Scikit-build-core supports dynamic metadata with three built-in plugins.

:::{warning}

Your package and third-party packages can also extend these with new plugins,
but this is currently not ready for development outside of scikit-build-core;
`tool.scikit-build.experimental=true` is required to use plugins that are not
shipped with scikit-build-core, since the interface is provisional and may
change between _minor_ versions.

:::

## `version`: Setuptools-scm

You can use [setuptools-scm](https://github.com/pypa/setuptools-scm) to pull the
version from VCS:

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

## Regex

If you want to pull a string-valued expression (usually version) from an
existing file, you can the integrated `regex` plugin to pull the information.

```toml
name = "mypackage"
dynamic = ["version"]

[tool.scikit-build.metadata.version]
provider = "scikit_build_core.metadata.regex"
input = "src/mypackage/__init__.py"
```

You can set a custom regex with `regex=`. By default when targeting version, you
get a reasonable regex for python files,
`'(?i)^(__version__|VERSION)(?: ?\: ?str)? *= *([\'"])v?(?P<value>.+?)\2'`. You
can set `result` to a format string to process the matches; the default is
`"{value}"`. You can also specify a regex for `remove=` which will strip any
matches from the final result. A more complex example:

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

This will remove the "dev" tag when it is equal to 0.

```{versionchanged} 0.10

Support for `result` and `remove` added.

```

## `readme`: Fancy-pypi-readme

You can use
[hatch-fancy-pypi-readme](https://github.com/hynek/hatch-fancy-pypi-readme) to
render your README:

```toml
[project]
name = "mypackage"
dynamic = ["readme"]

[tool.scikit-build]
metadata.readme.provider = "scikit_build_core.metadata.fancy_pypi_readme"

# tool.hatch.metadata.hooks.fancy-pypi-readme options here
```

```{versionchanged} 0.11.2

The version number feature now works.
```

## Template

You can access other metadata fields and produce templated outputs.

```toml
[tool.scikit-build.metadata.optional-dependencies]
provider = "scikit_build_core.metadata.template"
result = {"dev" = ["{project[name]}=={project[version]}"]}
```

You can use `project` to access the current metadata values. You can reference
other dynamic metadata fields, and they will be computed before this one. You
can use `result` to specify the output. The result must match the type of the
metadata field you are writing to.

```{versionadded} 0.11.2

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
[package]
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
