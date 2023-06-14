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
$ pip install . --config-settings=cmake.verbose=true --config-settings=logging.level=INFO
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

## Customizing the built wheel

The wheel will automatically look for Python packages at `<package_name>` and
`src/<package_name>`. If you want to list packages explicitly, you can:

```toml
[tool.scikit-build]
wheel.packages = ["python/mypackage"]
```

Or you can disable Python file inclusion entirely, and rely only on CMake's
installs, you can:

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
wheel.py.api = "py3"
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
wheel.expand-macos-universal-tags = false
```

## Configuring CMake arguments and defines

You can select a different build type, such as `Debug`:

````{tab} pyproject.toml

```toml
[tool.scikit-build]
cmake.build-type = "Debug"
```

````

`````{tab} config-settings


````{tab} pip

```console
$ pip install . --config-settings=cmake.build-type=Debug
```

````

````{tab} build

```console
$ pipx run build --wheel -Ccmake.build-type=Debug
```

````

````{tab} cibuildwheel

```toml
[tool.cibuildwheel.config-settings]
"cmake.build-type" = "Debug"
```

````

`````

````{tab} Environment

```yaml
SKBUILD_CMAKE_BUILD_TYPE: Debug
```

````

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
$ # NEXT VERSION OF PIP ONLY
$ pip install . -Ccmake.define.SOME_DEFINE=ON
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
SKBUILD_CMAKE_DEFINES: SOME_DEFINE=ON
```

````

You can also manually specify the exact cmake args. Beyond the normal
`SKBUILD_CMAKE_ARGS`, the `CMAKE_ARGS` space-separated environment variable is
also supported (with some filtering for options scikit-build-core doesn't
support overriding).

````{tab} pyproject.toml

```toml
[tool.scikit-build]
cmake.args = ["-DSOME_DEFINE=ON", "-DOTHER=OFF"]
```

````

`````{tab} config-settings


````{tab} pip

```console
$ pip install . --config-settings=cmake.args="-DSOME_DEFINE=ON;-DOTHER=OFF"
$ # NEXT VERSION OF PIP ONLY
$ pip install . -Ccmake.args=-SOME_DEFINE=ON -Ccmake.args=-DOTHER=OFF
```

````

````{tab} build

```console
$ pipx run build -Ccmake.args="-DSOME_DEFINE=ON;-DOTHER=OFF"
$ pipx run build -Ccmake.args=-DSOME_DEFINE=ON -Ccmake.args=-DOTHER=OFF
```

````

````{tab} cibuildwheel

```toml
[tool.cibuildwheel.config-settings]
"cmake.args" = ["-DSOME_DEFINE=ON", "-DOTHER=OFF"]
```

````

`````

````{tab} Environment

```yaml
SKBUILD_CMAKE_ARGS: -DSOME_DEFINE=ON;-DOTHER=OFF
CMAKE_ARGS: -DSOME_DEFINE=ON -DOTHER=OFF
```

````

## Dynamic metadata

Scikit-build-core 0.3.0 supports dynamic metadata with two built-in plugins.

:::{warning}

This is not ready for plugin development outside of scikit-build-core;
`tool.scikit-build.experimental=true` is required to use plugins that are not
shipped with scikit-build-core, since the interface is provisional. :::

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

[tool.setuptools_scm]
write_to = "src/package/_version.py"
```

This sets the python project version according to
[git tags](https://github.com/pypa/setuptools_scm/blob/fb261332d9b46aa5a258042d85baa5aa7b9f4fa2/README.rst#default-versioning-scheme)
or a
[`.git_archival.txt`](https://github.com/pypa/setuptools_scm/blob/fb261332d9b46aa5a258042d85baa5aa7b9f4fa2/README.rst#git-archives)
file, or equivalents for other VCS systems. With this, you may also to set the
cmake project version equivalently, e.g. using
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
$ pip install --no-build-isolation --config-settings=editiable.rebuild=true -ve.
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

````{tab} pyproject.toml

```toml
[tool.scikit-build]
build-dir = "build/{wheel_tag}"
```

````

`````{tab} config-settings


````{tab} pip

```console
$ pip install . --config-settings='build-dir=build/{wheel_tag}'
```

````

````{tab} build

```console
$ pipx run build --wheel -Cbuild-dir='build/{wheel_tag}'
```

````

````{tab} cibuildwheel

```toml
[tool.cibuildwheel.config-settings]
build-dir = "build/{wheel_tag}"
```

````

`````

````{tab} Environment

```yaml
SKBUILD_BUILD_DIR: "build/{wheel_tag}"
```

````

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
