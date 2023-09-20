# Cross-compiling

## macOS

### Intel to AppleSilicon

On macOS, AppleClang has excellent support for making Apple Silicon and
Universal2 binaries (both architectures in one binary). Scikit-build-core
respects `ARCHFLAGS` if `CMAKE_SYSTEM_PROCESSOR` is not in the cmake args. These
values are set by cibuildwheel when cross-compiling.

:::{warning}

If you link to any binaries, they need to be Universal2, so that you get the
Apple Silicon component. This means you cannot use homebrew binaries (which are
always native, and not designed to be used for building portable binaries
anyway). Header-only dependencies, including NumPy, do not need to be
Universal2.

:::

## Windows

### Intel to ARM

Scikit-build-core respects setuptools-style `DIST_EXTRA_CONFIG`. If is set to a
file, then scikit-build-core reads the `build_ext.library_dirs` paths to find
the library to link to. You will also need to set `SETUPTOOLS_EXT_SUFFIX` to the
correct suffix. These values are set by cibuildwheel when cross-compiling.

## Linux

It should be possible to cross-compile to Linux, but due to the challenges of
getting the manylinux RHEL devtoolkit compilers, this is currently a TODO. See
`py-build-cmake <https://tttapa.github.io/py-build-cmake/Cross-compilation.html>`\_
for an alternative package's usage of toolchain files.

### Intel to Emscripten (Pyodide)

When using pyodide-build, Python is set up to report the cross-compiling values
by setting `_PYTHON_SYSCONFIGDATA_NAME`. This causes values like `SOABI` and
`EXT_SUFFIX` to be reported by `sysconfig` as the cross-compiling values.

This is unfortunately incorrectly stripped from the cmake wrapper pyodide uses,
so FindPython will report the wrong values, but pyodide-build will rename the
.so's afterwards.
