# FAQs

## Starting a new project

The quickest way is the built-in `init` command:
`scikit-build init --backend pybind11 myproject`. See the
[quick start](getting_started.md#quick-start) for it and the other scaffolding
options (Scientific Python cookie, uv, buildgen), and the rest of that guide for
a walkthrough of what it generates.

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
with the `[tool.scikit-build.env]` table; see
[](../configuration/index.md#environment-variables-for-the-build).

## Dynamic setup.py options

Most common needs can be moved into your `CMakeLists.txt`. For example, if you
had a custom `setup.py` option (which setuptools has deprecated as well), you
can make it a CMake option and then pass it with
`-Ccmake.define.<OPTION_NAME>=<value>`. If you need to customize configuration
options, try `[[tool.scikit-build.overrides]]`. If that is missing some value
you need, please open an issue and let us know.

## Finding Python

When using `find_package(Python ...)`, only request the `Development.Module`
component, not `Development`; see [Finding Python](cmakelists.md#finding-python)
for the details (in short: `Development` also requires the embedding libraries,
which manylinux images intentionally do not ship).

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

Coverage and debug tools fail when the temporary build directory and isolated
source copy disappear after the build; the fix is a persistent `build-dir` with
`--no-build-isolation`. See [debugging and IDE integration](debugging.md) for
the workflow.

## IDE IntelliSense can't find headers (`compile_commands.json`)

Build isolation hides the binding libraries' include paths and the temporary
build dir discards `compile_commands.json`; export a compile database from a
persistent, non-isolated build and point your editor at it. See
[debugging and IDE integration](#compile-commands) for the commands.

(dependency-in-site-packages)=

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

(msvc-multi-config)=

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
  [inplace editable build](../configuration/editable.md#inplace-mode)), append
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

For a thin `ctypes`/`cffi` wrapper around a CMake-built shared library, install
the library next to your Python code and load it via `importlib.resources`; the
full walkthrough is in [shipping a library for ctypes](ctypes.md).

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
`make` or `ninja` to your `build:` table:

```{note}
The `scikit-build-core` recipe cannot depend on `cmake`, `make`, or `ninja`
itself, because that would add those to the wrong table (`host` instead of
`build`). Also, conda-build hard-codes `CMAKE_GENERATOR="Unix Makefiles"` on
UNIX systems, so set or unset this if you prefer Ninja.
```

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

Scikit-build-core has an early preview of [PEP 817][] wheel variant support —
several wheels for the same version differing by hardware or library features.
See [building wheel variants](../configuration/variants.md).

[^1]:
    Due to a [bug in packaging](https://github.com/pypa/packaging/issues/160),
    some backends may mistakenly produce the wrong tags (including
    scikit-build-core < 0.9), but the wheels are not actually
    manylinux/musllinux, just mistagged.

[^2]:
    Platforms like ARMv6 that do not have a manylinux spec are exempt from this
    rule.

<!-- prettier-ignore-start -->

[dozens of recipes]: https://github.com/search?type=code&q=org%3Aconda-forge+path%3Arecipe%2Fmeta.yaml+scikit-build-core
[pep 817]: https://peps.python.org/pep-0817

<!-- prettier-ignore-end -->
