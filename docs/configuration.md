# Configuration

Scikit-build-core supports a powerful unified configuration system. Every option
in scikit-build-core can be specified in one of three ways: as a
`pyproject.toml` option (preferred if static), as a config-settings options
(preferred if dynamic), or as an environment variable.

## Verbosity

You can increase the verbosity of the build with two settings - `cmake.verbose`
is a shortcut for verbose build output, and logging.level controls
scikit-build-core's internal logging. An example (with all configuration styles)
of setting both is:

````{tab} pyproject.toml

```toml
[tool.scikit-build]
cmake.verbose = true
logging.level = "INFO"
```

````

`````{tab} config-settings


````{tab} pip

```console
$ pip install . -v --config-settings=cmake.verbose=true --config-settings=logging.level=INFO
```

````

````{tab} build

```console
$ pipx run build --wheel -Ccmake.verbose=true -Clogging.level=INFO
```

````

````{tab} cibuildwheel

```toml
[tool.cibuildwheel.config-settings]
"cmake.verbose" = true
"logging.level" = "INFO"
```

````

`````

````{tab} Environment


```yaml
SKBUILD_CMAKE_VERBOSE: true
SKBUILD_LOGGING_LEVEL: "INFO"
```


````

:::{note}

When using `pip`, make sure you include at least a `-v` argument so that the
verbosity settings above are displayed.

:::

:::{warning}

In general, the environment variable method is intended as an emergency
workaround for legacy tooling.

:::

## Minimum version & defaults

Scikit-build-core, like CMake, has a special minimum required version setting.
If you set this, you get two benefits. First, if the version is less than this
version, you get a nice error message. But, more importantly, if
scikit-build-core is a newer version than the version set here, it will select
older defaults to help ensure your package can continue to build, even if a
default value changes in the future. This should help reduce the chance of ever
needed an upper cap on the scikit-build-core version, as upper caps are
discouraged.

It is recommended you set this value as high as you feel comfortable with, and
probably keep in sync with your build-system requirements.

```toml
[tool.scikit-build]
minimum-version = "0.2"
```

:::{warning}

The following behaviors are affected by `minimum-version`:

- `minimum-version` 0.5+ (or unset) provides the original name in metadata and
  properly normalized SDist names.
- `minimum-version` 0.5+ (or unset) strips binaries by default.

:::

## CMake and Ninja minimum versions

You can select a different minimum version for CMake and Ninja.
Scikit-build-core will automatically decide to download a wheel for these (if
possible) when the system version is less than this value.

For example, to require a recent CMake and Ninja:

```toml
[tool.scikit-build]
cmake.minimum-version = "3.26.1"
ninja.minimum-version = "1.11"
```

You can also enforce ninja to be required even if make is present on Unix:

```toml
[tool.scikit-build]
ninja.make-fallback = false
```

You can also control the FindPython backport; by default, a backport of CMake
3.26.1's FindPython will be used if the CMake version is less than 3.26.1; you
can turn this down if you'd like ("3.15", scikit-build-core's minimum version,
would turn it off).

```toml
[tool.scikit-build]
backport.find-python = "3.15"
```

## Configuring source file inclusion

Scikit-build-core defaults to using your `.gitignore` to select what to exclude
from the source distribution. You can list files to explicitly include and
exclude if you want:

```toml
[tool.scikit-build]
sdist.include = ["src/some_generated_file.txt"]
sdist.exclude = [".github"]
```

By default, scikit-build-core will respect `SOURCE_DATE_EPOCH`, and will lock
the modification time to a reproducible value if it's not set. You can disable
reproducible builds if you prefer, however:

```toml
[tool.scikit-build]
sdist.reproducible = false
```

You can also request CMake to run during this step:

```toml
[tool.scikit-build]
sdist.cmake = true
```

:::{note}

If you do this, you'll want to have some artifact from the configure in your
source directory; for example:

```cmake
include(FetchContent)

if(NOT SKBUILD_STATE STREQUAL "sdist"
   AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/pybind11/CMakeLists.txt")
  message(STATUS "Using integrated pybind11")
  set(FETCHCONTENT_FULLY_DISCONNECTED ON)
endif()

FetchContent_Declare(
  pybind11
  GIT_REPOSITORY https://github.com/pybind/pybind11.git
  GIT_TAG v2.11.1
  SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/pybind11)

set(PYBIND11_FINDPYTHON ON)
FetchContent_MakeAvailable(pybind11)
```

The `/pybind11` directory is in the `.gitignore` and important parts are in
`sdist.include`:

```toml
[tool.scikit-build]
sdist.cmake = true
sdist.include = [
  "pybind11/tools",
  "pybind11/include",
  "pybind11/CMakeLists.txt",
]
```

:::

## Customizing the built wheel

The wheel will automatically look for Python packages at `src/<package_name>`,
`python/<package_name>`, and `<package_name>`, in that order. If you want to
list packages explicitly, you can. The final path element is the package.

```toml
[tool.scikit-build]
wheel.packages = ["python/src/mypackage"]
```

Or you can disable Python file inclusion entirely, and rely only on CMake's
install mechanism, you can do that instead:

```toml
[tool.scikit-build]
wheel.packages = []
```

The install directory is normally site-packages; however, you can manually set
that to a different directory if you'd like to avoid changing your CMake files.
For example, to mimic scikit-build classic:

```toml
[tool.scikit-build]
wheel.install-dir = "mypackage"
```

:::{warning}

You can select a different wheel target directory, as well, but that syntax is
experimental; install to `${SKBUILD_DATA_DIR}`, etc. from within CMake instead
for now.

:::

By default, any `LICEN[CS]E*`, `COPYING*`, `NOTICE*`, or `AUTHORS*` file in the
root of the build directory will be picked up. You can specify an exact list of
files if you prefer, or if your license file is in a different directory.
Globbing patterns are supported.

```toml
[tool.scikit-build]
wheel.license-files = ["LICENSE"]
```

## Customizing the output wheel

The python API tags for your wheel will be correct assuming you are building a
CPython extension. If you are building a Limited ABI extension, you should set
the wheel tags for the version you support:

```toml
[tool.scikit-build]
wheel.py-api = "cp37"
```

Scikit-build-core will only target ABI3 if the version of Python is equal to or
newer than the one you set. `${SKBUILD_SABI_COMPONENT}` is set to
`Development.SABIModule` when targeting ABI3, and is an empty string otherwise.

If you are not using CPython at all, you can specify any version of Python is
fine:

```toml
[tool.scikit-build]
wheel.py-api = "py3"
```

Or even Python 2 + 3 (you still will need a version of Python scikit-build-core
supports to build the initial wheel):

```toml
[tool.scikit-build]
wheel.py-api = "py2.py3"
```

Some older versions of pip are unable to load standard universal tags;
scikit-build-core can expand the macOS universal tags for you for maximum
historic compatibility if you'd like:

```toml
[tool.scikit-build]
wheel.expand-macos-universal-tags = true
```

You can select only specific components to install:

```{conftabs} install.components ["python"]

```

And you can turn off binary stripping:

```{conftabs} install.strip False

```

## Configuring CMake arguments and defines

You can select a different build type, such as `Debug`:

```{conftabs} cmake.build-type "Debug"

```

You can specify CMake defines:

````{tab} pyproject.toml

```toml
[tool.scikit-build.cmake.define]
SOME_DEFINE = "ON"
```

````

`````{tab} config-settings


````{tab} pip

```console
$ pip install . --config-settings=cmake.define.SOME_DEFINE=ON
```

````

````{tab} build

```console
$ pipx run build --wheel -Ccmake.define.SOME_DEFINE=ON
```

````

````{tab} cibuildwheel

```toml
[tool.cibuildwheel.config-settings]
"cmake.define.SOME_DEFINE" = "ON"
```

````

`````

````{tab} Environment

```yaml
SKBUILD_CMAKE_DEFINE: SOME_DEFINE=ON
```

````

You can also manually specify the exact CMake args. Beyond the normal
`SKBUILD_CMAKE_ARGS`, the `CMAKE_ARGS` space-separated environment variable is
also supported (with some filtering for options scikit-build-core doesn't
support overriding).

```{conftabs} cmake.args ["-DSOME_DEFINE=ON", "-DOTHER=OFF"]

```

You can also specify this using `CMAKE_ARGS`, space separated:

```yaml
CMAKE_ARGS: -DSOME_DEFINE=ON -DOTHER=OFF
```

You can also specify only specific targets to build (leaving this off builds the
default targets):

```{conftabs} cmake.targets ["python"]

```

## Dynamic metadata

Scikit-build-core 0.3.0+ supports dynamic metadata with two built-in plugins.

:::{warning}

This is not ready for plugin development outside of scikit-build-core;
`tool.scikit-build.experimental=true` is required to use plugins that are not
shipped with scikit-build-core, since the interface is provisional and may
change between _minor_ versions.

:::

:::{tab} Setuptools-scm

You can use [setuptools-scm](https://github.com/pypa/setuptools_scm) to pull the
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
[git tags](https://github.com/pypa/setuptools_scm/blob/fb261332d9b46aa5a258042d85baa5aa7b9f4fa2/README.rst#default-versioning-scheme)
or a
[`.git_archival.txt`](https://github.com/pypa/setuptools_scm/blob/fb261332d9b46aa5a258042d85baa5aa7b9f4fa2/README.rst#git-archives)
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

:::

:::{tab} Fancy-pypi-readme

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

:::

:::{tab} Regex

If you want to pull a string-valued expression (usually version) from an
existing file, you can the integrated `regex` plugin to pull the information.

```toml
name = "mypackage"
dynamic = ["version"]

[tool.scikit-build.metadata.version]
provider = "scikit_build_core.metadata.regex"
input = "src/mypackage/__init__.py"
```

You can set a custom regex with `regex=`; use `(?P<value>...)` to capture the
value you want to use. By default when targeting version, you get a reasonable
regex for python files,
`'(?i)^(__version__|VERSION) *= *([\'"])v?(?P<value>.+?)\2'`.

```{versionadded} 0.5

```

:::

### Writing metadata

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

## Editable installs

Experimental support for editable installs is provided, with some caveats and
configuration. Recommendations:

- Use `--no-build-isolation` when doing an editable install is recommended; you
  should preinstall your dependencies.
- Automatic rebuilds do not have the original isolated build dir (pip deletes
  it).
- Select a `build-dir` when using editable installs, especially if you also
  enable automatic rebuilds.
- You need to reinstall to pick up new files.

Known limitations:

- Resources (via `importlib.resources`) are not properly supported (yet).

```console
# Very experimental rebuild on initial import feature
$ pip install --no-build-isolation --config-settings=editable.rebuild=true -ve.
```

Due to the length of this line already being long, you do not need to set the
`experimental` setting to use editable installs, but please consider them
experimental and subject to change.

You can disable the verbose rebuild output with `editable.verbose=false` if you
want. (Also available as the `SKBUILD_EDITABLE_VERBOSE` envvar when importing;
this will override if non-empty, and `"0"` will disable verbose output).

Currently one `editable.mode` is provided, `"redirect"`, which uses a custom
redirecting finder to combine the static CMake install dir with the original
source code. Python code added via scikit-build-core's package discovery will be
found in the original location, so changes there are picked up on import,
regardless of the `editable.rebuild` setting.

## Other options

You can select a custom build dir; by default scikit-build-core will use a
temporary dir. If you select a persistent one, you can get major rebuild
speedups.

```{conftabs} build-dir "build/{wheel_tag}"

```

There are several values you can access through Python's formatting syntax:

- `cache_tag`: `sys.implementation.cache_tag`
- `wheel_tag`: The tags as computed for the wheel
- `build_type`: The current build type (`Release` by default)
- `state`: The current run state, `sdist`, `wheel`, `editable`,
  `metadata_wheel`, and `metadata_editable`

Scikit-build-core also strictly validates configuration; if you need to disable
this, you can:

```toml
[tool.scikit-build]
strict-config = false
```

Scikit-build-core also occasionally has experimental features. This is applied
to features that do not yet carry the same forward compatibility (using
minimum-version) guarantee that other scikit-build-core features have. These can
only be used if you enable them:

```toml
[tool.scikit-build]
experimental = true
```

## Overrides

Scikit-build-core has an override system, similar to cibuildwheel and mypy. You
specify a `tool.scikit-build.overrides` array with an `if` key. That if key can
take several values, based on [PEP 508][]:

- `python_version`: The two-digit Python version. Takes a specifier set.
- `sys_platform`: The value of `sys.platform`. Takes a regex.
- `platform_machine`: The value of `platform.machine()`. Takes a regex.
- `platform_node`: The value of `platform.node()`. Takes a regex.
- `implementation_name`: The value of `sys.implementation.name`. Takes a regex.
- `implementation_version`: Derived from `sys.implementation.version`, following
  PEP 508. Takes a specifier set.

At least one must be provided. Then you can specify any collection of valid
options, and those will override if all the items in the `if` are true. They
will match top to bottom, overriding previous matches. For example:

```toml
[[tool.scikit-build.overrides]]
if.sys_platform = "darwin"
cmake.minimum-version = "3.18"
```

## Full schema

The full schema for the `tool.scikit-build` table is below:

```{jsonschema} ../src/scikit_build_core/resources/scikit-build.schema.json

```

[pep 508]: https://peps.python.org/pep-0508/#environment-markers
