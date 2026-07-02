# FAQs

## Starting a new project

The quickest way is the built-in `init` command:
`scikit-build init --backend pybind11 myproject` scaffolds a ready-to-build
project (run without `--backend` to pick a binding interactively). See the
[getting started guide](getting_started.md) for a walkthrough of what it
generates.

```{versionadded} 1.0
The `scikit-build init` command.
```

For a fully-featured project layout, use the [Scientific Python cookie][], which
makes a new project following the [Scientific Python Development Guidelines][].
Scikit-build-core is one of the backends you can select. The project will have a
lot of tooling prepared for you as well, including pre-commit checks and a
noxfile; be sure to read the guidelines to see what is there and how it works.

Another option is the [pybind11 example][].

## Multithreaded builds

For most generators, you can control the parallelization via a CMake define:

```bash
pip install -Ccmake.define.CMAKE_BUILD_PARALLEL_LEVEL=8 .
```

or an environment variable:

```bash
CMAKE_BUILD_PARALLEL_LEVEL=8 pip install .
```

The default generator on Unix-like platforms is Ninja, which automatically tries
to run in parallel with the number of cores on your machine.

If your project has historically used a different environment variable (such as
`MAX_JOBS`) to control this, you can forward it to `CMAKE_BUILD_PARALLEL_LEVEL`
with the `[tool.scikit-build.env]` table:

```toml
[tool.scikit-build.env]
CMAKE_BUILD_PARALLEL_LEVEL = { env = "MAX_JOBS" }
```

A directly-set `CMAKE_BUILD_PARALLEL_LEVEL` still wins, since `env` entries use
`setdefault` semantics unless `force = true` is given. See
[](../configuration/index.md#environment-variables-for-the-build) for the full
`env` table reference, including selecting a compiler and setting search paths.

```{versionadded} 1.0
The `[tool.scikit-build.env]` table.
```

## Dynamic setup.py options

Most common needs can be moved into your `CMakeLists.txt`. For example, if you
had a custom `setup.py` option (which setuptools has deprecated as well), you
can make it a CMake option and then pass it with
`-Ccmake.define.<OPTION_NAME>=<value>`. If you need to customize configuration
options, try `[[tool.scikit-build.overrides]]`. If that is missing some value
you need, please open an issue and let us know.

## Finding Python

When using `find_package(Python ...)`, you should only request the
`Development.Module` component. If you request `Development`, you will also
require the `Development.Embed` component, which will require the Python
libraries to be found for linking. When building a module on Unix, you do not
link to Python - the Python symbols are already loaded in the interpreter.
What's more, the manylinux image (which is used to make redistributable Linux
wheels) does not have the Python libraries, both to avoid this mistake, and to
reduce size.

## Cross compiling

When cross compiling, FindPython may not get the correct SOABI extension.
Scikit-build-core does know the correct extension, however, and sets it as
`SKBUILD_SOABI`. See [the SOABI docs](#soabi).

## Debugging a build

If you want to debug a scikit-build-core build, you have several options. If you
are using `pip`, make sure you are passing the `-v` flag, otherwise `pip`
suppresses all output. You can
[increase scikit-build-core's logging verbosity](#verbosity). You can also get a
printout of the current settings using:

```bash
scikit-build builder
```

```{versionchanged} 1.0
This is now a subcommand of the unified `scikit-build` CLI (previously
`python -m scikit_build_core.builder`).
```

## Coverage and debugging (gcov / gcovr / GDB)

Tools like `gcov`/`gcovr` and debuggers like GDB rely on **absolute paths**
baked into the build artifacts: gcov records the source path and compilation
directory in the `.gcno` (compile-time) and `.gcda` (run-time) files, and DWARF
debug info records the source path in the compiled extension. If those paths no
longer exist when you run the tool, you get errors such as

```console
$ gcovr --xml coverage.xml -r .
(ERROR) Trouble processing '.../CMakeFiles/foo.dir/_foo.c.gcda' with working directory '/home'.
```

or GDB that cannot show source lines even with debug flags enabled. Two default
behaviors are usually responsible:

- **The build directory is temporary.** Without {confval}`build-dir` set,
  scikit-build-core builds in a temporary directory that is deleted after the
  build, taking the `.gcno` files and the compiled extension with it. Set a
  persistent `build-dir`.
- **Build isolation copies the source.** `pip install .` and `python -m build`
  copy your project into a temporary directory before invoking the backend, so
  the compiler bakes those temporary source paths into the coverage and debug
  data. After the build the temporary source tree is gone.

The most reliable workflow is a persistent build directory with isolation
disabled, so both the build tree and the source tree stay in place:

```bash
pip install --no-build-isolation -Cbuild-dir=build -ve .
```

Then run gcovr against the persistent tree, pointing the root at your source:

```bash
gcovr -r . build
```

If you would rather not depend on the paths staying put, make the recorded paths
relocatable with compiler flags — `-fprofile-abs-path` for gcov and
`-ffile-prefix-map=<build>=<src>` (or `-fdebug-prefix-map=...` for debug info
only) — for example via {confval}`cmake.define` or `CFLAGS`.

## IDE IntelliSense can't find headers (`compile_commands.json`)

Editor tooling — the VSCode C/C++ extension, clangd, and similar — resolves
headers like `pybind11/pybind11.h` from your include paths. Two defaults hide
them:

- **Build dependencies live in a temporary overlay.** With build isolation (the
  default for `pip install .`, `python -m build`, `uv build`, and `uv sync`),
  binding libraries such as pybind11 and nanobind are installed into a throwaway
  environment that is deleted after the build. CMake reports a path such as
  `.../Temp/pip-build-env-xxxx/overlay/Lib/site-packages/pybind11/include`,
  which no longer exists when your editor looks for it.
- **The build directory is temporary.** Without {confval}`build-dir` set,
  scikit-build-core builds in a temporary directory, so the
  `compile_commands.json` CMake generates is discarded too.

The fix is to preinstall the build dependencies, disable build isolation, set a
persistent `build-dir`, and have CMake export a compile database:

````{tab} pip

```bash
pip install scikit-build-core pybind11
pip install --no-build-isolation --check-build-dependencies -ve . \
  -Cbuild-dir=build \
  -Ccmake.define.CMAKE_EXPORT_COMPILE_COMMANDS=1
```

````

````{tab} uv

```bash
uv pip install scikit-build-core pybind11
uv pip install --no-build-isolation -ve . \
  -Cbuild-dir=build \
  -Ccmake.define.CMAKE_EXPORT_COMPILE_COMMANDS=1
```

In a uv-managed project, disable isolation for your package instead, so
`uv sync` reuses the environment's build dependencies rather than a discarded
overlay:

```toml
[tool.uv]
no-build-isolation-package = ["mypackage"]
```

````

This writes `build/compile_commands.json` with real, persistent paths. You can
set the build directory in `pyproject.toml` instead of on the command line:

```toml
[tool.scikit-build]
build-dir = "build"
```

Then point your editor at the file. For clangd, add
`--compile-commands-dir=build` (or a `.clangd` with a
`CompileFlags.CompilationDatabase: build` entry); for the VSCode C/C++
extension, set
`"C_Cpp.default.compileCommands": "${workspaceFolder}/build/compile_commands.json"`.
See [editable installs](../configuration/index.md#editable-installs) for the
related `--no-build-isolation` recommendations.

## A dependency's library ends up in `site-packages/bin` or `lib`

If you build a shared dependency as part of your project (for example via
`add_subdirectory(...)` on a vendored library), you may find its library
installed to `site-packages/bin` (Windows) or `site-packages/lib` (Linux/macOS)
instead of next to your extension module. The `install(TARGETS ...)` command
sends its artifacts to the [GNUInstallDirs][] defaults — `bin` for Windows DLLs
(a `RUNTIME` artifact) and `lib` for `.so`/`.dylib` (a `LIBRARY` artifact) — and
scikit-build-core copies the whole install tree into the wheel. A library placed
there generally will not be found at import time, either.

The cleanest fix is usually to link the dependency statically so there is no
runtime library to place. If you need it shared, you can redirect the install
into your package directory and add the runtime hints yourself, or run a
wheel-repair tool. See [](#dynamic-linking) for all of the options.

[GNUInstallDirs]: inv:cmake:cmake:module#module:GNUInstallDirs

## Target output paths differ on MSVC (multi-config generators)

Multi-config generators — Visual Studio (the default on Windows), Xcode, and
Ninja Multi-Config — put each target's build artifact in a per-configuration
subdirectory. A `main` executable lands at `build/Release/main.exe`, not
`build/main.exe` the way it would with a single-config generator (Ninja,
Makefiles). This bites when you reference a built file by an assumed path.

Two rules keep this portable:

- **Get artifacts into the wheel with `install(...)`, not by path.** The install
  step strips the per-config subdirectory for you, and scikit-build-core only
  copies the install tree into the wheel — files left in the build directory are
  never packaged. When you do need the real path of a built target (in a custom
  command, or `install(FILES ...)`), use the `$<TARGET_FILE:main>` generator
  expression instead of writing out `Release/main.exe`.

  ```cmake
  add_executable(main main.cpp)
  install(TARGETS main DESTINATION ${SKBUILD_SCRIPTS_DIR})
  ```

- **Pin `*_OUTPUT_DIRECTORY` with an empty generator expression.** If you set
  `RUNTIME_OUTPUT_DIRECTORY` / `LIBRARY_OUTPUT_DIRECTORY` (for example to place
  a module for an
  [inplace editable build](../configuration/index.md#editable-installs)), append
  `$<0:>` so multi-config generators don't add the config subdirectory back on.
  This saves setting every `*_OUTPUT_DIRECTORY_<CONFIG>` variant by hand.

  ```cmake
  set_target_properties(mymod PROPERTIES
      LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/src/mypkg$<0:>")
  ```

On Windows you can also sidestep multi-config entirely by building with the
single-config Ninja generator: set `CMAKE_GENERATOR=Ninja` (or pass
`cmake.args = ["-G", "Ninja"]`). Unlike the Visual Studio generator, Ninja does
not set up the MSVC toolchain itself, so build from a Visual Studio Developer
Command Prompt (or after running `vcvarsall.bat`). scikit-build-core already
selects Ninja by default on non-MSVC Windows.

## Shipping a library to load with `ctypes`

If your package is a thin `ctypes` (or `cffi`) wrapper around a CMake-built
shared library, rather than a compiled Python extension, the goal is to install
the library alongside your Python code and then locate it at runtime without
hard-coding a path. This has the nice property that a single wheel works on
every Python version, since the library does not touch the Python ABI. The
tradeoff is that you have to find and load the library yourself.

### Install the library next to your Python code

Point the install destination at your package directory so the library lands in
`site-packages/mypackage/` next to `__init__.py`:

```cmake
install(TARGETS mylib DESTINATION mypackage)
```

The destination is relative to the platlib (`${SKBUILD_PLATLIB_DIR}`) by
default; you can name any of the [install trees](#install-directories)
explicitly if you need to. If you set `wheel.install-dir = "mypackage"`, then
the destination is relative to that instead, and a bare `DESTINATION .` works.

### Find it at runtime with `importlib.resources`

Do **not** compute the path relative to `__file__` — that assumes the package
lives on a real filesystem, which is not guaranteed (it could be in a zip, and
in an editable install the Python source and the compiled library live in
different directories). Use `importlib.resources` instead, which
scikit-build-core's editable installs fully support:

```python
import ctypes
import sys
from importlib.resources import files

# Pick the right suffix for the platform.
_suffix = {"win32": ".dll", "darwin": ".dylib"}.get(sys.platform, ".so")
_lib = files("mypackage") / f"libmylib{_suffix}"

lib = ctypes.CDLL(str(_lib))
```

For the general (zip-safe) case, wrap the traversable in
`importlib.resources.as_file`, which extracts the resource to a real path if
necessary. Because `ctypes` needs the file to remain on disk for the lifetime of
the process, keep the context manager open — for example with an
`contextlib.ExitStack` closed at interpreter exit:

```python
import atexit, ctypes
from contextlib import ExitStack
from importlib.resources import files, as_file

_files = ExitStack()
atexit.register(_files.close)
_lib = _files.enter_context(as_file(files("mypackage") / f"libmylib{_suffix}"))
lib = ctypes.CDLL(str(_lib))
```

### Editable installs and rebuilds

In redirect-mode editable installs (the default), `importlib.resources` finds
the compiled library through the redirecting finder, so the code above works
unchanged. Note that accessing a resource does **not** trigger a rebuild — plain
libraries are not importable modules, so the automatic `editable.rebuild`
on-import hook does not fire for them. To pick up C/C++ changes, either request
a rebuild explicitly (this works whenever a persistent `build-dir` is set, with
or without `editable.rebuild`)…

```python
import mypackage

mypackage.__loader__.rebuild()
```

…or import a real extension module from the same project first, which does fire
the on-import hook when `editable.rebuild` is enabled. See
[](#triggering-a-rebuild-manually) for the details and the `build-dir`
requirement.

### Runtime search paths

If your shipped library links against _other_ shared libraries, you still need
to make those discoverable at load time (`RPATH` on Linux/macOS,
`os.add_dll_directory` on Windows). See [](#dynamic-linking) for the full set of
options, including wheel-repair tools.

## Repairing wheels

Like most other backends[^1], scikit-build-core produces `linux` wheels, which
are not redistributable and cannot be uploaded to PyPI[^2]. You have to run your
wheels through `auditwheel` to make `manylinux` wheels. `cibuildwheel`
automatically does this for you. See [repairing](#repairing-wheels).

## Making a Conda recipe

`scikit-build-core` is available on conda-forge, and is used in [dozens of
recipes][]. There are a few things to keep in mind.

You need to recreate your `build-system.requires` in the `host` table, with the
conda versions of your dependencies. You also need to add `cmake` and either
`make` or `ninja` to your `build:` table. Conda-build hard-codes
`CMAKE_GENERATOR="Unix Makefiles"` on UNIX systems, so you have to set or unset
this to use Ninja if you prefer Ninja. The `scikit-build-core` recipe cannot
depend on `cmake`, `make`, or `ninja`, because that would add those to the wrong
table (`host` instead of `build`). Here's an example:

```yaml
build:
  script:
   - {{ PYTHON }} -m pip install . -vv

requirements:
  build:
    - python                              # [build_platform != target_platform]
    - cross-python_{{ target_platform }}  # [build_platform != target_platform]
    - {{ compiler('c') }}
    - {{ stdlib('c') }}
    - {{ compiler('cxx') }}
    - cmake >=3.15
    - make                                 # [not win]
  host:
    - python
    - pip
    - scikit-build-core >=0.12
  run:
    - python
```

## Supporting free-threaded builds on Windows

Windows currently requires a little extra care. You should set the C define
`Py_GIL_DISABLED` on Windows; due to the way the two builds share the same
config files, Python cannot set it for you on the free-threaded variant.

## Building wheel variants (experimental)

```{versionadded} 1.0

```

```{warning}
This is an early preview of [PEP 817][] wheel variant support. The interface may
change, and it must be opted into with `experimental = true`.
```

Scikit-build-core can attach variant metadata to a wheel, producing a
variant-labeled filename (the label becomes the final field of the wheel name)
and a `variant.json` file inside `*.dist-info`. This lets you ship several
wheels for the same version that differ by hardware or library features (CPU
ABI, CUDA version, BLAS implementation, etc.).

Because each variant of a build needs different settings, the variant options
are **only allowed in config-settings or `[[tool.scikit-build.overrides]]`** —
they cannot be hard-coded at the top level of `pyproject.toml`. The relevant
settings are:

- `variant` / `variant-name`: variant properties in
  `namespace :: feature :: value` form (repeatable).
- `variant-label`: override the computed label used in the wheel filename.
- `null-variant`: build the null variant (mutually exclusive with the above).

When any of these are set, [`variantlib`][] is automatically injected as a build
requirement, and the experimental flag must be enabled. For example, to build a
CPU-ABI variant with `pip`:

```bash
pip wheel . \
  -Cexperimental=true \
  -Cvariant="cpu :: abi :: cp313" \
  -Cvariant-label=cpu
```

Or to enable it for everyone via an override (still keeping the per-build values
in config-settings), put the experimental flag in `pyproject.toml`:

```toml
[tool.scikit-build]
experimental = true
```

Pass `-Cvariant=...` (and friends) at build time to select which variant to
produce.

[^1]:
    Due to a [bug in packaging](https://github.com/pypa/packaging/issues/160),
    some backends may mistakenly produce the wrong tags (including
    scikit-build-core < 0.9), but the wheels are not actually
    manylinux/musllinux, just mistagged.

[^2]:
    Platforms like ARMv6 that do not have a manylinux spec are exempt from this
    rule.

<!-- prettier-ignore-start -->

[scientific python cookie]: https://github.com/scientific-python/cookie
[scientific python development guidelines]: https://learn.scientific-python.org/development
[pybind11 example]: https://github.com/pybind/scikit_build_example
[dozens of recipes]: https://github.com/search?type=code&q=org%3Aconda-forge+path%3Arecipe%2Fmeta.yaml+scikit-build-core
[pep 817]: https://peps.python.org/pep-0817
[`variantlib`]: https://github.com/wheelnext/variantlib

<!-- prettier-ignore-end -->
