# Configuration

Scikit-build-core supports a powerful unified configuration system. Every option
in scikit-build-core can be specified in one of three ways: as a
`pyproject.toml` option (preferred if static), as a config-settings options
(preferred if dynamic), or as an environment variable. Note that config-settings
options can optionally be prefixed with `skbuild.`, for example
`-C skbuild.logging.level=INFO`.

(verbosity)=

## Verbosity

By default, the CMake configuration output is always shown, but it may be hidden
behind the build frontend setting, e.g. `pip` requires including `-v` argument
in order to display any output.

You can increase the verbosity of the build with two settings - `build.verbose`
is a shortcut for verbose build output (i.e. `cmake --build ... -v`), and
`logging.level` controls scikit-build-core's internal logging. An example (with
all configuration styles) of setting both is:

````{tab} pyproject.toml

```toml
[tool.scikit-build]
build.verbose = true
logging.level = "INFO"
```

````

`````{tab} config-settings


````{tab} pip

```console
$ pip install . -v --config-settings=build.verbose=true --config-settings=logging.level=INFO
```

````

````{tab} build

```console
$ pipx run build --wheel -Cbuild.verbose=true -Clogging.level=INFO
```

````

````{tab} cibuildwheel

```toml
[tool.cibuildwheel.config-settings]
"build.verbose" = true
"logging.level" = "INFO"
```

````

`````

````{tab} Environment


```yaml
SKBUILD_BUILD_VERBOSE: true
SKBUILD_LOGGING_LEVEL: "INFO"
```


````

:::{warning}

In general, the environment variable method is intended as an emergency
workaround for legacy tooling.

:::

:::{versionchanged} 0.10

`cmake.verbose` was renamed to `build.verbose`.

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

In your `pyproject.toml`, you can specify the special string
`"build-system.requires"`, which will read the minimum version from your
build-system requirements directly; you must specify a minimum there to use this
automatic feature.

```toml
[build-system]
requires = ["scikit-build-core>=0.10"]

[tool.scikit-build]
minimum-version = "build-system.requires"
```

:::{versionchanged} 0.10

The `"build-system.requires"` option was added.

:::

:::{warning}

The following behaviors are affected by `minimum-version`:

- `minimum-version` 0.5+ (or unset) provides the original name in metadata and
  properly normalized SDist names.
- `minimum-version` 0.5+ (or unset) strips binaries by default.
- `minimum-version` 0.8+ (or unset) `cmake.minimum-version` and
  `ninja.minimum-version` are replaced with `cmake.version` and `ninja.version`.
- `minimum-version` 0.10+ (or unset) `cmake.targets` and `cmake.verbose` are
  replaced with `build.targets` and `build.verbose`. The CMake minimum version
  will be detected if not given.

:::

## CMake and Ninja minimum versions

You can select a different minimum version for CMake and Ninja.
Scikit-build-core will automatically decide to download a wheel for these (if
possible) when the system version is less than this value.

For example, to require a recent CMake and Ninja:

```toml
[tool.scikit-build]
cmake.version = ">=3.26.1"
ninja.version = ">=1.11"
```

You can try to read the version from your CMakeLists.txt with the special string
`"CMakeLists.txt"`. This is an error if the minimum version was not statically
detectable in the file. If your `minimum-version` setting is unset or set to
"0.10" or higher, scikit-build-core will still try to read this if possible, and
will fall back on ">=3.15" if it can't read it.

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

```{versionadded} 0.8
These used to be called `cmake.minimum-version` and `ninja.minimum-version`, and
only took a single value. Now they are full specifier sets, allowing for more
complex version requirements, like `>=3.15,!=3.18.0`.
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

set(PYBIND11_FINDPYTHON ON)

if(NOT SKBUILD_STATE STREQUAL "sdist"
   AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/pybind11/CMakeLists.txt")
  message(STATUS "Using integrated pybind11")
  add_subdirectory(pybind11)
else()
  FetchContent_Declare(
    pybind11
    GIT_REPOSITORY https://github.com/pybind/pybind11.git
    GIT_TAG v2.12.0
    SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/pybind11)
  FetchContent_MakeAvailable(pybind11)
endif()
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

This can also be a table, allowing full customization of where a source package
maps to a wheel directory. The final components of both paths must match due to
the way editable installs work. The equivalent of the above is:

```toml
[tool.scikit-build.wheel.packages]
mypackage = "python/src/mypackage"
```

But you can also do more complex moves:

```toml
[tool.scikit-build.wheel.packages]
"mypackage/subpackage" = "python/src/subpackage"
```

:::{versionadded} 0.10

Support for the table form.

:::

You can disable Python file inclusion entirely, and rely only on CMake's install
mechanism:

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

You can exclude files from the built wheel (on top of the `sdist.exclude` list)
as well (not guaranteed to be respected by editable installs):

```toml
[tool.scikit-build]
wheel.exclude = ["**.pyx"]
```

:::{versionchanged} 0.9

Previously these were matched on the source path, rather than the wheel path,
and didn't apply to CMake output.

:::

:::{note}

There are two more settings that are primarily intended for `overrides` (see
below). `wheel.cmake` defaults to `true`, and this enables/disables building
with CMake. It also changes the default of `wheel.platlib` unless it's set
explicitly; CMake builds assume `wheel.platlib = true`, and CMake-less builds
assume `wheel.platlib = false` (purelib targeted instead).

:::

## Customizing the output wheel

The python API tags for your wheel will be correct assuming you are building a
CPython extension. If you are building a Limited ABI extension, you should set
the wheel tags for the version you support:

```toml
[tool.scikit-build]
wheel.py-api = "cp38"
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

You can also specify a build tag:

```{conftabs} wheel.build-tag 1

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

You can specify CMake defines as strings or bools:

````{tab} pyproject.toml

```toml
[tool.scikit-build.cmake.define]
SOME_DEFINE = "Foo"
SOME_OPTION = true
```

````

You can even specify a CMake define as a list of strings:

````{tab} pyproject.toml

```toml
[tool.scikit-build.cmake.define]
FOOD_GROUPS = [
    "Apple",
    "Lemon;Lime",
    "Banana",
    "Pineapple;Mango",
]
```

````

Semicolons inside the list elements will be escaped with a backslash (`\`) and
the resulting list elements will be joined together with semicolons (`;`) before
being converted to command-line arguments.

:::{versionchanged} 0.11

Support for list of strings.

:::

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

You can also (`pyproject.toml` only) specify a dict, with `env=` to load a
define from an environment variable, with optional `default=`.

```toml
[tool.scikit-build.cmake.define]
SOME_DEFINE = {env="SOME_DEFINE", default="EMPTY"}
```

You can also manually specify the exact CMake args. Beyond the normal
`SKBUILD_CMAKE_ARGS`, the `CMAKE_ARGS` space-separated environment variable is
also supported (with some filtering for options scikit-build-core doesn't
support overriding).

```{conftabs} cmake.args ["-DSOME_DEFINE=ON", "-DOTHER=OFF"]

```

:::{warning}

Setting defines through `cmake.args` in `pyproject.toml` is discouraged because
this cannot be later altered via command line. Use `cmake.define` instead.

:::

You can also specify this using `CMAKE_ARGS`, space separated:

```yaml
CMAKE_ARGS: -DSOME_DEFINE=ON -DOTHER=OFF
```

You can also specify only specific targets to build (leaving this off builds the
default targets):

```{conftabs} build.targets ["python"]

```

:::{versionchanged} 0.10

`cmake.targets` was renamed to `build.targets`.

:::

You can pass raw arguments directly to the build tool, as well:

```{conftabs} build.tool-args ["-j12", "-l13"]

```

```{versionadded} 0.9.4

```

## Editable installs

Experimental support for editable installs is provided, with some caveats and
configuration. Recommendations:

- Use `--no-build-isolation` when doing an editable install is recommended; you
  should preinstall your dependencies.
- Automatic rebuilds do not have the original isolated build dir (pip deletes
  it), so select a `build-dir` when using editable installs, especially if you
  also enable automatic rebuilds.
- You need to reinstall to pick up new files.

Known limitations:

- Resources (via `importlib.resources`) are not properly supported (yet).
  Currently experimentally supported except on Python 3.9 (3.8, 3.10, 3.11,
  3.12, and 3.13 work). `importlib_resources` may work on Python 3.9.

```console
# Very experimental rebuild on initial import feature
$ pip install --no-build-isolation --config-settings=editable.rebuild=true -Cbuild-dir=build -ve.
```

Due to the length of this line already being long, you do not need to set the
`experimental` setting to use editable installs, but please consider them
experimental and subject to change.

You can disable the verbose rebuild output with `editable.verbose=false` if you
want. (Also available as the `SKBUILD_EDITABLE_VERBOSE` envvar when importing;
this will override if non-empty, and `"0"` will disable verbose output).

The default `editable.mode`, `"redirect"`, uses a custom redirecting finder to
combine the static CMake install dir with the original source code. Python code
added via scikit-build-core's package discovery will be found in the original
location, so changes there are picked up on import, regardless of the
`editable.rebuild` setting.

:::{note}

A second experimental mode, `"inplace"`, is also available. This does an
in-place CMake build, so all the caveats there apply too -- only one build per
source directory, you can't change to an out-of-source builds without removing
the build artifacts, your source directory will be littered with build
artifacts, etc. Also, to make your binaries importable, you should set
`LIBRARY_OUTPUT_DIRECTORY` (include a generator expression, like the empty one
`$<0:>` for multi-config generator support, like MSVC, so you don't have to set
all possible `*_<CONFIG>` variations) to make sure they are placed inside your
source directory inside the Python packages; this will be run from the build
directory, rather than installed. This will also not support automatic rebuilds.
The build directory setting will be ignored if you use this and perform an
editable install. You can detect this mode by checking for an in-place build and
checking `SKBUILD` being set.

With all the caveats, this is very logically simple (one directory) and a near
identical replacement for `python setup.py build_ext --inplace`. Some third
party tooling might work better with this mode. Scikit-build-core will simply
install a `.pth` file that points at your source package(s) and do an inplace
CMake build.

On the command line, you can pass `-Ceditable.mode=inplace` to enable this mode.

:::

## Messages

You can add a message to be printed after a successful or failed build. For
example:

```toml
[tool.scikit-build]
messages.after-sucesss = "{green}Wheel successfully built"
messages.after-failure = """
{bold.red}Sorry{normal}, build failed. Your platform is {platform.platform}.
"""
```

This will be run through Python's formatter, so escape curly brackets if you
need them. Currently, there are several formatter-style keywords available:
`sys`, `platform` (parenthesis will be added for items like `platform.platform`
for you), `__version__` for scikit-build-core's version, and style keywords.

For styles, the colors are `default`, `red`, `green`, `yellow`, `blue`,
`magenta`, `cyan`, and `white`. These can be accessed as `fg.*` or `bg.*`,
without a qualifier the foreground is assumed. Styles like `normal`, `bold`,
`italic`, `underline`, `reverse` are also provided. A full clearing of all
styles is possible with `reset`. These all can be chained, as well, so
`bold.red.bg.blue` is valid, and will produce an optimized escape code. Remember
that you need to set the environment variable `FORCE_COLOR` to see colors with
pip.

```{versionadded} 0.10

```

## Other options

You can select a custom build dir; by default scikit-build-core will use a
temporary dir. If you select a persistent one, you can get major rebuild
speedups.

```{conftabs} build-dir "build/{wheel_tag}"

```

There are several values you can access through Python's formatting syntax. See
[](./formatted.md).

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

You can also fail the build with `fail = true`. This is useful with overrides if
you want to make a specific configuration fail. If this is set, extra
dependencies like `"cmake"` will not be requested.

```{versionadded} 0.10

```

## Overrides

The overrides system allows you to customize for a wide variety of situations.
It is described at [](#overrides).

## Full Schema

You can see the full schema at [](#schema).
