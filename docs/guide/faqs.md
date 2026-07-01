# FAQs

This section covers common needs.

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

## Things to try

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

If you would rather not depend on the paths staying put, make the recorded
paths relocatable with compiler flags — `-fprofile-abs-path` for gcov and
`-ffile-prefix-map=<build>=<src>` (or `-fdebug-prefix-map=...` for debug info
only) — for example via {confval}`cmake.define` or `CFLAGS`.

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
