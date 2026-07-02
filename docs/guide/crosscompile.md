# Cross-compiling

Generally scikit-build-core will try to account for environment variables that
specify to CMake directly how to cross-compile. Alternatively, you can define
manually how to cross-compile as detailed in [manual cross compilation] section.

```{tab} macOS

Unlike the other platforms, macOS has the ability to target older operating
systems with the `MACOSX_DEPLOYMENT_TARGET` variable. If that is not set, you
will get a wheel optimized for the current operating system. Popular
redistributable builders like cibuildwheel will set this for you.

**Intel to Apple Silicon:** AppleClang has excellent support for making Apple
Silicon and Universal2 binaries (both architectures in one binary).
Scikit-build-core respects `ARCHFLAGS` if `CMAKE_SYSTEM_PROCESSOR` is not in
the cmake args. These values are set by most redistributable builders like
cibuildwheel when cross-compiling.

:::{note}

If you link to any binaries, they need to be Universal2, so that you get the
Apple Silicon component. This means you cannot use homebrew binaries (which are
always native, and not designed to be used for building portable binaries
anyway). Header-only dependencies, including NumPy, do not need to be
Universal2.

:::

:::{warning}

Scikit-build-core only knows about `MACOSX_DEPLOYMENT_TARGET` and `ARCHFLAGS`;
if you set the target OS version or architectures any other way (CMake allows
several), it won't know and the wheel will not get the correct name.

:::

```

```{tab} Windows

**Intel to ARM:** Scikit-build-core respects setuptools-style
`DIST_EXTRA_CONFIG`. If it is set to a file, then scikit-build-core reads the
`build_ext.library_dirs` paths to find the library to link to. You will also
need to set `SETUPTOOLS_EXT_SUFFIX` to the correct suffix. These values are set
by cibuildwheel when cross-compiling.

```

```{tab} Linux

See [manual cross compilation] section for the general approach.

**Intel to Emscripten (Pyodide):** When using pyodide-build, Python is set up
to report the cross-compiling values by setting `_PYTHON_SYSCONFIGDATA_NAME`.
This causes values like `SOABI` and `EXT_SUFFIX` to be reported by `sysconfig`
as the cross-compiling values.

This is unfortunately incorrectly stripped from the cmake wrapper pyodide uses,
so FindPython will report the wrong values, but pyodide-build will rename the
.so's afterwards.

pyodide-build will also set `_PYTHON_HOST_PLATFORM` to the target Pyodide
platform, so scikit-build-core can use that to compute the correct wheel name.

```

```{tab} Android

To build for Android, you'll need the following items, all of which will be
provided automatically if you use cibuildwheel:

- A Python environment in which `sys.platform`, `sysconfig`, etc. all simulate
  Android.
- A
  [`CMAKE_TOOLCHAIN_FILE`](https://cmake.org/cmake/help/latest/envvar/CMAKE_TOOLCHAIN_FILE.html)
  environment variable, pointing to a file which does at least the following:
  - Set `CMAKE_SYSTEM_NAME`, `CMAKE_SYSTEM_PROCESSOR` and
    `CMAKE_SYSTEM_VERSION`.
  - Set `CMAKE_FIND_ROOT_PATH` to the location of the Python headers and
    libraries.
  - Set `CMAKE_CROSSCOMPILING_EMULATOR` to `/bin/sh -c [["$0" "$@"]]`. This
    allows CMake to run Python in the simulated Android environment when policy
    [CMP0190](https://cmake.org/cmake/help/latest/policy/CMP0190.html) is
    active.
- Compiler paths and flags, either in the toolchain file or in environment
  variables.

```

## Manual cross compilation

The manual cross compilation assumes you have [toolchain file] prepared defining
the cross-compilers and where to search for the target development files,
including the python library. A simple setup of this is to use the clang
compiler and point `CMAKE_SYSROOT` to a mounted copy of the target system's root

```cmake
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)

set(triple aarch64-linux-gnu)

set(CMAKE_C_COMPILER clang)
set(CMAKE_CXX_COMPILER clang++)
set(CMAKE_C_COMPILER_TARGET ${triple})
set(CMAKE_CXX_COMPILER_TARGET ${triple})

set(CMAKE_SYSROOT "/path/to/aarch64/mount/")
```

For more complex environments such as embedded devices, Android or iOS see
CMake's guide on how to write the [toolchain file].

You can pass the toolchain file using the environment variable
`CMAKE_TOOLCHAIN_FILE`, or the `cmake.toolchain-file` pyproject option. You may
also need to use `wheel.tags` to manually specify the wheel tags to use for the
file and `cmake.python-hints = false` if the target python should be detected
using the toolchain file instead.

:::{note}

Because most of the logic in [`FindPython`] is gated by the
`CMAKE_CROSSCOMPILING`, you generally should _not_ include the `Interpreter`
component in the `find_package` command or use the `Python_ARTIFACTS_PREFIX`
feature to distinguish the system and target components.

:::

:::{versionadded} 0.11

:::

### Crossenv

[Crossenv] cross compilation is supported in scikit-build-core. This tool
creates a fake virtual environment where configuration hints such as
`EXT_SUFFIX` are overwritten with the target's values. This should work without
specifying `wheel.tags` overwrites manually.

:::{note}

Because the target Python executable is being faked, the usage of
`CMAKE_CROSSCOMPILING_EMULATOR` for the `Interpreter` would not be correct in
this case.

:::

:::{versionadded} 0.11

:::

[manual cross compilation]: #manual-cross-compilation
[toolchain file]:
  https://cmake.org/cmake/help/latest/manual/cmake-toolchains.7.html#cross-compiling
[crossenv]: https://crossenv.readthedocs.io/en/latest/
[`FindPython`]: https://cmake.org/cmake/help/git-master/module/FindPython.html
